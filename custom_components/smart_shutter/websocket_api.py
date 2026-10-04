"""WebSocket API for the Custom UI Card (v0.9).

Enables the Lovelace Card (www/smart-shutter-card.js) to read/write all settings directly, which were previously only accessible through the Options Flow Dialog (Basic Settings, Custom Profile, External Triggers, Shutter Names) - without leaving the card.

Uses the same underlying validation/conflict logic as config_flow.py (see scheduler.find_overlapping_rules), so both ways (Options Dialog AND Card) will always provide the exact same result.

All commands require Admin Rights (like the Options Dialog also)."""
from __future__ import annotations

import logging
import re
import uuid

import voluptuous as vol
import homeassistant.util.dt as dt_util

from .seasons import CONF_SEASONAL_ENABLED, prepare_seasonal_options, seasonal_enabled, season_at

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_CATCH_UP_WINDOW,
    CONF_COVERS,
    CONF_CUSTOM_AREAS,
    CONF_CUSTOM_SCHEDULES,
    CONF_EXTERNAL_TRIGGERS,
    CONF_FROST_ENTITY,
    CONF_OUTSIDE_TEMP_SENSOR,
    CONF_INSIDE_TEMP_SENSOR,
    CONF_FROST_THRESHOLD_C,
    DEFAULT_FROST_THRESHOLD_C,
    CONF_HOME_SHORTCUTS,
    CONF_HOLIDAY_ENTITY,
    CONF_MANUAL_PAUSE_MINUTES,
    CONF_NAMES,
    CONF_NOTIFICATION_MAX_AGE,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_TEXT_FROST,
    CONF_NOTIFY_TEXT_MOVED,
    CONF_NOTIFY_TEXT_PRECLOSE,
    CONF_POSTPONE_OPTIONS,
    CONF_PRE_NOTIFY_LEAD,
    CONF_SHUTTER_AREAS,
    CONF_SHUTTER_NOTES,
    CONF_STAGGER_DELAY_MS,
    CUSTOM_AREA_ID_PREFIX,
    CUSTOM_SCHEDULE_ID_PREFIX,
    DATA_COORDINATOR,
    DATA_SCHEDULER_MANAGER,
    DEFAULT_CATCH_UP_WINDOW_MINUTES,
    DEFAULT_CUSTOM_SCHEDULE_INTERVAL_WEEKS,
    DEFAULT_MANUAL_PAUSE_MINUTES,
    DEFAULT_NOTIFICATION_MAX_AGE_MINUTES,
    DEFAULT_STAGGER_DELAY_MS,
    MAX_STAGGER_DELAY_MS,
    DEFAULT_POSTPONE_OPTIONS_MINUTES,
    DEFAULT_PRE_NOTIFY_LEAD_MINUTES,
    DOMAIN,
    EXTERNAL_TRIGGER_ID_PREFIX,
    SIGNAL_RECOMPUTE,
)
from .scheduler import compute_forecast, find_overlapping_rules
from .shutter_management import available_covers, async_update_covers

_LOGGER = logging.getLogger(__name__)

DEFAULT_HOME_SHORTCUTS = [
    {"id": "default-open", "name": "All up", "icon": "mdi:arrow-up-bold-circle-outline", "kind": "cover", "target": "all", "action": "open"},
    {"id": "default-stop", "name": "Stop", "icon": "mdi:stop-circle-outline", "kind": "cover", "target": "all", "action": "stop"},
    {"id": "default-close", "name": "All down", "icon": "mdi:arrow-down-bold-circle-outline", "kind": "cover", "target": "all", "action": "close"},
]
SHORTCUT_NAV_VIEWS = {
    "overview", "list", "settings-areas", "settings-basic", "settings-schedules",
    "settings-triggers", "settings-global", "settings-shutters",
}


def _validate_home_shortcut(shortcut: dict, area_ids: set[str]) -> tuple[dict | None, str | None]:
    """Return a normalized shortcut or a validation error code."""
    raw_id = shortcut.get("id")
    if raw_id is not None and not isinstance(raw_id, str):
        return None, "invalid_id"
    shortcut_id = raw_id or uuid.uuid4().hex[:12]
    raw_name = shortcut.get("name")
    raw_icon = shortcut.get("icon")
    if not isinstance(raw_name, str) or not isinstance(raw_icon, str):
        return None, "invalid_name" if not isinstance(raw_name, str) else "invalid_icon"
    name = raw_name.strip()
    icon = raw_icon.strip()
    kind = shortcut.get("kind")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,48}", shortcut_id):
        return None, "invalid_id"
    if not name or len(name) > 40:
        return None, "invalid_name"
    if len(icon) > 80 or not re.fullmatch(r"mdi:[a-z0-9-]+", icon):
        return None, "invalid_icon"

    if not isinstance(kind, str) or kind not in {"navigate", "cover", "postpone", "skip", "automation"}:
        return None, "invalid_kind"
    normalized = {"id": shortcut_id, "name": name, "icon": icon, "kind": kind}
    if kind == "navigate":
        view = shortcut.get("view")
        if not isinstance(view, str) or view not in SHORTCUT_NAV_VIEWS:
            return None, "invalid_view"
        normalized["view"] = view
        return normalized, None

    target = shortcut.get("target")
    if not isinstance(target, str) or (target != "all" and target not in area_ids):
        return None, "invalid_target"
    normalized["target"] = target
    action = shortcut.get("action")
    if not isinstance(action, str) or action not in ({"open", "close", "stop"} if kind == "cover" else {"open", "close"}):
        return None, "invalid_action"
    normalized["action"] = action
    if kind == "postpone":
        raw_minutes = shortcut.get("minutes")
        if isinstance(raw_minutes, bool) or not isinstance(raw_minutes, (int, str)):
            return None, "invalid_minutes"
        try:
            minutes = int(raw_minutes)
        except ValueError:
            return None, "invalid_minutes"
        if not 1 <= minutes <= 1440:
            return None, "invalid_minutes"
        normalized["minutes"] = minutes
    elif kind == "automation":
        if not isinstance(shortcut.get("enabled"), bool):
            return None, "invalid_enabled"
        normalized["enabled"] = shortcut["enabled"]
    return normalized, None


