"""Select-Platform: Time source (Global/Local) and trigger type.

Generated (Requirements document Section 6+10+11):
  Global (on device "Smart Shutter Manager – Global"): select.smart_shutter_global_open_typeZZ / _close_type
    (Time/Sunrise or Time/Sunset)
  Per Shutter:
    - select.<name>_open_source  (Global/Local)
    - select.<name>_close_source (Global/Local)
    - select.<name>_open_type    (only effective when source == Local)
    - select.<name>_close_type   (only effective when source == Local)

_source determines whether all (Type + Time/Offset) for an action is read from the global or local entities - see scheduler.py. Thus, z.B can be set globally "Sunset" for all shutters with source "Global" without setting anything per shutter."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ACTION_CLOSE,
    ACTION_OPEN,
    ACTION_TYPE_OPTIONS_BY_ACTION,
    DATA_COORDINATOR,
    DOMAIN,
    GLOBAL_DEVICE_ID,
    LEGACY_PROFILE_IDS,
    PROFILES,
    SIGNAL_RECOMPUTE,
    SOURCE_GLOBAL,
    SOURCE_LOCAL,
    TYPE_SUNRISE,
    TYPE_SUNSET,
    TYPE_TIME,
    position_source_registry_key,
)
from .coordinator import ManagedShutter, SmartShutterCoordinator
from .seasons import SEASONS, for_season, has_seasonal_profiles, seed_seasonal_entity

_LOGGER = logging.getLogger(__name__)

# Restore old language-based states once, then expose stable option keys.
_LEGACY_OPTIONS = {
    "Global": SOURCE_GLOBAL,
    "Individuell": SOURCE_LOCAL,
    "Uhrzeit": TYPE_TIME,
    "Sonnenaufgang": TYPE_SUNRISE,
    "Sonnenuntergang": TYPE_SUNSET,
}


def _type_options_for(action: str) -> list[str]:
    """Return stable option keys for an action."""
    return list(ACTION_TYPE_OPTIONS_BY_ACTION[action])


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Creates global and local source/type selects."""
    coordinator: SmartShutterCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    global_device_id = f"{GLOBAL_DEVICE_ID}_{entry.entry_id}"

    entities: list[SelectEntity] = []

    custom_profile_ids = [rule["id"] for rule in coordinator.custom_schedules]
    all_profiles = list(PROFILES) + custom_profile_ids
    for action in (ACTION_OPEN, ACTION_CLOSE):
        entities.append(GlobalActionTypeSelect(coordinator, global_device_id, action))

    # Diagnosis counters per entity type (see bug report "Source &
    # Goal position not usable" - entities were completely missing from the system,
    # although the same code for trigger type (ShutterSourceSelect)
    # has been proven to work. No errors visible in the logs, no
    # Reproduction step found - this logging should be done at the next
    # Show restart specifically, WHICH constructor for WHICH shutter
    # fails or whether the loop even sees the shutters.
    _LOGGER.debug(
        'Smart Shutter Manager: select setup starts with %d shutter in coordinator.shutters.',
        len(coordinator.shutters),
    )
    created_counts: dict[str, int] = {}
    failed_counts: dict[str, int] = {}

    for shutter in coordinator.shutters.values():
        for action in (ACTION_OPEN, ACTION_CLOSE):
            for cls, label in (
                (ShutterSourceSelect, "ShutterSourceSelect"),
                (PositionSourceSelect, "PositionSourceSelect"),
                (LocalActionTypeSelect, "LocalActionTypeSelect"),
            ):
                try:
                    entities.append(cls(coordinator, shutter, action))
                    created_counts[label] = created_counts.get(label, 0) + 1
                except Exception:  # noqa: BLE001 - keep other select entities available
                    failed_counts[label] = failed_counts.get(label, 0) + 1
                    _LOGGER.exception(
                        'Smart Shutter Manager: %s for %s/%s (Shutter %s) could not be created - will be skipped, the rest of the setup continues.',
                        label,
                        shutter.entity_id,
                        action,
                        shutter.device_id,
                    )
            # Show only profiles that are applicable for THIS shutter
            # ever be active: shared profiles (no
            # area_id) plus private profiles of the areas to which this
            # Shutter belongs to (see determine_active_profile in
            # scheduler.py - private area profiles are applied there
            # anyway only considered for matching shutters; without
            # this filter would still apply to EVERY shutter
            # unused ProfileTimeSourceSelect entities for FOREIGN
            # Area profiles created - confusing v.a. for guests).
            shutter_area_ids = set(coordinator.shutter_areas.get(shutter.entity_id, []))
            shutter_profiles = [
                p
                for p in all_profiles
                if p in PROFILES
                or not (coordinator.get_custom_schedule(p) or {}).get("area_id")
                or (coordinator.get_custom_schedule(p) or {}).get("area_id") in shutter_area_ids
            ]
            for profile in shutter_profiles:
                try:
                    entities.append(
                        ProfileTimeSourceSelect(coordinator, shutter, action, profile)
                    )
                    created_counts["ProfileTimeSourceSelect"] = (
                        created_counts.get("ProfileTimeSourceSelect", 0) + 1
                    )
                except Exception:  # noqa: BLE001
                    failed_counts["ProfileTimeSourceSelect"] = (
                        failed_counts.get("ProfileTimeSourceSelect", 0) + 1
                    )
                    _LOGGER.exception(
                        'Smart Shutter Manager: ProfileTimeSourceSelect for %s/%s/%s could not be created - will be skipped.',
                        shutter.entity_id,
                        action,
                        profile,
                    )

    _LOGGER.debug(
        "Smart Shutter Manager: select-Setup fertig - erstellt: %s, fehlgeschlagen: %s, "
        "gesamt an async_add_entities uebergeben: %d.",
        created_counts,
        failed_counts,
        len(entities),
    )

    if has_seasonal_profiles(coordinator):
        for season in SEASONS:
            for action in (ACTION_OPEN, ACTION_CLOSE):
                entities.append(for_season(GlobalActionTypeSelect(coordinator, global_device_id, action), season))
            for shutter in coordinator.shutters.values():
                for action in (ACTION_OPEN, ACTION_CLOSE):
                    entities.append(for_season(ShutterSourceSelect(coordinator, shutter, action), season))
                    entities.append(for_season(LocalActionTypeSelect(coordinator, shutter, action), season))
                    for profile in PROFILES:
                        entities.append(for_season(ProfileTimeSourceSelect(coordinator, shutter, action, profile), season))

    async_add_entities(entities)


