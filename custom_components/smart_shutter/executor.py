"""Executor: schedules real triggers, executes cover actions, manages
early warning + shift/skip + recovery logic on restart.

For each shutter and each action (open/close), a single, specific target time is calculated (regardless of whether it is time-based or sun-based - see scheduler.resolve_next_datetime) and scheduled via async_track_point_in_time.
After execution (or after skip/shift), the trigger reschedules itself automatically.

Early warning (on user request, configurable via the Options Flow -
NO fixed values in code):
  - coordinator.pre_notify_lead: how many minutes in advance a warning is given
    (0 = no early warning)
  - coordinator.postpone_options_minutes: which "+X minutes" buttons
    are offered (e.g. [5, 10, 15])
The early warning uses HA's mobile app notification actions (buttons).
Notify targets without action support show only the text, without buttons.

Recovery logic (on user request, also configurable):
  - coordinator.catch_up_window: how far back a missed time
    can be, to still be recovered on restart
    (0 = no recovery). Uses storage.LastExecutedStore to avoid re-issuing
    actions that were already executed today.

Priorities (Requirements document section 13): Frost protection (priority 2)
and automation off (priority 3) are checked before any execution.
If the shutter is already in the target position, nothing happens.
Manual operation is detected and user rules are followed later."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, time, timedelta
import logging

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import template as template_helper
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_state_change_event,
    async_track_time_change,
)
import homeassistant.util.dt as dt_util

from .seasons import seasonal_enabled, season_at

from .const import (
    ACTION_CLOSE,
    ACTION_OPEN,
    DEFAULT_POSITION,
    EVENT_FROST_BLOCKED,
    EVENT_MOVED,
    SIGNAL_RECOMPUTE,
    SOURCE_LOCAL,
    TYPE_SUNRISE,
    TYPE_SUNSET,
    automation_registry_key,
    global_automation_registry_key,
    position_registry_key,
    position_source_registry_key,
)
from .coordinator import ManagedShutter, SmartShutterCoordinator
from .helpers import render_notify_template
from .localization import display_text, is_german
from .manual_intervention import ManualInterventionGuard
from .scheduler import (
    determine_active_profile,
    get_action_type,
    resolve_next_datetime,
    resolve_todays_datetime,
)
from .storage import EventHistoryStore, LastExecutedStore, ManualPauseStore
from .sun_position import SunPositionMonitor
from .temporal_exceptions import exception_time, is_date_paused

_LOGGER = logging.getLogger(__name__)

_SERVICE_BY_ACTION = {ACTION_OPEN: "open_cover", ACTION_CLOSE: "close_cover"}

_NOTIFICATION_ACTION_EVENT = "mobile_app_notification_action"
_ACTION_PREFIX = "ssm"  # Prefix for our notification action IDs


def _render_template(
    hass: HomeAssistant, template_str: str, variables: dict, fallback: str
) -> str:
    """Thin alias for helpers.render_notify_template - kept,
    so that existing calls in this file remain unchanged. The
    actual implementation is in helpers.py, so that it can also
    be used by sun_position.py without creating a circular
    import between executor.py and sun_position.py."""
    return render_notify_template(hass, template_str, variables, fallback)


class NotificationBatcher:
    """Collects movement/frost protection events briefly and sends a single bundled notification instead of a flood of individual notifications.
    Pre-warnings (with buttons) are sent immediately per shutter
    as they are individually interactive."""

    _BATCH_WINDOW_SECONDS = 5

    def __init__(self, hass: HomeAssistant, coordinator: SmartShutterCoordinator) -> None:
        self.hass = hass
        self._coordinator = coordinator
        # v0.20: bundled after effective Notify-Service was separated (see
        # coordinator.effective_notify_service) - a area with
        # own Notify-Service-Override (e.g. Guest-Phone) receives a
        # OWN, containing only his shutters message, instead in
        # subscribe to the host's global collection message or this
        # to mix with foreign shutters.
        self._pending_moves: dict[str | None, list[tuple[str, str, str]]] = defaultdict(list)
        self._pending_frost: dict[str | None, list[str]] = defaultdict(list)
        self._flush_unsub = None

    @callback
    def report_movement(self, name: str, action_label: str, trigger_label: str, notify_target: str | None) -> None:
        self._pending_moves[notify_target].append((name, action_label, trigger_label))
        self._schedule_flush()

    @callback
    def report_frost_block(self, name: str, notify_target: str | None) -> None:
        self._pending_frost[notify_target].append(name)
        self._schedule_flush()

    @callback
    def _schedule_flush(self) -> None:
        if self._flush_unsub is not None:
            return
        self._flush_unsub = async_track_point_in_time(
            self.hass,
            self._flush,
            dt_util.now() + timedelta(seconds=self._BATCH_WINDOW_SECONDS),
        )

    @callback
    def _flush(self, _now=None) -> None:
        self._flush_unsub = None
        moves, self._pending_moves = self._pending_moves, defaultdict(list)
        frost, self._pending_frost = self._pending_frost, defaultdict(list)
        if moves or frost:
            targets = set(moves.keys()) | set(frost.keys())
            for target in targets:
                self.hass.async_create_task(
                    self._send_batch(target, moves.get(target, []), frost.get(target, []))
                )

    async def _send_batch(
        self, notify_target: str | None, moves: list[tuple[str, str, str]], frost: list[str]
    ) -> None:
        notify_service = notify_target
        if not notify_service or "." not in notify_service:
            return

        messages = []
        if moves:
            messages.append(self._format_moves(moves))
        if frost:
            names = ", ".join(frost)
            text = _render_template(
                self.hass,
                self._coordinator.notify_text_frost,
                {"names": names, "count": len(frost)},
                fallback=(f"Frostschutz aktiv: {names} {'wird' if len(frost) == 1 else 'werden'} nicht bewegt."
                          if is_german(self.hass) else f"Frost protection active: {names} will not move."),
            )
            messages.append(text)

        await self._call_notify(notify_service, "Smart Shutter Manager", "\n".join(messages))

    async def send_pre_close_warning(
        self,
        shutter: ManagedShutter,
        action: str,
        target_dt: datetime,
        postpone_options_minutes: list[int],
    ) -> None:
        """Immediate, individual warning with buttons (+X Min / Skip) - deliberately NOT bundled, as each response refers to
