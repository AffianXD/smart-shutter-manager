"""Date exceptions: scheduler, execution, persistence and guest boundaries."""
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_shutter import _async_update_listener, _prune_expired_exception_history, websocket_api as ws
from custom_components.smart_shutter.const import DATA_COORDINATOR, DOMAIN, MAX_RETAINED_EXPIRED_TEMPORAL_EXCEPTIONS
from custom_components.smart_shutter.coordinator import ManagedShutter, SmartShutterCoordinator
from custom_components.smart_shutter.executor import ShutterActionExecutor
from custom_components.smart_shutter.scheduler import compute_forecast, resolve_next_datetime, resolve_todays_datetime
from custom_components.smart_shutter.sensor import _apply_next_action
from custom_components.smart_shutter.sun_position import SunPositionMonitor
from custom_components.smart_shutter.temporal_exceptions import (
    applicable_exceptions, conflicting_exceptions, exception_allowed, is_date_paused, prune_expired_exceptions, validate_exception,
)

BERLIN = ZoneInfo("Europe/Berlin")


def rule(**changes):
    return {"id": "exception_one", "start_date": "2026-10-10", "end_date": "2026-10-14",
            "mode": "pause", "actions": ["open", "close"], "cover_ids": ["cover.bedroom"],
            "area_ids": [], "open_time": None, "close_time": None, **changes}


def coordinator(hass, rules=()):
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={"covers": ["cover.bedroom", "cover.office"]}, options={
        "temporal_exceptions": list(rules),
        "custom_areas": [{"id": "guest", "name": "Guest", "assigned_ha_user_ids": ["guest-user"]}, {"id": "host", "name": "Host"}],
        "shutter_areas": {"cover.bedroom": ["guest"], "cover.office": ["host"]},
    })
    entry.add_to_hass(hass)
    coord = SmartShutterCoordinator.__new__(SmartShutterCoordinator)
    coord.entry, coord.hass = entry, hass
    coord.options_snapshot, coord.data_snapshot = dict(entry.options), dict(entry.data)
    coord.shutters = {id: ManagedShutter(id, id) for id in entry.data["covers"]}
    coord.shutter_entities = {}
    coord.global_entities = {f"{a}_{p}": SimpleNamespace(native_value=time(8 if a == "open" else 20))
                             for a in ("open", "close") for p in ("weekday", "weekend", "holiday")}
    coord.get_action_override = Mock(return_value=None)
    hass.data[DOMAIN] = {entry.entry_id: {DATA_COORDINATOR: coord}}
    return coord


def connection(admin=True):
    return SimpleNamespace(user=SimpleNamespace(id="guest-user", is_admin=admin),
                           send_result=Mock(), send_error=Mock(), async_handle_exception=Mock())


async def invoke(hass, handler, conn, **message):
    handler(hass, conn, {"id": 1, **message})
    await hass.async_block_till_done()
    conn.async_handle_exception.assert_not_called()


def test_inclusive_dates_and_dynamic_area_membership(hass):
    coord = coordinator(hass, [rule(cover_ids=[], area_ids=["guest"], actions=["open"])])
    for day, paused in [(9, False), (10, True), (14, True), (15, False)]:
        assert is_date_paused(coord, "cover.bedroom", "open", date(2026, 10, day)) == paused
    assert not is_date_paused(coord, "cover.bedroom", "close", date(2026, 10, 12))
    assert not is_date_paused(coord, "cover.office", "open", date(2026, 10, 12))
    hass.config_entries.async_update_entry(coord.entry, options={**coord.entry.options, "shutter_areas": {"cover.office": ["guest"]}})
    assert is_date_paused(coord, "cover.office", "open", date(2026, 10, 12))
    assert not applicable_exceptions(coord, "cover.bedroom", date(2026, 10, 12))


def test_expired_history_keeps_all_current_rules_and_only_the_most_recent_limit():
    rules = [rule(id=f"old_{day}", start_date=f"2026-09-{day:02d}", end_date=f"2026-09-{day:02d}") for day in range(1, 14)]
    rules.extend([rule(id="today", start_date="2026-10-04", end_date="2026-10-04"),
                  rule(id="future", start_date="2026-11-01", end_date="2026-11-03")])
    retained = prune_expired_exceptions(rules, date(2026, 10, 4), MAX_RETAINED_EXPIRED_TEMPORAL_EXCEPTIONS)
    assert [item["id"] for item in retained] == [f"old_{day}" for day in range(4, 14)] + ["today", "future"]


