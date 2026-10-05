"""Scheduler calculation for Smart Shutter Manager.

Pure, stateless calculation logic: active time profile + next
open/close time points, including sun control (Section 11).
Used by sensor.py (display) AND executor.py (actual trigger).

For solar events, HA's built-in Astral calculation is used
(homeassistant.helpers.sun) - there is no custom solar logic.

The actual triggering of cover.open_cover/close_cover is taken over
by executor.py, not this module."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_event_next
import homeassistant.util.dt as dt_util

from .const import (
    ACTION_CLOSE,
    ACTION_OPEN,
    PROFILE_HOLIDAY,
    PROFILE_WEEKDAY,
    PROFILE_WEEKEND,
    PROFILES,
    SOURCE_LOCAL,
    TYPE_SUNRISE,
    TYPE_SUNSET,
    TYPE_TIME,
    automation_registry_key,
    global_automation_registry_key,
)
from .coordinator import ManagedShutter, SmartShutterCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class ShutterSchedule:
    """Result of the scheduler calculation for a shutter."""

    active_profile: str  # "weekday" | "weekend" | "holiday"
    next_open: datetime | None
    next_close: datetime | None
    open_automation_enabled: bool = True
    close_automation_enabled: bool = True

    @property
    def next_action(self) -> tuple[str, datetime] | None:
        """Returns (action, time) of the next upcoming action."""
        candidates = [
            (ACTION_OPEN, self.next_open),
            (ACTION_CLOSE, self.next_close),
        ]
        candidates = [(a, t) for a, t in candidates if t is not None]
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[1])


def is_holiday_active(hass: HomeAssistant, holiday_entity_id: str | None) -> bool:
    """Checks the configured holiday entity (Section 8).

Works generically for binary_sensor, input_boolean AND calendar, as all three report their state as 'on' when holidays/an event are currently active - the integration does not need its own holiday logic."""
    if not holiday_entity_id:
        return False
    state = hass.states.get(holiday_entity_id)
    if state is None:
        return False
    return state.state == "on"


_OVERLAP_CHECK_HORIZON_DAYS = 730  # ~2 years, see find_overlapping_rules


def find_overlapping_rules(
    candidate: dict, others: list[dict]
) -> list[dict]:
    """Finds other custom profiles that would match 'candidate' on at least one day within the next ~2 years simultaneously (same weekday AND matching interval pattern).
Used by both the Options Flow (config_flow.py) and the WebSocket API (websocket_api.py), so both paths for custom profile management apply the exact same check."""
    candidate_weekdays = set(candidate.get("weekdays", []))
    if not candidate_weekdays:
        return []

    relevant = [r for r in others if candidate_weekdays & set(r.get("weekdays", []))]
    if not relevant:
        return []

    overlapping: list[dict] = []
    today = date.today()
    for other in relevant:
        for offset in range(_OVERLAP_CHECK_HORIZON_DAYS):
            check_date = today + timedelta(days=offset)
            if custom_schedule_matches(candidate, check_date) and custom_schedule_matches(
                other, check_date
            ):
                overlapping.append(other)
                break
    return overlapping


def is_custom_profile(profile: str) -> bool:
    """True if 'profile' is a custom user profile (instead of one of the three built-in ones: weekday/weekend/holiday)."""
    return profile not in PROFILES


def custom_schedule_matches(rule: dict, check_date: date) -> bool:
    """Checks if a Custom Schedule rule for 'check_date' is active.

Day of the week must match AND the interval (every N weeks, starting from the reference week) must be fulfilled. Weeks are aligned to Monday, so it doesn't matter on which day of the week the reference date itself falls ("every 2 weeks Mo+Do" works regardless of whether the reference date is a Monday or Thursday)."""
    if check_date.weekday() not in rule.get("weekdays", []):
        return False

    end_date_raw = rule.get("end_date")
    if end_date_raw:
        try:
            if check_date > date.fromisoformat(end_date_raw):
                return False
        except ValueError:
            pass

    interval = rule.get("interval_weeks", 1) or 1
    if interval <= 1:
        return True

    reference_raw = rule.get("reference_date")
    if not reference_raw:
        return True
    try:
        reference_date = date.fromisoformat(reference_raw)
    except ValueError:
        return True

    ref_monday = reference_date - timedelta(days=reference_date.weekday())
    check_monday = check_date - timedelta(days=check_date.weekday())
    weeks_diff = (check_monday - ref_monday).days // 7
    return weeks_diff % interval == 0


