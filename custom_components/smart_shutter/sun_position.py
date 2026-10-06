"""Apply area-specific sun position rules (v0.13).

Watch sun.sun for changes in azimuth and elevation. When the sun enters an
area's configured range and exceeds its minimum elevation, move each member
shutter to the configured position once. The edge trigger avoids repeated
service calls while the condition stays true. The normal schedule takes over
when the sun leaves the range; no reverse movement is forced.

This module operates independently from the open/close schedule logic.
"""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
import homeassistant.util.dt as dt_util

from .coordinator import SmartShutterCoordinator
from .helpers import render_notify_template
from .localization import notification_template, is_german
from .storage import EventHistoryStore
from .temporal_exceptions import is_date_paused

_LOGGER = logging.getLogger(__name__)

SUN_ENTITY_ID = "sun.sun"

DEFAULT_SUN_NOTIFY_TEXT = (
    "Sun position rule '{{ area }}': moved {{ count }} "
    "shutter{{ 's' if count != 1 else '' }} to {{ position }}%."
)
DEFAULT_SUN_PRENOTIFY_TEXT = (
    "Sun position rule '{{ area }}': shutters will move to {{ position }}% "
    "in about {{ minutes }} minute{{ 's' if minutes != 1 else '' }}."
)


def _azimuth_in_range(azimuth: float, az_from: float, az_to: float) -> bool:
    """Checks if an Azimuth value (0-360°) is within the configured area - including support for areas that wrap around 360°/0° (e.g. 350° to 30° for a north-facing facade)."""
    az_from %= 360
    az_to %= 360
    azimuth %= 360
    if az_from <= az_to:
        return az_from <= azimuth <= az_to
    return azimuth >= az_from or azimuth <= az_to


