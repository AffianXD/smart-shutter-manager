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
from .seasons import SEASONS, local_wall_time, season_at, seasonal_enabled, seasonal_key
from .temporal_exceptions import applicable_exceptions, exception_time, is_date_paused

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
        return min(candidates, key=lambda item: dt_util.as_utc(item[1]))


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
    coordinator: SmartShutterCoordinator, shutter: ManagedShutter, action: str, season: str | None = None
) -> bool:
    """Checks the open_source/close_source selection (Global/Local) - now controls the same action's type, time, and daylight saving uniformly (see requirements document section 10, extended on user request to trigger type + offset)."""
    shutter_entities = coordinator.shutter_entities.get(shutter.entity_id, {})
    source_entity = _season_entity(shutter_entities, f"{action}_source", season)
    return bool(source_entity) and source_entity.source == SOURCE_LOCAL


def get_action_type(
    coordinator: SmartShutterCoordinator, shutter: ManagedShutter, action: str, season: str | None = None
) -> str:
    """Reads the trigger type (time/sunrise/sunset) - global or local, depending on open_source/close_source."""
    season = _current_season(coordinator) if season is None else season
    use_local = _use_local_source(coordinator, shutter, action, season)
    if use_local:
        shutter_entities = coordinator.shutter_entities.get(shutter.entity_id, {})
        type_entity = _season_entity(shutter_entities, f"{action}_type", season)
    else:
        type_entity = _season_entity(coordinator.global_entities, f"{action}_type", season)

    if type_entity is None:
        return TYPE_TIME
    return type_entity.action_type


def get_sun_offset(
    coordinator: SmartShutterCoordinator, shutter: ManagedShutter, action: str, season: str | None = None
) -> timedelta:
    """Reads the configured solar offset in minutes (section 11) - global or local, depending on open_source/close_source."""
    season = _current_season(coordinator) if season is None else season
    use_local = _use_local_source(coordinator, shutter, action, season)
    if use_local:
        shutter_entities = coordinator.shutter_entities.get(shutter.entity_id, {})
        offset_entity = _season_entity(shutter_entities, f"{action}_sun_offset", season)
    else:
        offset_entity = _season_entity(coordinator.global_entities, f"{action}_sun_offset", season)

    minutes = offset_entity.native_value if offset_entity is not None else 0
    return timedelta(minutes=minutes or 0)


def _use_local_time_source(
    coordinator: SmartShutterCoordinator,
    shutter: ManagedShutter,
    action: str,
    profile: str,
    season: str | None = None,
) -> bool:
    """Granular ALS _use_local_source: controls ONLY whether the target time for
    this single profile (weekday/weekend/holiday/Custom-XYZ) comes from local or
    global - independent of trigger type (time/sun), which is still uniformly controlled via open_source/close_source. Default without
    selection: Global (existing behavior remains unchanged)."""
    shutter_entities = coordinator.shutter_entities.get(shutter.entity_id, {})
    source_entity = _season_entity(shutter_entities, f"{action}_{profile}_time_source", None if is_custom_profile(profile) else season)
    return bool(source_entity) and source_entity.source == SOURCE_LOCAL


def resolve_fixed_time(
    coordinator: SmartShutterCoordinator,
    shutter: ManagedShutter,
    action: str,
    profile: str,
    season: str | None = None,
) -> time | None:
    """Reads the target time valid for action+profile (global or local), only relevant if the trigger type is 'time'.

For custom profiles, the global value does NOT come from a dedicated time entity, but directly from the rule definition (open_time/close_time), since custom profiles are created once in the options and do not require an additional global entity."""
    season = None if is_custom_profile(profile) else (season or _current_season(coordinator))
    use_local = _use_local_time_source(coordinator, shutter, action, profile, season)

    if use_local:
        shutter_entities = coordinator.shutter_entities.get(shutter.entity_id, {})
        time_entity = _season_entity(shutter_entities, f"{action}_{profile}", season)
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

    time_entity = _season_entity(coordinator.global_entities, f"{action}_{profile}", season)
    return time_entity.native_value if time_entity is not None else None


_MAX_LOOKAHEAD_DAYS = 35  # spacious horizon, also for rare custom profiles


def _season_entity(entities: dict, key: str, season: str | None):
    # Base fallback also covers entity setup/reload before seasonal registration.
    return entities.get(seasonal_key(key, season)) or entities.get(key)


def _current_season(coordinator) -> str | None:
    return season_at(dt_util.now()) if seasonal_enabled(coordinator) else None


def _global_fixed_time(coordinator, action, profile, season):
    if is_custom_profile(profile):
        rule = coordinator.get_custom_schedule(profile)
        raw = rule.get(f"{action}_time") if rule else None
        try:
            return time.fromisoformat(raw) if raw else None
        except ValueError:
            return None
    entity = _season_entity(coordinator.global_entities, f"{action}_{profile}", season)
    return entity.native_value if entity else None