def determine_active_profile(
    hass: HomeAssistant,
    coordinator: SmartShutterCoordinator,
    today: date | None = None,
    area_ids: list[str] | None = None,
) -> str:
    """Determines the active time profile for the specified (or today's) day. Order (highest priority first):
  1. Custom profiles (first matching rule in list order)
  2. Holidays (only on the weekdays configured in ferien_wochentage
     Default Mon-Fri - on weekends, normal weekend applies even if the holiday sensor is on)
  3. Weekend / workday

area_ids (v0.19): the area IDs of the shutter for which the
profile is determined (None = no specific shutter, e.g. the
global dashboard preview). Custom profiles with set
rule["area_id"] (private area profiles, see FEAT "Guests should
be able to set everything for their area") apply ONLY to shutters
that belong to this area - they are completely ignored (not visible or effective) for all other shutters, so that a private profile of a guest area never accidentally affects shutters of other areas or the host. Profiles WITHOUT area_id (shared, the previous default) still apply to all shutters."""
    check_date = today or date.today()
    area_id_set = set(area_ids) if area_ids else set()

    matches = [
        rule
        for rule in coordinator.custom_schedules
        if custom_schedule_matches(rule, check_date)
        and (not rule.get("area_id") or rule["area_id"] in area_id_set)
    ]
    if matches:
        if len(matches) > 1:
            _LOGGER.warning(
                "Mehrere Custom-Profile treffen am %s gleichzeitig zu (%s) - "
                "es gewinnt das zuerst definierte: %s",
                check_date,
                [m.get("name", m.get("id")) for m in matches],
                matches[0].get("name", matches[0].get("id")),
            )
        return matches[0]["id"]

    if is_holiday_active(hass, coordinator.holiday_entity_id) and (
        check_date.weekday() in coordinator.holiday_weekdays
    ):
        return PROFILE_HOLIDAY

    return PROFILE_WEEKEND if check_date.weekday() >= 5 else PROFILE_WEEKDAY


def _use_local_source(
    coordinator: SmartShutterCoordinator, shutter: ManagedShutter, action: str
) -> bool:
    """Checks the open_source/close_source selection (Global/Local) - now controls the same action's type, time, and daylight saving uniformly (see requirements document section 10, extended on user request to trigger type + offset)."""
    shutter_entities = coordinator.shutter_entities.get(shutter.entity_id, {})
    source_entity = shutter_entities.get(f"{action}_source")
    return bool(source_entity) and source_entity.source == SOURCE_LOCAL


def get_action_type(
    coordinator: SmartShutterCoordinator, shutter: ManagedShutter, action: str
) -> str:
    """Reads the trigger type (time/sunrise/sunset) - global or local, depending on open_source/close_source."""
    use_local = _use_local_source(coordinator, shutter, action)
    if use_local:
        shutter_entities = coordinator.shutter_entities.get(shutter.entity_id, {})
        type_entity = shutter_entities.get(f"{action}_type")
    else:
        type_entity = coordinator.global_entities.get(f"{action}_type")

    if type_entity is None:
        return TYPE_TIME
    return type_entity.action_type


def get_sun_offset(
    coordinator: SmartShutterCoordinator, shutter: ManagedShutter, action: str
) -> timedelta:
    """Reads the configured solar offset in minutes (section 11) - global or local, depending on open_source/close_source."""
    use_local = _use_local_source(coordinator, shutter, action)
    if use_local:
        shutter_entities = coordinator.shutter_entities.get(shutter.entity_id, {})
        offset_entity = shutter_entities.get(f"{action}_sun_offset")
    else:
        offset_entity = coordinator.global_entities.get(f"{action}_sun_offset")

    minutes = offset_entity.native_value if offset_entity is not None else 0
    return timedelta(minutes=minutes or 0)


def _use_local_time_source(
    coordinator: SmartShutterCoordinator,
    shutter: ManagedShutter,
    action: str,
    profile: str,
) -> bool:
    """Granular ALS _use_local_source: controls ONLY whether the target time for
    this single profile (weekday/weekend/holiday/Custom-XYZ) comes from local or
    global - independent of trigger type (time/sun), which is still uniformly controlled via open_source/close_source. Default without
    selection: Global (existing behavior remains unchanged)."""
    shutter_entities = coordinator.shutter_entities.get(shutter.entity_id, {})
    source_entity = shutter_entities.get(f"{action}_{profile}_time_source")
    return bool(source_entity) and source_entity.source == SOURCE_LOCAL


