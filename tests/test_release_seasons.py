"""Seasonal schedules across real DST boundaries and native HA persistence."""
from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
from homeassistant.core import State
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache

from custom_components.smart_shutter import scheduler
from custom_components.smart_shutter.const import DATA_COORDINATOR, DOMAIN, GLOBAL_DEVICE_ID
from custom_components.smart_shutter.executor import SchedulerManager
from custom_components.smart_shutter.seasons import prepare_seasonal_options, season_at
from custom_components.smart_shutter import websocket_api as ws

BERLIN = ZoneInfo("Europe/Berlin")


def make_schedule(enabled=True):
    globals_ = {}
    for action in ("open", "close"):
        for season, hour in (("summer", 21), ("winter", 19)):
            globals_[f"{action}_type_{season}"] = SimpleNamespace(action_type="time")
            globals_[f"{action}_sun_offset_{season}"] = SimpleNamespace(native_value=0)
            for profile in ("weekday", "weekend", "holiday"):
                globals_[f"{action}_{profile}_{season}"] = SimpleNamespace(native_value=time(hour))
                globals_[f"{action}_{profile}"] = SimpleNamespace(native_value=time(16))
        globals_[f"{action}_type"] = SimpleNamespace(action_type="time")
    coordinator = SimpleNamespace(
        entry=SimpleNamespace(options={"seasonal_enabled": enabled}),
        global_entities=globals_, shutter_entities={"cover.room": {}},
        shutter_areas={}, custom_schedules=[], holiday_entity_id=None,
        holiday_weekdays=set(range(5)), get_action_override=lambda *_: None,
    )
    coordinator.get_custom_schedule = lambda pid: next((r for r in coordinator.custom_schedules if r["id"] == pid), None)
    hass = SimpleNamespace(states=SimpleNamespace(get=lambda _: None))
    return hass, coordinator, SimpleNamespace(entity_id="cover.room")


@pytest.mark.parametrize("now,expected", [
    (datetime(2026, 3, 28, 22, tzinfo=BERLIN), datetime(2026, 3, 29, 21, tzinfo=BERLIN)),
    (datetime(2026, 10, 24, 22, tzinfo=BERLIN), datetime(2026, 10, 25, 19, tzinfo=BERLIN)),
    (datetime(2026, 1, 5, 12, tzinfo=BERLIN), datetime(2026, 1, 5, 19, tzinfo=BERLIN)),
    (datetime(2026, 7, 6, 12, tzinfo=BERLIN), datetime(2026, 7, 6, 21, tzinfo=BERLIN)),
])
def test_future_execution_uses_its_season_and_matches_global_preview(now, expected):
    hass, coordinator, shutter = make_schedule()
    profile = scheduler.determine_active_profile(hass, coordinator, now.date())
    assert scheduler.resolve_next_datetime(hass, coordinator, shutter, "close", profile, now) == expected
    assert scheduler.resolve_next_datetime_global(hass, coordinator, "close", profile, now) == expected


@pytest.mark.parametrize("profile", ["weekday", "weekend", "holiday"])
def test_individual_time_and_unset_fallback(profile):
    hass, coordinator, shutter = make_schedule()
    now = datetime(2026, 7, 6, 12, tzinfo=BERLIN)
    entities = coordinator.shutter_entities[shutter.entity_id]
    entities[f"close_{profile}_time_source_summer"] = SimpleNamespace(source="local")
    entities[f"close_{profile}_summer"] = SimpleNamespace(native_value=time(22, 15))
    assert scheduler.resolve_next_datetime(hass, coordinator, shutter, "close", profile, now).time() == time(22, 15)
    entities[f"close_{profile}_summer"].native_value = None
    assert scheduler.resolve_next_datetime(hass, coordinator, shutter, "close", profile, now).time() == time(21)


def test_sun_type_and_offset_are_seasonal_and_can_be_individual(monkeypatch):
    hass, coordinator, shutter = make_schedule()
    now = datetime(2026, 7, 6, 12, tzinfo=BERLIN)
    coordinator.global_entities["close_type_summer"].action_type = "sunset"
    coordinator.global_entities["close_sun_offset_summer"].native_value = 30
    calls = []

    def sun(_hass, event, utc_point_in_time, offset):
        calls.append((event, offset))
        return datetime.combine(utc_point_in_time.astimezone(BERLIN).date(), time(20), tzinfo=BERLIN) + offset

    monkeypatch.setattr(scheduler, "get_astral_event_next", sun)
    assert scheduler.resolve_next_datetime(hass, coordinator, shutter, "close", "weekday", now).time() == time(20, 30)
    assert ("sunset", timedelta(minutes=30)) in calls
    entities = coordinator.shutter_entities[shutter.entity_id]
    entities["close_source_summer"] = SimpleNamespace(source="local")
    entities["close_type_summer"] = SimpleNamespace(action_type="sunset")
    entities["close_sun_offset_summer"] = SimpleNamespace(native_value=-15)
    assert scheduler.resolve_next_datetime(hass, coordinator, shutter, "close", "weekday", now).time() == time(19, 45)
    winter = datetime(2026, 1, 5, 12, tzinfo=BERLIN)
    assert scheduler.resolve_next_datetime(hass, coordinator, shutter, "close", "weekday", winter).time() == time(19)


