"""Constants for Smart Shutter Manager."""
from __future__ import annotations

from datetime import time

from homeassistant.const import Platform

DOMAIN = "smart_shutter"

# Config-Entry Keys (Config Flow)
CONF_COVERS = "covers"          # List of selected cover.* entity_ids
CONF_NAMES = "names"            # Mapping entity_id -> display name

# Options Keys (Options Flow, Version 0.2+)
CONF_HOLIDAY_ENTITY = "holiday_entity"  # e.g. binary_sensor.schulferien
CONF_FROST_ENTITY = "frost_entity"      # e.g. binary_sensor.frost_sensor
CONF_OUTSIDE_TEMP_SENSOR = "outside_temp_sensor"  # global outdoor temperature sensor (sensor.*)
CONF_INSIDE_TEMP_SENSOR = "inside_temp_sensor"    # global indoor temperature sensor (fallback, sensor.*)
CONF_FROST_THRESHOLD_C = "frost_threshold_c"      # Threshold in °C, frost protection active at <= threshold
CONF_NOTIFY_SERVICE = "notify_service"  # e.g. "notify.notify" or "notify.mobile_app_..."
CONF_PRE_NOTIFY_LEAD = "pre_notify_lead_minutes"  # Warning X minutes in advance
CONF_POSTPONE_OPTIONS = "postpone_options_minutes"  # e.g. "5,10,15"
CONF_CATCH_UP_WINDOW = "catch_up_window_minutes"  # Catch-up window after restart
CONF_NOTIFY_TEXT_MOVED = "notify_text_moved"      # Jinja-Template
CONF_NOTIFY_TEXT_FROST = "notify_text_frost"      # Jinja-Template
CONF_NOTIFY_TEXT_PRECLOSE = "notify_text_preclose"  # Jinja-Template
CONF_NOTIFICATION_MAX_AGE = "notification_max_age_minutes"  # Ignore buttons of older notifications
CONF_MANUAL_PAUSE_MINUTES = "manual_pause_minutes"  # Automation pause after detected manual intervention
CONF_HOLIDAY_WEEKDAYS = "holiday_weekdays"
CONF_STAGGER_DELAY_MS = "stagger_delay_ms"  # Staggered command output, RF collision protection

# Defaults for the above-mentioned Options (all editable by the user)
DEFAULT_PRE_NOTIFY_LEAD_MINUTES = 5
DEFAULT_POSTPONE_OPTIONS_MINUTES: list[int] = [5, 10, 15]
DEFAULT_CATCH_UP_WINDOW_MINUTES = 120
DEFAULT_NOTIFICATION_MAX_AGE_MINUTES = 30
DEFAULT_MANUAL_PAUSE_MINUTES = 60
# Frost protection threshold (°C) for temperature-based frost protection
# (v0.17): Automation paused (like a manual intervention, see
# manual_intervention.py) for a shutter, as soon as the effective
# Indoor OR outdoor temperature falls below this value.
DEFAULT_FROST_THRESHOLD_C = 3.0
# Default Mo-Fr (Python date.weekday(): Monday=0 ... Sunday=6) - at
# Wochenende soll ohne explizite Konfiguration weiterhin das normale
# Wochenende-Profil gelten, auch wenn der Ferien-Sensor "an" ist.
DEFAULT_HOLIDAY_WEEKDAYS: list[str] = ["0", "1", "2", "3", "4"]
# 0 = off (default) - Commands to multiple shutters are executed simultaneously
# output as before. Value = milliseconds delay between
# each individual shutter during multiple actions (global schedule,
# Sun position area rule, "All shutters up/down/stop"
# RF collision protection for motor-based systems, see README.
DEFAULT_STAGGER_DELAY_MS = 0
MAX_STAGGER_DELAY_MS = 5000

# Standard notification texts as Jinja templates (freely available via the
# Options Flow customizable). Available variables:
# notify_text_moved:    names, count, action, trigger
# notify_text_frost:    names, count
# notify_text_preclose: name, time, action
DEFAULT_NOTIFY_TEXT_MOVED = (
    "{{ names }} {{ 'was' if count == 1 else 'were' }} {{ action }}. "
    "Trigger: {{ trigger }}."
)
DEFAULT_NOTIFY_TEXT_FROST = "Frost protection active: {{ names }} will not move."
DEFAULT_NOTIFY_TEXT_PRECLOSE = "{{ name }} closes at {{ time }}."

# Events fired by executor.py - for your own automations (event triggers)
EVENT_MOVED = f"{DOMAIN}_moved"
EVENT_FROST_BLOCKED = f"{DOMAIN}_frost_blocked"
EVENT_MANUAL_OVERRIDE = f"{DOMAIN}_manual_override"