def resolve_fixed_time(
    coordinator: SmartShutterCoordinator,
    shutter: ManagedShutter,
    action: str,
    profile: str,
) -> time | None:
    """Reads the target time valid for action+profile (global or local), only relevant if the trigger type is 'time'.

For custom profiles, the global value does NOT come from a dedicated time entity, but directly from the rule definition (open_time/close_time), since custom profiles are created once in the options and do not require an additional global entity."""
    use_local = _use_local_time_source(coordinator, shutter, action, profile)

    if use_local:
        shutter_entities = coordinator.shutter_entities.get(shutter.entity_id, {})
        time_entity = shutter_entities.get(f"{action}_{profile}")
        if time_entity is not None and time_entity.native_value is not None:
            return time_entity.native_value
        # "Individual" selected, but never had a custom value
        # set (native_value is None, e.g. just set via the
        # Map switched, without a time already entered
        # was). WITHOUT this fallback, resolve_fixed_time provided here
        # permanently None -> resolve_next_datetime failed across ALL
        # 35 days in the lookahead window -> the action was completely
        # and without any error message unplanned. Instead: on the
        # fall back to a global value until the user explicitly specifies one
        # enters their own time.
        _LOGGER.warning(
            "Smart Shutter Manager: %s has for '%s'/%s the time source 'Individual', but no own time set yet - temporarily using the global value.",
            shutter.entity_id,
            profile,
            action,
        )

    if is_custom_profile(profile):
        rule = coordinator.get_custom_schedule(profile)
        if rule is None:
            return None
        raw = rule.get(f"{action}_time")
        if not raw:
            return None
        try:
            return time.fromisoformat(raw)
        except ValueError:
            _LOGGER.warning(
                'Invalid time in Custom Profile %s (%s): %s', profile, action, raw
            )
            return None

    time_entity = coordinator.global_entities.get(f"{action}_{profile}")
    return time_entity.native_value if time_entity is not None else None


_MAX_LOOKAHEAD_DAYS = 35  # spacious horizon, also for rare custom profiles


def resolve_next_datetime(
    hass: HomeAssistant,
    coordinator: SmartShutterCoordinator,
    shutter: ManagedShutter,
    action: str,
    profile: str,
    now: datetime,
) -> datetime | None:
    """Calculates the next execution time for an action,
    regardless of whether it is time-based or sun-based - used by sensor.py AND
    executor.py, so that both calculate exactly the same.

    Important: iterates day by day (instead of just looking at "today" and
    blindly adding +1 day if needed), because the active profile can change
    from day to day (workday/weekend switch, holiday start/end, or a custom
    profile that only applies on certain weekdays). Without this, e.g.
    a custom profile that only applies on Thursdays would incorrectly
    continue using Thursday times on a Friday, instead of correctly falling
    back to holidays/weekend/workday."""
    # Active shift/skip override (from the warning,
    # see executor.py) takes precedence - and "expires" automatically once
    # its time has passed (no manual cleanup needed)
    override = coordinator.get_action_override(shutter.entity_id, action)
    if override is not None and override > now:
        return override

    area_ids = coordinator.shutter_areas.get(shutter.entity_id, [])

    # The TRIGGER TYPE (time/sunrise/sunset) is not
    # profile-dependent and does not change from day to day - only once
    # determine. Exception: on days with an active custom profile, ALWAYS
    # uses a fixed time, regardless of the trigger type (see
    # const.py - Custom profiles intentionally do not support solar position).
    action_type = get_action_type(coordinator, shutter, action)
    offset: timedelta | None = None

    for day_offset in range(_MAX_LOOKAHEAD_DAYS):
        candidate_date = (now + timedelta(days=day_offset)).date()
        # For "today", the passed 'profile' is already correct
        # (saves a recalculation); for all following days, this
        # active profile is determined again.
        day_profile = (
            profile
            if day_offset == 0
            else determine_active_profile(hass, coordinator, candidate_date, area_ids)
        )

        if is_custom_profile(day_profile):
            target_time = resolve_fixed_time(coordinator, shutter, action, day_profile)
            if target_time is None:
                continue  # This rule does not cover this action -> next day
            candidate_dt = datetime.combine(candidate_date, target_time, tzinfo=now.tzinfo)
        elif action_type in (TYPE_SUNRISE, TYPE_SUNSET):
            event = "sunrise" if action_type == TYPE_SUNRISE else "sunset"
            if offset is None:
                offset = get_sun_offset(coordinator, shutter, action)
            midnight = datetime.combine(candidate_date, time.min, tzinfo=now.tzinfo)
            result = get_astral_event_next(
                hass, event, utc_point_in_time=dt_util.as_utc(midnight), offset=offset
            )
            if result is None:
                continue
            candidate_dt = dt_util.as_local(result)
        else:
            target_time = resolve_fixed_time(coordinator, shutter, action, day_profile)
            if target_time is None:
                continue
            candidate_dt = datetime.combine(candidate_date, target_time, tzinfo=now.tzinfo)

        if candidate_dt > now:
            return candidate_dt

    return None


