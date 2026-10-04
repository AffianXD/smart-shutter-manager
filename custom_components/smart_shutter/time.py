"""Time-Platform: Time profiles for opening/closing.

Generated (Requirements Document Section 9+10):
  - Global (a common device "Smart Shutter Manager – Global"):
      time.smart_shutter_global_open_werktag / _weekend / _holiday
      time.smart_shutter_global_close_werktag / _weekend / _holiday
  - Local, per shutter (only effective if open_source/close_source
    is set to "Local", see select.py):
      time.<name>_open_workday / _weekend / _holiday
      time.<name>_close_workday / _weekend / _holiday

Note: The Requirements Document refers to the file "datetime.py" - technically
this is however the HA-Platform "time" correct, as we only need times (without date). Home Assistant loads platforms based on the file name, therefore this file is named "time.py"."""
from __future__ import annotations

from datetime import time as time_type
import logging

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ACTIONS,
    DATA_COORDINATOR,
    DEFAULT_TIMES,
    DOMAIN,
    GLOBAL_DEVICE_ID,
    PROFILE_WEEKDAY,
    LEGACY_PROFILE_IDS,
    PROFILES,
    SIGNAL_RECOMPUTE,
)
from .coordinator import ManagedShutter, SmartShutterCoordinator
from .seasons import SEASONS, for_season, has_seasonal_profiles, seed_seasonal_entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Creates global and local time profile entities."""
    coordinator: SmartShutterCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    # Unique global device ID per config entry, so that multiple
    # Integration instances (if someone does create them) do not
    # enter the enclosure.
    global_device_id = f"{GLOBAL_DEVICE_ID}_{entry.entry_id}"

    entities: list[TimeEntity] = []

    # Custom Profiles receive NO own global Time Entity (their
    # the global value is directly embedded in the rule definition, see
    # scheduler.resolve_fixed_time) - only local overrides per shutter,
    # so that a single shutter can deviate if needed.
    custom_profile_ids = [rule["id"] for rule in coordinator.custom_schedules]

    for action in ACTIONS:
        for profile in PROFILES:
            entities.append(
                GlobalProfileTime(coordinator, global_device_id, action, profile)
            )

    for shutter in coordinator.shutters.values():
        for action in ACTIONS:
            for profile in PROFILES:
                entities.append(
                    LocalProfileTime(coordinator, shutter, action, profile)
                )
            for profile in custom_profile_ids:
                entities.append(
                    LocalProfileTime(coordinator, shutter, action, profile)
                )

    if has_seasonal_profiles(coordinator):
        for season in SEASONS:
            for action in ACTIONS:
                for profile in PROFILES:
                    entities.append(for_season(GlobalProfileTime(coordinator, global_device_id, action, profile), season))
            for shutter in coordinator.shutters.values():
                for action in ACTIONS:
                    for profile in PROFILES:
                        entities.append(for_season(LocalProfileTime(coordinator, shutter, action, profile), season))

    async_add_entities(entities)


class _ProfileTimeBase(TimeEntity, RestoreEntity):
    """Common base for global and local time profile entities."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: SmartShutterCoordinator, action: str, profile: str) -> None:
        self._coordinator = coordinator
        self._action = action
        self._profile = profile
        self._registry_key = f"{action}_{profile}"
        self._attr_native_value = self._default_value(coordinator, action, profile)

    @staticmethod
    def _default_value(
        coordinator: SmartShutterCoordinator, action: str, profile: str
    ) -> time_type:
        """Start value for the Time-Entity. For the three built-in profiles from DEFAULT_TIMES, from the already configured time (so a local override starts with the same value as "Global"), otherwise weekday fallback."""
        if (action, profile) in DEFAULT_TIMES:
            return DEFAULT_TIMES[(action, profile)]

        rule = coordinator.get_custom_schedule(profile)
        raw = rule.get(f"{action}_time") if rule else None
        if raw:
            try:
                return time_type.fromisoformat(raw)
            except ValueError:
                pass
        return DEFAULT_TIMES[(action, PROFILE_WEEKDAY)]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        seed_seasonal_entity(self)
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            None,
            "unknown",
            "unavailable",
        ):
            try:
                self._attr_native_value = time_type.fromisoformat(last_state.state)
            except ValueError:
                _LOGGER.debug(
                    'Could not parse stored time value: %s',
                    last_state.state,
                )
        self._register()

    async def async_will_remove_from_hass(self) -> None:
        self._unregister()
        await super().async_will_remove_from_hass()

    async def async_set_value(self, value: time_type) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
        async_dispatcher_send(
            self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}"
        )

    def _register(self) -> None:
        raise NotImplementedError

    def _unregister(self) -> None:
        raise NotImplementedError


class GlobalProfileTime(_ProfileTimeBase):
    """Global time for an action (open/close) + a profile."""

    def __init__(
        self,
        coordinator: SmartShutterCoordinator,
        global_device_id: str,
        action: str,
        profile: str,
    ) -> None:
        super().__init__(coordinator, action, profile)
        self._attr_translation_key = f"global_{action}_{profile}"
        legacy_profile = LEGACY_PROFILE_IDS.get(profile, profile)
        self._attr_unique_id = f"{global_device_id}_{action}_{legacy_profile}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, global_device_id)},
            name="Smart Shutter Manager – Global",
            manufacturer="Smart Shutter Manager",
            model="Global settings",
        )

    def _register(self) -> None:
        self._coordinator.register_global_entity(self._registry_key, self)

    def _unregister(self) -> None:
        self._coordinator.unregister_global_entity(self._registry_key)


class LocalProfileTime(_ProfileTimeBase):
    """Local (individual) time override for a shutter."""

    def __init__(
        self,
        coordinator: SmartShutterCoordinator,
        shutter: ManagedShutter,
        action: str,
        profile: str,
    ) -> None:
        super().__init__(coordinator, action, profile)
        self._shutter = shutter
        if profile in PROFILES:
            self._attr_translation_key = f"local_{action}_{profile}"
        else:
            # Custom Profile: a common, generic translation key
            # per action with placeholder for the (freely selectable) name,
            # instead of having a separate one for each possible custom profile ID
            # translation needed.
            rule = coordinator.get_custom_schedule(profile)
            self._attr_translation_key = f"local_{action}_custom"
            self._attr_translation_placeholders = {
                "profile_name": rule.get("name", profile) if rule else profile
            }
        legacy_profile = LEGACY_PROFILE_IDS.get(profile, profile)
        self._attr_unique_id = f"{shutter.device_id}_{action}_{legacy_profile}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, shutter.device_id)})

    def _register(self) -> None:
        self._coordinator.register_shutter_entity(
            self._shutter.entity_id, self._registry_key, self
        )

    def _unregister(self) -> None:
        self._coordinator.unregister_shutter_entity(
            self._shutter.entity_id, self._registry_key
        )
