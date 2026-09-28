"""Detection of manual interventions on shutters (v0.14).

Monitors the state_changed-Events of all managed cover.* entities.
If the state or position of a shutter changes, without the own scheduler
(executor.py) or the sun position rule (sun_position.py) having triggered this movement
shortly before, it is considered a manual intervention - e.g. wall switch,
remote control, card quick action, HA More Info dialog, or a foreign automation.
The own automation then pauses for this shutter for a configurable duration
(default 60 minutes), so that a conscious user decision is not immediately
overridden. After the pause (or manual resumption), the regular schedule
resumes automatically - no separate "resume" is needed.

Intentionally designed as a standalone, lightweight module - it knows neither
the schedule calculation nor the sun position rule in detail, but provides
only two things: `mark_self_initiated()` (for the two modules that trigger movements)
and `is_paused()` (for executor.py)."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
import homeassistant.util.dt as dt_util

from .const import EVENT_MANUAL_OVERRIDE
from .coordinator import SmartShutterCoordinator
from .storage import EventHistoryStore, ManualPauseStore

_LOGGER = logging.getLogger(__name__)

# Time window within which a state change follows a
# own command is still considered as "that was myself" (motor runtime +
# Most cover integrations have a comfortable delay in reporting
# among them).
_SELF_INITIATED_GRACE = timedelta(seconds=45)


class ManualInterventionGuard:
    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: SmartShutterCoordinator,
        pause_store: ManualPauseStore,
        history_store: EventHistoryStore,
    ) -> None:
        self.hass = hass
        self._coordinator = coordinator
        self._pause_store = pause_store
        self._history_store = history_store
        self._unsub = None
        # cover_entity_id -> point in time (datetime), up to which a
        # State change is still considered self-triggered.
        self._self_initiated_until: dict[str, "object"] = {}

    def async_start(self) -> None:
        cover_entity_ids = list(self._coordinator.shutters.keys())
        if not cover_entity_ids:
            return
        self._unsub = async_track_state_change_event(
            self.hass, cover_entity_ids, self._handle_state_change
        )

    def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    def mark_self_initiated(self, cover_entity_id: str) -> None:
        """Calling executor.py and sun_position.py directly, UNMITTELBAR before calling a cover.*-service for a managed shutter prevents the system from incorrectly interpreting the user's movement as a manual intervention."""
        self._self_initiated_until[cover_entity_id] = dt_util.now() + _SELF_INITIATED_GRACE

    def is_paused(self, cover_entity_id: str) -> bool:
        raw = self._pause_store.get(cover_entity_id)
        if raw is None:
            return False
        try:
            until = dt_util.parse_datetime(raw)
        except (TypeError, ValueError):
            return False
        return until is not None and until > dt_util.now()

    def paused_until(self, cover_entity_id: str) -> str | None:
        return self._pause_store.get(cover_entity_id) if self.is_paused(cover_entity_id) else None

    def clear_pause(self, cover_entity_id: str) -> None:
        self._pause_store.clear(cover_entity_id)

    @callback
    def _handle_state_change(self, event: Event) -> None:
        cover_entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None or old_state is None or cover_entity_id is None:
            return  # first appearance of the entity etc. - nothing to do

        if self._was_self_initiated(cover_entity_id):
            return

        if not self._is_meaningful_movement(old_state, new_state):
            return

        pause_minutes = self._coordinator.manual_pause_minutes
        if pause_minutes <= 0:
            return  # Feature is disabled via configuration (0 minutes)

        # Many cover integrations (u.a. Shelly 2PM) report during
        # DURING a continuous drive, multiple individual position ticks
        # (0 -> 5 -> 10 -> ... -> 100), each of them a separate
        # state_changed-Event. Without this check, every tick
        # logged separately as a manual intervention (Spam - see
        # Bug report: 15+ identical entries within one minute).
        # As long as the previous pause is still running, it is considered a holiday. On user request, this applies both for open and
        # Continuation of the same intervention: only extend the pause, but
        # do not log/fire again.
        already_paused = self.is_paused(cover_entity_id)

        until = dt_util.now() + timedelta(minutes=pause_minutes)
        self._pause_store.set(cover_entity_id, until.isoformat())

        if already_paused:
            return

        self._history_store.add(
            cover_entity_id,
            None,
            "manual_override",
            f"Manueller Eingriff erkannt - Automatik pausiert bis {until.strftime('%H:%M')}",
            dt_util.now().isoformat(),
        )
        _LOGGER.info(
            'Smart Shutter Manager: Manual intervention detected for %s - automation paused until %s.',
            cover_entity_id,
            until.isoformat(),
        )
        self.hass.bus.async_fire(
            EVENT_MANUAL_OVERRIDE, {"entity_id": cover_entity_id, "paused_until": until.isoformat()}
        )

    def _was_self_initiated(self, cover_entity_id: str) -> bool:
        marked_until = self._self_initiated_until.get(cover_entity_id)
        return marked_until is not None and dt_util.now() < marked_until

    @staticmethod
    def _is_meaningful_movement(old_state, new_state) -> bool:
        """Filters out noise (e.g. attribute updates without real
        position/state change) - only a REAL movement should trigger
        a manual intervention.

        IMPORTANT: When a shutter returns from 'unavailable'/'unknown'
        (e.g. short WLAN/power outage, restart of the Shelly device or
        of Home Assistant itself), it reports its actual state afterward - this looks like a state change, but is NOT a movement. Without this exception, a short WLAN outage that disconnects multiple devices at once would trigger a false 'manual intervention' pause on multiple/all affected shutters at the same time - even though no one actually operated them (see bug report: a shutter is manually operated, but the pause message appears on every shutter)."""
        if old_state.state in ("unavailable", "unknown"):
            return False
        if old_state.state != new_state.state and new_state.state in (
            "open",
            "closed",
            "opening",
            "closing",
        ):
            return True
        old_pos = old_state.attributes.get("current_position")
        new_pos = new_state.attributes.get("current_position")
        if old_pos is not None and new_pos is not None and old_pos != new_pos:
            return True
        return False
