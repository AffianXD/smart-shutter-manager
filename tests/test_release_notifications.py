"""Behavior checks for individual notification routing and authorized persistence."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_shutter.const import DATA_COORDINATOR, DOMAIN
from custom_components.smart_shutter.coordinator import ManagedShutter, SmartShutterCoordinator
from custom_components.smart_shutter.executor import NotificationBatcher
from custom_components.smart_shutter.sun_position import SunPositionMonitor
from custom_components.smart_shutter import websocket_api as ws


def setup_entry(hass, **options):
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={"covers": ["cover.one", "cover.two", "cover.private"], "names": {}}, options={
        "notify_service": "notify.owner",
        "custom_areas": [{"id": "guest", "name": "Guest", "assigned_ha_user_ids": ["guest"]}, {"id": "private", "name": "Private"}],
        "shutter_areas": {"cover.one": ["guest", "private"], "cover.two": ["guest"], "cover.private": ["private"]},
        **options,
    })
    entry.add_to_hass(hass)
    coordinator = SmartShutterCoordinator(hass, entry)
    coordinator.shutters = {entity_id: ManagedShutter(entity_id, name) for entity_id, name in (
        ("cover.one", "One"), ("cover.two", "Two"), ("cover.private", "Private"),
    )}
    hass.data[DOMAIN] = {entry.entry_id: {DATA_COORDINATOR: coordinator}}
    return entry, coordinator


def connection(admin=False, user_id="guest"):
    return SimpleNamespace(user=SimpleNamespace(is_admin=admin, id=user_id), send_result=Mock(), send_error=Mock(), async_handle_exception=Mock())


async def invoke(hass, handler, conn, **msg):
    handler(hass, conn, {"id": 1, **msg})
    await hass.async_block_till_done()
    conn.async_handle_exception.assert_not_called()


@pytest.mark.parametrize("shutter,areas,global_service,expected", [
    ({}, [], "notify.owner", "notify.owner"),
    ({}, [], None, None),
    ({}, [{"notify_service": "notify.guest"}], None, "notify.guest"),
    ({}, [{"notify_service": "   "}], "notify.owner", "notify.owner"),
    ({}, [{"notification_mode": "off"}], "notify.owner", None),
    ({}, [{"notification_mode": "inherit", "notify_service": "notify.old"}, {"notify_service": "notify.second"}], "notify.owner", "notify.second"),
    ({}, [{"notification_mode": "off"}, {"notify_service": "notify.second"}], "notify.owner", None),
    ({}, [{"notify_service": "notify.first"}, {"notification_mode": "off"}], "notify.owner", "notify.first"),
    ({"notification_mode": "off"}, [{"notify_service": "notify.guest"}], "notify.owner", None),
    ({"notification_mode": "custom", "notify_service": "notify.phone"}, [{"notification_mode": "off"}], None, "notify.phone"),
    ({"notification_mode": "inherit"}, [{"notification_mode": "off"}], "notify.owner", None),
])
def test_notification_priority(hass, shutter, areas, global_service, expected):
    _, coordinator = setup_entry(hass, notify_service=global_service,
        custom_areas=[{"id": str(index), **area} for index, area in enumerate(areas)],
        shutter_areas={"cover.one": [str(index) for index in range(len(areas))]},
        shutter_notifications={"cover.one": shutter})
    assert coordinator.effective_notify_service("cover.one") == expected


def test_sun_uses_triggering_area_and_individual_override(hass):
    _, coordinator = setup_entry(hass, custom_areas=[{"id": "guest", "notify_service": "notify.first"}, {"id": "private", "notification_mode": "off"}],
        shutter_notifications={"cover.two": {"notification_mode": "custom", "notify_service": "notify.phone"}})
    trigger = coordinator.custom_areas[1]
    assert coordinator.effective_notify_service("cover.one") == "notify.first"
    assert coordinator.effective_notify_service("cover.one", trigger) is None
    assert coordinator.effective_notify_service("cover.two", trigger) == "notify.phone"


async def test_pre_close_uses_individual_recipient_and_retains_actions(hass):
    _, coordinator = setup_entry(hass, notify_service=None, custom_areas=[{"id": "guest", "notification_mode": "off"}],
        shutter_notifications={"cover.one": {"notification_mode": "custom", "notify_service": "notify.phone"}})
    batcher = NotificationBatcher(hass, coordinator)
    batcher._call_notify = AsyncMock()
    await batcher.send_pre_close_warning(coordinator.shutters["cover.one"], "close", datetime(2026, 10, 3, 20), [5, 15, 60])
    call = batcher._call_notify.call_args
    assert call.args[0] == "notify.phone"
    assert [button["action"] for button in call.kwargs["extra_data"]["actions"]] == [
        "ssm|postpone5|cover.one|close", "ssm|postpone15|cover.one|close", "ssm|skip|cover.one|close",
    ]
    batcher._call_notify.reset_mock()
    await batcher.send_pre_close_warning(coordinator.shutters["cover.two"], "close", datetime(2026, 10, 3, 20), [5])
    batcher._call_notify.assert_not_called()


async def test_movement_and_frost_batches_exclude_off_shutters(hass):
    _, coordinator = setup_entry(hass, shutter_notifications={"cover.two": {"notification_mode": "off"}})
    batcher = NotificationBatcher(hass, coordinator)
    batcher._call_notify = AsyncMock()
    for entity_id in ("cover.one", "cover.two"):
        service = coordinator.effective_notify_service(entity_id)
        batcher.report_movement(coordinator.shutters[entity_id].name, "closed", "Schedule", service)
        batcher.report_frost_block(coordinator.shutters[entity_id].name, service)
    batcher._flush_unsub()
    batcher._flush()
    await hass.async_block_till_done()
    batcher._call_notify.assert_awaited_once()
    assert batcher._call_notify.call_args.args[0] == "notify.owner"
    message = batcher._call_notify.call_args.args[2]
    assert "One" in message and "Two" not in message


@pytest.mark.parametrize("warning", [False, True])
async def test_sun_groups_names_and_counts_by_recipient(hass, monkeypatch, warning):
    _, coordinator = setup_entry(hass, shutter_notifications={
        "cover.one": {"notification_mode": "custom", "notify_service": "notify.phone"},
        "cover.two": {"notification_mode": "off"},
    })
    monitor = SunPositionMonitor.__new__(SunPositionMonitor)
    monitor.hass, monitor._coordinator = hass, coordinator
    notify = AsyncMock()
    monkeypatch.setattr(type(hass.services), "async_call", notify)
    area = {"name": "South", "notify_service": "notify.area", "sun_position_target": 30,
        "sun_notify_text": "{{ names }}:{{ count }}:{{ position }}",
        "sun_prenotify_text": "{{ names }}:{{ count }}:{{ minutes }}"}
    members = ["cover.one", "cover.two", "cover.private", "cover.one"]
    if warning:
        await monitor._send_prenotification(area, members, 5)
    else:
        await monitor._send_notification(area, members, 30)
    messages = {f"{call.args[0]}.{call.args[1]}": call.args[2]["message"] for call in notify.call_args_list}
    value = 5 if warning else 30
    assert messages == {"notify.phone": f"One:1:{value}", "notify.area": f"Private:1:{value}"}


async def test_sun_off_area_still_allows_shutter_recipient(hass, monkeypatch):
    _, coordinator = setup_entry(hass, shutter_notifications={"cover.one": {"notification_mode": "custom", "notify_service": "notify.phone"}})
    monitor = SunPositionMonitor.__new__(SunPositionMonitor)
    monitor.hass, monitor._coordinator = hass, coordinator
    notify = AsyncMock()
    monkeypatch.setattr(type(hass.services), "async_call", notify)
    await monitor._send_notification({"name": "South", "notification_mode": "off"}, ["cover.one", "cover.two"], 30)
    notify.assert_awaited_once()
    assert notify.call_args.args[:2] == ("notify", "phone")


async def test_guest_save_read_and_reset_preserve_other_settings(hass):
    entry, _ = setup_entry(hass, shutter_notifications={"cover.private": {"notification_mode": "off"}})
    hass.services.async_register("notify", "phone", lambda call: None)
    conn = connection()
    await invoke(hass, ws.handle_save_shutter_notifications, conn, entity_id="cover.one", notification_mode="custom", notify_service=" notify.phone ")
    conn.send_error.assert_not_called()
    assert entry.options["shutter_notifications"] == {
        "cover.one": {"notification_mode": "custom", "notify_service": "notify.phone"}, "cover.private": {"notification_mode": "off"},
    }
    await invoke(hass, ws.handle_get_config, conn)
    config = conn.send_result.call_args.args[1]
    assert config["shutter_notifications"] == {"cover.one": {"notification_mode": "custom", "notify_service": "notify.phone"}}
    assert config["basic_settings"] == {}
    await invoke(hass, ws.handle_save_shutter_notifications, conn, entity_id="cover.one", notification_mode="inherit")
    assert entry.options["shutter_notifications"] == {"cover.private": {"notification_mode": "off"}}
    assert entry.options["notify_service"] == "notify.owner"
    # A new coordinator after a reload reads the persisted overrides.
    reloaded = SmartShutterCoordinator(hass, entry)
    assert reloaded.effective_notify_service("cover.private") is None
    assert reloaded.effective_notify_service("cover.one") == "notify.owner"


@pytest.mark.parametrize("entity_id,admin,user_id,error", [
    ("cover.private", False, "guest", "unauthorized"),
    ("cover.one", False, "unassigned", "unauthorized"),
    ("cover.unknown", True, "owner", "not_found"),
])
async def test_unauthorized_or_unknown_shutter_save_does_not_mutate(hass, entity_id, admin, user_id, error):
    entry, _ = setup_entry(hass)
    before = dict(entry.options)
    conn = connection(admin, user_id)
    await invoke(hass, ws.handle_save_shutter_notifications, conn, entity_id=entity_id, notification_mode="off")
    assert conn.send_error.call_args.args[1] == error
    assert dict(entry.options) == before


@pytest.mark.parametrize("service", ["", "notify.missing", "light.turn_on", "notify.phone.extra"])
async def test_invalid_custom_recipient_does_not_mutate(hass, service):
    entry, _ = setup_entry(hass)
    before = dict(entry.options)
    conn = connection()
    await invoke(hass, ws.handle_save_shutter_notifications, conn, entity_id="cover.one", notification_mode="custom", notify_service=service)
    assert conn.send_error.call_args.args[1] == "invalid_notifications"
    assert dict(entry.options) == before


@pytest.mark.parametrize("admin", [False, True])
@pytest.mark.parametrize("mode,service,valid", [("custom", "notify.phone", True), ("off", "", True), ("custom", "notify.missing", False), ("invalid", "", False)])
async def test_area_modes_validate_for_admin_and_guest(hass, admin, mode, service, valid):
    entry, _ = setup_entry(hass)
    hass.services.async_register("notify", "phone", lambda call: None)
    before = dict(entry.options)
    fields = {"notification_mode": mode, "notify_service": service}
    conn = connection(admin)
    if admin:
        areas = [{**area, **fields} if area["id"] == "guest" else dict(area) for area in entry.options["custom_areas"]]
        await invoke(hass, ws.handle_save_custom_areas, conn, areas=areas)
    else:
        await invoke(hass, ws.handle_save_own_area_settings, conn, area_id="guest", fields=fields)
    if valid:
        conn.send_error.assert_not_called()
        assert entry.options["custom_areas"][0]["notification_mode"] == mode
        assert entry.options["custom_areas"][1] == before["custom_areas"][1]
    else:
        assert conn.send_error.call_args.args[1] == "invalid_notifications"
        assert dict(entry.options) == before


async def test_unchanged_legacy_area_recipient_survives_unrelated_edit(hass):
    entry, _ = setup_entry(hass, custom_areas=[{"id": "guest", "name": "Old", "notify_service": "notify.old"}])
    conn = connection(True)
    await invoke(hass, ws.handle_save_custom_areas, conn, areas=[{"id": "guest", "name": "New", "notification_mode": "custom", "notify_service": "notify.old"}])
    conn.send_error.assert_not_called()
    assert entry.options["custom_areas"][0]["notify_service"] == "notify.old"


async def test_cover_removal_prunes_only_removed_notification_settings(hass):
    entry, _ = setup_entry(hass, shutter_notifications={"cover.one": {"notification_mode": "off"}, "cover.two": {"notification_mode": "custom", "notify_service": "notify.phone"}})
    conn = connection(True)
    await invoke(hass, ws.handle_save_covers, conn, covers=["cover.one", "cover.private"])
    assert entry.options["shutter_notifications"] == {"cover.one": {"notification_mode": "off"}}