def test_entry_prunes_expired_history_without_removing_active_rules(hass):
    old = [rule(id=f"old_{day}", start_date=f"2026-09-{day:02d}", end_date=f"2026-09-{day:02d}") for day in range(1, 14)]
    coord = coordinator(hass, [*old, rule(id="current", start_date="2026-10-04", end_date="2026-10-04")])
    assert _prune_expired_exception_history(hass, coord.entry, date(2026, 10, 4)) is True
    assert [item["id"] for item in coord.temporal_exceptions] == [f"old_{day}" for day in range(4, 14)] + ["current"]


def test_long_overlapping_pauses_skip_overrides_and_resume_normal_time(hass):
    coord = coordinator(hass, [rule(end_date="2027-02-01", actions=["open"]), rule(id="two", start_date="2027-01-31", end_date="2027-02-05", actions=["open"])])
    shutter = coord.shutters["cover.bedroom"]
    now = datetime(2026, 10, 11, 7, tzinfo=BERLIN)
    coord.get_action_override.return_value = now + timedelta(hours=3)
    target = resolve_next_datetime(hass, coord, shutter, "open", "weekend", now)
    assert target == datetime(2027, 2, 6, 8, tzinfo=BERLIN)
    assert target.utcoffset() == timedelta(hours=1)
    assert resolve_todays_datetime(hass, coord, shutter, "open", "weekend", now) is None
    coord.get_action_override.return_value = datetime(2027, 2, 6, 11, tzinfo=BERLIN)
    assert resolve_next_datetime(hass, coord, shutter, "open", "weekend", now).hour == 11


def test_alternate_times_leave_other_action_unchanged_and_never_roll_past_time_forward(hass):
    coord = coordinator(hass, [rule(mode="times", open_time="10:30")])
    shutter = coord.shutters["cover.bedroom"]
    now = datetime(2026, 10, 12, 11, tzinfo=BERLIN)
    assert resolve_next_datetime(hass, coord, shutter, "open", "weekday", now) == datetime(2026, 10, 13, 10, 30, tzinfo=BERLIN)
    assert resolve_next_datetime(hass, coord, shutter, "close", "weekday", now).hour == 20
    assert resolve_todays_datetime(hass, coord, shutter, "open", "weekday", now).hour == 10
    coord.get_action_override.return_value = now + timedelta(hours=1)
    assert resolve_next_datetime(hass, coord, shutter, "open", "weekday", now) == now + timedelta(hours=1)


def test_sun_times_are_overridden_and_paused_actual_solar_dates_are_skipped(hass, monkeypatch):
    coord = coordinator(hass, [rule(mode="times", open_time="10:30")])
    coord.global_entities["open_type"] = SimpleNamespace(action_type="sunrise")
    coord.global_entities["open_sun_offset"] = SimpleNamespace(native_value=0)
    from custom_components.smart_shutter import scheduler
    solar = Mock(return_value=datetime(2026, 10, 15, 7, tzinfo=BERLIN))
    monkeypatch.setattr(scheduler, "get_astral_event_next", solar)
    target = resolve_next_datetime(hass, coord, coord.shutters["cover.bedroom"], "open", "weekday", datetime(2026, 10, 12, 6, tzinfo=BERLIN))
    assert target.hour == 10 and target.minute == 30
    solar.assert_not_called()


def test_solar_event_on_a_paused_actual_date_is_skipped(hass, monkeypatch):
    coord = coordinator(hass, [rule(start_date="2026-10-13", end_date="2026-10-13", actions=["open"])])
    coord.global_entities["open_type"] = SimpleNamespace(action_type="sunrise")
    coord.global_entities["open_sun_offset"] = SimpleNamespace(native_value=0)
    from custom_components.smart_shutter import scheduler

    def sunrise_on_requested_or_next_day(_hass, _event, utc_point_in_time, offset):
        requested_day = utc_point_in_time.astimezone(BERLIN).date()
        actual_day = date(2026, 10, 13) if requested_day == date(2026, 10, 12) else requested_day
        return datetime.combine(actual_day, time(7), BERLIN)

    monkeypatch.setattr(scheduler, "get_astral_event_next", sunrise_on_requested_or_next_day)
    target = resolve_next_datetime(
        hass,
        coord,
        coord.shutters["cover.bedroom"],
        "open",
        "weekday",
        datetime(2026, 10, 12, 6, tzinfo=BERLIN),
    )

    assert target == datetime(2026, 10, 14, 7, tzinfo=BERLIN)


