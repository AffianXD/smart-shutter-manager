"""Virtual-only covers for local development; no hardware or network IO."""
from homeassistant.helpers.discovery import async_load_platform


async def async_setup(hass, config):
    await async_load_platform(hass, "cover", "codex_ui_test", {}, config)
    return True