def _visible_home_shortcuts(shortcuts: list[dict], allowed_area_ids: set[str] | None) -> list[dict]:
    """Hide shortcuts whose target or destination is outside a guest's view."""
    if allowed_area_ids is None:
        return shortcuts
    if not allowed_area_ids:
        return []
    visible = []
    guest_views = {"overview", "list", "settings-areas"}
    for shortcut in shortcuts:
        if shortcut.get("kind") == "navigate":
            if shortcut.get("view") in guest_views:
                visible.append(shortcut)
        elif shortcut.get("target") == "all":
            if shortcut.get("kind") != "automation":
                visible.append(shortcut)
        elif shortcut.get("target") in allowed_area_ids:
            visible.append(shortcut)
    return visible


def _get_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry | None:
    """Returns the specified (or, if none is specified, the first loaded) config entry of the integration."""
    domain_data = hass.data.get(DOMAIN, {})
    if entry_id:
        entry_data = domain_data.get(entry_id)
        if entry_data is None:
            return None
        return entry_data[DATA_COORDINATOR].entry
    for entry_data in domain_data.values():
        return entry_data[DATA_COORDINATOR].entry
    return None


def _notify_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Triggers an immediate recompute signal so sensors/map do not have to wait for the next cycle after a change. The actual reload (rebuild entities) occurs as usual through the existing update listener in __init__.py."""
    async_dispatcher_send(hass, f"{SIGNAL_RECOMPUTE}_{entry.entry_id}")


def _allowed_area_ids(coordinator, connection) -> set[str] | None:
    """Access control for guests (v0.18): Admins are still allowed to do everything as before (None = no restrictions). Non-admin HA users may only see/control the Custom areas that have been explicitly assigned to their HA user ID (area["assigned_ha_user_ids"], see the Area form in the map -> section "Access"). A non-admin user with no assignments at all receives an empty set (nothing).

IMPORTANT: This is ONLY the view/control level within the integration (which areas are provided by get_config, which areas may be modified by save_own_area_settings). The actual movement of the shutters is handled via native cover.*/switch.*-Service calls directly from the map - these are controlled by HA's OWN user/entity permission system (Settings -> People -> Users -> Area access), not by this feature. Without a properly restricted, non-admin HA user role set there, a guest can still move ANY shutter that their HA account has access to - regardless of what is returned here."""
    if connection.user.is_admin:
        return None
    user_id = connection.user.id
    return {
        area["id"]
        for area in coordinator.custom_areas
        if area.get("id") and user_id in (area.get("assigned_ha_user_ids") or [])
    }


def _cover_allowed(coordinator, cover_entity_id: str, allowed_area_ids: set[str] | None) -> bool:
    """True if allowed_area_ids is None (admin, unrestricted) OR the shutter belongs to at least one allowed area."""
    if allowed_area_ids is None:
        return True
    shutter_area_ids = coordinator.shutter_areas.get(cover_entity_id) or []
    return any(a in allowed_area_ids for a in shutter_area_ids)


