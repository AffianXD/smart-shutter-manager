"""Coordinator for Smart Shutter Manager.

The Coordinator manages the selected shutters (ManagedShutter)
and makes them available to the platforms. Since version 0.2, it also serves
as a central registry: the entities created by select.py/time.py register
here, so that scheduler.py can directly access their current values - without
having to go through entity_id-Strings and the state machine lookup."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CATCH_UP_WINDOW,
    CONF_COVERS,
    CONF_CUSTOM_AREAS,
    CONF_CUSTOM_SCHEDULES,
    CONF_TEMPORAL_EXCEPTIONS,
    CONF_SHUTTER_NOTES,
    CONF_EXTERNAL_TRIGGERS,
    CONF_MANUAL_PAUSE_MINUTES,
    CONF_SHUTTER_AREAS,
    CONF_FROST_ENTITY,
    CONF_OUTSIDE_TEMP_SENSOR,
    CONF_INSIDE_TEMP_SENSOR,
    CONF_FROST_THRESHOLD_C,
    DEFAULT_FROST_THRESHOLD_C,
    CONF_HOLIDAY_ENTITY,
    CONF_HOLIDAY_WEEKDAYS,
    DEFAULT_HOLIDAY_WEEKDAYS,
    CONF_STAGGER_DELAY_MS,
    DEFAULT_STAGGER_DELAY_MS,
    CONF_NAMES,
    CONF_NOTIFY_SERVICE,
    CONF_SHUTTER_NOTIFICATIONS,
    CONF_NOTIFY_TEXT_FROST,
    CONF_NOTIFY_TEXT_MOVED,
    CONF_NOTIFY_TEXT_PRECLOSE,
    CONF_NOTIFICATION_MAX_AGE,
    CONF_POSTPONE_OPTIONS,
    CONF_PRE_NOTIFY_LEAD,
    DEFAULT_CATCH_UP_WINDOW_MINUTES,
    DEFAULT_NOTIFY_TEXT_FROST,
    DEFAULT_NOTIFY_TEXT_MOVED,
    DEFAULT_NOTIFY_TEXT_PRECLOSE,
    DEFAULT_MANUAL_PAUSE_MINUTES,
    DEFAULT_NOTIFICATION_MAX_AGE_MINUTES,
    DEFAULT_POSTPONE_OPTIONS_MINUTES,
    DEFAULT_PRE_NOTIFY_LEAD_MINUTES,
    DOMAIN,
)
from .helpers import clean_base_name, get_area_name, get_ha_area_id, find_temperature_sensor_in_area
from .storage import ActionOverrideStore
from .localization import notification_template
from .notification_settings import notification_mode

_LOGGER = logging.getLogger(__name__)


@dataclass
class ManagedShutter:
    """Represents a roller shutter managed by the Smart Shutter Manager.

    entity_id: the existing cover.* entity of the manufacturer integration
    name: display name (e.g. "Living Room"), already cleaned up from redundant "Roller Blind"/"Cover" words
    area: automatically inherited area (Area) from the cover, if available
    device_id: a unique ID for the HA device created by us"""

    entity_id: str
    name: str
    area: str | None = None
    device_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Unique, stable device ID based on the cover entity_id.
        self.device_id = f"{DOMAIN}_{self.entity_id}"


class SmartShutterCoordinator:
    """Maintains the runtime state of a Config Entry (=integration instance)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.options_snapshot = dict(entry.options)
        self.data_snapshot = dict(entry.data)
        self.shutters: dict[str, ManagedShutter] = {}

        # Registry for entities that evaluate scheduler.py:
        # - self.shutter_entities[cover_entity_id][key] = Entity object
        # (key e.g. "open_source", "close_source",
        # "open_werktag", "close_ferien", ...)
        # - self.global_entities[key] = Entity object (global time profiles)
        self.shutter_entities: dict[str, dict[str, Any]] = {}
        self.global_entities: dict[str, Any] = {}

        # Active shift/skip overrides from the warning
        # (executor.py): {cover_entity_id: {aktion: ziel_datetime}}.
        # scheduler.resolve_next_datetime checks this BEFORE the normal
        # Calculation so that sensor.next_action and the Executor are always
        # show the same (possibly shifted) time. An override
        # expires automatically as soon as its time in the
        # The past is history - no manual cleanup is needed.
        self.action_overrides: dict[str, dict[str, Any]] = {}
        # Human-readable source for each active override (e.g. "Notification",
        # "Bulk: All close", "External Trigger: Alarm Clock") - only for the
        # Display in the Override banner on the map, no domain logic is attached.
        self.action_override_sources: dict[str, dict[str, str]] = {}
        self._override_store = ActionOverrideStore(hass, entry.entry_id)

        # Cache: custom area_id -> automatically detected temperature sensor
        # (or None = none found). Is filled lazily and on each
        # Reload (see __init__.py Update-Listener -> new Coordinator)
        # anyway discarded; the reason for the cache is only to keep the registry-
        # Do not search for find_temperature_sensor_in_area in every case
        # Need to re-run the frost protection check.
        self._area_temp_sensor_cache: dict[str, str | None] = {}

        self._load_from_entry()

    async def async_load_overrides(self) -> None:
        """Loads persisted shift/skip overrides (see storage.ActionOverrideStore). MUST be called before the catch-up check (executor.catch_up_if_missed), otherwise a previously skipped event via notification would be incorrectly caught up after a restart."""
        await self._override_store.async_load()
        for shutter_entity_id, action, iso_dt, source in self._override_store.all_items():
            if not iso_dt:
                continue
            try:
                target = datetime.fromisoformat(iso_dt)
            except ValueError:
                continue
            self.action_overrides.setdefault(shutter_entity_id, {})[action] = target
            if source:
                self.action_override_sources.setdefault(shutter_entity_id, {})[action] = source

    def set_action_override(
        self, cover_entity_id: str, action: str, target, source: str | None = None
    ) -> None:
        self.action_overrides.setdefault(cover_entity_id, {})[action] = target
        if source:
            self.action_override_sources.setdefault(cover_entity_id, {})[action] = source
        else:
            self.action_override_sources.get(cover_entity_id, {}).pop(action, None)
        self._override_store.set(cover_entity_id, action, target.isoformat(), source)

    def get_action_override(self, cover_entity_id: str, action: str):
        return self.action_overrides.get(cover_entity_id, {}).get(action)

    def get_action_override_source(self, cover_entity_id: str, action: str) -> str | None:
        return self.action_override_sources.get(cover_entity_id, {}).get(action)

    def clear_action_override(self, cover_entity_id: str, action: str) -> None:
        self.action_overrides.get(cover_entity_id, {}).pop(action, None)
        self.action_override_sources.get(cover_entity_id, {}).pop(action, None)
        self._override_store.clear(cover_entity_id, action)

    def _load_from_entry(self) -> None:
        """Builds the list of ManagedShutter from the Config-Entry data."""
        covers: list[str] = self.entry.data.get(CONF_COVERS, [])
        names: dict[str, str] = self.entry.data.get(CONF_NAMES, {})

        self.shutters = {}
        for cover_entity_id in covers:
            raw_name = names.get(cover_entity_id) or self._fallback_name(
                cover_entity_id
            )
            # Remove redundant words ("Shutter", "Cover", ...) so that
            # later device/entity names do not contain "shutter" twice
            # (e.g. Cover is already called "Roller Shutter Kitchen").
            display_name = clean_base_name(raw_name)
            area = get_area_name(self.hass, cover_entity_id)

            self.shutters[cover_entity_id] = ManagedShutter(
                entity_id=cover_entity_id, name=display_name, area=area
            )
            self.shutter_entities.setdefault(cover_entity_id, {})

        _LOGGER.debug(
            'Coordinator initialized with %d shutters: %s',
            len(self.shutters),
            list(self.shutters.keys()),
        )

    def _fallback_name(self, entity_id: str) -> str:
        """Generates a readable fallback name from the entity_id."""
        state = self.hass.states.get(entity_id)
        if state and state.name:
            return state.name
        return entity_id.split(".", 1)[-1].replace("_", " ").title()

    @property
    def holiday_entity_id(self) -> str | None:
        """The user-selected global holiday entity (Options Flow)."""
        return self.entry.options.get(CONF_HOLIDAY_ENTITY)

    @property
    def holiday_weekdays(self) -> set[int]:
        """Weekdays (Monday=0 to Sunday=6) when the holiday profile applies.

        The default is Monday through Friday; the weekend profile still
        applies on weekends even when the holiday entity is active.
        """
        raw = self.entry.options.get(CONF_HOLIDAY_WEEKDAYS, DEFAULT_HOLIDAY_WEEKDAYS)
        try:
            return {int(v) for v in raw}
        except (TypeError, ValueError):
            return set(int(v) for v in DEFAULT_HOLIDAY_WEEKDAYS)

    @property
    def stagger_delay_ms(self) -> int:
        """Delay in milliseconds between individual commands in multiple actions (RF collision protection, see Options Flow "Scheduled Command Output"). 0 = off (default)."""
        try:
            value = int(self.entry.options.get(CONF_STAGGER_DELAY_MS, DEFAULT_STAGGER_DELAY_MS))
        except (TypeError, ValueError):
            return DEFAULT_STAGGER_DELAY_MS
        return max(0, value)

    def stagger_index(self, cover_entity_id: str) -> int:
        """Stable, deterministic order of all shutters (sorted by entity_id) - basis for the staged command output, so that the same shutter starts at the same position every time (instead of a random dict order)."""
        ordered = sorted(self.shutters.keys())
        try:
            return ordered.index(cover_entity_id)
        except ValueError:
            return 0

    @property
    def frost_entity_id(self) -> str | None:
        """The user-selected frost protection entity (Options Flow).

        State "on" means frost protection active -> no automatic movement
        (Requirements Document Section 14, Priority 2 in Section 13)."""
        return self.entry.options.get(CONF_FROST_ENTITY)

    @property
    def outside_temp_sensor_id(self) -> str | None:
        """Global outdoor temperature sensor (v0.17, Map/Options Flow) -
        flows into both the temperature-based frost protection and,
        as Jinja variable 'outside_temp', into the free additional condition
        of the sun position rule (see sun_position._evaluate_condition)."""
        return self.entry.options.get(CONF_OUTSIDE_TEMP_SENSOR)

    @property
    def inside_temp_sensor_id(self) -> str | None:
        """Global indoor temperature sensor (v0.17) - fallback if
        neither a manually set nor an automatically detected
        area sensor exists (see area_temp_sensor)."""
        return self.entry.options.get(CONF_INSIDE_TEMP_SENSOR)

    @property
    def frost_threshold_c(self) -> float:
        """Global frost protection threshold in °C (v0.17) - Automation
        pauses as soon as the effective inside OR outside temperature falls below
        this value. Overridable per area (area["frost_threshold_c"])."""
        try:
            return float(self.entry.options.get(CONF_FROST_THRESHOLD_C, DEFAULT_FROST_THRESHOLD_C))
        except (TypeError, ValueError):
            return DEFAULT_FROST_THRESHOLD_C

    def area_temp_sensor(self, area: dict[str, Any]) -> str | None:
        """Determines the EFFECTIVE indoor temperature sensor for an area, in this order:
1. Manually configured sensor in the area (area["inside_temp_sensor"]).
2. Automatically detected sensor: if all members of the area share the same HA area (room), it searches for a sensor.* with device_class 'temperature' (see helpers.find_temperature_sensor_in_area). The result is cached per area (also 'none found', to avoid repeated failed registry searches).
3. None - the caller then falls back to the global inside_temp_sensor_id."""
        manual = (area.get("inside_temp_sensor") or "").strip()
        if manual:
            return manual

        area_id = area.get("id")
        if area_id in self._area_temp_sensor_cache:
            return self._area_temp_sensor_cache[area_id]

        members = [
            cover_entity_id
            for cover_entity_id, area_ids in self.shutter_areas.items()
            if area_id in area_ids
        ]
        ha_area_ids = {get_ha_area_id(self.hass, m) for m in members}
        ha_area_ids.discard(None)
        detected: str | None = None
        if len(ha_area_ids) == 1:
            detected = find_temperature_sensor_in_area(self.hass, next(iter(ha_area_ids)))
        self._area_temp_sensor_cache[area_id] = detected
        return detected

    def area_frost_threshold(self, area: dict[str, Any]) -> float:
        """Effective frost protection threshold for an area - local override (area["frost_threshold_c"] if set, otherwise the global value (frost_threshold_c))."""
        override = area.get("frost_threshold_c")
        if override is not None and override != "":
            try:
                return float(override)
            except (TypeError, ValueError):
                pass
        return self.frost_threshold_c

    @property
    def shutter_notifications(self) -> dict[str, dict[str, Any]]:
        """Persisted notification overrides for individual source covers."""
        return self.entry.options.get(CONF_SHUTTER_NOTIFICATIONS, {})

    def effective_notify_service(self, cover_entity_id: str, area: dict[str, Any] | None = None) -> str | None:
        """Resolve shutter -> first explicit area -> global, including explicit off.

        Sun rules pass their triggering area instead of all assigned areas.
        """
        settings = [self.shutter_notifications.get(cover_entity_id, {})]
        settings.extend([area] if area is not None else self.get_shutter_areas(cover_entity_id))
        for setting in settings:
            mode = notification_mode(setting)
            if mode == "off":
                return None
            if mode == "custom":
                return (setting.get("notify_service") or "").strip() or None
        return self.notify_service

    def _read_temp(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    def area_effective_temps(self, area: dict[str, Any]) -> tuple[float | None, float | None]:
        """Returns (inside_temp, outside_temp) for an area - used
        as Jinja variables in the free additional condition of the
        sun position rule (sun_position._evaluate_condition), so the
        user can write '{{ outside_temp > inside_temp }}' instead of a entity_id."""
        inside_sensor = self.area_temp_sensor(area) or self.inside_temp_sensor_id
        return self._read_temp(inside_sensor), self._read_temp(self.outside_temp_sensor_id)

    def is_frost_active_for(self, cover_entity_id: str) -> bool:
        """Central frost protection test for a shutter (v0.17, used by executor._is_frost_active). Combines two independent, each optional paths - one is enough to trigger frost protection:
        1. Classic: a binary_sensor entity (frost_entity_id, since v0.2) is 'on' calculated by the user.
        2. New (v0.17): the effective indoor or outdoor temperature is at or below the effective threshold (per area or global, see area_temp_sensor/area_frost_threshold). A shutter can belong to multiple areas - it's enough if one of them recognizes frost."""
        frost_entity_id = self.frost_entity_id
        if frost_entity_id:
            state = self.hass.states.get(frost_entity_id)
            if state is not None and state.state == "on":
                return True

        areas = self.get_shutter_areas(cover_entity_id)
        if areas:
            for area in areas:
                inside_temp, outside_temp = self.area_effective_temps(area)
                threshold = self.area_frost_threshold(area)
                if inside_temp is not None and inside_temp <= threshold:
                    return True
                if outside_temp is not None and outside_temp <= threshold:
                    return True
            return False

        # No area assigned -> only the global internal sensor + the
        # global thresholds are evaluable.
        inside_temp = self._read_temp(self.inside_temp_sensor_id)
        outside_temp = self._read_temp(self.outside_temp_sensor_id)
        threshold = self.frost_threshold_c
        if inside_temp is not None and inside_temp <= threshold:
            return True
        if outside_temp is not None and outside_temp <= threshold:
            return True
        return False

    @property
    def notify_service(self) -> str | None:
        """Optional notify service (e.g. 'notify.notify'), which notifies when
        actual movements are executed (Options Flow).
        Empty/None = no notifications."""
        return self.entry.options.get(CONF_NOTIFY_SERVICE)

    @property
    def pre_notify_lead(self) -> timedelta:
        """How long before closing the warning comes (Options Flow, Default see const.DEFAULT_PRE_NOTIFY_LEAD_MINUTES)."""
        minutes = self.entry.options.get(
            CONF_PRE_NOTIFY_LEAD, DEFAULT_PRE_NOTIFY_LEAD_MINUTES
        )
        try:
            return timedelta(minutes=float(minutes))
        except (TypeError, ValueError):
            return timedelta(minutes=DEFAULT_PRE_NOTIFY_LEAD_MINUTES)

    @property
    def postpone_options_minutes(self) -> list[int]:
        """Selectable shift options in minutes (Options Flow, e.g. '5,10,15'), Default see const.DEFAULT_POSTPONE_OPTIONS_MINUTES."""
        raw = self.entry.options.get(CONF_POSTPONE_OPTIONS)
        if not raw:
            return list(DEFAULT_POSTPONE_OPTIONS_MINUTES)
        result: list[int] = []
        for part in str(raw).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                result.append(int(part))
            except ValueError:
                _LOGGER.warning('Invalid postpone option ignored: %s', part)
        return result or list(DEFAULT_POSTPONE_OPTIONS_MINUTES)

    @property
    def notification_max_age(self) -> timedelta:
        """How old a warning notification can be at most, so that a button tap (move/skip) is still accepted (options flow, 0 = check disabled). Prevents a tap on an outdated notification from triggering anything."""
        minutes = self.entry.options.get(
            CONF_NOTIFICATION_MAX_AGE, DEFAULT_NOTIFICATION_MAX_AGE_MINUTES
        )
        try:
            return timedelta(minutes=float(minutes))
        except (TypeError, ValueError):
            return timedelta(minutes=DEFAULT_NOTIFICATION_MAX_AGE_MINUTES)

    @property
    def manual_pause_minutes(self) -> int:
        """How long the automation pauses for the affected shutter after a manual intervention is detected (basic settings, 0 = detection disabled)."""
        raw = self.entry.options.get(CONF_MANUAL_PAUSE_MINUTES, DEFAULT_MANUAL_PAUSE_MINUTES)
        try:
            return max(0, int(raw))
        except (TypeError, ValueError):
            return DEFAULT_MANUAL_PAUSE_MINUTES

    @property
    def catch_up_window(self) -> timedelta:
        """How far a restart can be in the past for a missed action to be caught up (Options Flow, Default see const.DEFAULT_CATCH_UP_WINDOW_MINUTES)."""
        minutes = self.entry.options.get(
            CONF_CATCH_UP_WINDOW, DEFAULT_CATCH_UP_WINDOW_MINUTES
        )
        try:
            return timedelta(minutes=float(minutes))
        except (TypeError, ValueError):
            return timedelta(minutes=DEFAULT_CATCH_UP_WINDOW_MINUTES)

    @property
    def notify_text_moved(self) -> str:
        """Jinja-Template for the motion notification (Options Flow).
        Variables: names, count, action, trigger."""
        return notification_template(
            self.hass, CONF_NOTIFY_TEXT_MOVED,
            self.entry.options.get(CONF_NOTIFY_TEXT_MOVED), DEFAULT_NOTIFY_TEXT_MOVED,
        )

    @property
    def notify_text_frost(self) -> str:
        """Jinja-Template for the frost protection notification (Options Flow).
        Variables: names, count."""
        return notification_template(
            self.hass, CONF_NOTIFY_TEXT_FROST,
            self.entry.options.get(CONF_NOTIFY_TEXT_FROST), DEFAULT_NOTIFY_TEXT_FROST,
        )

    @property
    def notify_text_preclose(self) -> str:
        """Jinja-Template for the warning before closing (Options Flow).
        Variables: name, time, action."""
        return notification_template(
            self.hass, CONF_NOTIFY_TEXT_PRECLOSE,
            self.entry.options.get(CONF_NOTIFY_TEXT_PRECLOSE), DEFAULT_NOTIFY_TEXT_PRECLOSE,
        )

    @property
    def temporal_exceptions(self) -> list[dict[str, Any]]:
        """Persisted whole-day pauses and alternate times."""
        return list(self.entry.options.get(CONF_TEMPORAL_EXCEPTIONS, []))

    @property
    def custom_schedules(self) -> list[dict[str, Any]]:
        """List of custom profiles (options flow).

Each entry is a dict according to the structure in const.py (id, name, weekdays, interval_weeks, reference_date, end_date, open_time, close_time). The list is already in priority order (first match wins in case of overlap, see scheduler.determine_active_profile)."""
        raw = self.entry.options.get(CONF_CUSTOM_SCHEDULES, [])
        return list(raw) if isinstance(raw, list) else []

    @property
    def shutter_notes(self) -> dict[str, str]:
        """Free-text notes per shutter (v0.20.1) - typical purpose:
    explain WHY individual settings were chosen for this shutter
    (e.g. position limit instead of full open/close), e.g.
    "Potted plant on the windowsill, do not close below 20%".
    It is displayed in the "Apply to Members" confirmation dialog
    to prevent an individual override from being accidentally
    overwritten without seeing the reason for it."""
        raw = self.entry.options.get(CONF_SHUTTER_NOTES, {})
        return dict(raw) if isinstance(raw, dict) else {}

    def get_shutter_note(self, cover_entity_id: str) -> str:
        return self.shutter_notes.get(cover_entity_id, "")

    def get_custom_schedule(self, profile_id: str) -> dict[str, Any] | None:
        """Finds a custom profile by its ID, or None."""
        for rule in self.custom_schedules:
            if rule.get("id") == profile_id:
                return rule
        return None

    @property
    def external_triggers(self) -> list[dict[str, Any]]:
        """List of custom external triggers (options flow, v0.7). Each entry: id, name, entity_id, action - see const.py for the exact structure."""
        raw = self.entry.options.get(CONF_EXTERNAL_TRIGGERS, [])
        return list(raw) if isinstance(raw, list) else []

    def get_external_trigger_by_name(self, name: str) -> dict[str, Any] | None:
        """Finds an external trigger by its name (case-sensitive exactly), used by the service smart_shutter.set_external_ trigger, so external automations can reference the name instead of an internal ID."""
        for trigger in self.external_triggers:
            if trigger.get("name") == name:
                return trigger
        return None

    @property
    def custom_areas(self) -> list[dict[str, Any]]:
        """List of custom areas (front/back/etc., options flow / map). Structure see const.py."""
        raw = self.entry.options.get(CONF_CUSTOM_AREAS, [])
        return list(raw) if isinstance(raw, list) else []

    def get_custom_area(self, area_id: str) -> dict[str, Any] | None:
        for area in self.custom_areas:
            if area.get("id") == area_id:
                return area
        return None

    @property
    def shutter_areas(self) -> dict[str, list[str]]:
        """Mapping cover_entity_id -> list of area_ids (since v0.16, multiple areas can be controlled simultaneously per shutter, e.g. "Back" AND "Living Areas"). Backward compatible: old persistence structure (single area_id-String instead of list, before v0.16) is automatically converted to a single-element list when read."""
        raw = self.entry.options.get(CONF_SHUTTER_AREAS, {})
        if not isinstance(raw, dict):
            return {}
        result: dict[str, list[str]] = {}
        for cover_entity_id, value in raw.items():
            if isinstance(value, list):
                result[cover_entity_id] = [v for v in value if isinstance(v, str)]
            elif isinstance(value, str):
                result[cover_entity_id] = [value]
            # None/empty values (old "no area" marker) -> shutter
            # simply does not appear in the result, equivalent to an empty list.
        return result

    def get_shutter_areas(self, cover_entity_id: str) -> list[dict[str, Any]]:
        """Returns ALL associated areas for a shutter (may be empty)."""
        area_ids = self.shutter_areas.get(cover_entity_id, [])
        areas = [self.get_custom_area(area_id) for area_id in area_ids]
        return [a for a in areas if a is not None]

    # --- Registry methods, used by select.py / time.py -------------

    def register_shutter_entity(
        self, cover_entity_id: str, key: str, entity_obj: Any
    ) -> None:
        """Register a shutter's local select or time entity."""
        self.shutter_entities.setdefault(cover_entity_id, {})[key] = entity_obj

    def unregister_shutter_entity(self, cover_entity_id: str, key: str) -> None:
        self.shutter_entities.get(cover_entity_id, {}).pop(key, None)

    def register_global_entity(self, key: str, entity_obj: Any) -> None:
        """Enters a global Time-Entity (e.g. 'open_werktag')."""
        self.global_entities[key] = entity_obj

    def unregister_global_entity(self, key: str) -> None:
        self.global_entities.pop(key, None)
