"""Number platform: solar offset (offset), global and per shutter.

Creates (requirements document section 11):
  Global (on device "Smart Shutter Manager – Global"):
    - number.smart_shutter_global_open_sun_offset
    - number.smart_shutter_global_close_sun_offset
  Per shutter (only effective if open_source/close_source == Local):
    - number.<name>_open_sun_offset
    - number.<name>_close_sun_offset

Value range each -120 to +120 minutes."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ACTION_CLOSE,
    ACTION_OPEN,
    DATA_COORDINATOR,
    DEFAULT_POSITION,
    DOMAIN,
    GLOBAL_DEVICE_ID,
    POSITION_MAX,
    POSITION_MIN,
    SIGNAL_RECOMPUTE,
    SUN_OFFSET_DEFAULT,
    SUN_OFFSET_MAX,
    SUN_OFFSET_MIN,
    position_registry_key,
)
from .coordinator import ManagedShutter, SmartShutterCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Creates global and local solar offset entities."""
    coordinator: SmartShutterCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    global_device_id = f"{GLOBAL_DEVICE_ID}_{entry.entry_id}"

    entities: list[NumberEntity] = []

    for action in (ACTION_OPEN, ACTION_CLOSE):
        entities.append(GlobalSunOffsetNumber(coordinator, global_device_id, action))
        entities.append(GlobalPositionNumber(coordinator, global_device_id, action))

    for shutter in coordinator.shutters.values():
        for action in (ACTION_OPEN, ACTION_CLOSE):
            entities.append(LocalSunOffsetNumber(coordinator, shutter, action))
            entities.append(LocalPositionNumber(coordinator, shutter, action))

    async_add_entities(entities)


class _SunOffsetBase(NumberEntity, RestoreEntity):
    """Common base: Offset in minutes (-120..+120), registered in the Coordinator."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:sun-clock"
    _attr_native_min_value = SUN_OFFSET_MIN
    _attr_native_max_value = SUN_OFFSET_MAX
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: SmartShutterCoordinator, action: str, registry_key: str) -> None:
        self._coordinator = coordinator
        self._action = action
        self._registry_key = registry_key
        self._attr_native_value = SUN_OFFSET_DEFAULT

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            None,
            "unknown",
            "unavailable",
        ):
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                pass
        self._register()

    async def async_will_remove_from_hass(self) -> None:
        self._unregister()
        await super().async_will_remove_from_hass()

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
        async_dispatcher_send(
            self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}"
        )

    def _register(self) -> None:
        raise NotImplementedError

    def _unregister(self) -> None:
        raise NotImplementedError


class GlobalSunOffsetNumber(_SunOffsetBase):
    """Global sun offset, applies to shutters with source 'Global'."""

    def __init__(
        self, coordinator: SmartShutterCoordinator, global_device_id: str, action: str
    ) -> None:
        super().__init__(coordinator, action, registry_key=f"{action}_sun_offset")
        self._attr_translation_key = f"global_{self._registry_key}"
        self._attr_unique_id = f"{global_device_id}_{self._registry_key}"
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


class LocalSunOffsetNumber(_SunOffsetBase):
    """Local (individual) solar offset, only effective when source is 'Local'."""

    def __init__(
        self,
        coordinator: SmartShutterCoordinator,
        shutter: ManagedShutter,
        action: str,
    ) -> None:
        super().__init__(coordinator, action, registry_key=f"{action}_sun_offset")
        self._shutter = shutter
        self._attr_translation_key = f"local_{self._registry_key}"
        self._attr_unique_id = f"{shutter.device_id}_{self._registry_key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, shutter.device_id)})

    def _register(self) -> None:
        self._coordinator.register_shutter_entity(
            self._shutter.entity_id, self._registry_key, self
        )

    def _unregister(self) -> None:
        self._coordinator.unregister_shutter_entity(
            self._shutter.entity_id, self._registry_key
        )


class _PositionBase(NumberEntity, RestoreEntity):
    """Common base: Target position in percent (0-100), registered in
    the Coordinator. 100% = fully open, 0% = fully closed -
    the default corresponds to the previous behavior (full open/
    close), until the user consciously sets a different value."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:arrow-expand-vertical"
    _attr_native_min_value = POSITION_MIN
    _attr_native_max_value = POSITION_MAX
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: SmartShutterCoordinator, action: str, registry_key: str) -> None:
        self._coordinator = coordinator
        self._action = action
        self._registry_key = registry_key
        self._attr_native_value = DEFAULT_POSITION[action]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            None,
            "unknown",
            "unavailable",
        ):
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                pass
        self._register()

    async def async_will_remove_from_hass(self) -> None:
        self._unregister()
        await super().async_will_remove_from_hass()

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
        async_dispatcher_send(
            self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}"
        )

    def _register(self) -> None:
        raise NotImplementedError

    def _unregister(self) -> None:
        raise NotImplementedError


class GlobalPositionNumber(_PositionBase):
    """Global target position, applies to shutters with position source 'Global'."""

    def __init__(
        self, coordinator: SmartShutterCoordinator, global_device_id: str, action: str
    ) -> None:
        super().__init__(coordinator, action, registry_key=position_registry_key(action))
        self._attr_translation_key = f"global_{self._registry_key}"
        self._attr_unique_id = f"{global_device_id}_{self._registry_key}"
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


class LocalPositionNumber(_PositionBase):
    """Local (individual) target position, only effective if position source is 'local'."""

    def __init__(
        self,
        coordinator: SmartShutterCoordinator,
        shutter: ManagedShutter,
        action: str,
    ) -> None:
        super().__init__(coordinator, action, registry_key=position_registry_key(action))
        self._shutter = shutter
        self._attr_translation_key = f"local_{self._registry_key}"
        self._attr_unique_id = f"{shutter.device_id}_{self._registry_key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, shutter.device_id)})

    def _register(self) -> None:
        self._coordinator.register_shutter_entity(
            self._shutter.entity_id, self._registry_key, self
        )

    def _unregister(self) -> None:
        self._coordinator.unregister_shutter_entity(
            self._shutter.entity_id, self._registry_key
        )
