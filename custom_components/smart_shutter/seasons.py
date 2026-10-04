"""Optional daylight-saving profiles, using Home Assistant's local timezone."""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

CONF_SEASONAL_ENABLED = "seasonal_enabled"
CONF_SEASONAL_INITIAL_VALUES = "seasonal_initial_values"
SEASONS = ("summer", "winter")


def seasonal_enabled(coordinator) -> bool:
    return bool(getattr(getattr(coordinator, "entry", None), "options", {}).get(CONF_SEASONAL_ENABLED, False))


def has_seasonal_profiles(coordinator) -> bool:
    """Keep native values registered after disabling, avoiding restore expiry."""
    return seasonal_enabled(coordinator) or CONF_SEASONAL_INITIAL_VALUES in coordinator.entry.options


def season_at(moment: datetime) -> str:
    """DST, rather than calendar seasons or a fixed UTC offset, selects summer."""
    return "summer" if moment.dst() else "winter"


def seasonal_key(key: str, season: str | None) -> str:
    return f"{key}_{season}" if season else key


def prepare_seasonal_options(coordinator, options: dict) -> None:
    """Snapshot restored base values once, immediately before first activation."""
    if not options.get(CONF_SEASONAL_ENABLED) or CONF_SEASONAL_INITIAL_VALUES in options:
        return
    initial = {}
    if coordinator is not None:
        groups = {"global": coordinator.global_entities, **coordinator.shutter_entities}
        for owner, entities in groups.items():
            values = {}
            for key, entity in entities.items():
                if key.endswith(SEASONS) or not key.startswith(("open_", "close_")):
                    continue
                if "position" in key or "custom_" in key:
                    continue
                value = getattr(entity, "current_option", None)
                if value is None:
                    value = getattr(entity, "native_value", None)
                if isinstance(value, time):
                    value = value.isoformat()
                if isinstance(value, (str, float, int)):
                    values[key] = value
            initial[owner] = values
    options[CONF_SEASONAL_INITIAL_VALUES] = initial


def for_season(entity, season: str):
    """Give a native entity a separate registry identity and translated label."""
    entity._season_base_key = entity._registry_key
    entity._registry_key = seasonal_key(entity._registry_key, season)
    entity._attr_unique_id = seasonal_key(entity._attr_unique_id, season)
    entity._attr_translation_key = seasonal_key(entity._attr_translation_key, season)
    return entity


def seed_seasonal_entity(entity) -> None:
    """Seed before RestoreEntity; persisted seasonal edits always win."""
    key = getattr(entity, "_season_base_key", None)
    if key is None:
        return
    coordinator = entity._coordinator
    shutter = getattr(entity, "_shutter", None)
    owner = shutter.entity_id if shutter else "global"
    raw = coordinator.entry.options.get(CONF_SEASONAL_INITIAL_VALUES, {}).get(owner, {}).get(key)
    if raw is None:
        return
    if hasattr(entity, "_attr_options"):
        if raw in entity._attr_options:
            entity._attr_current_option = raw
    elif isinstance(entity._attr_native_value, time):
        entity._attr_native_value = time.fromisoformat(raw)
    else:
        entity._attr_native_value = raw


def local_wall_time(day, clock: time, tzinfo, fold: int = 0) -> datetime:
    """Resolve gaps to the first valid local minute; retain a chosen fold."""
    wall = datetime.combine(day, clock).replace(fold=fold)
    for _ in range(24 * 60 + 1):
        candidate = wall.replace(tzinfo=tzinfo)
        roundtrip = candidate.astimezone(timezone.utc).astimezone(tzinfo)
        if roundtrip.replace(tzinfo=None) == wall:
            return candidate
        wall = (wall + timedelta(minutes=1)).replace(second=0, microsecond=0, fold=fold)
    raise ValueError("No valid local time within one day")
