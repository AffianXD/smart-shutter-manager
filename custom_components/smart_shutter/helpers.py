"""Common helper functions for Smart Shutter Manager."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import template as template_helper

_LOGGER = logging.getLogger(__name__)


def render_notify_template(
    hass: HomeAssistant, template_str: str, variables: dict, fallback: str
) -> str:
    """Render a user-defined notification template with a safe fallback.

    Keep this helper here so the executor and sun position module can share
    it without a circular import.
    """
    try:
        rendered = template_helper.Template(template_str, hass).async_render(
            variables, parse_result=False
        )
        return str(rendered)
    except Exception:  # noqa: BLE001 - a user template must not stop notifications
        _LOGGER.exception("Notification template failed; using default text: %s", template_str)
        return fallback


# Remove generic cover terms before appending "shutter" to device names.
_REDUNDANT_WORDS = {"rollladen", "rolladen", "cover", "shutter"}


def clean_base_name(name: str) -> str:
    """Removes redundant shutter/cover terms from a name.

    "Rollladen Küche" -> "Küche"
    "Küche Rollladen"  -> "Küche"
    "Büro"              -> "Büro" (unchanged)"""
    words = [w for w in name.split() if w.lower() not in _REDUNDANT_WORDS]
    cleaned = " ".join(words).strip(" -_")
    return cleaned or name


def get_ha_area_id(hass: HomeAssistant, entity_id: str) -> str | None:
    """Like get_area_name(), but returns the HA internal area ID instead of the display name - basis for automatic temperature sensor detection (see find_temperature_sensor_in_area)."""
    ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get(entity_id)
    if entity_entry is None:
        return None

    area_id = entity_entry.area_id
    if area_id is None and entity_entry.device_id:
        dev_reg = dr.async_get(hass)
        device_entry = dev_reg.async_get(entity_entry.device_id)
        if device_entry:
            area_id = device_entry.area_id
    return area_id


def find_temperature_sensor_in_area(hass: HomeAssistant, ha_area_id: str | None) -> str | None:
    """Searches for the first sensor.*-Entity with device_class 'temperature' that is assigned to the same HA area as ha_area_id (directly or through its device) - for automatic indoor temperature detection in custom areas (v0.17) when no sensor is manually set. In case of multiple hits, a deterministic choice is made alphabetically for the first one. Only finds sensors whose device_class is registered in the entity registry (standard case for most integrations)."""
    if ha_area_id is None:
        return None
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    candidates: list[str] = []
    for entity_entry in ent_reg.entities.values():
        if not entity_entry.entity_id.startswith("sensor."):
            continue
        device_class = entity_entry.device_class or entity_entry.original_device_class
        if device_class != "temperature":
            continue
        entity_area_id = entity_entry.area_id
        if entity_area_id is None and entity_entry.device_id:
            device_entry = dev_reg.async_get(entity_entry.device_id)
            if device_entry:
                entity_area_id = device_entry.area_id
        if entity_area_id == ha_area_id:
            candidates.append(entity_entry.entity_id)
    candidates.sort()
    return candidates[0] if candidates else None


def get_area_name(hass: HomeAssistant, entity_id: str) -> str | None:
    """Determines the area (Area) of an entity - directly or via its device.

Used to automatically take over the area during initial setup and thus save manual configuration effort."""
    ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get(entity_id)
    if entity_entry is None:
        return None

    area_id = entity_entry.area_id
    if area_id is None and entity_entry.device_id:
        dev_reg = dr.async_get(hass)
        device_entry = dev_reg.async_get(entity_entry.device_id)
        if device_entry:
            area_id = device_entry.area_id

    if area_id is None:
        return None

    area_reg = ar.async_get(hass)
    area_entry = area_reg.async_get_area(area_id)
    return area_entry.name if area_entry else None
