"""Smart Shutter Manager – intelligent automation layer for cover.* entities.

See the requirements document for the full range of functions.
This file contains the setup/teardown of the integration including the
SchedulerManager (executor.py) and the two services through which
own automations can intervene (skip_action/postpone_action)."""
from __future__ import annotations

from datetime import time as dt_time
import json
import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ACTION_CLOSE,
    ACTION_OPEN,
    DATA_COORDINATOR,
    DATA_SCHEDULER_MANAGER,
    DOMAIN,
    CONF_HOLIDAY_WEEKDAYS,
    LEGACY_PROFILE_IDS,
    PLATFORMS,
    PROFILES,
    SERVICE_CLEAR_MANUAL_PAUSE,
    SERVICE_CLEAR_OVERRIDE,
    SERVICE_POSTPONE_ACTION,
    SERVICE_SET_EXTERNAL_TRIGGER,
    SERVICE_SKIP_ACTION,
    SIGNAL_RECOMPUTE,
)
from .coordinator import SmartShutterCoordinator
from .executor import SchedulerManager
from .websocket_api import async_register_websocket_commands
from .shutter_management import async_cleanup_removed_shutters

_LOGGER = logging.getLogger(__name__)

_CARD_FILENAME = "smart-shutter-card.js"
_CARD_URL_BASE = f"/{DOMAIN}_frontend/{_CARD_FILENAME}"


def _read_manifest_version() -> str:
    """Reads the version number from manifest.json to append it as a cache-busting query parameter to the map URL (see _CARD_URL_PATH below). Without this, browsers (and possibly a preceding reverse proxy) would continue to serve the old, cached JS file under the same URL after an update - exactly the problem that occurred in v0.10.0."""
    try:
        manifest_path = Path(__file__).parent / "manifest.json"
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f).get("version", "0")
    except Exception:  # noqa: BLE001 - version only controls cache busting
        return "0"


_CARD_URL_PATH = f"{_CARD_URL_BASE}?v={_read_manifest_version()}"
_PANEL_WEBCOMPONENT_NAME = "smart-shutter-panel"
_PANEL_URL_PATH = "smart-shutter"
_PANEL_TITLE = "Shutters"
_PANEL_ICON = "mdi:window-shutter"