def test_forecast_pause_priority_and_dst_boundary(hass):
    coord = coordinator(hass, [rule(mode="times", start_date="2026-10-24", end_date="2026-10-26", open_time="10:00"),
                              rule(id="two", start_date="2026-10-25", end_date="2026-10-25", actions=["open"])])
    forecast = compute_forecast(hass, coord, coord.shutters["cover.bedroom"], days=4, now=datetime(2026, 10, 24, 6, tzinfo=BERLIN))
    opens = [ts for action, ts in forecast if action == "open"]
    assert [(ts.day, ts.hour) for ts in opens] == [(24, 10), (26, 10), (27, 8)]
    assert opens[0].utcoffset() == timedelta(hours=2)
    assert opens[1].utcoffset() == timedelta(hours=1)
    assert len([ts for action, ts in forecast if action == "close"]) == 4


@pytest.mark.parametrize("changes,error", [
    ({"start_date": "2026-10-15"}, "invalid_dates"), ({"end_date": "bad"}, "invalid_dates"),
    ({"cover_ids": []}, "invalid_targets"), ({"area_ids": "guest"}, "invalid_targets"),
    ({"cover_ids": ["cover.unknown"]}, "invalid_targets"), ({"actions": []}, "invalid_actions"),
    ({"mode": "times"}, "missing_times"), ({"mode": "times", "open_time": "26:00"}, "invalid_times"),
    ({"mode": "times", "open_time": "08:00:30"}, "invalid_times"),
])
def test_validation(hass, changes, error):
    assert validate_exception(rule(**changes), coordinator(hass)) == error


def test_missing_existing_targets_can_be_retained_but_never_execute_for_other_covers(hass):
    coord = coordinator(hass)
    existing = rule(cover_ids=["cover.missing"])
    assert validate_exception(existing, coord, existing) is None
    assert validate_exception(existing, coord) == "invalid_targets"


def test_conflicts_match_dates_targets_and_actions(hass):
    coord = coordinator(hass)
    candidate = rule(mode="times", open_time="10:00")
    overlapping = rule(id="two", mode="times", cover_ids=[], area_ids=["guest"], open_time="11:00")
    assert conflicting_exceptions(candidate, [overlapping], coord) == [overlapping]
    for other in [rule(mode="pause"), rule(mode="times", close_time="21:00"),
                  rule(mode="times", open_time="11:00", cover_ids=["cover.office"]),
                  rule(mode="times", open_time="11:00", start_date="2026-10-15", end_date="2026-10-15")]:
        assert not conflicting_exceptions(candidate, [other], coord)


async def test_save_edit_delete_preserve_other_options_and_stable_id(hass):
    coord = coordinator(hass)
    conn = connection()
    await invoke(hass, ws.handle_save_temporal_exception, conn, type="smart_shutter/save_temporal_exception", exception={**rule(), "id": None})
    created = conn.send_result.call_args.args[1]["exception"]
    assert created["id"].startswith("exception_")
    await invoke(hass, ws.handle_save_temporal_exception, conn, type="smart_shutter/save_temporal_exception", exception={**created, "actions": ["open"]})
    assert coord.temporal_exceptions[0]["id"] == created["id"]
    assert coord.temporal_exceptions[0]["actions"] == ["open"]
    await invoke(hass, ws.handle_delete_temporal_exception, conn, type="smart_shutter/delete_temporal_exception", exception_id=created["id"])
    assert coord.temporal_exceptions == []
    assert coord.custom_areas[0]["id"] == "guest"


async def test_save_keeps_only_ten_expired_and_rejects_a_rule_outside_that_history(hass, monkeypatch):
    now = datetime(2026, 10, 4, 12, tzinfo=BERLIN)
    monkeypatch.setattr(ws.dt_util, "now", lambda: now)
    past = [rule(id=f"old_{day}", start_date=f"2026-09-{day:02d}", end_date=f"2026-09-{day:02d}") for day in range(1, 11)]
    coord = coordinator(hass, past)
    conn = connection()
    newest = rule(id=None, start_date="2026-09-30", end_date="2026-09-30")
    await invoke(hass, ws.handle_save_temporal_exception, conn, type="smart_shutter/save_temporal_exception", exception=newest)
    assert conn.send_result.call_args.args[1]["success"] is True
    assert [item["id"] for item in coord.temporal_exceptions] == [f"old_{day}" for day in range(2, 11)] + [conn.send_result.call_args.args[1]["exception"]["id"]]
    before = list(coord.temporal_exceptions)
    ancient = rule(id=None, start_date="2000-01-01", end_date="2000-01-01")
    await invoke(hass, ws.handle_save_temporal_exception, conn, type="smart_shutter/save_temporal_exception", exception=ancient)
    assert conn.send_result.call_args.args[1] == {"success": False, "validation_error": "expired_limit"}
    assert coord.temporal_exceptions == before