def resolve_next_datetime_global(
    hass: HomeAssistant,
    coordinator: SmartShutterCoordinator,
    action: str,
    profile: str,
    now: datetime,
) -> datetime | None:
    """Like resolve_next_datetime, but exclusively calculated from global Entities - independent of whether individual shutters override locally. For global preview display (Dashboard). Uses the same day-by-day logic as resolve_next_datetime (see there for the reasoning)."""
    type_entity = coordinator.global_entities.get(f"{action}_type")
    action_type = type_entity.action_type if type_entity is not None else TYPE_TIME
    offset_entity = coordinator.global_entities.get(f"{action}_sun_offset")
    offset_minutes = offset_entity.native_value if offset_entity is not None else 0
    offset = timedelta(minutes=offset_minutes or 0)

    for day_offset in range(_MAX_LOOKAHEAD_DAYS):
        candidate_date = (now + timedelta(days=day_offset)).date()
        day_profile = (
            profile
            if day_offset == 0
            else determine_active_profile(hass, coordinator, candidate_date)
        )

        if is_custom_profile(day_profile):
            rule = coordinator.get_custom_schedule(day_profile)
            target_time = None
            if rule is not None:
                raw = rule.get(f"{action}_time")
                if raw:
                    try:
                        target_time = time.fromisoformat(raw)
                    except ValueError:
                        target_time = None
            if target_time is None:
                continue
            candidate_dt = datetime.combine(candidate_date, target_time, tzinfo=now.tzinfo)
        elif action_type in (TYPE_SUNRISE, TYPE_SUNSET):
            event = "sunrise" if action_type == TYPE_SUNRISE else "sunset"
            midnight = datetime.combine(candidate_date, time.min, tzinfo=now.tzinfo)
            result = get_astral_event_next(
                hass, event, utc_point_in_time=dt_util.as_utc(midnight), offset=offset
            )
            if result is None:
                continue
            candidate_dt = dt_util.as_local(result)
        else:
            time_entity = coordinator.global_entities.get(f"{action}_{day_profile}")
            target_time = time_entity.native_value if time_entity is not None else None
            if target_time is None:
                continue
            candidate_dt = datetime.combine(candidate_date, target_time, tzinfo=now.tzinfo)

        if candidate_dt > now:
            return candidate_dt

    return None


def resolve_todays_datetime(
    hass: HomeAssistant,
    coordinator: SmartShutterCoordinator,
    shutter: ManagedShutter,
    action: str,
    profile: str,
    now: datetime,
) -> datetime | None:
    """Like resolve_next_datetime, but WITHOUT rollover to tomorrow - provides the time calculated for TODAY, even if it is in the past. Only used for catch-up check after HA restart (executor.py), not for display/regular arm."""
    if is_custom_profile(profile):
        target_time = resolve_fixed_time(coordinator, shutter, action, profile)
        if target_time is None:
            return None
        return datetime.combine(now.date(), target_time, tzinfo=now.tzinfo)

    action_type = get_action_type(coordinator, shutter, action)

    if action_type in (TYPE_SUNRISE, TYPE_SUNSET):
        event = "sunrise" if action_type == TYPE_SUNRISE else "sunset"
        offset = get_sun_offset(coordinator, shutter, action)
        midnight_today = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
        result = get_astral_event_next(
            hass, event, utc_point_in_time=dt_util.as_utc(midnight_today), offset=offset
        )
        return dt_util.as_local(result) if result else None

    target_time = resolve_fixed_time(coordinator, shutter, action, profile)
    if target_time is None:
        return None
    return datetime.combine(now.date(), target_time, tzinfo=now.tzinfo)


def is_automation_enabled(
    coordinator: SmartShutterCoordinator, action: str, shutter: ManagedShutter | None = None
) -> bool:
    """Checks if automation is active for an action (global AND, if a shutter is specified, also locally) - exactly the same logic as executor.ShutterActionExecutor._execute(). This way, sensor.next_action (and also the Custom-UI card) never shows a time that would not be executed because automation is deactivated (bugfix: previously "Close at 20:00" was shown, even if automation for closing was explicitly deactivated)."""
    global_switch = coordinator.global_entities.get(global_automation_registry_key(action))
    if global_switch is not None and not global_switch.is_on:
        return False
    if shutter is not None:
        shutter_entities = coordinator.shutter_entities.get(shutter.entity_id, {})
        local_switch = shutter_entities.get(automation_registry_key(action))
        if local_switch is not None and not local_switch.is_on:
            return False
    return True


