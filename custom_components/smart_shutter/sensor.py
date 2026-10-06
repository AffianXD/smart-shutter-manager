"""Sensor-Platform: Status display of Scheduler calculation.

Generated per Shutter (Requirements document Section 15):
  - sensor.<name>_active_profile  ("Workdays" / "Weekends" / "Holiday")
  - sensor.<name>_next_action     (e.g. "Close at 21:30 today")

These sensors do not trigger any movement themselves - they only display what has been calculated. The actual triggering of cover.open_cover/close_cover is taken over since version 0.3 by executor.py, which uses the same scheduler.py calculation (including sun control)."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later, async_track_time_interval
import homeassistant.util.dt as dt_util

from .const import (
    ACTION_OPEN,
    DATA_COORDINATOR,
    DATA_SCHEDULER_MANAGER,
    DOMAIN,
    GLOBAL_DEVICE_ID,
    SIGNAL_RECOMPUTE,
)
from .coordinator import ManagedShutter, SmartShutterCoordinator
from .seasons import seasonal_enabled, season_at
from .localization import display_text, is_german
from .scheduler import ShutterSchedule, compute_global_schedule, compute_schedule
from .temporal_exceptions import applicable_exceptions, is_date_paused

_LOGGER = logging.getLogger(__name__)

_BUILTIN_PROFILES = {"weekday", "weekend", "holiday"}

UPDATE_INTERVAL = timedelta(minutes=1)
STARTUP_SAFETY_DELAY = 5  # Seconds


def _profile_label(coordinator: SmartShutterCoordinator, profile: str) -> str:
    """Display name for an active profile - for the three built-in profiles from _PROFILE_LABELS, for custom profiles the name assigned by the user (instead of the internal ID)."""
    if profile in _BUILTIN_PROFILES:
        return profile
    rule = coordinator.get_custom_schedule(profile)
    return rule["name"] if rule else profile


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Creates the status sensors for all shutters."""
    coordinator: SmartShutterCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    entities: list[SensorEntity] = []
    for shutter in coordinator.shutters.values():
        entities.append(ActiveProfileSensor(coordinator, shutter))
        entities.append(NextActionSensor(coordinator, shutter))

    global_device_id = f"{GLOBAL_DEVICE_ID}_{entry.entry_id}"
    entities.append(GlobalActiveProfileSensor(coordinator, global_device_id))
    entities.append(GlobalNextActionSensor(coordinator, global_device_id))

    async_add_entities(entities)

    @callback
    def _recompute_all(_now=None) -> None:
        for sensor_entity in entities:
            sensor_entity.recompute()

    # Recalculate every 60s (e.g. when midnight changes the profile,
    # (or if the holiday entity changes) - as a fallback. The actual
    # immediate update happens via SIGNAL_RECOMPUTE-Signal
    # (see _BaseScheduleSensor), that select.py/time.py/number.py in
    # send for each change.
    cancel_interval = async_track_time_interval(hass, _recompute_all, UPDATE_INTERVAL)
    entry.async_on_unload(cancel_interval)

    # Security network: recalculate again shortly after start, if the
    # first calculation (async_added_to_hass) ran, before all
    # select-/time-/number-Entities their registration in the Coordinator
    # had completed (platform setup runs partially in parallel).
    cancel_startup = async_call_later(hass, STARTUP_SAFETY_DELAY, _recompute_all)
    entry.async_on_unload(cancel_startup)