async def test_guest_area_scope_is_enforced_for_create_edit_delete(hass):
    host_rule = rule(id="host-rule")
    coord = coordinator(hass, [host_rule])
    guest = connection(False)
    guest_rule = rule(id=None, cover_ids=[], area_ids=["guest"])
    await invoke(hass, ws.handle_save_temporal_exception, guest, type="smart_shutter/save_temporal_exception", exception=guest_rule)
    assert guest.send_result.call_args.args[1]["success"]
    for attempted in [rule(id=None), rule(id=None, cover_ids=[], area_ids=["host"]),
                      rule(id="host-rule", cover_ids=[], area_ids=["guest"])]:
        await invoke(hass, ws.handle_save_temporal_exception, guest, type="smart_shutter/save_temporal_exception", exception=attempted)
        assert guest.send_error.call_args.args[1] == "unauthorized"
    await invoke(hass, ws.handle_delete_temporal_exception, guest, type="smart_shutter/delete_temporal_exception", exception_id="host-rule")
    assert guest.send_error.call_args.args[1] == "unauthorized"
    assert coord.temporal_exceptions[0] == host_rule
    assert exception_allowed(guest_rule, {"guest"})
    assert not exception_allowed(host_rule, {"guest"})


async def test_conflicting_times_do_not_mutate_or_leak_host_targets_to_guest(hass):
    coord = coordinator(hass, [rule(mode="times", open_time="10:00")])
    guest = connection(False)
    before = dict(coord.entry.options)
    await invoke(hass, ws.handle_save_temporal_exception, guest, type="smart_shutter/save_temporal_exception", exception=rule(id=None, mode="times", cover_ids=[], area_ids=["guest"], open_time="11:00"))
    result = guest.send_result.call_args.args[1]
    assert result == {"success": False, "validation_error": "conflicting_times", "conflicts": []}
    assert coord.entry.options == before


async def test_area_membership_change_cannot_create_overlapping_timed_exceptions(hass):
    first = rule(id="first", mode="times", cover_ids=[], area_ids=["guest"], open_time="09:00")
    second = rule(id="second", mode="times", cover_ids=[], area_ids=["host"], open_time="10:00")
    coord = coordinator(hass, [first, second])
    conn = connection()
    before = dict(coord.entry.options)

    await invoke(
        hass,
        ws.handle_save_shutter_areas,
        conn,
        type="smart_shutter/save_shutter_areas",
        shutter_areas={"cover.bedroom": ["guest", "host"], "cover.office": ["host"]},
    )

    assert conn.send_result.call_args.args[1] == {
        "success": False,
        "validation_error": "conflicting_temporal_exceptions",
    }
    assert coord.entry.options == before


async def test_pause_blocks_execution_warning_and_restart_catch_up(hass, monkeypatch):
    coord = coordinator(hass, [rule()])
    now = datetime(2026, 10, 12, 8, 5, tzinfo=BERLIN)
    from custom_components.smart_shutter import executor as module
    monkeypatch.setattr(module.dt_util, "now", lambda: now)
    history, store, notifier = Mock(), Mock(), Mock()
    worker = ShutterActionExecutor(hass, coord, coord.shutters["cover.bedroom"], notifier, store, history, Mock())
    call = AsyncMock()
    monkeypatch.setattr(type(hass.services), "async_call", call)
    await worker._execute("open")
    call.assert_not_called()
    assert history.add.call_args.args[3] == "Automation paused (date exception)"
    worker._target_dt["close"] = now + timedelta(hours=1)
    await worker._make_prenotify_callback("close")(now)
    notifier.send_pre_close_warning.assert_not_called()
    worker._execute = AsyncMock()
    await worker.catch_up_if_missed(now)
    worker._execute.assert_not_called()


