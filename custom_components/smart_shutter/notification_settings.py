"""Notification inheritance and validation shared by runtime and WebSocket API."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant


def validate_pre_notify_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Validate the independent closing-warning override for one shutter."""
    mode = settings.get("pre_notify_mode", "inherit")
    if mode not in ("inherit", "off", "custom"):
        raise ValueError("Choose inherit, off, or custom for the closing warning.")
    if mode == "inherit":
        return {}
    result: dict[str, Any] = {"pre_notify_mode": mode}
    if mode == "custom":
        minutes = settings.get("pre_notify_lead_minutes")
        if type(minutes) is not int or not 1 <= minutes <= 1440:
            raise ValueError("Closing-warning lead time must be a whole number from 1 to 1440 minutes.")
        result["pre_notify_lead_minutes"] = minutes
    return result


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
