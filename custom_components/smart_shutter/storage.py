"""Persistence: remembers when an action was last executed.

Basis for the catch-up logic in executor.py: only if an action has not been executed today,
    does a catch-up after a HA restart make any sense."""
from __future__ import annotations

from datetime import date
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


class LastExecutedStore:
    """Persists {rollladen_entity_id: {action: 'YYYY-MM-DD'}}."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"smart_shutter_last_executed_{entry_id}"
        )
        self._data: dict[str, dict[str, str]] = {}

    async def async_load(self) -> None:
        loaded = await self._store.async_load()
        self._data = loaded or {}

    def get(self, shutter_entity_id: str, action: str) -> date | None:
        raw = self._data.get(shutter_entity_id, {}).get(action)
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    def set(self, shutter_entity_id: str, action: str, when: date) -> None:
        self._data.setdefault(shutter_entity_id, {})[action] = when.isoformat()
        self._store.async_delay_save(lambda: self._data, 5)


class ActionOverrideStore:
    """Persists active shift/skip overrides
    ({rollladen_entity_id: {action: 'ISO-Datetime'}}), so they survive a HA restart.

    Without this persistence, an explicitly selected "skip today" via notification
    would be lost after a restart, and the catch-up logic (see executor.catch_up_if_missed) would execute
    the action that was intentionally skipped."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"smart_shutter_overrides_{entry_id}"
        )
        self._data: dict[str, dict[str, str]] = {}

    async def async_load(self) -> None:
        loaded = await self._store.async_load()
        self._data = loaded or {}

        changed = False
        for actions in self._data.values():
            for action, value in actions.items():
                if isinstance(value, dict) and ("bis" in value or "quelle" in value):
                    actions[action] = {
                        "until": value.get("until", value.get("bis")),
                        "source": value.get("source", value.get("quelle")),
                    }
                    changed = True
        if changed:
            self._store.async_delay_save(lambda: self._data, 0)

    def all_items(self):
        """Provides (shutter_entity_id, action, iso_datetime, source) for all stored overrides - for restoration on startup. The old persistence structure (pure ISO string, before introduction of the override source) remains readable, returns source=None in that case."""
        for shutter_entity_id, actions in self._data.items():
            for action, value in actions.items():
                if isinstance(value, dict):
                    yield shutter_entity_id, action, value.get("until"), value.get("source")
                else:
                    yield shutter_entity_id, action, value, None

    def set(
        self, shutter_entity_id: str, action: str, iso_datetime: str, source: str | None = None
    ) -> None:
        self._data.setdefault(shutter_entity_id, {})[action] = {
            "until": iso_datetime,
            "source": source,
        }
        self._store.async_delay_save(lambda: self._data, 5)

    def clear(self, shutter_entity_id: str, action: str) -> None:
        if shutter_entity_id in self._data:
            self._data[shutter_entity_id].pop(action, None)
            self._store.async_delay_save(lambda: self._data, 5)


class ManualPauseStore:
    """Persists until the automation for a shutter pauses because a manual intervention (wall switch, remote control, card, other automation - everything that is not from the own scheduler) has been detected. {rollladen_entity_id: 'ISO-Datetime'}.

This is conscious per shutter (not per action) - a manual intervention practically always affects the entire shutter, not just opening or just closing."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"smart_shutter_manual_pause_{entry_id}"
        )
        self._data: dict[str, str] = {}

    async def async_load(self) -> None:
        loaded = await self._store.async_load()
        self._data = loaded or {}

    def get(self, shutter_entity_id: str) -> str | None:
        return self._data.get(shutter_entity_id)

    def set(self, shutter_entity_id: str, iso_datetime: str) -> None:
        self._data[shutter_entity_id] = iso_datetime
        self._store.async_delay_save(lambda: self._data, 5)

    def clear(self, shutter_entity_id: str) -> None:
        if self._data.pop(shutter_entity_id, None) is not None:
            self._store.async_delay_save(lambda: self._data, 5)


MAX_EVENTS_PER_SHUTTER = 200


class EventHistoryStore:
    """Persists the event history (pre-notification sent, actually moved,
    skipped, postponed, ...) per shutter - basis for the "event history"
    and "timeline" view on the map. Independent of the HA log, since this
    is not filterable by shutter/action and is not a reliable source of history
    across restarts. Limited per shutter on MAX_EVENTS_PER_SHUTTER (FIFO),
    to prevent the storage file from growing indefinitely.

    Structure: {rollladen_entity_id: [ {ts, action, type, detail}, ... ]}
    ts = ISO-Datetime, action = 'open'/'close'/None, type = e.g.
    'prenotify'/'executed'/'skipped'/'postponed'."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"smart_shutter_history_{entry_id}"
        )
        self._data: dict[str, list[dict]] = {}

    async def async_load(self) -> None:
        loaded = await self._store.async_load()
        self._data = loaded or {}

    def add(self, shutter_entity_id: str, action: str | None, event_type: str, detail: str, ts_iso: str) -> None:
        events = self._data.setdefault(shutter_entity_id, [])
        events.append({"ts": ts_iso, "action": action, "type": event_type, "detail": detail})
        if len(events) > MAX_EVENTS_PER_SHUTTER:
            del events[: len(events) - MAX_EVENTS_PER_SHUTTER]
        self._store.async_delay_save(lambda: self._data, 5)

    def get(self, shutter_entity_id: str, limit: int = 50) -> list[dict]:
        events = self._data.get(shutter_entity_id, [])
        return list(reversed(events[-limit:]))