async def test_exception_edits_rearm_without_startup_catch_up_or_entity_reload(hass, monkeypatch):
    coord = coordinator(hass)
    reload = AsyncMock()
    monkeypatch.setattr(type(hass.config_entries), "async_reload", reload)
    hass.config_entries.async_update_entry(coord.entry, options={**coord.entry.options, "temporal_exceptions": [rule()]})
    await _async_update_listener(hass, coord.entry)
    reload.assert_not_called()
    # A cover management change must still rebuild generated entities.
    hass.config_entries.async_update_entry(coord.entry, data={"covers": ["cover.bedroom"]})
    await _async_update_listener(hass, coord.entry)
    reload.assert_awaited_once()


def test_active_exception_sensor_attributes(hass, monkeypatch):
    coord = coordinator(hass, [rule()])
    from custom_components.smart_shutter import sensor as module
    now = datetime(2026, 10, 12, 6, tzinfo=BERLIN)
    monkeypatch.setattr(module.dt_util, "now", lambda: now)
    shutter = coord.shutters["cover.bedroom"]
    schedule = module.compute_schedule(hass, coord, shutter, now)
    sensor = SimpleNamespace(hass=hass, _coordinator=coord, _shutter=shutter)
    _apply_next_action(sensor, schedule)
    assert sensor._attr_extra_state_attributes["date_pause_actions"] == ["close", "open"]
    assert sensor._attr_extra_state_attributes["temporal_exceptions"][0]["id"] == "exception_one"


async def test_pause_added_during_stagger_delay_blocks_actual_service(hass, monkeypatch):
    coord = coordinator(hass)
    from custom_components.smart_shutter import executor as module
    monkeypatch.setattr(module.dt_util, "now", lambda: datetime(2026, 10, 12, 8, tzinfo=BERLIN))
    guard = Mock()
    guard.is_paused.return_value = False
    worker = ShutterActionExecutor(hass, coord, coord.shutters["cover.bedroom"], Mock(), Mock(), Mock(), guard)
    worker._is_frost_active = Mock(return_value=False)
    worker._already_in_target_state = Mock(return_value=False)
    worker._target_position = Mock(return_value=100)
    async def delay():
        hass.config_entries.async_update_entry(coord.entry, options={**coord.entry.options, "temporal_exceptions": [rule()]})
    worker._apply_stagger_delay = delay
    call = AsyncMock()
    monkeypatch.setattr(type(hass.services), "async_call", call)
    await worker._execute("open")
    call.assert_not_called()
    guard.mark_self_initiated.assert_not_called()


async def test_rearming_pause_records_omitted_day_for_restart_after_deletion(hass, monkeypatch):
    coord = coordinator(hass, [rule()])
    from custom_components.smart_shutter import executor as module
    monkeypatch.setattr(module.dt_util, "now", lambda: datetime(2026, 10, 12, 8, 5, tzinfo=BERLIN))
    values = {}
    store = SimpleNamespace(get=lambda cover, action: values.get((cover, action)),
                            set=lambda cover, action, day: values.update({(cover, action): day}))
    worker = ShutterActionExecutor(hass, coord, coord.shutters["cover.bedroom"], Mock(), store, Mock(), Mock())
    worker._arm("open")
    assert values[("cover.bedroom", "open")] == date(2026, 10, 12)
    worker.cancel_all()
    hass.config_entries.async_update_entry(coord.entry, options={**coord.entry.options, "temporal_exceptions": []})
    worker._execute = AsyncMock()
    await worker.catch_up_if_missed(datetime(2026, 10, 12, 8, 5, tzinfo=BERLIN))
    worker._execute.assert_not_called()


async def test_sun_position_rule_respects_directional_pause(hass, monkeypatch):
    coord = coordinator(hass, [rule(actions=["close"])])
    from custom_components.smart_shutter import sun_position as module
    monkeypatch.setattr(module.dt_util, "now", lambda: datetime(2026, 10, 12, tzinfo=BERLIN))
    hass.states.async_set("cover.bedroom", "open", {"supported_features": 4, "current_position": 100})
    service = AsyncMock()
    monkeypatch.setattr(type(hass.services), "async_call", service)
    monitor = SunPositionMonitor(hass, coord, Mock())
    monitor._apply_position_to_members({"id": "guest"}, 50)
    await hass.async_block_till_done()
    service.assert_not_called()
    hass.states.async_set("cover.bedroom", "closed", {"supported_features": 4, "current_position": 0})
    monitor._apply_position_to_members({"id": "guest"}, 50)
    await hass.async_block_till_done()
    service.assert_awaited_once()