exactly this one shutter."""
        notify_service = self._coordinator.effective_notify_service(shutter.entity_id)
        if not notify_service or "." not in notify_service:
            return

        message = _render_template(
            self.hass,
            self._coordinator.notify_text_preclose,
            {"name": shutter.name, "time": target_dt.strftime("%H:%M"),
             "action": display_text(self.hass, action), "action_raw": action},
            fallback=(f"{shutter.name} schließt um {target_dt.strftime('%H:%M')} Uhr."
                      if is_german(self.hass) else f"{shutter.name} closes at {target_dt.strftime('%H:%M')}."),
        )

        # Android/iOS reliably show up to 3 action buttons only -
        # with more buttons, z.B is hidden. Android sometimes has its own
        # Standard: Suggest (5/15/60 min "sleep") instead of
        # our buttons. Therefore: max. 2 shift options + Skip.
        limited_postpone = postpone_options_minutes[:2]
        actions = [
            {
                "action": f"{_ACTION_PREFIX}|postpone{minutes}|{shutter.entity_id}|{action}",
                "title": f"+{minutes} Min",
            }
            for minutes in limited_postpone
        ]
        actions.append(
            {
                "action": f"{_ACTION_PREFIX}|skip|{shutter.entity_id}|{action}",
                "title": display_text(self.hass, "Skip today"),
            }
        )

        # IMPORTANT: no "tag" anymore - a reused tag caused issues on Android
        # with repeated notifications, own "Sleep" buttons
        # (5/15/60 Min) instead of our own actions.
        await self._call_notify(
            notify_service,
            display_text(self.hass, "Shutter closing soon"),
            message,
            extra_data={"actions": actions},
        )

    async def _call_notify(
        self,
        notify_service: str,
        title: str,
        message: str,
        extra_data: dict | None = None,
    ) -> None:
        domain, service = notify_service.split(".", 1)
        payload = {"title": title, "message": message}
        if extra_data:
            payload["data"] = extra_data
        try:
            await self.hass.services.async_call(domain, service, payload, blocking=False)
        except Exception:  # noqa: BLE001 - Benachrichtigung darf nie die Automation stoppen
            _LOGGER.exception(
                "Notification about '%s' could not be sent", notify_service
            )

    def _format_moves(self, moves: list[tuple[str, str, str]]) -> str:
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for name, action_label, trigger_label in moves:
            groups[(action_label, trigger_label)].append(name)

        lines = []
        for (action_label, trigger_label), names in groups.items():
            joined = ", ".join(names)
            text = _render_template(
                self.hass,
                self._coordinator.notify_text_moved,
                {
                    "names": joined,
                    "count": len(names),
                    "action": display_text(self.hass, action_label),
                    "trigger": display_text(self.hass, trigger_label),
                    "action_raw": action_label,
                    "trigger_raw": trigger_label,
                },
                fallback=(
                    f"{joined} {display_text(self.hass, 'was' if len(names) == 1 else 'were')} "
                    f"{display_text(self.hass, action_label)}. "
                    f"{display_text(self.hass, 'Trigger')}: {display_text(self.hass, trigger_label)}."
                ),
            )
            lines.append(text)
        return "\n".join(lines)

    def cancel(self) -> None:
        if self._flush_unsub is not None:
            self._flush_unsub()
            self._flush_unsub = None
        self._pending_moves = defaultdict(list)
        self._pending_frost = defaultdict(list)


class ShutterActionExecutor:
    """Manages the real triggers for opening and closing a shutter, including warning and reaction to movement/overshooting."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: SmartShutterCoordinator,
        shutter: ManagedShutter,
        notifier: NotificationBatcher,
        last_executed_store: LastExecutedStore,
        history_store: EventHistoryStore,
        manual_intervention_guard: ManualInterventionGuard,
    ) -> None:
        self.hass = hass
        self._coordinator = coordinator
        self._shutter = shutter
        self._notifier = notifier
        self._last_executed_store = last_executed_store
        self._history_store = history_store
        self._manual_intervention_guard = manual_intervention_guard

        self._unsub_exec: dict[str, callable] = {}
        self._unsub_prenotify: dict[str, callable] = {}
        self._target_dt: dict[str, datetime] = {}
        # When the warning was actually sent (per action) -
        # so that tapping a button on a long-outdated notification
        # can be ignored, see handle_notification_response.
        self._prenotify_sent_at: dict[str, datetime] = {}

    def _log_event(self, action: str | None, event_type: str, detail: str) -> None:
        """Writes an entry in the event history (storage.EventHistoryStore) - basis for the "Event History" and "Timeline" view of the map."""
        self._history_store.add(
            self._shutter.entity_id, action, event_type, detail, dt_util.now().isoformat()
        )

    @callback
    def arm_all(self, *_args, **_kwargs) -> None:
        """Plans new opening+closing (discards previous triggers)."""
        self._arm(ACTION_OPEN)
        self._arm(ACTION_CLOSE)

    def cancel_all(self) -> None:
        for action in (ACTION_OPEN, ACTION_CLOSE):
            self._cancel_exec(action)
            self._cancel_prenotify(action)

    def _cancel_exec(self, action: str) -> None:
        unsub = self._unsub_exec.pop(action, None)
        if unsub is not None:
            unsub()

    def _cancel_prenotify(self, action: str) -> None:
        unsub = self._unsub_prenotify.pop(action, None)
        if unsub is not None:
            unsub()

    @callback
    def _arm(self, action: str) -> None:
        self._cancel_exec(action)
        self._cancel_prenotify(action)
        # A new target time makes any previously sent warning
        # invalid - their send time may no longer be used for the
        # Age check of a button tap is taken into account.
        self._prenotify_sent_at.pop(action, None)

        now = dt_util.now()
        # Remember suppressed actions even without a timer: deleting the pause
        # followed by a restart must not catch up today's omitted movement.
        self._record_date_pause(action)
        profile = determine_active_profile(
            self.hass, self._coordinator, now.date(),
            self._coordinator.shutter_areas.get(self._shutter.entity_id, []),
        )
        # resolve_next_datetime automatically takes into account an active
        # Move/Override (see handle_notification_response),
        # as long as its time is still in the future.
        next_dt = resolve_next_datetime(
            self.hass, self._coordinator, self._shutter, action, profile, now
        )
        if next_dt is None:
            _LOGGER.warning(
                "Smart Shutter Manager: could not calculate a valid next action for %s/%s (custom profile without a matching rule, invalid configuration, etc.); action remains unscheduled until recalculation.",
                self._shutter.entity_id,
                action,
            )
            return

        self._target_dt[action] = next_dt

        pre_lead = self._coordinator.pre_notify_lead
        if action == ACTION_CLOSE and pre_lead > timedelta(0) and (dt_util.as_utc(next_dt) - dt_util.as_utc(now)) > pre_lead:
            pre_time = dt_util.as_utc(next_dt) - pre_lead
            self._unsub_prenotify[action] = async_track_point_in_time(
                self.hass, self._make_prenotify_callback(action), pre_time
            )

        self._unsub_exec[action] = async_track_point_in_time(
            self.hass, self._make_time_callback(action), next_dt
        )

    def _make_time_callback(self, action: str):
        async def _fire(_now) -> None:
            try:
                await self._execute(action)
            except Exception:  # noqa: BLE001 - continue scheduling other shutters
                # Without this try/except, an unexpected error in
                # _execute() causes the rescheduling for the
                # next day (_arm further down) is NEVER executed -
                # the shutter would then remain until the next HA restart
                # completely unplanned, without it showing up in the log.
                # _LOGGER.exception writes the full traceback clearly
                # recognizable with shutter reference in log.
                _LOGGER.exception(
                    "Smart Shutter Manager: unexpected error during execution of '%s' for %s - will be rescheduled for the next action anyway.",
                    action,
                    self._shutter.entity_id,
                )
            finally:
                self._arm(action)  # reschedule for tomorrow (or next solar event)

        return _fire

    def _make_prenotify_callback(self, action: str):
        async def _fire(_now) -> None:
            target = self._target_dt.get(action)
            if target is None:
                return
            if is_date_paused(self._coordinator, self._shutter.entity_id, action, dt_util.now().date()):
                return
            if self._already_in_target_state(action):
                # Shutter is already in the target position (e.g. manual
                # or by an earlier action) - no warning
                # not needed, because nothing would happen anyway.
                _LOGGER.debug(
                    "Warning for '%s' (%s) skipped - already in target position.",
                    self._shutter.entity_id,
                    action,
                )
                return
            self._prenotify_sent_at[action] = dt_util.now()
            await self._notifier.send_pre_close_warning(
                self._shutter, action, target, self._coordinator.postpone_options_minutes
            )
            self._log_event(action, "prenotify", "Warning sent")

        return _fire

    @callback
    def handle_notification_response(
        self,
        command: str,
        action: str,
        from_notification: bool = True,
        source: str | None = None,
    ) -> None:
        """Responds to a button tap from the warning OR a direct service call (smart_shutter.skip_action/postpone_action).
        Sets an override in the coordinator (which also reads sensor.next_action), replans immediately and sends a recompute signal right away, so the display is updated immediately instead of waiting for the next 60s tick.

        from_notification=False (service call) intentionally bypasses the age check - it only applies to actual notification taps, not to explicit service calls."""
        current_target = self._target_dt.get(action)
        if current_target is None:
            return

        # Ignore old notifications (Options Flow,
        # notification_max_age_minutes, 0 = test skipped). Prevents,
        # that tapping on a long-outdated notification still
        # something triggers it - e.g. because the phone delivers them late
        # had or the user had overlooked them.
        if from_notification:
            sent_at = self._prenotify_sent_at.get(action)
            max_age = self._coordinator.notification_max_age
            if sent_at is not None and max_age > timedelta(0):
                age = dt_util.now() - sent_at
                if age > max_age:
                    _LOGGER.info(
                        "Notification action '%s' for %s ignored - notification is %.0f minutes old (Limit: %.0f minutes)",
                        command,
                        self._shutter.entity_id,
                        age.total_seconds() / 60,
                        max_age.total_seconds() / 60,
                    )
                    return

        if command == "skip":
            # Calculate next occurrence AFTER the skipped one (not
            # blind +1 day, so that profile change/weekend remains correct).
            future_now = current_target + timedelta(seconds=1)
            profile = determine_active_profile(
                self.hass, self._coordinator, future_now.date(),
                self._coordinator.shutter_areas.get(self._shutter.entity_id, []),
            )
            new_target = resolve_next_datetime(
                self.hass, self._coordinator, self._shutter, action, profile, future_now
            )
        elif command.startswith("postpone"):
            try:
                minutes = int(command.removeprefix("postpone"))
            except ValueError:
                return
            new_target = current_target + timedelta(minutes=minutes)
        else:
            return

        if new_target is None:
            return

        if command == "skip":
            self._log_event(action, "skipped", "Skipped by user")
        else:
            self._log_event(action, "postponed", f"Postponed by user by {minutes} min")

        self._coordinator.set_action_override(
            self._shutter.entity_id,
            action,
            new_target,
            source=source or ("Benachrichtigung" if from_notification else "Service-Aufruf"),
        )
        self._arm(action)
        async_dispatcher_send(
            self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}"
        )

    @callback
    def set_external_override(
        self, action: str, target_dt: datetime, source: str | None = None
    ) -> None:
        """Sets an override with an absolute, externally provided time point (Service smart_shutter.set_external_trigger, see
        __init__.py + config_flow.py "External Triggers manage").
        Technically identical to Shift/Skip (same override mechanism, so persistence/priority/display work exactly the same) - only without button tap, but with a pre-calculated target time point."""
        self._coordinator.set_action_override(
            self._shutter.entity_id, action, target_dt, source=source or "Externer Trigger"
        )
        self._arm(action)
        async_dispatcher_send(
            self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}"
        )

    def _is_frost_active(self) -> bool:
        return self._coordinator.is_frost_active_for(self._shutter.entity_id)

    def _target_position(self, action: str) -> int:
        """Reads the configured target position (0-100%) for an action - default 100% (open) / 0% (close), local or global depending on position_source_registry_key (independent of the time/solar switch and profile times)."""
        shutter_entities = self._coordinator.shutter_entities.get(
            self._shutter.entity_id, {}
        )
        source_entity = shutter_entities.get(position_source_registry_key(action))
        use_local = bool(source_entity) and source_entity.source == SOURCE_LOCAL

        if use_local:
            position_entity = shutter_entities.get(position_registry_key(action))
        else:
            position_entity = self._coordinator.global_entities.get(
                position_registry_key(action)
            )

        if position_entity is None:
            return DEFAULT_POSITION[action]
        try:
            return int(position_entity.native_value)
        except (TypeError, ValueError):
            return DEFAULT_POSITION[action]

    def _already_in_target_state(self, action: str) -> bool:
        """Checks if the shutter is already in the target position.

Bugfix: HA's coarse cover status "open" only means "position > 0%", not "fully open" - a shutter closed to 30% was thus falsely recognized as "already open" and an open action was skipped. Now, if the cover supports position specification, it is exactly checked against the configured target position (standard 100%/0%, but also deviating partial positions, see number.py); only without position support is the coarse status reverted to (no further information is available then) - and only for the full targets 100%/0% is meaningful."""
        cover_state = self.hass.states.get(self._shutter.entity_id)
        if cover_state is None:
            return False

        target_position = self._target_position(action)
        position = cover_state.attributes.get("current_position")
        if position is not None:
            return position == target_position

        if target_position == 100:
            return cover_state.state == "open"
        if target_position == 0:
            return cover_state.state == "closed"
        return False  # Partial position without position support is not reliably verifiable

    async def _apply_stagger_delay(self) -> None:
        """Staggered command output (RF collision protection, see Options
        Flow "Staggered Command Output"): waits before the actual
        cover.open_cover/close_cover-Aufruf a time proportional to the
        stable position of this shutter (alphabetically after
        entity_id), so that during a global/area-wide
        multiple action, not all RF commands go out at the same time
        and interfere with each other. 0ms (Default) = no
        effect, behavior as before."""
        delay_ms = self._coordinator.stagger_delay_ms
        if delay_ms <= 0:
            return
        index = self._coordinator.stagger_index(self._shutter.entity_id)
        if index <= 0:
            return
        await asyncio.sleep((index * delay_ms) / 1000)

    def _record_date_pause(self, action: str) -> bool:
        today = dt_util.now().date()
        if not is_date_paused(self._coordinator, self._shutter.entity_id, action, today):
            return False
        if self._last_executed_store.get(self._shutter.entity_id, action) != today:
            self._log_event(action, "skipped", "Automation paused (date exception)")
            self._last_executed_store.set(self._shutter.entity_id, action, today)
        return True

    async def _execute(self, action: str) -> None:
        """Checks manual pause + frost protection + automation, skips already reached target positions, then calls open/close_cover and reports actual movement to the NotificationBatcher."""
        if self._record_date_pause(action):
            return
        if self._manual_intervention_guard.is_paused(self._shutter.entity_id):
            paused_until = self._manual_intervention_guard.paused_until(self._shutter.entity_id)
            _LOGGER.info(
                'Automation for %s paused (manual intervention detected until %s) - action skipped',
                self._shutter.entity_id,
                paused_until,
            )
            self._log_event(action, "skipped", "Automation paused (manual intervention)")
            self._last_executed_store.set(self._shutter.entity_id, action, dt_util.now().date())
            return

        if self._is_frost_active():
            _LOGGER.info(
                'Frost protection active - movement for %s skipped',
                self._shutter.entity_id,
            )
            self._notifier.report_frost_block(
                self._shutter.name, self._coordinator.effective_notify_service(self._shutter.entity_id)
            )
            self._log_event(action, "skipped", "Frost protection active")
            self._last_executed_store.set(self._shutter.entity_id, action, dt_util.now().date())
            self.hass.bus.async_fire(
                EVENT_FROST_BLOCKED,
                {"entity_id": self._shutter.entity_id, "name": self._shutter.name},
            )
            return

        global_switch = self._coordinator.global_entities.get(
            global_automation_registry_key(action)
        )
        if global_switch is not None and not global_switch.is_on:
            _LOGGER.info(
                'Global automation (%s) is off - action for %s skipped',
                action,
                self._shutter.entity_id,
            )
            self._log_event(action, "skipped", "Global automation disabled")
            self._last_executed_store.set(self._shutter.entity_id, action, dt_util.now().date())
            return

        shutter_entities = self._coordinator.shutter_entities.get(
            self._shutter.entity_id, {}
        )
        automation_switch = shutter_entities.get(automation_registry_key(action))
        if automation_switch is not None and not automation_switch.is_on:
            _LOGGER.info(
                'Automation (%s) is off for %s - action skipped',
                action,
                self._shutter.entity_id,
            )
            self._log_event(action, "skipped", "Individual automation disabled")
            self._last_executed_store.set(self._shutter.entity_id, action, dt_util.now().date())
            return

        if self._already_in_target_state(action):
            cover_state = self.hass.states.get(self._shutter.entity_id)
            position = (
                cover_state.attributes.get("current_position", "unbekannt")
                if cover_state is not None
                else "unbekannt"
            )
            _LOGGER.info(
                "%s is already in the target position for '%s' (Position: %s) - no action",
                self._shutter.entity_id,
                action,
                position,
            )
            self._log_event(action, "skipped", f"Already at target position ({position})")
            self._last_executed_store.set(self._shutter.entity_id, action, dt_util.now().date())
            return

        service = _SERVICE_BY_ACTION[action]
        target_position = self._target_position(action)
        service_data: dict = {"entity_id": self._shutter.entity_id}

        if target_position not in (0, 100):
            cover_state = self.hass.states.get(self._shutter.entity_id)
            supported = (
                cover_state.attributes.get("supported_features", 0)
                if cover_state is not None
                else 0
            )
            if supported & CoverEntityFeature.SET_POSITION:
                service = "set_cover_position"
                service_data["position"] = target_position
            else:
                _LOGGER.warning(
                    "%s does not support position control - configured target position %s%% for '%s' cannot be reached, use full %s instead",
                    self._shutter.entity_id,
                    target_position,
                    action,
                    "Open" if action == ACTION_OPEN else "Close",
                )

        _LOGGER.info(
            "Smart Shutter Manager: %s -> cover.%s (%s)",
            self._shutter.name,
            service,
            self._shutter.entity_id,
        )
        await self._apply_stagger_delay()
        if self._record_date_pause(action):
            return
        self._manual_intervention_guard.mark_self_initiated(self._shutter.entity_id)
        await self.hass.services.async_call(
            "cover",
            service,
            service_data,
            blocking=False,
        )
        self._last_executed_store.set(self._shutter.entity_id, action, dt_util.now().date())
        self._coordinator.clear_action_override(self._shutter.entity_id, action)

        action_label = "opened" if action == ACTION_OPEN else "closed"
        trigger_label = self._trigger_label(action)
        self._notifier.report_movement(
            self._shutter.name,
            action_label,
            trigger_label,
            self._coordinator.effective_notify_service(self._shutter.entity_id),
        )
        self._log_event(action, "executed", f"{action_label} ({trigger_label}, target {target_position}%)")

        # For your own automations (event trigger): "when Smart Shutter
        # If Manager X moved it, then also do Y.
        self.hass.bus.async_fire(
            EVENT_MOVED,
            {
                "entity_id": self._shutter.entity_id,
                "name": self._shutter.name,
                "action": action,
                "trigger": trigger_label,
            },
        )

    def _trigger_label(self, action: str) -> str:
        if exception_time(self._coordinator, self._shutter.entity_id, action, dt_util.now().date()) is not None:
            return "Schedule"
        action_type = get_action_type(self._coordinator, self._shutter, action)
        if action_type == TYPE_SUNRISE:
            return "Sunrise"
        if action_type == TYPE_SUNSET:
            return "Sunset"
        return "Schedule"

    async def catch_up_if_missed(self, now: datetime) -> None:
        """Catch-up logic: checks at startup whether an action was supposed to run today but (e.g. due to a HA restart) has not yet been executed - and catches it up if it is not too old (coordinator.catch_up_window)."""
        catch_up_window = self._coordinator.catch_up_window
        if catch_up_window <= timedelta(0):
            return

        profile = determine_active_profile(
            self.hass, self._coordinator, now.date(),
            self._coordinator.shutter_areas.get(self._shutter.entity_id, []),
        )

        for action in (ACTION_OPEN, ACTION_CLOSE):
            override = self._coordinator.get_action_override(
                self._shutter.entity_id, action
            )
            if override is not None and dt_util.as_utc(override) > dt_util.as_utc(now):
                # User has already explicitly moved/skipped
                # (Override now survives a HA restart, see
                # storage.ActionOverrideStore) - the regular arm()-planning
                # takes over correctly. Without this check, a
                # consciously skipped action here erroneously retried.
                continue

            todays_target = resolve_todays_datetime(
                self.hass, self._coordinator, self._shutter, action, profile, now
            )
            if todays_target is None or dt_util.as_utc(todays_target) > dt_util.as_utc(now):
                continue  # not yet due - normal arm takes over

            if dt_util.as_utc(now) - dt_util.as_utc(todays_target) > catch_up_window:
                continue  # too long ago, no longer meaningful to catch up

            already_done = self._last_executed_store.get(self._shutter.entity_id, action)
            if already_done == now.date():
                continue  # already executed today

            _LOGGER.info(
                'Catch-up action: %s (%s), target was %s - catching up',
                self._shutter.entity_id,
                action,
                todays_target,
            )
            try:
                await self._execute(action)
            except Exception:  # noqa: BLE001 - siehe _make_time_callback
                # Without this try/except, an error here would
                # Catch-up loop in SchedulerManager.async_start() for
                # Cancel all shutters (not just this one) and
                # self._rearm_all() would never be called - not a single one
                # Shutter would then be automatically scheduled.
                _LOGGER.exception(
                    "Smart Shutter Manager: unexpected error during retrieval of '%s' for %s.",
                    action,
                    self._shutter.entity_id,
                )


