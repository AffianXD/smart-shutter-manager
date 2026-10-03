"""Cancellable virtual motion with native Home Assistant cover semantics."""
import asyncio

from homeassistant.components.cover import CoverEntity, CoverEntityFeature


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([VirtualCover("alpha", 20), VirtualCover("beta", 65),
                        VirtualCover("gamma", 100)])


class VirtualCover(CoverEntity):
    _attr_should_poll = False
    _attr_supported_features = (CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE |
                                CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION)

    def __init__(self, key, position):
        self._attr_unique_id = f"codex_ui_test_{key}"
        self._attr_name = f"Codex UI Test {key.title()}"
        self._attr_current_cover_position = position
        self._attr_is_closed = position == 0
        self._attr_is_opening = False
        self._attr_is_closing = False
        self._motion = None
        self._calls = 0

    @property
    def extra_state_attributes(self):
        return {"ui_test_only": True, "control_calls": self._calls}

    async def _stop(self):
        if self._motion is not None:
            self._motion.cancel()
            try:
                await self._motion
            except asyncio.CancelledError:
                pass
            self._motion = None
        self._attr_is_opening = self._attr_is_closing = False

    async def _move(self, target):
        await self._stop()
        self._calls += 1
        position = self._attr_current_cover_position
        self._attr_is_opening = target > position
        self._attr_is_closing = target < position
        self.async_write_ha_state()
        if target != position:
            self._motion = self.hass.async_create_task(self._animate(target))

    async def _animate(self, target):
        try:
            while self._attr_current_cover_position != target:
                await asyncio.sleep(0.1)
                position = self._attr_current_cover_position
                step = min(2, abs(target - position))
                self._attr_current_cover_position += step if target > position else -step
                self._attr_is_closed = self._attr_current_cover_position == 0
                self.async_write_ha_state()
        finally:
            self._attr_is_opening = self._attr_is_closing = False
            self.async_write_ha_state()

    async def async_open_cover(self, **kwargs):
        await self._move(100)

    async def async_close_cover(self, **kwargs):
        await self._move(0)

    async def async_stop_cover(self, **kwargs):
        await self._stop()
        self._calls += 1
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs):
        await self._move(max(0, min(100, int(kwargs["position"]))))

    async def async_will_remove_from_hass(self):
        await self._stop()