def _compute_all_conflicts(schedules: list[dict]) -> dict[str, list[str]]:
    """Checks all custom profiles pairwise for overlaps (not just when creating/editing a single one) - basis for the permanently visible conflict display in the map (FR15). Returns {rule_id: [rule_id, ...]} only for profiles that ACTUALLY collide with at least one other."""
    conflicts: dict[str, list[str]] = {}
    for rule in schedules:
        others = [r for r in schedules if r.get("id") != rule.get("id")]
        overlapping = find_overlapping_rules(rule, others)
        if overlapping:
            conflicts[rule["id"]] = [o["id"] for o in overlapping]
    return conflicts


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/get_config",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def handle_get_config(hass, connection, msg):
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    options = entry.options
    shortcuts = options.get(CONF_HOME_SHORTCUTS, DEFAULT_HOME_SHORTCUTS)
    allowed_area_ids = _allowed_area_ids(coordinator, connection)

    if allowed_area_ids is not None and not allowed_area_ids:
        # Non-admin, not assigned to any area -> do not grant access,
        # instead of aborting with a hard error (the map shows
        # instead of a loading error, provide a friendly reminder).
        connection.send_result(
            msg["id"],
            {
                "entry_id": entry.entry_id,
                "restricted": True,
                "shortcuts": _visible_home_shortcuts(shortcuts, allowed_area_ids),
                "basic_settings": {},
                "custom_areas": [],
                "shutter_areas": {},
                "area_auto_temp_sensors": {},
                "custom_schedules": [],
                "schedule_conflicts": {},
                "external_triggers": [],
                "covers": [],
            },
        )
        return

    # Base settings (global sensors, notification service
    # etc.) are host configuration - guests generally receive them
    # not visible, not even for reading (no need for pure
    # Area control, see area_effective_temps/area_auto_temp_sensors
    # further down, which already contain the actually relevant values
    # resolved with delivery).
    basic_settings = (
        {
            "seasonal_enabled": seasonal_enabled(coordinator),
            "holiday_entity": options.get(CONF_HOLIDAY_ENTITY),
            "frost_entity": options.get(CONF_FROST_ENTITY),
            "outside_temp_sensor": options.get(CONF_OUTSIDE_TEMP_SENSOR),
            "inside_temp_sensor": options.get(CONF_INSIDE_TEMP_SENSOR),
            "frost_threshold_c": options.get(CONF_FROST_THRESHOLD_C, DEFAULT_FROST_THRESHOLD_C),
            "notify_service": options.get(CONF_NOTIFY_SERVICE),
            "pre_notify_lead_minutes": options.get(
                CONF_PRE_NOTIFY_LEAD, DEFAULT_PRE_NOTIFY_LEAD_MINUTES
            ),
            "postpone_options_minutes": options.get(CONF_POSTPONE_OPTIONS)
            or ",".join(str(m) for m in DEFAULT_POSTPONE_OPTIONS_MINUTES),
            "catch_up_window_minutes": options.get(
                CONF_CATCH_UP_WINDOW, DEFAULT_CATCH_UP_WINDOW_MINUTES
            ),
            "notification_max_age_minutes": options.get(
                CONF_NOTIFICATION_MAX_AGE, DEFAULT_NOTIFICATION_MAX_AGE_MINUTES
            ),
            "manual_pause_minutes": options.get(
                CONF_MANUAL_PAUSE_MINUTES, DEFAULT_MANUAL_PAUSE_MINUTES
            ),
            "stagger_delay_ms": options.get(CONF_STAGGER_DELAY_MS, DEFAULT_STAGGER_DELAY_MS),
            "notify_text_moved": coordinator.notify_text_moved,
            "notify_text_frost": coordinator.notify_text_frost,
            "notify_text_preclose": coordinator.notify_text_preclose,
        }
        if allowed_area_ids is None
        else {}
    )

    all_covers = [
        {"entity_id": cover_entity_id, "name": shutter.name}
        for cover_entity_id, shutter in coordinator.shutters.items()
    ]
    covers = (
        all_covers
        if allowed_area_ids is None
        else [c for c in all_covers if _cover_allowed(coordinator, c["entity_id"], allowed_area_ids)]
    )
    allowed_cover_ids = {c["entity_id"] for c in covers}

    custom_areas = (
        coordinator.custom_areas
        if allowed_area_ids is None
        else [a for a in coordinator.custom_areas if a.get("id") in allowed_area_ids]
    )
    shutter_areas = (
        coordinator.shutter_areas
        if allowed_area_ids is None
        else {
            cover_entity_id: area_ids
            for cover_entity_id, area_ids in coordinator.shutter_areas.items()
            if cover_entity_id in allowed_cover_ids
        }
    )
    # Time profile: shared (no area_id, weekday/weekend/
    # Holiday-like profiles remain invisible to guests -
    # global and not area-specific, a guest should neither belong to a foreign
    # /Host profile can still be accidentally edited. NEW
    # (v0.19): private area profiles (rule["area_id"] set) are
    # supplied for guests when they are in one of their allowed areas
    # belong - see FEAT "Guests should have everything for their area
    # can be adjusted" + save_own_area_schedules further below as well as
    # scheduler.determine_active_profile (private profiles appear
    # anyway only considered for shutters in the same area).
    custom_schedules = (
        coordinator.custom_schedules
        if allowed_area_ids is None
        else [
            rule
            for rule in coordinator.custom_schedules
            if rule.get("area_id") and rule["area_id"] in allowed_area_ids
        ]
    )
    external_triggers = coordinator.external_triggers if allowed_area_ids is None else []

    # Automatically detected indoor temperature sensors per area (v0.17,
    # see coordinator.area_temp_sensor) - only informative for the map
    # (Hint text "Automatically detected: ..."), does not change the
    # Persistence. Only for areas WITHOUT manually configured sensor
    # relevant at all, but is calculated for all (cheap, no
    # Registry access when the sensor is already set manually).
    area_auto_temp_sensors = {
        area["id"]: coordinator.area_temp_sensor(area)
        for area in custom_areas
        if area.get("id") and not (area.get("inside_temp_sensor") or "").strip()
    }

    shutter_notes = {
        cover_entity_id: note
        for cover_entity_id, note in coordinator.shutter_notes.items()
        if cover_entity_id in allowed_cover_ids
    }

    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "restricted": allowed_area_ids is not None,
            "shortcuts": _visible_home_shortcuts(shortcuts, allowed_area_ids),
            "basic_settings": basic_settings,
            "seasonal_enabled": seasonal_enabled(coordinator),
            "active_season": season_at(dt_util.now()),
            "custom_areas": custom_areas,
            "shutter_areas": shutter_areas,
            "area_auto_temp_sensors": area_auto_temp_sensors,
            "custom_schedules": custom_schedules,
            "schedule_conflicts": _compute_all_conflicts(custom_schedules),
            "external_triggers": external_triggers,
            "covers": covers,
            "shutter_notes": shutter_notes,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/save_basic_settings",
        vol.Optional("entry_id"): str,
        vol.Optional("seasonal_enabled"): bool,
        vol.Optional("holiday_entity"): vol.Any(str, None),
        vol.Optional("frost_entity"): vol.Any(str, None),
        vol.Optional("outside_temp_sensor"): vol.Any(str, None),
        vol.Optional("inside_temp_sensor"): vol.Any(str, None),
        vol.Optional("frost_threshold_c"): vol.Coerce(float),
        vol.Optional("notify_service"): vol.Any(str, None),
        vol.Optional("pre_notify_lead_minutes"): vol.Coerce(int),
        vol.Optional("postpone_options_minutes"): vol.Any(str, None),
        vol.Optional("catch_up_window_minutes"): vol.Coerce(int),
        vol.Optional("notification_max_age_minutes"): vol.Coerce(int),
        vol.Optional("manual_pause_minutes"): vol.Coerce(int),
        vol.Optional("stagger_delay_ms"): vol.Coerce(int),
        vol.Optional("notify_text_moved"): vol.Any(str, None),
        vol.Optional("notify_text_frost"): vol.Any(str, None),
        vol.Optional("notify_text_preclose"): vol.Any(str, None),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def handle_save_basic_settings(hass, connection, msg):
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    data = dict(entry.options)
    if CONF_SEASONAL_ENABLED in msg:
        data[CONF_SEASONAL_ENABLED] = msg[CONF_SEASONAL_ENABLED]
        coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
        prepare_seasonal_options(coordinator, data)

    if "holiday_entity" in msg:
        if msg["holiday_entity"]:
            data[CONF_HOLIDAY_ENTITY] = msg["holiday_entity"]
        else:
            data.pop(CONF_HOLIDAY_ENTITY, None)
    if "frost_entity" in msg:
        if msg["frost_entity"]:
            data[CONF_FROST_ENTITY] = msg["frost_entity"]
        else:
            data.pop(CONF_FROST_ENTITY, None)
    if "outside_temp_sensor" in msg:
        if msg["outside_temp_sensor"]:
            data[CONF_OUTSIDE_TEMP_SENSOR] = msg["outside_temp_sensor"]
        else:
            data.pop(CONF_OUTSIDE_TEMP_SENSOR, None)
    if "inside_temp_sensor" in msg:
        if msg["inside_temp_sensor"]:
            data[CONF_INSIDE_TEMP_SENSOR] = msg["inside_temp_sensor"]
        else:
            data.pop(CONF_INSIDE_TEMP_SENSOR, None)
    if "frost_threshold_c" in msg:
        data[CONF_FROST_THRESHOLD_C] = msg["frost_threshold_c"]
    if "notify_service" in msg:
        value = (msg["notify_service"] or "").strip()
        if value:
            data[CONF_NOTIFY_SERVICE] = value
        else:
            data.pop(CONF_NOTIFY_SERVICE, None)
    if "pre_notify_lead_minutes" in msg:
        data[CONF_PRE_NOTIFY_LEAD] = msg["pre_notify_lead_minutes"]
    if "postpone_options_minutes" in msg:
        value = (msg["postpone_options_minutes"] or "").strip()
        if value:
            data[CONF_POSTPONE_OPTIONS] = value
        else:
            data.pop(CONF_POSTPONE_OPTIONS, None)
    if "catch_up_window_minutes" in msg:
        data[CONF_CATCH_UP_WINDOW] = msg["catch_up_window_minutes"]
    if "notification_max_age_minutes" in msg:
        data[CONF_NOTIFICATION_MAX_AGE] = msg["notification_max_age_minutes"]
    if "manual_pause_minutes" in msg:
        data[CONF_MANUAL_PAUSE_MINUTES] = msg["manual_pause_minutes"]
    if "stagger_delay_ms" in msg:
        data[CONF_STAGGER_DELAY_MS] = max(0, min(MAX_STAGGER_DELAY_MS, msg["stagger_delay_ms"]))
    for key in ("notify_text_moved", "notify_text_frost", "notify_text_preclose"):
        conf_key = {
            "notify_text_moved": CONF_NOTIFY_TEXT_MOVED,
            "notify_text_frost": CONF_NOTIFY_TEXT_FROST,
            "notify_text_preclose": CONF_NOTIFY_TEXT_PRECLOSE,
        }[key]
        if key in msg:
            value = (msg[key] or "").strip()
            if value:
                data[conf_key] = value
            else:
                data.pop(conf_key, None)

    hass.config_entries.async_update_entry(entry, options=data)
    connection.send_result(msg["id"], {"success": True})


