"""Switch Platform: Automatic status per shutter + global master switch.

Creates a separate HA device for each managed shutter with a translated name (Section 5 of the requirements document) with one automatic switch for opening AND one for closing (separated since v0.6.2, on user request - previously there was only one common switch for both directions).

In addition (on user request): two global master switches (opening/closing separated) on the device "Smart Shutter Manager – Global", which can deactivate all shutters at once for the respective direction without having to access each individually.

Priority 3 from Section 13: If the automation is disabled for a direction (local OR global), executor.py will no longer trigger an automatic movement for EXACTLY THIS direction - the other direction remains unaffected, as does manual operation. Both switch types register themselves in the Coordinator, so executor.py can query their state directly."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
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
    DOMAIN,
    GLOBAL_DEVICE_ID,
    SIGNAL_RECOMPUTE,
    automation_registry_key,
    global_automation_registry_key,
)
from .coordinator import ManagedShutter, SmartShutterCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Creates the automation switches (open + close separated) for all shutters + the two global master switches."""
    coordinator: SmartShutterCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    global_device_id = f"{GLOBAL_DEVICE_ID}_{entry.entry_id}"

    entities: list[SwitchEntity] = [
        GlobalAutomationSwitch(coordinator, global_device_id, action)
        for action in (ACTION_OPEN, ACTION_CLOSE)
    ]
    for shutter in coordinator.shutters.values():
        for action in (ACTION_OPEN, ACTION_CLOSE):
            entities.append(ShutterAutomationSwitch(coordinator, shutter, action))

    async_add_entities(entities)


class ShutterAutomationSwitch(SwitchEntity, RestoreEntity):
    """Turns the automation of one direction (open OR close)
    of a single shutter on/off."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self, coordinator: SmartShutterCoordinator, shutter: ManagedShutter, action: str
    ) -> None:
        self._coordinator = coordinator
        self._shutter = shutter
        self._action = action
        self._registry_key = automation_registry_key(action)
        self._attr_translation_key = self._registry_key
        self._attr_unique_id = f"{shutter.device_id}_{self._registry_key}"
        self._attr_is_on = True  # Standard: Automatic mode active

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, shutter.device_id)},
            translation_key="managed_shutter",
            translation_placeholders={"name": shutter.name},
            manufacturer="Smart Shutter Manager",
            model="Managed Shutter",
            suggested_area=shutter.area,
        )

    async def async_added_to_hass(self) -> None:
        """Restores the last state after a restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"

        self._coordinator.register_shutter_entity(
            self._shutter.entity_id, self._registry_key, self
        )

    async def async_will_remove_from_hass(self) -> None:
        self._coordinator.unregister_shutter_entity(
            self._shutter.entity_id, self._registry_key
        )
        await super().async_will_remove_from_hass()

    async def async_turn_on(self, **kwargs) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()
        async_dispatcher_send(
            self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}"
        )

    async def async_turn_off(self, **kwargs) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
        async_dispatcher_send(
            self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}"
        )


class GlobalAutomationSwitch(SwitchEntity, RestoreEntity):
    """Global master switch for ONE direction (open OR close):
    OFF disables the automation for this direction for ALL shutters
    at once, regardless of their individual switches."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-remove"

    def __init__(
        self, coordinator: SmartShutterCoordinator, global_device_id: str, action: str
    ) -> None:
        self._coordinator = coordinator
        self._action = action
        self._registry_key = global_automation_registry_key(action)
        self._attr_translation_key = self._registry_key
        self._attr_unique_id = f"{global_device_id}_{self._registry_key}"
        # New installations require an explicit per-direction activation in
        # the onboarding guide. RestoreEntity keeps established choices intact.
        self._attr_is_on = False

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, global_device_id)},
            name="Smart Shutter Manager – Global",
            manufacturer="Smart Shutter Manager",
            model="Global settings",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"

        self._coordinator.register_global_entity(self._registry_key, self)

    async def async_will_remove_from_hass(self) -> None:
        self._coordinator.unregister_global_entity(self._registry_key)
        await super().async_will_remove_from_hass()

    async def async_turn_on(self, **kwargs) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()
        async_dispatcher_send(
            self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}"
        )

    async def async_turn_off(self, **kwargs) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
        async_dispatcher_send(
            self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}"
        )