def test_custom_profile_and_manual_override_take_precedence():
    hass, coordinator, shutter = make_schedule()
    now = datetime(2026, 7, 6, 12, tzinfo=BERLIN)
    coordinator.custom_schedules = [{"id": "custom_guest", "weekdays": list(range(7)), "close_time": "23:10"}]
    profile = scheduler.determine_active_profile(hass, coordinator, now.date())
    assert profile == "custom_guest"
    assert scheduler.resolve_next_datetime(hass, coordinator, shutter, "close", profile, now).time() == time(23, 10)
    postponed = now + timedelta(days=1)
    coordinator.get_action_override = lambda *_: postponed
    assert scheduler.resolve_next_datetime(hass, coordinator, shutter, "close", profile, now) == postponed


def test_spring_gap_moves_to_first_valid_minute():
    hass, coordinator, shutter = make_schedule()
    for season in ("summer", "winter"):
        coordinator.global_entities[f"open_weekend_{season}"].native_value = time(2, 30)
    now = datetime(2026, 3, 29, 0, tzinfo=BERLIN)
    expected = datetime(2026, 3, 29, 3, tzinfo=BERLIN)
    assert scheduler.resolve_next_datetime(hass, coordinator, shutter, "open", "weekend", now) == expected
    assert scheduler.resolve_todays_datetime(hass, coordinator, shutter, "open", "weekend", now) == expected


def test_autumn_fold_is_once_and_compares_absolute_instants():
    hass, coordinator, shutter = make_schedule()
    for season in ("summer", "winter"):
        coordinator.global_entities[f"open_weekend_{season}"].native_value = time(2, 30)
    now = datetime(2026, 10, 25, 0, tzinfo=BERLIN)
    first = scheduler.resolve_next_datetime(hass, coordinator, shutter, "open", "weekend", now)
    assert first.fold == 0 and first.time() == time(2, 30)
    # At the second 02:15 the first 02:30 has already passed.
    second_hour = datetime(2026, 10, 25, 2, 15, tzinfo=BERLIN, fold=1)
    following = scheduler.resolve_next_datetime(hass, coordinator, shutter, "open", "weekend", second_hour)
    assert following.date() > now.date()
    forecast = scheduler.compute_forecast(hass, coordinator, shutter, days=2, now=now)
    assert len([event for event in forecast if event[0] == "open" and event[1].date() == now.date()]) == 1


@pytest.mark.parametrize("zone", ["UTC", "Asia/Kolkata", "Africa/Johannesburg"])
def test_no_dst_zone_uses_winter(zone):
    hass, coordinator, shutter = make_schedule()
    now = datetime(2026, 7, 6, 12, tzinfo=ZoneInfo(zone))
    assert season_at(now) == "winter"
    assert scheduler.resolve_next_datetime(hass, coordinator, shutter, "close", "weekday", now).time() == time(19)


def test_disabled_uses_existing_entities():
    hass, coordinator, shutter = make_schedule(enabled=False)
    now = datetime(2026, 7, 6, 12, tzinfo=BERLIN)
    assert scheduler.resolve_next_datetime(hass, coordinator, shutter, "close", "weekday", now).time() == time(16)


def test_first_activation_snapshots_current_values_only_once():
    _, coordinator, _ = make_schedule(enabled=False)
    entity = coordinator.global_entities["close_weekday"]
    entity.native_value = time(20, 45)
    options = {"seasonal_enabled": True}
    prepare_seasonal_options(coordinator, options)
    assert options["seasonal_initial_values"]["global"]["close_weekday"] == "20:45:00"
    entity.native_value = time(18)
    prepare_seasonal_options(coordinator, options)
    assert options["seasonal_initial_values"]["global"]["close_weekday"] == "20:45:00"


def test_season_transition_recomputes_without_catchup(monkeypatch):
    hass, coordinator, _ = make_schedule()
    coordinator.entry.entry_id = "test"
    manager = SchedulerManager(hass, coordinator)
    manager._season_state = (str(BERLIN), "summer")
    calls = []
    monkeypatch.setattr("custom_components.smart_shutter.executor.dt_util.as_local", lambda moment: moment.astimezone(BERLIN))
    monkeypatch.setattr("custom_components.smart_shutter.executor.async_dispatcher_send", lambda *args: calls.append(args))
    manager._check_season(datetime(2026, 10, 25, 1, 0, 10, tzinfo=timezone.utc))
    manager._check_season(datetime(2026, 10, 25, 1, 1, 10, tzinfo=timezone.utc))
    assert len(calls) == 1


