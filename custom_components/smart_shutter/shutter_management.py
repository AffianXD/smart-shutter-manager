"""Shared cover selection, validation, and cleanup for card and options flow."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import (
    ACTION_CLOSE, ACTION_OPEN, CONF_COVERS, CONF_NAMES, CONF_EXTERNAL_TRIGGERS,
    CONF_SHUTTER_AREAS, CONF_SHUTTER_NOTES, DATA_COORDINATOR,
    DATA_SCHEDULER_MANAGER, DOMAIN, REQUIRED_COVER_FEATURES,
)


@callback
def discover_eligible_covers(hass: HomeAssistant) -> dict[str, str]:
    """Find existing covers with open, close, and stop support."""
    return {
        state.entity_id: f"{state.attributes.get('friendly_name', state.entity_id)} ({state.entity_id})"
        for state in hass.states.async_all("cover")
        if state.attributes.get("supported_features", 0) & REQUIRED_COVER_FEATURES == REQUIRED_COVER_FEATURES
    }


@callback
def available_covers(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, str]:
    """Keep configured covers selectable even while missing or unavailable."""
    covers = discover_eligible_covers(hass)
    for entity_id in entry.data.get(CONF_COVERS, []):
        name = entry.data.get(CONF_NAMES, {}).get(entity_id, entity_id)
        covers.setdefault(entity_id, f"{name} ({entity_id})")
    return covers


@callback
def async_update_covers(hass: HomeAssistant, entry: ConfigEntry, selected: list[str], *, options: dict | None = None) -> None:
    """Validate new covers and preserve configuration for retained covers.

    Entry updates use HA's existing update listener to unload old entities and
    executors before rebuilding the selected set. Empty selections are allowed.
    """
    covers = list(dict.fromkeys(selected))
    available = available_covers(hass, entry)
    if any(entity_id not in available for entity_id in covers):
        raise ValueError("invalid_selection")
    kept = set(covers)
    removed = set(entry.data.get(CONF_COVERS, [])) - kept
    data = {**entry.data, CONF_COVERS: covers, CONF_NAMES: {
        entity_id: name for entity_id, name in entry.data.get(CONF_NAMES, {}).items() if entity_id in kept
    }}
    new_options = dict(entry.options if options is None else options)
    for key in (CONF_SHUTTER_AREAS, CONF_SHUTTER_NOTES):
        if key in new_options:
            new_options[key] = {entity_id: value for entity_id, value in new_options[key].items() if entity_id in kept}
    if CONF_EXTERNAL_TRIGGERS in new_options:
        new_options[CONF_EXTERNAL_TRIGGERS] = [
            trigger for trigger in new_options[CONF_EXTERNAL_TRIGGERS]
            if not trigger.get("entity_id") or trigger["entity_id"] in kept
        ]
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = runtime.get(DATA_COORDINATOR)
    manager = runtime.get(DATA_SCHEDULER_MANAGER)
    for entity_id in removed:
        if coordinator is not None and hasattr(coordinator, "clear_action_override"):
            for action in (ACTION_OPEN, ACTION_CLOSE):
                coordinator.clear_action_override(entity_id, action)
        guard = getattr(manager, "manual_intervention_guard", None)
        if guard is not None:
            guard.clear_pause(entity_id)
    hass.config_entries.async_update_entry(entry, data=data, options=new_options)


@callback
def async_cleanup_removed_shutters(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove only this entry's generated devices/entities after an unload.

    Source cover entities belong to their original integrations. Restrict all
    cleanup to generated shutter device identifiers owned by this config entry.
    """
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    kept = {f"{DOMAIN}_{entity_id}" for entity_id in entry.data.get(CONF_COVERS, [])}
    for device in list(dr.async_entries_for_config_entry(devices, entry.entry_id)):
        identifiers = {value for domain, value in device.identifiers if domain == DOMAIN and value.startswith(f"{DOMAIN}_cover.")}
        if not identifiers or identifiers & kept:
            continue
        for entity in list(er.async_entries_for_config_entry(entities, entry.entry_id)):
            if entity.device_id == device.id:
                entities.async_remove(entity.entity_id)
        # Older HA versions can share a device across config entries.
        owners = getattr(device, "config_entries", {entry.entry_id})
        if set(owners) - {entry.entry_id}:
            devices.async_update_device(device.id, remove_config_entry_id=entry.entry_id)
        else:
            devices.async_remove_device(device.id)
