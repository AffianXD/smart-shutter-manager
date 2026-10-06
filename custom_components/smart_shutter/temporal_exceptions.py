"""Whole-day exceptions, shared by validation, scheduling and execution."""
from __future__ import annotations

from datetime import date, time

from .const import CONF_TEMPORAL_EXCEPTIONS


def prune_exception_history(hass, entry, today: date, max_count: int) -> tuple[list[dict], bool]:
    """Persist the bounded expired history and return its current rules."""
    current = entry.options.get(CONF_TEMPORAL_EXCEPTIONS, [])
    retained = prune_expired_exceptions(current, today, max_count)
    if retained == current:
        return retained, False
    hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_TEMPORAL_EXCEPTIONS: retained})
    return retained, True


def exception_targets(rule: dict, coordinator, shutter_areas: dict | None = None) -> set[str]:
    """Resolve current area members, retaining missing explicit targets for display."""
    areas = set(rule.get("area_ids", []))
    memberships = coordinator.shutter_areas if shutter_areas is None else shutter_areas
    return set(rule.get("cover_ids", [])) | {
        cover for cover, cover_areas in memberships.items()
        if areas.intersection(cover_areas)
    }


def applicable_exceptions(coordinator, cover_id: str, day: date) -> list[dict]:
    return [
        rule for rule in getattr(coordinator, "temporal_exceptions", [])
        if rule["start_date"] <= day.isoformat() <= rule["end_date"]
        and cover_id in exception_targets(rule, coordinator)
    ]


def prune_expired_exceptions(rules: list[dict], today: date, max_count: int) -> list[dict]:
    """Keep every current/future exception and only the most recently expired ones."""
    if max_count < 0:
        raise ValueError("max_count cannot be negative")
    expired: list[tuple[int, str, str, str]] = []
    for index, rule in enumerate(rules):
        try:
            end = date.fromisoformat(rule["end_date"])
        except (KeyError, TypeError, ValueError):
            continue
        if end < today:
            expired.append((index, end.isoformat(), str(rule.get("start_date", "")), str(rule.get("id", ""))))
    retained = {item[0] for item in sorted(expired, key=lambda item: item[1:], reverse=True)[:max_count]}
    expired_indexes = {item[0] for item in expired}
    return [rule for index, rule in enumerate(rules) if index not in expired_indexes or index in retained]


def is_date_paused(coordinator, cover_id: str, action: str, day: date) -> bool:
    return any(
        rule["mode"] == "pause" and action in rule["actions"]
        for rule in applicable_exceptions(coordinator, cover_id, day)
    )


def exception_time(coordinator, cover_id: str, action: str, day: date) -> time | None:
    for rule in applicable_exceptions(coordinator, cover_id, day):
        if rule["mode"] == "times" and rule.get(f"{action}_time"):
            return time.fromisoformat(rule[f"{action}_time"])
    return None


def exception_allowed(rule: dict, allowed_area_ids: set[str] | None) -> bool:
    """Guests can manage a single assigned area's rules, never shared host rules."""
    return allowed_area_ids is None or (
        not rule.get("cover_ids") and len(rule.get("area_ids", [])) == 1
        and rule["area_ids"][0] in allowed_area_ids
    )


def validate_exception(rule: dict, coordinator, existing: dict | None = None) -> str | None:
    """Reject malformed fields before storing or evaluating a rule."""
    if rule.get("mode") not in ("pause", "times"):
        return "invalid_mode"
    try:
        start = date.fromisoformat(rule["start_date"])
        end = date.fromisoformat(rule["end_date"])
    except (KeyError, TypeError, ValueError):
        return "invalid_dates"
    if start > end or rule["start_date"] != start.isoformat() or rule["end_date"] != end.isoformat():
        return "invalid_dates"
    for key in ("cover_ids", "area_ids"):
        values = rule.get(key)
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            return "invalid_targets"
    if not (rule["cover_ids"] or rule["area_ids"]):
        return "invalid_targets"
    # Existing missing targets can be retained; newly invented ones cannot.
    known_covers = set(coordinator.shutters) | set((existing or {}).get("cover_ids", []))
    known_areas = {area["id"] for area in coordinator.custom_areas} | set((existing or {}).get("area_ids", []))
    if set(rule["cover_ids"]) - known_covers or set(rule["area_ids"]) - known_areas:
        return "invalid_targets"
    if rule["mode"] == "pause":
        actions = rule.get("actions")
        if not isinstance(actions, list) or not actions or any(a not in ("open", "close") for a in actions):
            return "invalid_actions"
    else:
        if not (rule.get("open_time") or rule.get("close_time")):
            return "missing_times"
        for action in ("open", "close"):
            value = rule.get(f"{action}_time")
            if value is not None:
                try:
                    parsed = time.fromisoformat(value)
                    if len(value) != 5 or parsed.tzinfo is not None:
                        return "invalid_times"
                except (TypeError, ValueError):
                    return "invalid_times"
    return None


def conflicting_exceptions(
    rule: dict,
    others: list[dict],
    coordinator,
    shutter_areas: dict | None = None,
) -> list[dict]:
    if rule["mode"] != "times":
        return []
    targets = exception_targets(rule, coordinator, shutter_areas)
    return [
        other for other in others
        if other["mode"] == "times"
        and rule["start_date"] <= other["end_date"]
        and other["start_date"] <= rule["end_date"]
        and (targets & exception_targets(other, coordinator, shutter_areas)
             or set(rule["area_ids"]) & set(other["area_ids"]))
        and any(rule.get(f"{a}_time") and other.get(f"{a}_time") for a in ("open", "close"))
    ]


def conflicting_exception_pairs(
    rules: list[dict], coordinator, shutter_areas: dict | None = None
) -> list[tuple[dict, dict]]:
    """Find rule pairs that would target the same shutter at overlapping times."""
    conflicts = []
    for index, rule in enumerate(rules):
        conflicts.extend(
            (rule, other)
            for other in conflicting_exceptions(rule, rules[index + 1 :], coordinator, shutter_areas)
        )
    return conflicts