class SchedulerManager:
    """Creates/manages a ShutterActionExecutor per shutter, the shared NotificationBatcher, the catch-up logic on startup, and the shared triggers (Signal, Midnight, Holiday entity, Notification buttons)."""

    def __init__(self, hass: HomeAssistant, coordinator: SmartShutterCoordinator) -> None:
        self.hass = hass
        self._coordinator = coordinator
        self._executors: dict[str, ShutterActionExecutor] = {}
        self._notifier: NotificationBatcher | None = None
        self._last_executed_store: LastExecutedStore | None = None
        self.history_store: EventHistoryStore | None = None
        self._sun_position_monitor: SunPositionMonitor | None = None
        self.manual_intervention_guard: ManualInterventionGuard | None = None
        self._unsub_signal: callable | None = None
        self._unsub_midnight: callable | None = None
        self._unsub_season: callable | None = None
        self._season_state = None
        self._unsub_holiday: callable | None = None
        self._unsub_notification_action: callable | None = None

    async def async_start(self) -> None:
        self._last_executed_store = LastExecutedStore(
            self.hass, self._coordinator.entry.entry_id
        )
        await self._last_executed_store.async_load()

        self.history_store = EventHistoryStore(self.hass, self._coordinator.entry.entry_id)
        await self.history_store.async_load()

        manual_pause_store = ManualPauseStore(self.hass, self._coordinator.entry.entry_id)
        await manual_pause_store.async_load()
        self.manual_intervention_guard = ManualInterventionGuard(
            self.hass, self._coordinator, manual_pause_store, self.history_store
        )
        self.manual_intervention_guard.async_start()

        self._sun_position_monitor = SunPositionMonitor(
            self.hass, self._coordinator, self.history_store, self.manual_intervention_guard
        )
        self._sun_position_monitor.async_start()

        # IMPORTANT: Overrides (moving/skipping) BEFORE the catch-up-
        # Load check, otherwise a before restart intentionally
        # skipped date incorrectly resubmitted (see
        # catch_up_if_missed).
        await self._coordinator.async_load_overrides()

        self._notifier = NotificationBatcher(self.hass, self._coordinator)

        for shutter in self._coordinator.shutters.values():
            self._executors[shutter.entity_id] = ShutterActionExecutor(
                self.hass,
                self._coordinator,
                shutter,
                self._notifier,
                self._last_executed_store,
                self.history_store,
                self.manual_intervention_guard,
            )

        entry_id = self._coordinator.entry.entry_id
        self._unsub_signal = async_dispatcher_connect(
            self.hass, f"{SIGNAL_RECOMPUTE}_{entry_id}", self._rearm_all
        )

        self._unsub_midnight = async_track_time_change(
            self.hass, self._rearm_all, hour=0, minute=0, second=10
        )

        if seasonal_enabled(self._coordinator):
            self._season_state = (str(dt_util.now().tzinfo), season_at(dt_util.now()))
            self._unsub_season = async_track_time_change(
                self.hass, self._check_season, second=10
            )

        holiday_entity_id = self._coordinator.holiday_entity_id
        if holiday_entity_id:
            self._unsub_holiday = async_track_state_change_event(
                self.hass, [holiday_entity_id], self._rearm_all
            )

        self._unsub_notification_action = self.hass.bus.async_listen(
            _NOTIFICATION_ACTION_EVENT, self._handle_notification_action
        )

        # Catch-up check BEFORE the regular arm, so that today's missed
        # Actions are caught up before the normal schedule takes effect.
        now = dt_util.now()
        for executor in self._executors.values():
            try:
                await executor.catch_up_if_missed(now)
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    'Smart Shutter Manager: Catch-up check for %s failed - other shutters are still scheduled normally.',
                    executor._shutter.entity_id,
                )

        self._rearm_all()

    @callback
    def _check_season(self, now: datetime) -> None:
        local_now = dt_util.as_local(now)
        state = (str(local_now.tzinfo), season_at(local_now))
        if state != self._season_state:
            self._season_state = state
            # No restart catch-up: only recompute future actions and previews.
            async_dispatcher_send(self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}")

    @callback
    def _rearm_all(self, *_args, **_kwargs) -> None:
        for executor in self._executors.values():
            executor.arm_all()

    def request_skip(self, cover_entity_id: str, action: str, source: str | None = None) -> bool:
        """For service smart_shutter.skip_action - skips the next action for a shutter (only for today)."""
        executor = self._executors.get(cover_entity_id)
        if executor is None:
            return False
        executor.handle_notification_response(
            "skip", action, from_notification=False, source=source
        )
        return True

    def request_postpone(
        self, cover_entity_id: str, action: str, minutes: int, source: str | None = None
    ) -> bool:
        """For service smart_shutter.postpone_action - shifts the next action for a shutter by X minutes."""
        executor = self._executors.get(cover_entity_id)
        if executor is None:
            return False
        executor.handle_notification_response(
            f"postpone{minutes}", action, from_notification=False, source=source
        )
        return True

    def request_clear_override(self, cover_entity_id: str, action: str) -> bool:
        """For service smart_shutter.clear_override - immediately cancels an active shift/skip override so that the regular schedule applies again (see resolve_next_datetime: an active override otherwise always takes precedence)."""
        if cover_entity_id not in self._executors:
            return False
        self._coordinator.clear_action_override(cover_entity_id, action)
        async_dispatcher_send(self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}")
        return True

    def request_clear_manual_pause(self, cover_entity_id: str) -> bool:
        """For service smart_shutter.clear_manual_pause - immediately cancels an ongoing automation pause (detected manual intervention), instead of waiting for the configured duration to expire."""
        if cover_entity_id not in self._executors or self.manual_intervention_guard is None:
            return False
        self.manual_intervention_guard.clear_pause(cover_entity_id)
        async_dispatcher_send(self.hass, f"{SIGNAL_RECOMPUTE}_{self._coordinator.entry.entry_id}")
        return True

    def request_external_trigger(
        self, cover_entity_id: str, action: str, target_time: time, source: str | None = None
    ) -> bool:
        """For service smart_shutter.set_external_trigger - sets the next target time for a shutter to a predefined external time. If it is still in the future today, it applies to today, otherwise to tomorrow (e.g. alarm clock time set shortly before midnight -> applies to the next morning)."""
        executor = self._executors.get(cover_entity_id)
        if executor is None:
            return False
        now = dt_util.now()
        candidate = datetime.combine(now.date(), target_time, tzinfo=now.tzinfo)
        if candidate <= now:
            candidate += timedelta(days=1)
        executor.set_external_override(action, candidate, source=source)
        return True

    @callback
    def _handle_notification_action(self, event: Event) -> None:
        action_str = event.data.get("action", "")
        if not action_str.startswith(f"{_ACTION_PREFIX}|"):
            return
        parts = action_str.split("|", 3)
        if len(parts) != 4:
            return
        _, command, shutter_entity_id, action = parts
        executor = self._executors.get(shutter_entity_id)
        if executor is None:
            return
        executor.handle_notification_response(command, action)

    def stop(self) -> None:
        for executor in self._executors.values():
            executor.cancel_all()
        self._executors.clear()

        if self._notifier is not None:
            self._notifier.cancel()
            self._notifier = None

        for unsub_attr in (
            "_unsub_signal",
            "_unsub_midnight",
            "_unsub_season",
            "_unsub_holiday",
            "_unsub_notification_action",
        ):
            unsub = getattr(self, unsub_attr)
            if unsub is not None:
                unsub()
                setattr(self, unsub_attr, None)