# Services, through which own automations/scripts can intervene
SERVICE_SKIP_ACTION = "skip_action"
SERVICE_POSTPONE_ACTION = "postpone_action"
SERVICE_CLEAR_OVERRIDE = "clear_override"
SERVICE_CLEAR_MANUAL_PAUSE = "clear_manual_pause"

# Minimum features a cover must support to be recognized
# (SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP)
REQUIRED_COVER_FEATURES = 0b00000011 | 0b00001000  # OPEN(1) | CLOSE(2) | STOP(8)

# Platforms rolled out from this version.
PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SELECT,
    Platform.TIME,
    Platform.NUMBER,
    Platform.SENSOR,
]

# Internal storage in hass.data[DOMAIN][entry_id]
DATA_COORDINATOR = "coordinator"
DATA_SCHEDULER_MANAGER = "scheduler_manager"

# Dispatcher signal (per config entry with entry_id suffix), via which
# select.py/time.py/number.py triggers an immediate recalculation of the sensors
# AND a new planning of the actual Triggers (executor.py).
SIGNAL_RECOMPUTE = f"{DOMAIN}_recompute"

# ID of the shared "global" device, where the global
# Time-profile entities (see requirements document Section 9).
GLOBAL_DEVICE_ID = f"{DOMAIN}_global"

# Registry key of the global Master Automation Switch (switch.py) -
# switches ALL shutters at once, without touching each one individually
# to have to.
# Registry keys for the (since v0.6.2) separated automation -
# Switches - Opening and closing can be done independently
# deactivate each other, locally (per shutter) AND globally.
# Local registry key (coordinator.shutter_entities): automation_open / automation_close
# Global registry key (coordinator.global_entities): global_automation_open / global_automation_close
def automation_registry_key(action: str) -> str:
    return f"automation_{action}"


def global_automation_registry_key(action: str) -> str:
    return f"global_automation_{action}"

# Time profiles (requirements document Section 8) and actions (Open/Close)
PROFILE_WEEKDAY = "weekday"
PROFILE_WEEKEND = "weekend"
PROFILE_HOLIDAY = "holiday"
PROFILES: list[str] = [PROFILE_WEEKDAY, PROFILE_WEEKEND, PROFILE_HOLIDAY]

# Keep historical unique IDs stable so existing Home Assistant entities retain
# their entity IDs when the internal profile keys become language neutral.
LEGACY_PROFILE_IDS = {
    PROFILE_WEEKDAY: "werktag",
    PROFILE_WEEKEND: "wochenende",
    PROFILE_HOLIDAY: "ferien",
}

ACTION_OPEN = "open"
ACTION_CLOSE = "close"
ACTIONS: list[str] = [ACTION_OPEN, ACTION_CLOSE]

# Sources for the time control of a single shutter (only relevant,
# if the trigger type is "time", see TYPE_TIME below)
SOURCE_GLOBAL = "global"
SOURCE_LOCAL = "local"
SOURCE_OPTIONS: list[str] = [SOURCE_GLOBAL, SOURCE_LOCAL]

# Trigger type per action (requirements document section 6+11): time or
# Solar event. On user request, this applies both for open and
# close (requirements document refers to it only for "close_type") - however with
# each only the meaningful sun option (Open -> sunrise,
# Closes at sunset, not both.
TYPE_TIME = "time"
TYPE_SUNRISE = "sunrise"
TYPE_SUNSET = "sunset"

ACTION_TYPE_OPTIONS_BY_ACTION: dict[str, list[str]] = {
    ACTION_OPEN: [TYPE_TIME, TYPE_SUNRISE],
    ACTION_CLOSE: [TYPE_TIME, TYPE_SUNSET],
}

# Default values for the global time profiles (Requirements Document Section 9).
# Local overrides start with the same values until the user changes them.
DEFAULT_TIMES: dict[tuple[str, str], time] = {
    (ACTION_OPEN, PROFILE_WEEKDAY): time(7, 0),
    (ACTION_OPEN, PROFILE_WEEKEND): time(8, 30),
    (ACTION_OPEN, PROFILE_HOLIDAY): time(9, 0),
    (ACTION_CLOSE, PROFILE_WEEKDAY): time(21, 30),
    (ACTION_CLOSE, PROFILE_WEEKEND): time(22, 30),
    (ACTION_CLOSE, PROFILE_HOLIDAY): time(22, 0),
}

# Sun offset per action: -120 to +120 minutes (Section 11)
SUN_OFFSET_MIN = -120
SUN_OFFSET_MAX = 120
SUN_OFFSET_DEFAULT = 0

# --- Custom profiles (v0.6): user-defined, recurring exceptions ---
# Are set ONCE in the options and apply globally for
# ALL shutters (but can be configured per shutter like any other profile through
# a local time can be overwritten, see "{action}_{profile}_time_source").
# Custom Profiles intentionally support ONLY fixed times (no solar position).
CONF_CUSTOM_SCHEDULES = "custom_schedules"  # list[dict], see structure below
CONF_SHUTTER_NOTES = "shutter_notes"  # dict[cover_entity_id, str] - see coordinator.get_shutter_note()