_SKIP_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("action", default=ACTION_CLOSE): vol.In([ACTION_OPEN, ACTION_CLOSE]),
        vol.Optional("source"): cv.string,
        vol.Optional("quelle"): cv.string,  # v0.20 compatibility alias
    }
)
_POSTPONE_SCHEMA = _SKIP_SCHEMA.extend(
    {vol.Required("minutes"): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440))}
)
_CLEAR_OVERRIDE_SCHEMA = _SKIP_SCHEMA
_CLEAR_MANUAL_PAUSE_SCHEMA = vol.Schema({vol.Required("entity_id"): cv.entity_id})
_EXTERNAL_TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Required("time"): cv.string,  # "HH:MM" or "HH:MM:SS", see _handle_set_external_trigger
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Sets up a Smart-Shutter-Config-Entry."""
    hass.data.setdefault(DOMAIN, {})

    async_cleanup_removed_shutters(hass, entry)
    coordinator = SmartShutterCoordinator(hass, entry)
    scheduler_manager = SchedulerManager(hass, coordinator)

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_SCHEDULER_MANAGER: scheduler_manager,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Abandoned select/time-Entities of a deleted entity
    # Remove Custom Profiles (config_flow.py) from the Entity Registry,
    # so that they do not remain lying around as "not available".
    _async_cleanup_orphaned_profile_entities(hass, entry, coordinator)

    # All platforms (select/time/number/sensor) are now complete
    # configured - only now can the SchedulerManager meaningfully its
    # Schedule a trigger (it reads select/time/number values beforehand
    # not yet registered). async_start() also loads the
    # Catch-up status (storage.py) and catches up missed actions.
    await scheduler_manager.async_start()

    # An initial signal additionally ensures that the sensors
    # (sensor.py) calculate with fully registered Entities.
    async_dispatcher_send(hass, f"{SIGNAL_RECOMPUTE}_{entry.entry_id}")

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    entry.async_on_unload(scheduler_manager.stop)

    _async_register_services(hass)
    await _async_register_frontend(hass)
    _async_register_websocket_api(hass)

    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Upgrade persisted options before the v0.21 entities are set up."""
    if entry.version > 2:
        return False
    if entry.version == 2:
        return True

    options = dict(entry.options)
    if "ferien_wochentage" in options:
        options[CONF_HOLIDAY_WEEKDAYS] = options.pop("ferien_wochentage")
    hass.config_entries.async_update_entry(entry, options=options, version=2)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Removes a Smart-Shutter config entry again."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reloads the entry when options change (relevant from version 0.2 onward)."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_cleanup_orphaned_profile_entities(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: SmartShutterCoordinator
) -> None:
    """Removes entities that have become orphaned due to configuration changes:

    1. select-/time-entities of a custom profile that has since been deleted
       (see config_flow.py: async_step_custom_schedule_actions ->
       'delete').
    2. The single automatic switch per shutter/global up to v0.6.1,
       replaced by two separate ones (open/close, since v0.6.2).

    Without this cleanup routine, such entities would remain permanently as
    'not available' in the entity registry, because HA does not automatically
    remove dynamic entities from the registry.

    Detection (case 1): The unique IDs generated by select.py/time.py for
    profile-bound entities always have the form
    '{shutter_device_id}_{open|close}_{profile}[_time_source]'. If the
    'profile' part in it is no longer a valid profile (neither one of the
    three built-in ones nor a currently existing custom profile ID), the entity
    is orphaned.

    Deliberately NOT touched: '..._open_source' / '..._open_type' (fixed,
    non-profile-bound selects)."""
    registry = er.async_get(hass)
    valid_profiles = set(PROFILES) | set(LEGACY_PROFILE_IDS.values()) | {
        r["id"] for r in coordinator.custom_schedules
    }
    device_ids = {shutter.device_id for shutter in coordinator.shutters.values()}
    # IMPORTANT: EVERY fixed (not profile-bound) Select-suffix must be listed here
    # registered, otherwise this routine considers it as a
    # orphaned profile and deletes it immediately upon the next restart
    # again (see bug report v0.15.5: "position_source" was missing here,
    # thereby all PositionSourceSelect-entities disappeared system-wide
    # immediately after their creation, without any error message).
    fixed_suffixes = {"source", "type", "position_source"}

    removed = 0
    for reg_entry in list(er.async_entries_for_config_entry(registry, entry.entry_id)):
        if reg_entry.domain == "switch":
            # v0.6.2: the ONE automation switch per shutter/global was
            # replaced by two separate (Open/Close) commands - the
            # old Unique-ID ends exactly on "_automation" (without
            # "_open"/"_close" afterwards), new ones end with "_automation_open"
            # or "_automation_close". Only the EXACT old standalone
            # Case is removed to avoid accidentally matching anything new.
            if reg_entry.unique_id.endswith("_automation"):
                registry.async_remove(reg_entry.entity_id)
                removed += 1
            continue

        if reg_entry.domain not in ("select", "time"):
            continue

        remainder: str | None = None
        for device_id in device_ids:
            for action in (ACTION_OPEN, ACTION_CLOSE):
                marker = f"{device_id}_{action}_"
                if reg_entry.unique_id.startswith(marker):
                    remainder = reg_entry.unique_id[len(marker):]
                    break
            if remainder is not None:
                break

        if remainder is None or remainder in fixed_suffixes:
            continue  # does not belong to our shutter devices, or is a fixed (not profile-bound) Select

        profile = (
            remainder[: -len("_time_source")]
            if remainder.endswith("_time_source")
            else remainder
        )
        if profile in valid_profiles:
            continue

        registry.async_remove(reg_entry.entity_id)
        removed += 1

    if removed:
        _LOGGER.info(
            'Smart Shutter Manager: %d orphaned entity(s) removed (deleted custom profile or outdated automation switch).',
            removed,
        )


