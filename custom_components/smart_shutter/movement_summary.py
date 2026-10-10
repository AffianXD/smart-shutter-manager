"""Describe only the unique shutters whose movement commands were executed."""
from __future__ import annotations

from .localization import is_german


def movement_summary(hass, coordinator, moves) -> tuple[str, int]:
    """Describe coverage of the whole instance, never just a recipient's subset.

    Complete overlapping areas share members without counting them twice.
    Names without entity IDs cannot prove complete instance or area coverage.
    """
    unique = {}
    for move in moves:
        name, _, _ = move[:3]
        entity_id = move[3] if len(move) > 3 else None
        unique.setdefault(entity_id or ("name", name), (entity_id, name))
    count = len(unique)
    names = [name for _, name in unique.values()]
    if count <= 1:
        return ", ".join(names), count
    reported = {entity_id for entity_id, _ in unique.values() if entity_id}
    universe = set(coordinator.shutters)
    german = is_german(hass)
    if len(reported) == count and reported == universe:
        return "Alle Rollläden" if german else "All shutters", count

    assignments = coordinator.shutter_areas
    complete = []
    for area in coordinator.custom_areas:
        area_id, area_name = area.get("id"), area.get("name")
        members = {entity_id for entity_id in universe if area_id in assignments.get(entity_id, [])}
        if area_name and members and members <= reported:
            complete.append((str(area_name), members))
    # Prefer a larger complete area to redundant nested labels. Keep complete
    # overlapping areas when each contributes an additional member.
    complete.sort(key=lambda item: (-len(item[1]), item[0]))
    chosen = []
    covered = set()
    for area_name, members in complete:
        if members <= covered:
            continue
        chosen.append(area_name)
        covered.update(members)
    remaining = [name for entity_id, name in unique.values() if entity_id not in covered]
    if not chosen:
        return ", ".join(names), count
    area_names = (" und " if german else " and ").join(chosen)
    if german:
        subject = f"Rollläden im Bereich {area_names}" if len(chosen) == 1 else f"Rollläden in den Bereichen {area_names}"
        if remaining:
            subject += " sowie " + ", ".join(remaining)
    else:
        subject = f"Shutters in {area_names}"
        if remaining:
            subject += " and " + ", ".join(remaining)
    return subject, count


def movement_phrase(hass, action_label: str, count: int) -> str:
    """A completed service call confirms a command, not an end position."""
    if is_german(hass):
        suffix = {"opened": " hoch", "closed": " herunter"}.get(action_label, " zur Zielposition")
        return ("fährt" if count == 1 else "fahren") + suffix
    suffix = {"opened": " opening", "closed": " closing"}.get(action_label, " moving to the target position")
    return ("is" if count == 1 else "are") + suffix
