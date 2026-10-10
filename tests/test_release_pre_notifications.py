"""Independent closing-warning inheritance, persistence and scheduling."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_shutter.const import DATA_COORDINATOR, DOMAIN
from custom_components.smart_shutter.coordinator import ManagedShutter, SmartShutterCoordinator
from custom_components.smart_shutter import executor, websocket_api as ws
from custom_components.smart_shutter.notification_settings import validate_pre_notify_settings


def setup(hass, settings=None, lead=5):
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={"covers": ["cover.one"]}, options={
        "notify_service": "notify.owner", "pre_notify_lead_minutes": lead,
        "shutter_notifications": {"cover.one": settings} if settings else {},
    })
    entry.add_to_hass(hass)
    coordinator = SmartShutterCoordinator(hass, entry)
    coordinator.shutters = {"cover.one": ManagedShutter("cover.one", "One")}
    hass.data[DOMAIN] = {entry.entry_id: {DATA_COORDINATOR: coordinator}}
    return entry, coordinator


@pytest.mark.parametrize("settings,global_lead,expected", [
    ({}, 5, 5),
    ({"notification_mode": "custom", "notify_service": "notify.phone"}, 7, 7),
    ({"notification_mode": "off"}, 5, 5),
    ({"pre_notify_mode": "inherit"}, 0, 0),
    ({"pre_notify_mode": "off"}, 5, 0),
    ({"pre_notify_mode": "custom", "pre_notify_lead_minutes": 12}, 0, 12),
    ({"pre_notify_mode": "custom", "pre_notify_lead_minutes": "invalid"}, 7, 7),
])
def test_effective_warning_lead_preserves_legacy_and_recipient_settings(hass, settings, global_lead, expected):
    _, coordinator = setup(hass, settings, global_lead)
    assert coordinator.effective_pre_notify_lead("cover.one") == timedelta(minutes=expected)
    recipient = None if settings.get("notification_mode") == "off" else settings.get("notify_service", "notify.owner")
    assert coordinator.effective_notify_service("cover.one") == recipient


@pytest.mark.parametrize("minutes", [None, 0, -1, 1441, 1.5, True, "5"])
def test_custom_warning_rejects_invalid_lead(minutes):
    with pytest.raises(ValueError):
        validate_pre_notify_settings({"pre_notify_mode": "custom", "pre_notify_lead_minutes": minutes})


async def save(hass, **fields):
    conn = SimpleNamespace(user=SimpleNamespace(is_admin=True, id="owner"),
        send_result=Mock(), send_error=Mock(), async_handle_exception=Mock())
    ws.handle_save_shutter_notifications(hass, conn, {"id": 1, "entity_id": "cover.one", **fields})
    await hass.async_block_till_done()
    conn.async_handle_exception.assert_not_called()
    return conn


async def test_warning_override_survives_old_client_and_recipient_reset(hass):
    entry, _ = setup(hass)
    conn = await save(hass, notification_mode="inherit", pre_notify_mode="custom", pre_notify_lead_minutes=5)
    conn.send_error.assert_not_called()
    assert entry.options["shutter_notifications"]["cover.one"]["pre_notify_lead_minutes"] == 5
    await save(hass, notification_mode="off")
    assert entry.options["shutter_notifications"]["cover.one"]["pre_notify_mode"] == "custom"
    await save(hass, notification_mode="inherit")
    reloaded = SmartShutterCoordinator(hass, entry)
    assert reloaded.effective_notify_service("cover.one") == "notify.owner"
    assert reloaded.effective_pre_notify_lead("cover.one") == timedelta(minutes=5)
    await save(hass, notification_mode="inherit", pre_notify_mode="inherit")
    assert entry.options["shutter_notifications"] == {}


async def test_warning_off_preserves_custom_recipient(hass):
    entry, _ = setup(hass)
    hass.services.async_register("notify", "phone", lambda call: None)
    conn = await save(hass, notification_mode="custom", notify_service="notify.phone", pre_notify_mode="off")
    conn.send_error.assert_not_called()
    reloaded = SmartShutterCoordinator(hass, entry)
    assert reloaded.effective_notify_service("cover.one") == "notify.phone"
    assert reloaded.effective_pre_notify_lead("cover.one") == timedelta(0)


async def test_warning_off_suppresses_delivery_without_changing_recipient(hass):
    _, coordinator = setup(hass, {"pre_notify_mode": "off"})
    notifier = executor.NotificationBatcher(hass, coordinator)
    notifier._call_notify = AsyncMock()
    await notifier.send_pre_close_warning(coordinator.shutters["cover.one"], "close", datetime(2026, 10, 10, 20), [5])
    notifier._call_notify.assert_not_called()
    assert coordinator.effective_notify_service("cover.one") == "notify.owner"


@pytest.mark.parametrize("fields", [
    {"pre_notify_mode": "invalid"},
    {"pre_notify_mode": "custom"},
    {"pre_notify_mode": "custom", "pre_notify_lead_minutes": 0},
    {"pre_notify_mode": "custom", "pre_notify_lead_minutes": 1441},
])
async def test_invalid_warning_save_does_not_mutate(hass, fields):
    entry, _ = setup(hass)
    before = dict(entry.options)
    conn = await save(hass, notification_mode="inherit", **fields)
    assert conn.send_error.call_args.args[1] == "invalid_notifications"
    assert dict(entry.options) == before


@pytest.mark.parametrize("mode,minutes,expected_lead", [("off", None, None), ("custom", 12, 12), ("inherit", None, 5)])
def test_scheduler_uses_independent_warning_time(hass, monkeypatch, mode, minutes, expected_lead):
    _, coordinator = setup(hass, {"pre_notify_mode": mode, "pre_notify_lead_minutes": minutes})
    now = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
    target = now + timedelta(hours=1)
    monkeypatch.setattr(executor.dt_util, "now", lambda: now)
    monkeypatch.setattr(executor, "determine_active_profile", lambda *args: {})
    monkeypatch.setattr(executor, "resolve_next_datetime", lambda *args: target)
    tracker = Mock(return_value=Mock())
    monkeypatch.setattr(executor, "async_track_point_in_time", tracker)
    worker = executor.ShutterActionExecutor(hass, coordinator, coordinator.shutters["cover.one"], Mock(), Mock(), Mock(), Mock())
    worker._arm("close")
    scheduled = [call.args[2] for call in tracker.call_args_list]
    expected = [target] if expected_lead is None else [target - timedelta(minutes=expected_lead), target]
    assert scheduled == expected
    tracker.reset_mock()
    worker._arm("open")
    assert [call.args[2] for call in tracker.call_args_list] == [target]
    worker.cancel_all()