def _async_register_services(hass: HomeAssistant) -> None:
    """Registers the services once (regardless of the number of Config Entries) - for own automations/scripts."""
    if hass.services.has_service(DOMAIN, SERVICE_SKIP_ACTION):
        return

    async def _handle_skip(call: ServiceCall) -> None:
        _find_manager_and_run(
            hass, call.data["entity_id"],
            lambda manager: manager.request_skip(
                call.data["entity_id"], call.data["action"],
                call.data.get("source", call.data.get("quelle")),
            ),
        )

    async def _handle_postpone(call: ServiceCall) -> None:
        _find_manager_and_run(
            hass, call.data["entity_id"],
            lambda manager: manager.request_postpone(
                call.data["entity_id"],
                call.data["action"],
                call.data["minutes"],
                call.data.get("source", call.data.get("quelle")),
            ),
        )

    async def _handle_clear_override(call: ServiceCall) -> None:
        _find_manager_and_run(
            hass, call.data["entity_id"],
            lambda manager: manager.request_clear_override(call.data["entity_id"], call.data["action"]),
        )

    async def _handle_clear_manual_pause(call: ServiceCall) -> None:
        _find_manager_and_run(
            hass, call.data["entity_id"],
            lambda manager: manager.request_clear_manual_pause(call.data["entity_id"]),
        )

    async def _handle_set_external_trigger(call: ServiceCall) -> None:
        name = call.data["name"]
        # .strip(): Templates in automations (e.g. "{{ states(...) }}")
        # can create leading/trailing whitespace - time.
        # fromisoformat() is strict and would otherwise do so without reason
        # reject, even though the actual value is valid.
        time_str = str(call.data["time"]).strip()
        try:
            target_time = dt_time.fromisoformat(time_str)
        except ValueError:
            _LOGGER.warning(
                "smart_shutter.set_external_trigger: invalid time '%s' (expected e.g. '07:15' or '07:15:00')",
                time_str,
            )
            return
        _find_manager_by_trigger_name(hass, name, target_time)

    hass.services.async_register(DOMAIN, SERVICE_SKIP_ACTION, _handle_skip, schema=_SKIP_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_POSTPONE_ACTION, _handle_postpone, schema=_POSTPONE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_OVERRIDE, _handle_clear_override, schema=_CLEAR_OVERRIDE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_MANUAL_PAUSE, _handle_clear_manual_pause, schema=_CLEAR_MANUAL_PAUSE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_EXTERNAL_TRIGGER,
        _handle_set_external_trigger,
        schema=_EXTERNAL_TRIGGER_SCHEMA,
    )


