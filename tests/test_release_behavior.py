"""Regression checks for guest access, frost, notification routing, and area triggers."""

from datetime import time
from types import SimpleNamespace

from custom_components.smart_shutter.__init__ import _find_manager_by_trigger_name
from custom_components.smart_shutter.const import (
    DATA_COORDINATOR,
    DATA_SCHEDULER_MANAGER,
    DOMAIN,
)
from custom_components.smart_shutter.coordinator import SmartShutterCoordinator
from custom_components.smart_shutter import websocket_api as ws


def _coordinator(options: dict, states: dict | None = None) -> SmartShutterCoordinator:
    coordinator = SmartShutterCoordinator.__new__(SmartShutterCoordinator)
    coordinator.entry = SimpleNamespace(options=options)
    coordinator.hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: (states or {}).get(entity_id))
    )
    coordinator._area_temp_sensor_cache = {}
    return coordinator


def test_guest_can_only_access_assigned_area_covers() -> None:
    coordinator = _coordinator(
        {
            "custom_areas": [
                {"id": "guest", "assigned_ha_user_ids": ["guest-user"]},
                {"id": "private", "assigned_ha_user_ids": ["owner"]},
            ],
            "shutter_areas": {
                "cover.guest": ["guest"],
                "cover.shared": ["guest", "private"],
                "cover.private": ["private"],
            },
        }
    )
    guest = SimpleNamespace(user=SimpleNamespace(id="guest-user", is_admin=False))
    unassigned = SimpleNamespace(user=SimpleNamespace(id="stranger", is_admin=False))
    admin = SimpleNamespace(user=SimpleNamespace(id="owner", is_admin=True))

    assert ws._allowed_area_ids(coordinator, guest) == {"guest"}
    assert ws._cover_allowed(coordinator, "cover.guest", {"guest"})
    assert ws._cover_allowed(coordinator, "cover.shared", {"guest"})
    assert not ws._cover_allowed(coordinator, "cover.private", {"guest"})
    assert ws._allowed_area_ids(coordinator, unassigned) == set()
    assert not ws._cover_allowed(coordinator, "cover.guest", set())
    assert ws._allowed_area_ids(coordinator, admin) is None
    assert ws._cover_allowed(coordinator, "cover.private", None)


def test_all_card_websocket_commands_are_registered(monkeypatch) -> None:
    names: list[str] = []
    monkeypatch.setattr(ws.websocket_api, "async_register_command", lambda hass, handler: names.append(handler.__name__))

    ws.async_register_websocket_commands(object())

    assert len(names) == 17
    assert len(set(names)) == 17
    assert {
        "handle_get_config",
        "handle_save_shortcuts",
        "handle_save_shutter_notifications",
        "handle_complete_onboarding",
        "handle_save_own_area_settings",
        "handle_save_own_area_schedules",
        "handle_get_forecast",
    } <= set(names)


def test_frost_blocks_for_binary_sensor_or_either_assigned_area() -> None:
    states = {
        "binary_sensor.frost": SimpleNamespace(state="off"),
        "sensor.outside": SimpleNamespace(state="6"),
        "sensor.guest_inside": SimpleNamespace(state="2"),
        "sensor.private_inside": SimpleNamespace(state="18"),
    }
    coordinator = _coordinator(
        {
            "frost_entity": "binary_sensor.frost",
            "outside_temp_sensor": "sensor.outside",
            "frost_threshold_c": 0,
            "custom_areas": [
                {"id": "guest", "inside_temp_sensor": "sensor.guest_inside", "frost_threshold_c": 3},
                {"id": "private", "inside_temp_sensor": "sensor.private_inside"},
            ],
            "shutter_areas": {"cover.shared": ["guest", "private"], "cover.private": ["private"]},
        },
        states,
    )

    assert coordinator.is_frost_active_for("cover.shared")
    assert not coordinator.is_frost_active_for("cover.private")
    states["binary_sensor.frost"] = SimpleNamespace(state="on")
    assert coordinator.is_frost_active_for("cover.private")


def test_notification_service_uses_area_override() -> None:
    coordinator = _coordinator(
        {
            "notify_service": "notify.owner",
            "custom_areas": [{"id": "guest", "notify_service": "notify.guest"}],
            "shutter_areas": {"cover.guest": ["guest"]},
        }
    )
    assert coordinator.effective_notify_service("cover.guest") == "notify.guest"
    assert coordinator.effective_notify_service("cover.other") == "notify.owner"


def test_external_area_trigger_reaches_every_member_only() -> None:
    calls: list[tuple] = []
    manager = SimpleNamespace(request_external_trigger=lambda *args, **kwargs: calls.append((args, kwargs)) or True)
    coordinator = _coordinator(
        {
            "external_triggers": [{"name": "Wake up", "area_id": "guest", "action": "open"}],
            "shutter_areas": {
                "cover.one": ["guest"],
                "cover.two": ["guest", "shared"],
                "cover.other": ["shared"],
            },
        }
    )
    hass = SimpleNamespace(data={DOMAIN: {"entry": {DATA_COORDINATOR: coordinator, DATA_SCHEDULER_MANAGER: manager}}})

    _find_manager_by_trigger_name(hass, "Wake up", time(7, 15))

    assert [args[0] for args, _ in calls] == ["cover.one", "cover.two"]
    assert all(args[1:] == ("open", time(7, 15)) for args, _ in calls)
    assert all(kwargs["source"] == "External trigger: Wake up" for _, kwargs in calls)