# Structure of a Custom Schedule entry (dict, JSON-serializable):
# id:              str   - stable unique ID, e.g. "custom_3f9a1b2c"
# name:            str   - display name, freely selectable by the user
# weekdays:        list[int]  - 0=Monday ... 6=Sunday (datetime.weekday())
# interval_weeks:  int   - 1 = every week, 2 = every second week, ...
# reference_date:  str   - ISO date (YYYY-MM-DD), reference week for the interval
# end_date:        str | None - ISO date from which the rule no longer applies (optional)
# open_time:       str | None - ISO time (HH:MM), None = leave open unchanged
# close_time:      str | None - ISO time (HH:MM), None = leave closed unchanged
CUSTOM_SCHEDULE_ID_PREFIX = "custom_"
DEFAULT_CUSTOM_SCHEDULE_INTERVAL_WEEKS = 1

# Weekday abbreviations for the options flow (ISO weekday order).
WEEKDAY_KEYS: list[str] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# External triggers (v0.7) are named rules whose target time is set by a
# service call rather than a calendar pattern. They use the same override
# mechanism as postpone and skip actions. Once set, an external trigger takes
# priority over all profiles until its scheduled time has passed.
CONF_EXTERNAL_TRIGGERS = "external_triggers"  # list[dict], see structure below

# Structure of an External Trigger Entry (dict, JSON serializable):
# id:         str - stable unique ID, e.g. "trigger_3f9a1b2c"
# name:       str - name assigned by the user, used in the service
# smart_shutter.set_external_trigger used as a reference
# entity_id:  str|None - the cover.* entity for which this trigger applies
# (used exclusively with area_id - exactly one of the two is set)
# area_id:    str|None - area whose shutters ALL are triggered
# (v0.20.2) - for example, an entire bedroom via a wake-up automation
# action:     str - "open" or "close"
EXTERNAL_TRIGGER_ID_PREFIX = "trigger_"

SERVICE_SET_EXTERNAL_TRIGGER = "set_external_trigger"

# Custom areas (v0.11) group shutters under user-defined names. An area stores
# default trigger types, sun offsets, and target positions for open and close.
# Applying an area's settings copies them to each member's individual entities
# and reschedules their actions. Areas are presets, not an additional scheduler
# resolution layer between global and individual settings. A shutter may belong
# to multiple areas.
CONF_CUSTOM_AREAS = "custom_areas"  # list[dict], see structure below
CONF_SHUTTER_AREAS = "shutter_areas"  # dict[cover_entity_id, list[area_id]] (since v0.16, previously: single area_id-String)

# Structure of a Custom Area entry (dict, JSON-serializable):
# id:                str       - stable unique ID, e.g. "area_3f9a1b2c"
# name:              str       - display name, freely selectable by the user (e.g. "Hinten")
# open_type:         str|None  - "time"/"sunrise", None = do not overwrite
# close_type:        str|None  - "time"/"sunset", None = do not override
# open_sun_offset:   int|None  - minutes, None = do not overwrite
# close_sun_offset:  int|None  - minutes, None = do not overwrite
# open_position:     int|None  - 0-100, None = do not overwrite
# close_position:    int|None  - 0-100, None = do not overwrite
# sun_position_enabled: bool   - Is solar position control active? (v0.13)
# sun_azimuth_from:  int|None  - 0-360°, start of the azimuth area
# sun_azimuth_to:    int|None  - 0-360°, End (Wrap-around over 360°/0° supported)
# sun_elevation_min: float|None - Minimum sun height in degrees
# sun_elevation_hysteresis: float|None - Hysteresis buffer in degrees (default 0).
# First when the elevation drops by this amount BELOW the minimum height
# (or when the Azimuth leaves the area), the rule can trigger again.
# sun_position_target: int|None - 0-100, target position when rule is active
# sun_condition_template: str|None - freely definable Jinja template,
# must additionally result in "true" alongside Azimuth/Elevation (e.g.
# Outdoor/indoor temperature comparison). Fail-closed in case of errors.
# sun_notify_enabled: bool  - Send notification when the rule is triggered?
# sun_notify_text:    str|None - Jinja template, variables: area, count,
# position, names. None/empty = default text.
CUSTOM_AREA_ID_PREFIX = "area_"

# Target position (v0.7): opening and closing may use positions other than
# 100% and 0%. A global value can be overridden for each shutter, separately
# from the profile-specific times.
POSITION_MIN = 0
POSITION_MAX = 100
DEFAULT_POSITION: dict[str, int] = {ACTION_OPEN: 100, ACTION_CLOSE: 0}


def position_registry_key(action: str) -> str:
    return f"{action}_position"


def position_source_registry_key(action: str) -> str:
    return f"{action}_position_source"