def _async_register_websocket_api(hass: HomeAssistant) -> None:
    """Registers the WebSocket commands of the Custom-UI (once per HA process, see websocket_api.py)."""
    if hass.data.get(f"{DOMAIN}_ws_registered"):
        return
    hass.data[f"{DOMAIN}_ws_registered"] = True
    async_register_websocket_commands(hass)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Makes the Custom Lovelace card (www/smart-shutter-card.js) available over a static path - MUST NOT be manually copied to config/www/. Additionally, it registers the Lovelace resource automatically (only works for Dashboards in Storage Mode; for YAML-managed Dashboards, please add manually, see README)."""
    if hass.data.get(f"{DOMAIN}_frontend_registered"):
        return
    hass.data[f"{DOMAIN}_frontend_registered"] = True

    www_path = Path(__file__).parent / "www" / _CARD_FILENAME
    await hass.http.async_register_static_paths(
        [StaticPathConfig(_CARD_URL_BASE, str(www_path), False)]
    )
    _LOGGER.debug("Smart Shutter Manager: frontend card available at %s", _CARD_URL_BASE)

    await _async_register_lovelace_resource(hass)
    await _async_register_panel(hass)


async def _async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Best effort: automatically registers the card as a Lovelace resource
    in the frontend. Can fail (e.g. YAML-managed dashboards, or if
    internal Lovelace data structures have changed between HA versions) -
    this is intentionally not fatal, see README for the manual step as fallback."""
    try:
        lovelace_data = hass.data.get("lovelace")
        resources = getattr(lovelace_data, "resources", None)
        if resources is None and isinstance(lovelace_data, dict):
            resources = lovelace_data.get("resources")
        if resources is None:
            _LOGGER.debug(
                'Smart Shutter Manager: no Lovelace Resource Collection found (maybe YAML-managed dashboards) - please add the resource manually.'
            )
            return

        if not getattr(resources, "loaded", True):
            await resources.async_load()

        for item in resources.async_items():
            if item.get("url", "").split("?")[0] != _CARD_URL_BASE:
                continue
            if item.get("url") == _CARD_URL_PATH:
                return  # already registered on the latest version
            # Replace the old version query so the browser loads the updated card.
            try:
                await resources.async_update_item(item["id"], {"url": _CARD_URL_PATH})
                _LOGGER.info(
                    'Smart Shutter Manager: Lovelace resource updated to new version (%s).',
                    _CARD_URL_PATH,
                )
            except Exception:  # noqa: BLE001 - resource registration is best effort
                _LOGGER.debug(
                    'Smart Shutter Manager: Lovelace resource could not be automatically updated - please change it manually to %s (see README).',
                    _CARD_URL_PATH,
                    exc_info=True,
                )
            return

        await resources.async_create_item({"res_type": "module", "url": _CARD_URL_PATH})
        _LOGGER.info(
            'Smart Shutter Manager: Lovelace resource automatically registered (%s). Clear browser cache if necessary (Ctrl+F5), so that the map appears in the selection dialog.',
            _CARD_URL_PATH,
        )
    except Exception:  # noqa: BLE001 - resource registration is best effort
        _LOGGER.debug(
            'Smart Shutter Manager: Lovelace resource could not be automatically registered - please add it manually (see README): %s',
            _CARD_URL_PATH,
            exc_info=True,
        )


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Registers a custom Sidebar entry ("Shutters"), which displays the map fully (panel_custom) - in addition to the normal use as a map on any dashboard, which still works unchanged. Uses the same JS file/the same static path, only a different custom element class is defined (smart-shutter-panel instead of smart-shutter-card)."""
    try:
        await panel_custom.async_register_panel(
            hass,
            webcomponent_name=_PANEL_WEBCOMPONENT_NAME,
            frontend_url_path=_PANEL_URL_PATH,
            sidebar_title=_PANEL_TITLE,
            sidebar_icon=_PANEL_ICON,
            module_url=_CARD_URL_PATH,
            embed_iframe=False,
            require_admin=False,
        )
        _LOGGER.debug("Smart Shutter Manager: sidebar panel registered (%s)", _PANEL_URL_PATH)
    except ValueError:
        # Panel with this URL already exists (e.g. after a reload) -
        # panel_custom.async_register_panel raises ValueError instead
        # just ignore it. This is not a real error here.
        _LOGGER.debug("Smart Shutter Manager: sidebar panel already registered.")


def _find_manager_and_run(hass: HomeAssistant, entity_id: str, action_fn) -> None:
    """Searches across all Config entries for the SchedulerManager that manages the specified shutter and executes action_fn on it."""
    for entry_data in hass.data.get(DOMAIN, {}).values():
        manager: SchedulerManager = entry_data[DATA_SCHEDULER_MANAGER]
        if action_fn(manager):
            return
    _LOGGER.warning(
        'Smart Shutter Manager: no managed shutter found for %s', entity_id
    )


def _find_manager_by_trigger_name(
    hass: HomeAssistant, name: str, target_time: dt_time
) -> None:
    """Searches across all Config entries for the External Trigger configured in the Options with a matching name and applies the provided target time to its shutter(+action) (see executor.SchedulerManager.request_external_trigger).

Since v0.20.2, a Trigger can reference an entire area instead of a single shutter (trigger["entity_id"]) (trigger["area_id"]) - then the target time is set for ALL shutters in this area, e.g. This allows controlling an entire room through an external automation (alarm clock, presence detection, etc.) instead of just a single window."""
    for entry_data in hass.data.get(DOMAIN, {}).values():
        coordinator: SmartShutterCoordinator = entry_data[DATA_COORDINATOR]
        trigger = coordinator.get_external_trigger_by_name(name)
        if trigger is None:
            continue
        manager: SchedulerManager = entry_data[DATA_SCHEDULER_MANAGER]
        area_id = trigger.get("area_id")
        if area_id:
            member_ids = [
                cover_entity_id
                for cover_entity_id, area_ids in coordinator.shutter_areas.items()
                if area_id in area_ids
            ]
            applied = False
            for cover_entity_id in member_ids:
                if manager.request_external_trigger(
                    cover_entity_id, trigger["action"], target_time,
                    source=f"External trigger: {name}",
                ):
                    applied = True
            if applied:
                return
            continue
        if manager.request_external_trigger(
            trigger["entity_id"], trigger["action"], target_time,
            source=f"External trigger: {name}",
        ):
            return
    _LOGGER.warning(
        "smart_shutter.set_external_trigger: kein Externer Trigger mit "
        "Namen '%s' gefunden (Options Flow -> Externe Trigger verwalten)",
        name,
    )