def _validate_schedule_shape(rule: dict) -> str | None:
    """Minimal validation of a custom schedule entry (same rules as config_flow.py). Returns an error code, or None if everything matches."""
    if not rule.get("name") or not str(rule["name"]).strip():
        return "no_name"
    if not rule.get("weekdays"):
        return "no_weekdays"
    if not rule.get("open_time") and not rule.get("close_time"):
        return "no_time"
    return None


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/save_custom_schedules",
        vol.Optional("entry_id"): str,
        vol.Required("schedules"): [dict],
        vol.Optional("force", default=False): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def handle_save_custom_schedules(hass, connection, msg):
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    schedules = msg["schedules"]

    # Assign each rule a stable ID if it does not already have one (new
    # created) - same ID assignment as config_flow.py.
    for rule in schedules:
        if not rule.get("id"):
            rule["id"] = f"{CUSTOM_SCHEDULE_ID_PREFIX}{uuid.uuid4().hex[:8]}"

    for rule in schedules:
        error = _validate_schedule_shape(rule)
        if error:
            connection.send_result(
                msg["id"],
                {"success": False, "validation_error": error, "rule_id": rule.get("id")},
            )
            return

    if not msg["force"]:
        conflicts = []
        for i, rule in enumerate(schedules):
            others = schedules[:i] + schedules[i + 1 :]
            overlaps = find_overlapping_rules(rule, others)
            if overlaps:
                conflicts.append(
                    {
                        "rule_id": rule["id"],
                        "rule_name": rule.get("name", rule["id"]),
                        "overlapping_with": [
                            {"id": o["id"], "name": o.get("name", o["id"])} for o in overlaps
                        ],
                    }
                )
        if conflicts:
            connection.send_result(msg["id"], {"success": False, "conflicts": conflicts})
            return

    data = dict(entry.options)
    data[CONF_CUSTOM_SCHEDULES] = schedules
    hass.config_entries.async_update_entry(entry, options=data)
    _notify_reload(hass, entry)
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/save_external_triggers",
        vol.Optional("entry_id"): str,
        vol.Required("triggers"): [dict],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def handle_save_external_triggers(hass, connection, msg):
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    old_triggers = {t["id"]: t for t in coordinator.external_triggers}

    triggers = msg["triggers"]
    names_seen: set[str] = set()
    for trigger in triggers:
        if not trigger.get("id"):
            trigger["id"] = f"{EXTERNAL_TRIGGER_ID_PREFIX}{uuid.uuid4().hex[:8]}"
        name = (trigger.get("name") or "").strip()
        if not name:
            connection.send_result(
                msg["id"], {"success": False, "validation_error": "no_name", "trigger_id": trigger["id"]}
            )
            return
        if name in names_seen:
            connection.send_result(
                msg["id"],
                {"success": False, "validation_error": "duplicate_name", "trigger_id": trigger["id"]},
            )
            return
        names_seen.add(name)
        trigger["name"] = name
        # v0.20.2: entity_id (single shutter) OR area_id (whole
        # Area) - exactly one of the two must be set.
        if not trigger.get("entity_id") and not trigger.get("area_id"):
            connection.send_result(
                msg["id"], {"success": False, "validation_error": "no_entity", "trigger_id": trigger["id"]}
            )
            return
        if trigger.get("entity_id") and trigger.get("area_id"):
            trigger["area_id"] = None

    # For deleted triggers, remove any possibly still active override
    # (otherwise the last set time would remain, even though the
    # associated triggers no longer exist) - same logic as
    # config_flow.py._clear_trigger_override.
    new_ids = {t["id"] for t in triggers}
    for old_id, old_trigger in old_triggers.items():
        if old_id not in new_ids:
            if old_trigger.get("area_id"):
                for cover_entity_id, area_ids in coordinator.shutter_areas.items():
                    if old_trigger["area_id"] in area_ids:
                        coordinator.clear_action_override(cover_entity_id, old_trigger["action"])
            elif old_trigger.get("entity_id"):
                coordinator.clear_action_override(old_trigger["entity_id"], old_trigger["action"])

    data = dict(entry.options)
    data[CONF_EXTERNAL_TRIGGERS] = triggers
    hass.config_entries.async_update_entry(entry, options=data)
    _notify_reload(hass, entry)
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/rename_shutters",
        vol.Optional("entry_id"): str,
        vol.Required("names"): {str: str},
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def handle_rename_shutters(hass, connection, msg):
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    covers = entry.data.get(CONF_COVERS, [])
    names = {
        entity_id: name.strip()
        for entity_id, name in msg["names"].items()
        if entity_id in covers and name and name.strip()
    }

    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_NAMES: names}
    )
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/get_event_history",
        vol.Optional("entry_id"): str,
        vol.Optional("entity_id"): str,
        vol.Optional("limit", default=50): int,
    }
)
@websocket_api.async_response
async def handle_get_event_history(hass, connection, msg):
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    scheduler_manager = hass.data[DOMAIN][entry.entry_id][DATA_SCHEDULER_MANAGER]
    history_store = scheduler_manager.history_store
    if history_store is None:
        connection.send_result(msg["id"], {"events": {}})
        return

    limit = msg.get("limit", 50)
    entity_id = msg.get("entity_id")
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    allowed_area_ids = _allowed_area_ids(coordinator, connection)

    if entity_id:
        if not _cover_allowed(coordinator, entity_id, allowed_area_ids):
            connection.send_error(msg["id"], "unauthorized", "No access to this shutter.")
            return
        events = {entity_id: history_store.get(entity_id, limit)}
    else:
        events = {
            cover_entity_id: history_store.get(cover_entity_id, limit)
            for cover_entity_id in coordinator.shutters
            if _cover_allowed(coordinator, cover_entity_id, allowed_area_ids)
        }

    connection.send_result(msg["id"], {"events": events})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/get_forecast",
        vol.Optional("entry_id"): str,
        vol.Optional("entity_id"): str,
        vol.Optional("days", default=7): vol.All(int, vol.Range(min=1, max=14)),
    }
)
@websocket_api.async_response
async def handle_get_forecast(hass, connection, msg):
    """Forecast timeline (native time-line feature, future part - see compute_forecast in scheduler.py). Provides for each shutter the upcoming open/close terms for the next `days` days. No `entity_id` specified -> for ALL (allowed) shutters (global forecast timeline across the dashboard)."""
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    days = msg.get("days", 7)
    entity_id = msg.get("entity_id")
    allowed_area_ids = _allowed_area_ids(coordinator, connection)

    if entity_id:
        if not _cover_allowed(coordinator, entity_id, allowed_area_ids):
            connection.send_error(msg["id"], "unauthorized", "No access to this shutter.")
            return
        target_ids = [entity_id]
    else:
        target_ids = [
            cid for cid in coordinator.shutters if _cover_allowed(coordinator, cid, allowed_area_ids)
        ]

    forecast: dict[str, list[dict[str, str]]] = {}
    for cover_entity_id in target_ids:
        shutter = coordinator.shutters.get(cover_entity_id)
        if shutter is None:
            continue
        entries = compute_forecast(hass, coordinator, shutter, days)
        forecast[cover_entity_id] = [
            {"action": action, "ts": ts.isoformat()} for action, ts in entries
        ]

    connection.send_result(msg["id"], {"forecast": forecast})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/save_own_area_settings",
        vol.Optional("entry_id"): str,
        vol.Required("area_id"): str,
        vol.Required("fields"): dict,
    }
)
@websocket_api.async_response
async def handle_save_own_area_settings(hass, connection, msg):
    """Allows non-admin users (guests, v0.18) to change the OPERATIONAL
    settings of their own assigned area - e.g.
    for Airbnb/rental properties, where guests should be allowed to set up
    their own shutter automation, without access to other areas or structural
    settings (name, members, user assignment) - handle_save_custom_areas (admin-only)
    remains responsible for that.

    Intentionally only a field whitelist is allowed (see ALLOWED_FIELDS)
    instead of replacing the entire area like handle_save_custom_areas -
    a guest can never accidentally (or maliciously via a manipulated frontend)
    change the id/name/member list/user assignment, even if they send it in the request."""
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    area_id = msg["area_id"]
    allowed_area_ids = _allowed_area_ids(coordinator, connection)
    if allowed_area_ids is not None and area_id not in allowed_area_ids:
        connection.send_error(msg["id"], "unauthorized", "No access to this area.")
        return

    ALLOWED_FIELDS = {
        "open_type", "close_type", "open_sun_offset", "close_sun_offset",
        "open_position", "close_position",
        "sun_position_enabled", "sun_azimuth_from", "sun_azimuth_to",
        "sun_elevation_min", "sun_elevation_hysteresis", "sun_position_target",
        "sun_condition_template", "sun_notify_enabled", "sun_notify_text",
        "sun_prenotify_enabled", "sun_prenotify_lead_minutes", "sun_prenotify_text",
        "inside_temp_sensor", "frost_threshold_c",
        "notify_service",  # v0.20: own notification recipient for this area
    }
    fields = {k: v for k, v in msg["fields"].items() if k in ALLOWED_FIELDS}

    areas = list(coordinator.custom_areas)
    idx = next((i for i, a in enumerate(areas) if a.get("id") == area_id), None)
    if idx is None:
        connection.send_error(msg["id"], "not_found", "Area not found.")
        return

    areas[idx] = {**areas[idx], **fields}
    data = dict(entry.options)
    data[CONF_CUSTOM_AREAS] = areas
    hass.config_entries.async_update_entry(entry, options=data)
    _notify_reload(hass, entry)
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/save_own_area_schedules",
        vol.Optional("entry_id"): str,
        vol.Required("area_id"): str,
        vol.Required("schedules"): [dict],
        vol.Optional("force", default=False): bool,
    }
)
@websocket_api.async_response
async def handle_save_own_area_schedules(hass, connection, msg):
    """Private, area-specific time plan profiles (v0.19) - counterpart to handle_save_custom_schedules (admin-only, shared profiles for the entire installation). With this, guests (or the admin for them) can create their own weekday/weekend/holiday-like rules only for their own area without touching the shared profiles of the installation or other areas.

Replaces (like handle_save_own_area_settings) only the rules belonging to this area, not the entire custom_schedules-Liste - all shared as well as foreign area-related rules remain untouched, even if they are missing in the accompanying `fields`/`schedules`-payload. `area_id` is enforced server-side (never taken from the request), so a guest can never assign a rule to another area.

Effectiveness is already structurally restricted to the own area: scheduler.determine_active_profile() considers a profile with set area_id only for shutters belonging to this area - a private profile can never accidentally influence host- or neighbor-area shutters, not even in case of a bug in the UI."""
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    area_id = msg["area_id"]
    allowed_area_ids = _allowed_area_ids(coordinator, connection)
    if allowed_area_ids is not None and area_id not in allowed_area_ids:
        connection.send_error(msg["id"], "unauthorized", "No access to this area.")
        return
    if not coordinator.get_custom_area(area_id):
        connection.send_error(msg["id"], "not_found", "Area not found.")
        return

    new_area_schedules = msg["schedules"]
    for rule in new_area_schedules:
        rule["area_id"] = area_id  # enforced server-side, see Docstring
        if not rule.get("id"):
            rule["id"] = f"{CUSTOM_SCHEDULE_ID_PREFIX}{uuid.uuid4().hex[:8]}"

    for rule in new_area_schedules:
        error = _validate_schedule_shape(rule)
        if error:
            connection.send_result(
                msg["id"],
                {"success": False, "validation_error": error, "rule_id": rule.get("id")},
            )
            return

    # Rules from OTHER areas + shared rules remain unchanged -
    # only the excerpt for 'area_id' is replaced.
    other_schedules = [r for r in coordinator.custom_schedules if r.get("area_id") != area_id]

    if not msg["force"]:
        conflicts = []
        for i, rule in enumerate(new_area_schedules):
            others_for_check = (
                other_schedules + new_area_schedules[:i] + new_area_schedules[i + 1 :]
            )
            overlaps = find_overlapping_rules(rule, others_for_check)
            if overlaps:
                conflicts.append(
                    {
                        "rule_id": rule["id"],
                        "rule_name": rule.get("name", rule["id"]),
                        "overlapping_with": [
                            {"id": o["id"], "name": o.get("name", o["id"])} for o in overlaps
                        ],
                    }
                )
        if conflicts:
            connection.send_result(msg["id"], {"success": False, "conflicts": conflicts})
            return

    merged_schedules = other_schedules + new_area_schedules
    data = dict(entry.options)
    data[CONF_CUSTOM_SCHEDULES] = merged_schedules
    hass.config_entries.async_update_entry(entry, options=data)
    _notify_reload(hass, entry)
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/save_custom_areas",
        vol.Optional("entry_id"): str,
        vol.Required("areas"): [dict],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def handle_save_custom_areas(hass, connection, msg):
    """Saves the list of custom areas (front/back/etc.).
    Deleting an area does not automatically clean up the assignment of affected shutters in handle_save_shutter_areas - the map simply filters out orphaned area_ids when displayed (see smart-shutter-card.js _model.shutterArea)."""
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    areas = msg["areas"]
    for area in areas:
        if not area.get("id"):
            area["id"] = f"{CUSTOM_AREA_ID_PREFIX}{uuid.uuid4().hex[:8]}"
        if not area.get("name") or not str(area["name"]).strip():
            connection.send_result(
                msg["id"], {"success": False, "validation_error": "no_name", "area_id": area.get("id")}
            )
            return

    data = dict(entry.options)
    data[CONF_CUSTOM_AREAS] = areas
    hass.config_entries.async_update_entry(entry, options=data)
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/save_shortcuts",
        vol.Optional("entry_id"): str,
        vol.Required("shortcuts"): [dict],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def handle_save_shortcuts(hass, connection, msg):
    """Persist the shared, ordered dashboard shortcuts for one config entry."""
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    area_ids = {
        area.get("id")
        for area in entry.options.get(CONF_CUSTOM_AREAS, [])
        if area.get("id")
    }
    normalized = []
    ids = set()
    for shortcut in msg["shortcuts"]:
        item, error = _validate_home_shortcut(shortcut, area_ids)
        if error:
            connection.send_result(msg["id"], {"success": False, "validation_error": error})
            return
        if item["id"] in ids:
            connection.send_result(msg["id"], {"success": False, "validation_error": "duplicate_id"})
            return
        ids.add(item["id"])
        normalized.append(item)

    data = dict(entry.options)
    data[CONF_HOME_SHORTCUTS] = normalized
    hass.config_entries.async_update_entry(entry, options=data)
    connection.send_result(msg["id"], {"success": True, "shortcuts": normalized})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/save_shutter_areas",
        vol.Optional("entry_id"): str,
        vol.Required("shutter_areas"): {str: vol.Any([str], str, None)},
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def handle_save_shutter_areas(hass, connection, msg):
    """Saves the shutter -> area assignment. Since v0.16, a shutter can belong to multiple areas at the same time (e.g. "Back" AND "Living rooms") - hence a list instead of a single value.
    Also takes a single area_id-String or None for downward compatibility and normalizes it to a list (or removes the shutter completely if it's in no area anymore)."""
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    covers = entry.data.get(CONF_COVERS, [])
    shutter_areas: dict[str, list[str]] = {}
    for entity_id, value in msg["shutter_areas"].items():
        if entity_id not in covers:
            continue
        if isinstance(value, list):
            area_ids = [v for v in value if v]
        elif value:
            area_ids = [value]
        else:
            area_ids = []
        if area_ids:
            shutter_areas[entity_id] = area_ids

    data = dict(entry.options)
    data[CONF_SHUTTER_AREAS] = shutter_areas
    hass.config_entries.async_update_entry(entry, options=data)
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "smart_shutter/save_shutter_note",
        vol.Optional("entry_id"): str,
        vol.Required("entity_id"): str,
        vol.Required("note"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def handle_save_shutter_note(hass, connection, msg):
    """Free-text note for a single shutter (v0.20.1) - typical purpose: explain why individual settings (e.g. a position limit instead of full open/close) were chosen for this shutter. It is displayed in the confirmation dialog of "Apply to Members" so that an individual override is not accidentally overwritten without knowing the reason.

Not admin-only: anyone who has access to the area of the shutter (or is an admin) may maintain the note for this specific shutter - aligns with the principle that "guests should be able to set everything for their area"."""
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return

    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entity_id = msg["entity_id"]
    allowed_area_ids = _allowed_area_ids(coordinator, connection)
    if not _cover_allowed(coordinator, entity_id, allowed_area_ids):
        connection.send_error(msg["id"], "unauthorized", "No access to this shutter.")
        return

    notes = dict(coordinator.shutter_notes)
    note = (msg.get("note") or "").strip()
    if note:
        notes[entity_id] = note
    else:
        notes.pop(entity_id, None)

    data = dict(entry.options)
    data[CONF_SHUTTER_NOTES] = notes
    hass.config_entries.async_update_entry(entry, options=data)
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command({
    vol.Required("type"): "smart_shutter/get_available_covers",
    vol.Optional("entry_id"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
async def handle_get_available_covers(hass, connection, msg):
    """Return supported and already configured covers for the management UI."""
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return
    connection.send_result(msg["id"], {
        "entry_id": entry.entry_id,
        "covers": [{"entity_id": entity_id, "name": label} for entity_id, label in available_covers(hass, entry).items()],
        "selected": list(entry.data.get(CONF_COVERS, [])),
        "names": dict(entry.data.get(CONF_NAMES, {})),
    })


@websocket_api.websocket_command({
    vol.Required("type"): "smart_shutter/save_covers",
    vol.Optional("entry_id"): str,
    vol.Required("covers"): [str],
    vol.Optional("names"): {str: str},
})
@websocket_api.require_admin
@websocket_api.async_response
async def handle_save_covers(hass, connection, msg):
    """Update the managed set; HA's update listener rebuilds the entities."""
    entry = _get_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Shutter Manager config entry not found.")
        return
    try:
        async_update_covers(hass, entry, msg["covers"], names=msg.get("names"))
    except ValueError:
        connection.send_error(msg["id"], "invalid_selection", "Select supported cover entities.")
        return
    connection.send_result(msg["id"], {"success": True})


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Registers all WebSocket commands of the Custom UI (once per HA process, regardless of the number of Config Entries)."""
    websocket_api.async_register_command(hass, handle_get_available_covers)
    websocket_api.async_register_command(hass, handle_save_covers)
    websocket_api.async_register_command(hass, handle_get_config)
    websocket_api.async_register_command(hass, handle_save_basic_settings)
    websocket_api.async_register_command(hass, handle_save_custom_schedules)
    websocket_api.async_register_command(hass, handle_save_external_triggers)
    websocket_api.async_register_command(hass, handle_rename_shutters)
    websocket_api.async_register_command(hass, handle_get_event_history)
    websocket_api.async_register_command(hass, handle_get_forecast)
    websocket_api.async_register_command(hass, handle_save_custom_areas)
    websocket_api.async_register_command(hass, handle_save_shortcuts)
    websocket_api.async_register_command(hass, handle_save_shutter_areas)
    websocket_api.async_register_command(hass, handle_save_own_area_settings)
    websocket_api.async_register_command(hass, handle_save_own_area_schedules)
    websocket_api.async_register_command(hass, handle_save_shutter_note)