class SunPositionMonitor:
    """Manages the sun position regulation for ALL areas of a Config Entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: SmartShutterCoordinator,
        history_store: EventHistoryStore,
        manual_intervention_guard=None,
    ) -> None:
        self.hass = hass
        self._coordinator = coordinator
        self._history_store = history_store
        self._manual_intervention_guard = manual_intervention_guard
        self._unsub = None
        # Remembers per area whether the rule is currently "triggered"
        # (Hysteresis state, not just a snapshot of the
        # Condition) - only when the elevation is sufficiently BELOW the
        # Threshold falls (or the Azimuth leaves the area) will
        # switched back to "armed" state and can trigger again. Prevents
        # repeated triggering, if the sun is only barely around the
        # Threshold oscillates.
        self._area_triggered: dict[str, bool] = {}
        # For the prenotification (optional, see _maybe_prenotify): last
        # Elevation + time per area, to determine the rate of change
        # (Degree/Minute) to estimate, as well as whether for the CURRENT approach
        # already warned (not new for every check)
        self._area_last_elevation: dict[str, tuple[float, datetime]] = {}
        self._area_prenotified: dict[str, bool] = {}

    def async_start(self) -> None:
        self._unsub = async_track_state_change_event(
            self.hass, [SUN_ENTITY_ID], self._handle_sun_update
        )
        # Check once initially, instead of waiting for the next sun.sun update
        # to wait (this may take several minutes after a HA restart).
        self._check_all_areas()

    def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_sun_update(self, event: Event) -> None:
        self._check_all_areas()

    def _check_all_areas(self) -> None:
        sun_state = self.hass.states.get(SUN_ENTITY_ID)
        if sun_state is None:
            return
        try:
            azimuth = float(sun_state.attributes["azimuth"])
            elevation = float(sun_state.attributes["elevation"])
        except (KeyError, TypeError, ValueError):
            return

        for area in self._coordinator.custom_areas:
            if not area.get("sun_position_enabled"):
                self._area_triggered.pop(area["id"], None)
                self._area_last_elevation.pop(area["id"], None)
                self._area_prenotified.pop(area["id"], None)
                continue
            self._check_area(area, azimuth, elevation)

    def _check_area(self, area: dict, azimuth: float, elevation: float) -> None:
        az_from = area.get("sun_azimuth_from")
        az_to = area.get("sun_azimuth_to")
        min_elevation = area.get("sun_elevation_min")
        target_position = area.get("sun_position_target")
        if az_from is None or az_to is None or min_elevation is None or target_position is None:
            return

        # Hysteresis buffer for the elevation threshold (degrees, default 0
        # = no buffer, purely backward-compatible behavior for
        # existing areas without this value). Prevents
        # Value that barely oscillates around the threshold, the rule
        # triggers multiple times in a row.
        hysteresis = area.get("sun_elevation_hysteresis") or 0
        azimuth_ok = _azimuth_in_range(azimuth, az_from, az_to)

        already_triggered = self._area_triggered.get(area["id"], False)
        if already_triggered:
            # First, 'disable' (ready for the next trigger)
            # if the elevation has dropped sufficiently below the threshold
            # is OR the Azimuth has left the area.
            if elevation < (min_elevation - hysteresis) or not azimuth_ok:
                self._area_triggered[area["id"]] = False
                self._area_prenotified[area["id"]] = False  # new approach possible
            self._area_last_elevation[area["id"]] = (elevation, dt_util.now())
            return  # as long as "armed", do not trigger again

        is_active = elevation >= min_elevation and azimuth_ok

        # Additional, user-defined condition (Jinja-
        # Template, e.g. Exterior/Interior Temperature Comparison) - must
        # in addition to Azimuth/Elevation must be fulfilled. Intentionally as
        # Template instead of fixed options (temperature, brightness, ...)
        # so that really ANY arbitrary condition can be based on existing
        # Entities is possible, just like with the notification texts.
        condition_template = (area.get("sun_condition_template") or "").strip()
        if is_active and condition_template:
            is_active = self._evaluate_condition(area, condition_template)
        if is_active:
            self._area_triggered[area["id"]] = True
            self._area_prenotified[area["id"]] = False
            self._apply_position_to_members(area, target_position)
        else:
            self._maybe_prenotify(area, elevation, azimuth_ok, min_elevation)

        self._area_last_elevation[area["id"]] = (elevation, dt_util.now())

    def _maybe_prenotify(
        self, area: dict, elevation: float, azimuth_ok: bool, min_elevation: float
    ) -> None:
        """Optional early warning, BEFORE the sun position rule actually
        triggers (activatable/deactivatable per area individually, separate
        from the "Notification after triggering" field). Since the sun position
        is continuously monitored (unlike with a schedule, there is no exactly
        known trigger time in advance), the remaining time until the minimum
        elevation is estimated based on the CURRENT rate of change (degrees per
        minute, from the last two measurements) - an estimate, not an exact
        prediction. Given the relatively slow and uniform movement of the sun
        over a few minutes, this is sufficiently accurate in practice."""
        area_id = area["id"]
        if not area.get("sun_prenotify_enabled"):
            return
        if not azimuth_ok:
            return  # Azimuth not yet in the window - no meaningful ETA possible
        if self._area_prenotified.get(area_id):
            return  # a warning has already been issued for this approach

        last = self._area_last_elevation.get(area_id)
        if last is None:
            return  # first measurement, no rate calculable yet
        last_elevation, last_time = last
        elapsed_minutes = (dt_util.now() - last_time).total_seconds() / 60
        if elapsed_minutes <= 0:
            return
        rate = (elevation - last_elevation) / elapsed_minutes  # Degree/Minute
        if rate <= 0:
            return  # Elevation decreases or stagnates - does not approach

        remaining_degrees = min_elevation - elevation
        if remaining_degrees <= 0:
            return  # should have already triggered, nothing to do here

        eta_minutes = remaining_degrees / rate
        lead_minutes = area.get("sun_prenotify_lead_minutes") or 5
        if eta_minutes > lead_minutes:
            return  # too early

        self._area_prenotified[area_id] = True
        members = [
            cover_entity_id
            for cover_entity_id, area_ids in self._coordinator.shutter_areas.items()
            if area_id in area_ids
        ]
        if not members:
            return
        self.hass.async_create_task(self._send_prenotification(area, members, eta_minutes))

    def _notification_groups(self, area: dict, members: list[str]) -> dict[str, list[str]]:
        """Group only enabled shutters by recipient in the triggering area's context."""
        groups: dict[str, list[str]] = {}
        for entity_id in dict.fromkeys(members):
            service = self._coordinator.effective_notify_service(entity_id, area)
            if not service or "." not in service:
                continue
            shutter = self._coordinator.shutters.get(entity_id)
            groups.setdefault(service, []).append(shutter.name if shutter else entity_id)
        return groups

    async def _send_prenotification(self, area: dict, members: list[str], eta_minutes: float) -> None:
        for service, names in self._notification_groups(area, members).items():
            await self._send_group_prenotification(area, names, eta_minutes, service)

    async def _send_group_prenotification(self, area: dict, names: list[str], eta_minutes: float, notify_service: str) -> None:

        template_str = notification_template(
            self.hass, "sun_prenotify_text", (area.get("sun_prenotify_text") or "").strip(), DEFAULT_SUN_PRENOTIFY_TEXT,
        )
        variables = {
            "area": area.get("name"),
            "bereich": area.get("name"),
            "position": area.get("sun_position_target"),
            "count": len(names),
            "names": ", ".join(names),
            "minutes": round(eta_minutes),
            "minuten": round(eta_minutes),
        }
        message = render_notify_template(
            self.hass,
            template_str,
            variables,
            fallback=(f"Sonnenstandsregel '{area.get('name')}': Rollläden fahren in Kürze."
                      if is_german(self.hass) else f"Sun position rule '{area.get('name')}': shutters will move shortly."),
        )
        domain, service = notify_service.split(".", 1)
        try:
            await self.hass.services.async_call(
                domain, service, {"title": "Smart Shutter Manager", "message": message}, blocking=False
            )
        except Exception:  # noqa: BLE001 - Benachrichtigung darf die Automation nie stoppen
            _LOGGER.exception(
                "Sun Position Rule '%s': warning about '%s' could not be sent",
                area.get("name"),
                notify_service,
            )

    def _evaluate_condition(self, area: dict, condition_template: str) -> bool:
        """Renders the freely defined additional condition. In case of a template error or an ambiguous result, it is safely NOT triggered (fail-closed) - a broken template should not accidentally move shutters.

Since v0.17, 'outside_temp' and 'inside_temp' (float or None, see coordinator.area_effective_temps) are made available as Jinja-variables - the temperature sensor entered in the basic settings or in the area can be referenced without entity_id in the template, e.g. '{{ outside_temp > inside_temp }}'"""
        inside_temp, outside_temp = self._coordinator.area_effective_temps(area)
        variables = {"inside_temp": inside_temp, "outside_temp": outside_temp}
        rendered = render_notify_template(self.hass, condition_template, variables, fallback="")
        return rendered.strip().lower() in ("true", "1", "yes", "on")

    def _apply_position_to_members(self, area: dict, target_position: int) -> None:
        # IMPORTANT: since v0.16.0 a shutter can be assigned to multiple areas
        # can belong to multiple at the same time - coordinator.shutter_areas provides
        # hence a LIST of area_ids per shutter, not a single one
        # Value more (Regression bug found on 2026-08-10: the old
        # Equality check `area_id == area["id"]` compared a
        # List with a string and was therefore ALWAYS False - the
        # Sun position rule has been in effect since the multiple area switch
        # no more members, without any error message).
        members = [
            cover_entity_id
            for cover_entity_id, area_ids in self._coordinator.shutter_areas.items()
            if area["id"] in area_ids
        ]
        if not members:
            return

        _LOGGER.info(
            "Smart Shutter Manager: Sun position rule '%s' active - moving %d shutters to %s%%.",
            area.get("name"),
            len(members),
            target_position,
        )
        moved_members: list[str] = []
        for cover_entity_id in members:
            cover_state = self.hass.states.get(cover_entity_id)
            current = cover_state.attributes.get("current_position") if cover_state else None
            actions = ("open", "close") if current is None else (
                "open" if target_position > current else "close",
            )
            if any(is_date_paused(self._coordinator, cover_entity_id, action, dt_util.now().date()) for action in actions):
                continue
            supported = cover_state.attributes.get("supported_features", 0) if cover_state else 0
            if not (supported & CoverEntityFeature.SET_POSITION):
                _LOGGER.warning(
                    "Smart Shutter Manager: %s does not support position control - sun position rule '%s' cannot be applied here.",
                    cover_entity_id,
                    area.get("name"),
                )
                continue
            if self._manual_intervention_guard is not None:
                self._manual_intervention_guard.mark_self_initiated(cover_entity_id)
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "cover",
                    "set_cover_position",
                    {"entity_id": cover_entity_id, "position": target_position},
                )
            )
            self._history_store.add(
                cover_entity_id,
                None,
                "sun_position",
                f"Area '{area.get('name')}': moved to {target_position}% (sun position rule)",
                dt_util.now().isoformat(),
            )
            moved_members.append(cover_entity_id)

        if area.get("sun_notify_enabled") and moved_members:
            self.hass.async_create_task(self._send_notification(area, moved_members, target_position))

    async def _send_notification(self, area: dict, members: list[str], target_position: int) -> None:
        for service, names in self._notification_groups(area, members).items():
            await self._send_group_notification(area, names, target_position, service)

    async def _send_group_notification(self, area: dict, names: list[str], target_position: int, notify_service: str) -> None:

        template_str = notification_template(
            self.hass, "sun_notify_text", (area.get("sun_notify_text") or "").strip(), DEFAULT_SUN_NOTIFY_TEXT,
        )
        variables = {
            "area": area.get("name"),
            "bereich": area.get("name"),
            "position": target_position,
            "count": len(names),
            "names": ", ".join(names),
        }
        message = render_notify_template(
            self.hass,
            template_str,
            variables,
            fallback=(f"Sonnenstandsregel '{area.get('name')}': {len(names)} {'Rollladen' if len(names) == 1 else 'Rollläden'} auf {target_position}% gefahren."
                      if is_german(self.hass) else f"Sun position rule '{area.get('name')}': moved {len(names)} shutters to {target_position}%."),
        )
        domain, service = notify_service.split(".", 1)
        try:
            await self.hass.services.async_call(
                domain, service, {"title": "Smart Shutter Manager", "message": message}, blocking=False
            )
        except Exception:  # noqa: BLE001 - Benachrichtigung darf die Automation nie stoppen
            _LOGGER.exception(
                "Sun Position Rule '%s': notification about '%s' could not be sent",
                area.get("name"),
                notify_service,
            )