def compute_global_schedule(
    hass: HomeAssistant,
    coordinator: SmartShutterCoordinator,
    now: datetime | None = None,
) -> ShutterSchedule:
    """Like compute_schedule, but for the global preview (no specific shutter) - shows what the global settings would currently do."""
    now = now or dt_util.now()
    profile = determine_active_profile(hass, coordinator, now.date())

    open_enabled = is_automation_enabled(coordinator, ACTION_OPEN)
    close_enabled = is_automation_enabled(coordinator, ACTION_CLOSE)

    next_open = (
        resolve_next_datetime_global(hass, coordinator, ACTION_OPEN, profile, now)
        if open_enabled
        else None
    )
    next_close = (
        resolve_next_datetime_global(hass, coordinator, ACTION_CLOSE, profile, now)
        if close_enabled
        else None
    )

    return ShutterSchedule(
        active_profile=profile,
        next_open=next_open,
        next_close=next_close,
        open_automation_enabled=open_enabled,
        close_automation_enabled=close_enabled,
    )


def compute_schedule(
    hass: HomeAssistant,
    coordinator: SmartShutterCoordinator,
    shutter: ManagedShutter,
    now: datetime | None = None,
) -> ShutterSchedule:
    """Calculates the active profile as well as the next open/close times."""
    now = now or dt_util.now()
    profile = determine_active_profile(
        hass, coordinator, now.date(), coordinator.shutter_areas.get(shutter.entity_id, [])
    )

    open_enabled = is_automation_enabled(coordinator, ACTION_OPEN, shutter)
    close_enabled = is_automation_enabled(coordinator, ACTION_CLOSE, shutter)

    next_open = (
        resolve_next_datetime(hass, coordinator, shutter, ACTION_OPEN, profile, now)
        if open_enabled
        else None
    )
    next_close = (
        resolve_next_datetime(hass, coordinator, shutter, ACTION_CLOSE, profile, now)
        if close_enabled
        else None
    )

    return ShutterSchedule(
        active_profile=profile,
        next_open=next_open,
        next_close=next_close,
        open_automation_enabled=open_enabled,
        close_automation_enabled=close_enabled,
    )


# Security threshold for compute_forecast() - if resolve_next_datetime
# for some reason remain stuck at the same point in time,
# prevents an infinite loop (should never be reached in practice
# see the comment below).
_FORECAST_MAX_ITERATIONS_PER_ACTION = 60


def compute_forecast(
    hass: HomeAssistant,
    coordinator: SmartShutterCoordinator,
    shutter: ManagedShutter,
    days: int,
    now: datetime | None = None,
    include_disabled: bool = False,
) -> list[tuple[str, datetime]]:
    """Calculates the upcoming open/close appointments for ONE shutter over the next `days` days (forecast timeline, see card "Timeline" - native HA history can only show past by definition, future must be calculated manually).

Simply iterates compute_schedule() repeatedly with a progressing `now` cursor per action (open/close separated) - exactly the same principle that resolve_next_datetime already uses for the 35-day lookahead of a single action, here just multiple times in a row per action, until the horizon is exceeded.

Returns a time-sorted list (action, datetime). Starts deliberately at the beginning of today (00:00), not at "now" - otherwise, already past but today-occurring appointments would completely disappear from the display (bug report: "Timeline points for today disappear if the event has already passed"). The actual scheduling (real triggering) is unaffected by this - this function is only used for the forecast display in the card, never for real triggering."""
    now = now or dt_util.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = day_start + timedelta(days=days)
    results: list[tuple[str, datetime]] = []

    for action in (ACTION_OPEN, ACTION_CLOSE):
        if not include_disabled and not is_automation_enabled(coordinator, action, shutter):
            continue
        cursor = day_start
        area_ids = coordinator.shutter_areas.get(shutter.entity_id, [])
        for _ in range(_FORECAST_MAX_ITERATIONS_PER_ACTION):
            profile = determine_active_profile(hass, coordinator, cursor.date(), area_ids)
            candidate = resolve_next_datetime(hass, coordinator, shutter, action, profile, cursor)
            if candidate is None or candidate > horizon:
                break
            results.append((action, candidate))
            # Search further a microsecond after the found time,
            # otherwise the same date would be found again (infinite loop).
            cursor = candidate + timedelta(seconds=1)

    results.sort(key=lambda item: item[1])
    return results
