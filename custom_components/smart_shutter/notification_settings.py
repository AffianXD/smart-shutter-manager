"""Notification inheritance and validation shared by runtime and WebSocket API."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant


def notification_mode(settings: dict[str, Any]) -> str:
    """Keep legacy area recipients effective when no explicit mode is stored."""
    mode = settings.get("notification_mode")
    if mode is None:
        service = settings.get("notify_service")
        return "custom" if isinstance(service, str) and service.strip() else "inherit"
    return mode


def validate_notification_settings(hass: HomeAssistant, settings: dict[str, Any]) -> dict[str, str]:
    """Normalize settings, rejecting invalid modes and unavailable recipients."""
    mode = notification_mode(settings)
    if mode not in ("inherit", "off", "custom"):
        raise ValueError("Choose inherit, off, or custom.")
    service = settings.get("notify_service") or ""
    if not isinstance(service, str):
        raise ValueError("Select a registered notify service.")
    service = service.strip()
    if mode == "custom":
        domain, separator, name = service.partition(".")
        if domain != "notify" or not separator or not name or not hass.services.has_service(domain, name):
            raise ValueError("Select a registered notify service.")
    else:
        service = ""
    return {"notification_mode": mode, "notify_service": service}