class _RegisteredSelectBase(SelectEntity, RestoreEntity):
    """Common base: Registration in the Coordinator + Change signal."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartShutterCoordinator, registry_key: str) -> None:
        self._coordinator = coordinator
        self._registry_key = registry_key

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        seed_seasonal_entity(self)
        last_state = await self.async_get_last_state()
        if last_state is not None:
            restored = _LEGACY_OPTIONS.get(last_state.state, last_state.state)
            if restored in self._attr_options:
                self._attr_current_option = restored
        self._register()

    async def async_will_remove_from_hass(self) -> None:
        self._unregister()
        await super().async_will_remove_from_hass()

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            _LOGGER.warning('Invalid option %s for %s', option, self.entity_id)
            return
        self._attr_current_option = option
        self.async_write_ha_state()
        # Recalculate sensors AND actual triggers (executor.py)
        async_dispatcher_send(
            self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}"
        )

    def _register(self) -> None:
        raise NotImplementedError

    def _unregister(self) -> None:
        raise NotImplementedError


class ShutterSourceSelect(_RegisteredSelectBase):
    """Choose between global and local profile for opening or closing."""

    _attr_icon = "mdi:swap-horizontal"
    _attr_options = [SOURCE_GLOBAL, SOURCE_LOCAL]

    def __init__(
        self,
        coordinator: SmartShutterCoordinator,
        shutter: ManagedShutter,
        action: str,
    ) -> None:
        super().__init__(coordinator, registry_key=f"{action}_source")
        self._shutter = shutter
        self._action = action
        self._attr_translation_key = f"{action}_source"
        self._attr_unique_id = f"{shutter.device_id}_{action}_source"
        self._attr_current_option = SOURCE_GLOBAL
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, shutter.device_id)})

    @property
    def source(self) -> str:
        """Current value as internal key ('global' or 'local')."""
        return self._attr_current_option

    def _register(self) -> None:
        self._coordinator.register_shutter_entity(
            self._shutter.entity_id, self._registry_key, self
        )

    def _unregister(self) -> None:
        self._coordinator.unregister_shutter_entity(
            self._shutter.entity_id, self._registry_key
        )


class PositionSourceSelect(_RegisteredSelectBase):
    """Choose between global and local target position (0-100%) - independent of ShutterSourceSelect (Trigger-Type/Sun offset) and ProfileTimeSourceSelect (Time per profile)."""

    _attr_icon = "mdi:arrow-expand-vertical"
    _attr_options = [SOURCE_GLOBAL, SOURCE_LOCAL]

    def __init__(
        self,
        coordinator: SmartShutterCoordinator,
        shutter: ManagedShutter,
        action: str,
    ) -> None:
        super().__init__(coordinator, registry_key=position_source_registry_key(action))
        self._shutter = shutter
        self._action = action
        self._attr_translation_key = self._registry_key
        self._attr_unique_id = f"{shutter.device_id}_{self._registry_key}"
        self._attr_current_option = SOURCE_GLOBAL
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, shutter.device_id)})

    @property
    def source(self) -> str:
        """Current value as internal key ('global' or 'local')."""
        return self._attr_current_option

    def _register(self) -> None:
        self._coordinator.register_shutter_entity(
            self._shutter.entity_id, self._registry_key, self
        )

    def _unregister(self) -> None:
        self._coordinator.unregister_shutter_entity(
            self._shutter.entity_id, self._registry_key
        )


class ProfileTimeSourceSelect(_RegisteredSelectBase):
    """Granular local/global selection ONLY for the time of a single
    profile (weekday/weekend/holiday/Custom-XYZ) - independent of
    ShutterSourceSelect, which still controls trigger type + sun offset for
    an action uniformly (across profiles).

    Example: a shutter can use the global time on weekdays,
    but deviate locally during holidays - see
    scheduler._use_local_time_source."""

    _attr_icon = "mdi:calendar-sync"
    _attr_options = [SOURCE_GLOBAL, SOURCE_LOCAL]

    def __init__(
        self,
        coordinator: SmartShutterCoordinator,
        shutter: ManagedShutter,
        action: str,
        profile: str,
    ) -> None:
        super().__init__(coordinator, registry_key=f"{action}_{profile}_time_source")
        self._shutter = shutter
        self._action = action
        self._profile = profile
        self._attr_current_option = SOURCE_GLOBAL
        legacy_profile = LEGACY_PROFILE_IDS.get(profile, profile)
        self._attr_unique_id = f"{shutter.device_id}_{action}_{legacy_profile}_time_source"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, shutter.device_id)})

        if profile in PROFILES:
            self._attr_translation_key = f"{action}_{profile}_time_source"
        else:
            # Custom Profile: generic key + placeholder (see time.py)
            rule = coordinator.get_custom_schedule(profile)
            self._attr_translation_key = f"{action}_custom_time_source"
            self._attr_translation_placeholders = {
                "profile_name": rule.get("name", profile) if rule else profile
            }

    @property
    def source(self) -> str:
        """Current value as internal key ('global' or 'local')."""
        return self._attr_current_option

    def _register(self) -> None:
        self._coordinator.register_shutter_entity(
            self._shutter.entity_id, self._registry_key, self
        )

    def _unregister(self) -> None:
        self._coordinator.unregister_shutter_entity(
            self._shutter.entity_id, self._registry_key
        )


class _ActionTypeSelectBase(_RegisteredSelectBase):
    """Common base for global/local: time/sunrise/sunset"""

    _attr_icon = "mdi:weather-sunset"

    def __init__(self, coordinator: SmartShutterCoordinator, action: str, registry_key: str) -> None:
        super().__init__(coordinator, registry_key)
        self._action = action
        self._attr_options = _type_options_for(action)
        self._attr_current_option = TYPE_TIME

    @property
    def action_type(self) -> str:
        """Current value as internal key ('time'/'sunrise'/'sunset')."""
        return self._attr_current_option


class GlobalActionTypeSelect(_ActionTypeSelectBase):
    """Global trigger type, applies to all shutters with source 'Global'."""

    def __init__(
        self, coordinator: SmartShutterCoordinator, global_device_id: str, action: str
    ) -> None:
        super().__init__(coordinator, action, registry_key=f"{action}_type")
        self._global_device_id = global_device_id
        self._attr_translation_key = f"global_{action}_type"
        self._attr_unique_id = f"{global_device_id}_{action}_type"
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


class LocalActionTypeSelect(_ActionTypeSelectBase):
    """Local (individual) trigger type, only effective when source is 'Local'."""

    def __init__(
        self,
        coordinator: SmartShutterCoordinator,
        shutter: ManagedShutter,
        action: str,
    ) -> None:
        super().__init__(coordinator, action, registry_key=f"{action}_type")
        self._shutter = shutter
        self._attr_translation_key = f"local_{action}_type"
        self._attr_unique_id = f"{shutter.device_id}_{action}_type"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, shutter.device_id)})

    def _register(self) -> None:
        self._coordinator.register_shutter_entity(
            self._shutter.entity_id, self._registry_key, self
        )

    def _unregister(self) -> None:
        self._coordinator.unregister_shutter_entity(
            self._shutter.entity_id, self._registry_key
        )