async def test_admin_activation_api_seeds_without_losing_other_options(hass):
    _, coordinator, _ = make_schedule(enabled=False)
    entry = MockConfigEntry(domain=DOMAIN, version=2, options={"notify_service": "notify.owner"})
    entry.add_to_hass(hass)
    coordinator.entry = entry
    hass.data[DOMAIN] = {entry.entry_id: {DATA_COORDINATOR: coordinator}}
    conn = SimpleNamespace(user=SimpleNamespace(is_admin=True), send_result=Mock(), send_error=Mock(), async_handle_exception=Mock())
    ws.handle_save_basic_settings(hass, conn, {"id": 1, "type": "smart_shutter/save_basic_settings", "seasonal_enabled": True})
    await hass.async_block_till_done()
    conn.async_handle_exception.assert_not_called()
    assert entry.options["seasonal_enabled"] is True
    assert entry.options["notify_service"] == "notify.owner"
    assert entry.options["seasonal_initial_values"]["global"]["close_weekday"] == "16:00:00"
    conn.user.is_admin = False
    with pytest.raises(Unauthorized):
        ws.handle_save_basic_settings(hass, conn, {"id": 2, "type": "smart_shutter/save_basic_settings", "seasonal_enabled": False})
    assert entry.options["seasonal_enabled"] is True


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_options_flow_enables_seasons_and_seeds_values(hass):
    _, coordinator, _ = make_schedule(enabled=False)
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={"covers": []})
    entry.add_to_hass(hass)
    coordinator.entry = entry
    hass.data[DOMAIN] = {entry.entry_id: {DATA_COORDINATOR: coordinator}}
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "basic_settings"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"seasonal_enabled": True})
    assert result["type"] == "create_entry"
    assert entry.options["seasonal_enabled"] is True
    assert entry.options["seasonal_initial_values"]["global"]["close_weekday"] == "16:00:00"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_native_entities_seed_restore_and_survive_orphan_cleanup(hass):
    hass.states.async_set("cover.room", "closed", {"supported_features": 11, "current_position": 0})
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={"covers": ["cover.room"]}, options={
        "seasonal_enabled": True,
        "seasonal_initial_values": {
            "global": {"close_weekday": "20:45:00", "close_type": "sunset", "close_sun_offset": 25},
            "cover.room": {"close_source": "local", "close_weekday_time_source": "local", "close_weekday": "22:10:00"},
        },
        "catch_up_window_minutes": 0,
    })
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    stored = registry.async_get_or_create("time", DOMAIN,
        f"{GLOBAL_DEVICE_ID}_{entry.entry_id}_close_werktag_summer",
        config_entry=entry, suggested_object_id="persisted_season")
    mock_restore_cache(hass, [State(stored.entity_id, "23:15:00")])
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    assert coordinator.global_entities["close_weekday_summer"].native_value == time(23, 15)
    assert coordinator.global_entities["close_weekday_winter"].native_value == time(20, 45)
    assert coordinator.global_entities["close_type_summer"].action_type == "sunset"
    assert coordinator.global_entities["close_sun_offset_winter"].native_value == 25
    assert coordinator.shutter_entities["cover.room"]["close_source_summer"].source == "local"
    local = coordinator.shutter_entities["cover.room"]["close_weekday_winter"]
    assert local.native_value == time(22, 10)
    from custom_components.smart_shutter import _async_cleanup_orphaned_profile_entities
    _async_cleanup_orphaned_profile_entities(hass, entry, coordinator)
    assert registry.async_get(local.entity_id) is not None
    assert registry.async_get(coordinator.shutter_entities["cover.room"]["close_source_summer"].entity_id) is not None
    await local.async_set_value(time(23, 5))
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    hass.config_entries.async_update_entry(entry, options={**entry.options, "seasonal_enabled": False})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    disabled = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    assert disabled.entry.options["seasonal_enabled"] is False
    assert disabled.shutter_entities["cover.room"]["close_weekday_winter"].native_value == time(23, 5)
    assert scheduler.resolve_fixed_time(disabled, disabled.shutters["cover.room"], "close", "weekday") == disabled.global_entities["close_weekday"].native_value
    assert registry.async_get(local.entity_id) is not None
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    hass.config_entries.async_update_entry(entry, options={**entry.options, "seasonal_enabled": True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    restored = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    assert restored.shutter_entities["cover.room"]["close_weekday_winter"].native_value == time(23, 5)
    assert restored.shutter_entities["cover.room"]["close_weekday_winter"].entity_id == local.entity_id
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