class _BaseScheduleSensor(SensorEntity):
    """Common base: Signal listener + Recompute mechanism.
    Subclasses provide via _compute_schedule() either a
    per-shutter or a global calculation."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartShutterCoordinator) -> None:
        self._coordinator = coordinator

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.recompute()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}",
                self._handle_recompute_signal,
            )
        )

    @callback
    def _handle_recompute_signal(self) -> None:
        self.recompute()

    def recompute(self) -> None:
        """Recalculates the schedule and updates the sensor value."""
        schedule = self._compute_schedule()
        self._apply_schedule(schedule)
        if self.hass is not None:
            self.async_write_ha_state()

    def _compute_schedule(self) -> ShutterSchedule:
        raise NotImplementedError

    def _apply_schedule(self, schedule: ShutterSchedule) -> None:
        raise NotImplementedError


class _ShutterScheduleSensor(_BaseScheduleSensor):
    """Base for per-shutter sensors (active_profile/next_action)."""

    def __init__(
        self, coordinator: SmartShutterCoordinator, shutter: ManagedShutter
    ) -> None:
        super().__init__(coordinator)
        self._shutter = shutter
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, shutter.device_id)})

    def _compute_schedule(self) -> ShutterSchedule:
        return compute_schedule(self.hass, self._coordinator, self._shutter)


class _GlobalScheduleSensor(_BaseScheduleSensor):
    """Base for the global preview sensors (on the device 'Global')."""

    def __init__(self, coordinator: SmartShutterCoordinator, global_device_id: str) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, global_device_id)},
            name="Smart Shutter Manager – Global",
            manufacturer="Smart Shutter Manager",
            model="Global settings",
        )
        self._global_device_id = global_device_id

    def _compute_schedule(self) -> ShutterSchedule:
        return compute_global_schedule(self.hass, self._coordinator)


class ActiveProfileSensor(_ShutterScheduleSensor):
    """Displays the currently active time profile (weekday/weekend/holiday)."""

    _attr_translation_key = "active_profile"
    _attr_icon = "mdi:calendar-text"

    def __init__(self, coordinator: SmartShutterCoordinator, shutter: ManagedShutter) -> None:
        super().__init__(coordinator, shutter)
        self._attr_unique_id = f"{shutter.device_id}_active_profile"

    def _apply_schedule(self, schedule: ShutterSchedule) -> None:
        self._attr_native_value = _profile_label(self._coordinator, schedule.active_profile)


class NextActionSensor(_ShutterScheduleSensor):
    """Displays the next calculated action, e.g. 'Closing at 21:30 today.'"""

    _attr_translation_key = "next_action"
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator: SmartShutterCoordinator, shutter: ManagedShutter) -> None:
        super().__init__(coordinator, shutter)
        self._attr_unique_id = f"{shutter.device_id}_next_action"

    def _apply_schedule(self, schedule: ShutterSchedule) -> None:
        _apply_next_action(self, schedule)


class GlobalActiveProfileSensor(_GlobalScheduleSensor):
    """Global preview: active profile according to global settings."""

    _attr_translation_key = "global_active_profile"
    _attr_icon = "mdi:calendar-text"

    def __init__(self, coordinator: SmartShutterCoordinator, global_device_id: str) -> None:
        super().__init__(coordinator, global_device_id)
        self._attr_unique_id = f"{global_device_id}_active_profile"

    def _apply_schedule(self, schedule: ShutterSchedule) -> None:
        self._attr_native_value = _profile_label(self._coordinator, schedule.active_profile)


class GlobalNextActionSensor(_GlobalScheduleSensor):
    """Global preview: next action according to global settings -
    independent of local overrides of individual shutters. Intended for the
    dashboard, to see at a glance what is globally active."""

    _attr_translation_key = "global_next_action"
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator: SmartShutterCoordinator, global_device_id: str) -> None:
        super().__init__(coordinator, global_device_id)
        self._attr_unique_id = f"{global_device_id}_next_action"

    def _apply_schedule(self, schedule: ShutterSchedule) -> None:
        _apply_next_action(self, schedule)


def _apply_next_action(sensor: _BaseScheduleSensor, schedule: ShutterSchedule) -> None:
    """Common formatting for per-shutter and global next_action-Sensor."""
    next_action = schedule.next_action

    debug_attrs = {
        "profile": schedule.active_profile,
        "seasonal_enabled": seasonal_enabled(sensor._coordinator),
        "active_season": season_at(dt_util.now()),
        "next_open": schedule.next_open.isoformat() if schedule.next_open else None,
        "next_close": schedule.next_close.isoformat()
        if schedule.next_close
        else None,
        "open_automation_enabled": schedule.open_automation_enabled,
        "close_automation_enabled": schedule.close_automation_enabled,
    }
    shutter = getattr(sensor, "_shutter", None)
    if shutter is not None:
        active = applicable_exceptions(sensor._coordinator, shutter.entity_id, dt_util.now().date())
        debug_attrs["temporal_exceptions"] = active
        debug_attrs["date_pause_actions"] = sorted({
            action for rule in active if rule["mode"] == "pause" for action in rule["actions"]
        })

    if next_action is None:
        if not schedule.open_automation_enabled and not schedule.close_automation_enabled:
            sensor._attr_native_value = display_text(sensor.hass, "Automation disabled")
        else:
            sensor._attr_native_value = display_text(sensor.hass, "Unknown")
        sensor._attr_extra_state_attributes = debug_attrs
        return

    action, when = next_action
    action_label = "open" if action == ACTION_OPEN else "close"
    days_ahead = (when.date() - dt_util.now().astimezone(when.tzinfo).date()).days
    if days_ahead in (0, 1):
        day_label = display_text(sensor.hass, "Today" if days_ahead == 0 else "Tomorrow")
    else:
        day_label = when.strftime("%d.%m.%Y" if is_german(sensor.hass) else "%Y-%m-%d")

    sensor._attr_native_value = f"{day_label} {when.strftime('%H:%M')} {display_text(sensor.hass, action_label)}"
    sensor._attr_extra_state_attributes = {
        "action": action_label,
        "scheduled_at": when.isoformat(),
        **debug_attrs,
    }

    # Transparency for Bug Diagnosis: an active shifting/skipping-
    # Override (see resolve_next_datetime) always takes precedence over the
    # regular schedule calculation - without visible indication it works as
    # freshly changed individual time incorrectly as if it
    # ignored, although in reality only the older override is still active.
    shutter = getattr(sensor, "_shutter", None)
    if shutter is not None:
        override = sensor._coordinator.get_action_override(shutter.entity_id, action)
        if override is not None and is_date_paused(sensor._coordinator, shutter.entity_id, action, override.date()):
            override = None
        sensor._attr_extra_state_attributes["override_active"] = override is not None
        sensor._attr_extra_state_attributes["override_until"] = (
            override.isoformat() if override is not None else None
        )
        sensor._attr_extra_state_attributes["override_source"] = (
            sensor._coordinator.get_action_override_source(shutter.entity_id, action)
            if override is not None
            else None
        )

        # Transparency for Manual Intervention Detection: was the
        # Automation paused because someone adjusted the shutter independently of
        # did the automation move? Without this hint, it appears as if a
        # skipped action otherwise inexplicable.
        guard = None
        scheduler_manager = sensor.hass.data.get(DOMAIN, {}).get(
            sensor._coordinator.entry.entry_id, {}
        ).get(DATA_SCHEDULER_MANAGER)
        if scheduler_manager is not None:
            guard = scheduler_manager.manual_intervention_guard
        if guard is not None:
            sensor._attr_extra_state_attributes["manual_pause_active"] = guard.is_paused(
                shutter.entity_id
            )
            sensor._attr_extra_state_attributes["manual_pause_until"] = guard.paused_until(
                shutter.entity_id
            )