def _resolve_day(hass, coordinator, shutter, action, profile, day, tzinfo):
    """One action per local day, resolved with the season at its actual instant."""
    if shutter is not None:
        if is_date_paused(coordinator, shutter.entity_id, action, day):
            return None
        alternate_time = exception_time(coordinator, shutter.entity_id, action, day)
        if alternate_time is not None:
            return local_wall_time(day, alternate_time, tzinfo)

    custom = is_custom_profile(profile)
    seasons = SEASONS if seasonal_enabled(coordinator) and not custom else (None,)
    candidates = []
    for season in seasons:
        if shutter is None:
            type_entity = _season_entity(coordinator.global_entities, f"{action}_type", season)
            action_type = type_entity.action_type if type_entity else TYPE_TIME
            offset_entity = _season_entity(coordinator.global_entities, f"{action}_sun_offset", season)
            offset = timedelta(minutes=(offset_entity.native_value or 0) if offset_entity else 0)
            clock = _global_fixed_time(coordinator, action, profile, season)
        else:
            action_type = get_action_type(coordinator, shutter, action, season)
            offset = get_sun_offset(coordinator, shutter, action, season)
            clock = resolve_fixed_time(coordinator, shutter, action, profile, season)

        if not custom and action_type in (TYPE_SUNRISE, TYPE_SUNSET):
            event = "sunrise" if action_type == TYPE_SUNRISE else "sunset"
            midnight = local_wall_time(day, time.min, tzinfo)
            result = get_astral_event_next(hass, event, utc_point_in_time=dt_util.as_utc(midnight), offset=offset)
            moments = [result.astimezone(tzinfo)] if result else []
        elif clock is not None:
            moments = [local_wall_time(day, clock, tzinfo)]
        else:
            moments = []
        candidates.extend(moment for moment in moments if season is None or season_at(moment) == season)
    return min(candidates, key=dt_util.as_utc) if candidates else None


def _resolve_next(hass, coordinator, shutter, action, profile, now):
    area_ids = coordinator.shutter_areas.get(shutter.entity_id, []) if shutter else None
    candidate_ordinal = now.date().toordinal()
    checked_days = 0
    while checked_days < _MAX_LOOKAHEAD_DAYS and candidate_ordinal <= date.max.toordinal():
        day = date.fromordinal(candidate_ordinal)
        if shutter is not None:
            pauses = [
                rule for rule in applicable_exceptions(coordinator, shutter.entity_id, day)
                if rule["mode"] == "pause" and action in rule["actions"]
            ]
            if pauses:
                pause_end = date.fromisoformat(max(rule["end_date"] for rule in pauses))
                candidate_ordinal = pause_end.toordinal() + 1
                continue

        day_offset = (day - now.date()).days
        day_profile = profile if day_offset == 0 else determine_active_profile(hass, coordinator, day, area_ids)
        candidate = _resolve_day(hass, coordinator, shutter, action, day_profile, day, now.tzinfo)
        candidate_ordinal += 1
        checked_days += 1
        if (
            candidate is not None
            and dt_util.as_utc(candidate) > dt_util.as_utc(now)
            and (
                shutter is None
                or not is_date_paused(
                    coordinator, shutter.entity_id, action, candidate.date()
                )
            )
        ):
            return candidate
    return None


def resolve_next_datetime(
    hass: HomeAssistant,
    coordinator: SmartShutterCoordinator,
    shutter: ManagedShutter,
    action: str,
    profile: str,
    now: datetime,
) -> datetime | None:
    """Next local/global action, with manual overrides taking precedence."""
    override = coordinator.get_action_override(shutter.entity_id, action)
    if (override is not None and dt_util.as_utc(override) > dt_util.as_utc(now)
            and not is_date_paused(coordinator, shutter.entity_id, action, override.date())):
        return override
    return _resolve_next(hass, coordinator, shutter, action, profile, now)


def resolve_next_datetime_global(
    hass: HomeAssistant,
    coordinator: SmartShutterCoordinator,
    action: str,
    profile: str,
    now: datetime,
) -> datetime | None:
    """Global preview shares the same date and season resolution as execution."""
    return _resolve_next(hass, coordinator, None, action, profile, now)


def resolve_todays_datetime(
    hass: HomeAssistant,
    coordinator: SmartShutterCoordinator,
    shutter: ManagedShutter,
    action: str,
    profile: str,
    now: datetime,
) -> datetime | None:
    """Resolve today's target for restart recovery without rolling to tomorrow."""
    return _resolve_day(hass, coordinator, shutter, action, profile, now.date(), now.tzinfo)


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
            cursor = (
                (dt_util.as_utc(candidate) + timedelta(seconds=1)).astimezone(now.tzinfo)
                if now.tzinfo is not None else candidate + timedelta(seconds=1)
            )

    results.sort(key=lambda item: dt_util.as_utc(item[1]))
    return results
