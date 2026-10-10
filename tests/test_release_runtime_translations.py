"""Regression checks for localized backend output and stable action attributes."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from freezegun import freeze_time
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_shutter.coordinator import ManagedShutter, SmartShutterCoordinator
from custom_components.smart_shutter.executor import NotificationBatcher
from custom_components.smart_shutter.scheduler import ShutterSchedule
from custom_components.smart_shutter.sensor import GlobalNextActionSensor, NextActionSensor
from custom_components.smart_shutter.sun_position import SunPositionMonitor


def coordinator(hass, options=None):
    return SmartShutterCoordinator(hass, MockConfigEntry(
        domain="smart_shutter", data={"covers": [], "names": {}}, options=options or {},
    ))


@pytest.mark.parametrize("language,expected", [
    ("de", "Küche, Büro fahren herunter. Auslöser: Sonnenuntergang."),
    ("de-DE", "Küche, Büro fahren herunter. Auslöser: Sonnenuntergang."),
    ("en", "Küche, Büro are closing. Trigger: Sunset."),
    ("fr", "Küche, Büro are closing. Trigger: Sunset."),
])
async def test_movement_notifications_follow_ha_language(hass, language, expected):
    hass.config.language = language
    batcher = NotificationBatcher(hass, coordinator(hass))
    assert batcher._format_moves([("Küche", "closed", "Sunset"), ("Büro", "closed", "Sunset")]) == expected


async def test_custom_german_template_receives_translated_action_and_trigger(hass):
    hass.config.language = "de"
    template = "{{ names }} wurden {{ action }}. Auslöser: {{ trigger }}."
    coord = coordinator(hass, {"notify_text_moved": template})
    batcher = NotificationBatcher(hass, coord)
    assert batcher._format_moves([("Küche", "closed", "Sunset")]) == "Küche wurden geschlossen. Auslöser: Sonnenuntergang."
    assert coord.entry.options["notify_text_moved"] == template


@pytest.mark.parametrize("sensor_cls", [GlobalNextActionSensor, NextActionSensor])
@pytest.mark.parametrize("language,day,action,expected", [
    ("de", 0, "close", "Heute 19:38 schließen"),
    ("de", 1, "open", "Morgen 19:38 öffnen"),
    ("en", 0, "close", "Today 19:38 close"),
    ("en", 1, "open", "Tomorrow 19:38 open"),
    ("de", 3, "close", "05.10.2026 19:38 schließen"),
])
async def test_next_action_sensor_display_and_attributes(hass, sensor_cls, language, day, action, expected):
    hass.config.language = language
    coord = coordinator(hass)
    arg = ManagedShutter("cover.kitchen", "Küche") if sensor_cls is NextActionSensor else "global"
    sensor = sensor_cls(coord, arg)
    sensor.hass = hass
    when = datetime(2026, 10, 2, 19, 38, tzinfo=timezone.utc) + timedelta(days=day)
    with freeze_time("2026-10-02 12:00:00+00:00"):
        sensor._apply_schedule(ShutterSchedule("weekday", when if action == "open" else None, when if action == "close" else None))
    assert sensor.native_value == expected
    assert sensor.extra_state_attributes["action"] == action
    assert sensor.extra_state_attributes["scheduled_at"] == when.isoformat()


@pytest.mark.parametrize("enabled,expected", [(False, "Automatik deaktiviert"), (True, "Unbekannt")])
async def test_unscheduled_sensor_status_is_german(hass, enabled, expected):
    hass.config.language = "de"
    sensor = GlobalNextActionSensor(coordinator(hass), "global")
    sensor.hass = hass
    sensor._apply_schedule(ShutterSchedule("weekday", None, None, enabled, enabled))
    assert sensor.native_value == expected


async def test_preclose_warning_and_frost_notification_are_german(hass):
    hass.config.language = "de"
    batcher = NotificationBatcher(hass, coordinator(hass, {"notify_service": "notify.phone"}))
    batcher._call_notify = AsyncMock()
    await batcher.send_pre_close_warning(ManagedShutter("cover.kitchen", "Küche"), "close", datetime(2026, 10, 2, 19, 38), [5, 10, 15])
    call = batcher._call_notify.call_args
    assert call.args[1:3] == ("Rollladen schließt bald", "Küche schließt um 19:38 Uhr.")
    assert call.kwargs["extra_data"]["actions"][-1] == {"action": "ssm|skip|cover.kitchen|close", "title": "Heute überspringen"}
    await batcher._send_batch("notify.phone", [], ["Küche"])
    assert batcher._call_notify.call_args.args[2] == "Frostschutz aktiv: Küche wird nicht bewegt."


async def test_invalid_template_falls_back_to_german(hass):
    hass.config.language = "de"
    batcher = NotificationBatcher(hass, coordinator(hass, {"notify_text_moved": "{{ broken"}))
    assert batcher._format_moves([("Küche", "opened", "Sunrise")]) == "Küche fährt hoch. Auslöser: Sonnenaufgang."


async def test_sun_rule_notifications_are_german(hass, monkeypatch):
    hass.config.language = "de"
    monitor = SunPositionMonitor.__new__(SunPositionMonitor)
    monitor.hass = hass
    monitor._coordinator = coordinator(hass, {"notify_service": "notify.phone"})
    monitor._coordinator.shutters["cover.kitchen"] = ManagedShutter("cover.kitchen", "Küche")
    notify = AsyncMock()
    monkeypatch.setattr(type(hass.services), "async_call", notify)
    area = {"name": "Süd", "sun_position_target": 30}
    await monitor._send_notification(area, ["cover.kitchen"], 30)
    assert notify.call_args.args[2]["message"] == "Sonnenstandsregel 'Süd': 1 Rollladen auf 30% gefahren."
    await monitor._send_prenotification(area, ["cover.kitchen"], 5)
    assert notify.call_args.args[2]["message"] == "Sonnenstandsregel 'Süd': Rollläden fahren in etwa 5 Minuten auf 30%."
    await monitor._send_prenotification(area, ["cover.kitchen"], 1)
    assert notify.call_args.args[2]["message"] == "Sonnenstandsregel 'Süd': Rollläden fahren in etwa 1 Minute auf 30%."


async def test_saved_default_copies_follow_language_and_custom_raw_values_work(hass):
    from custom_components.smart_shutter.const import DEFAULT_NOTIFY_TEXT_MOVED
    hass.config.language = "de"
    coord = coordinator(hass, {"notify_text_moved": DEFAULT_NOTIFY_TEXT_MOVED})
    batcher = NotificationBatcher(hass, coord)
    assert batcher._format_moves([("Küche", "closed", "Schedule")]) == "Küche fährt herunter. Auslöser: Zeitplan."
    assert coord.entry.options["notify_text_moved"] == DEFAULT_NOTIFY_TEXT_MOVED
    raw = "{{ action_raw }} / {{ trigger_raw }} / {{ action }} / {{ trigger }}"
    batcher = NotificationBatcher(hass, coordinator(hass, {"notify_text_moved": raw}))
    assert batcher._format_moves([("Küche", "opened", "Sunrise")]) == "opened / Sunrise / geöffnet / Sonnenaufgang"


async def test_english_warning_keeps_technical_button_payload(hass):
    hass.config.language = "en"
    batcher = NotificationBatcher(hass, coordinator(hass, {"notify_service": "notify.phone"}))
    batcher._call_notify = AsyncMock()
    await batcher.send_pre_close_warning(ManagedShutter("cover.kitchen", "Kitchen"), "close", datetime(2026, 10, 2, 19, 38), [5])
    call = batcher._call_notify.call_args
    assert call.args[1:3] == ("Shutter closing soon", "Kitchen closes at 19:38.")
    assert call.kwargs["extra_data"]["actions"][-1]["title"] == "Skip today"
