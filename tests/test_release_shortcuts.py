"""Validate persistence and visibility rules for dashboard shortcuts."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_shutter.const import DATA_COORDINATOR, DOMAIN
from custom_components.smart_shutter.websocket_api import (
    DEFAULT_HOME_SHORTCUTS,
    _visible_home_shortcuts,
    handle_save_shortcuts,
)


def _connection():
    return SimpleNamespace(
        user=SimpleNamespace(is_admin=True, id="admin"),
        send_result=Mock(),
        send_error=Mock(),
        async_handle_exception=Mock(),
    )


async def _invoke(hass, connection, msg):
    handle_save_shortcuts(hass, connection, {"id": 1, **msg})
    await hass.async_block_till_done()
    connection.async_handle_exception.assert_not_called()


def _entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={"covers": ["cover.kitchen"], "names": {}},
        options={
            "notify_service": "notify.owner",
            "custom_areas": [{"id": "south", "name": "South"}],
        },
    )
    entry.add_to_hass(hass)
    hass.data[DOMAIN] = {entry.entry_id: {DATA_COORDINATOR: SimpleNamespace(entry=entry)}}
    return entry


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_save_shortcuts_normalizes_and_preserves_other_options(hass):
    entry = _entry(hass)
    conn = _connection()
    shortcuts = [
        {
            "id": "morning",
            "name": "  Open south  ",
            "icon": "mdi:window-shutter-open",
            "kind": "cover",
            "target": "south",
            "action": "open",
            "ignored": "field",
        },
        {
            "id": "later",
            "name": "Close in 20",
            "icon": "mdi:clock-outline",
            "kind": "postpone",
            "target": "all",
            "action": "close",
            "minutes": "20",
        },
    ]
    await _invoke(hass, conn, {"type": "smart_shutter/save_shortcuts", "shortcuts": shortcuts})

    assert conn.send_result.call_args.args[1] == {"success": True, "shortcuts": [
        {"id": "morning", "name": "Open south", "icon": "mdi:window-shutter-open", "kind": "cover", "target": "south", "action": "open"},
        {"id": "later", "name": "Close in 20", "icon": "mdi:clock-outline", "kind": "postpone", "target": "all", "action": "close", "minutes": 20},
    ]}
    assert entry.options["home_shortcuts"] == conn.send_result.call_args.args[1]["shortcuts"]
    assert entry.options["notify_service"] == "notify.owner"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_save_shortcuts_rejects_invalid_targets_actions_and_duplicate_ids(hass):
    entry = _entry(hass)
    conn = _connection()
    before = dict(entry.options)
    cases = [
        {"id": "bad-target", "name": "Bad", "icon": "mdi:home", "kind": "cover", "target": "unknown", "action": "open"},
        {"id": "bad-action", "name": "Bad", "icon": "mdi:home", "kind": "cover", "target": "all", "action": "call_service"},
        {"id": "bad-icon", "name": "Bad", "icon": "javascript:alert", "kind": "navigate", "view": "overview"},
    ]
    for shortcut in cases:
        await _invoke(hass, conn, {"type": "smart_shutter/save_shortcuts", "shortcuts": [shortcut]})
        assert conn.send_result.call_args.args[1]["success"] is False
        assert entry.options == before

    duplicate = {"id": "same", "name": "Okay", "icon": "mdi:home", "kind": "navigate", "view": "overview"}
    await _invoke(hass, conn, {"type": "smart_shutter/save_shortcuts", "shortcuts": [duplicate, duplicate]})
    assert conn.send_result.call_args.args[1] == {"success": False, "validation_error": "duplicate_id"}
    assert entry.options == before


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_save_shortcuts_rejects_unhashable_values_and_non_integer_minutes(hass):
    entry = _entry(hass)
    conn = _connection()
    base = {"id": "malformed", "name": "Malformed", "icon": "mdi:home"}
    cases = [
        ({**base, "kind": [], "target": "all", "action": "open"}, "invalid_kind"),
        ({**base, "kind": "navigate", "view": {}}, "invalid_view"),
        ({**base, "kind": "cover", "target": {}, "action": "open"}, "invalid_target"),
        ({**base, "kind": "cover", "target": "all", "action": []}, "invalid_action"),
        ({**base, "kind": "postpone", "target": "all", "action": "open", "minutes": True}, "invalid_minutes"),
        ({**base, "kind": "postpone", "target": "all", "action": "open", "minutes": 1.5}, "invalid_minutes"),
    ]

    for shortcut, error in cases:
        await _invoke(hass, conn, {"type": "smart_shutter/save_shortcuts", "shortcuts": [shortcut]})
        assert conn.send_result.call_args.args[1] == {"success": False, "validation_error": error}
        assert entry.options.get("home_shortcuts") is None


def test_shortcut_visibility_keeps_guest_targets_inside_assigned_areas():
    shortcuts = [
        *DEFAULT_HOME_SHORTCUTS,
        {"id": "south-open", "kind": "cover", "target": "south"},
        {"id": "north-open", "kind": "cover", "target": "north"},
        {"id": "admin-settings", "kind": "navigate", "view": "settings-global"},
        {"id": "areas", "kind": "navigate", "view": "settings-areas"},
        {"id": "automation", "kind": "automation", "target": "all"},
    ]

    assert [item["id"] for item in _visible_home_shortcuts(shortcuts, {"south"})] == [
        "default-open", "default-stop", "default-close", "south-open", "areas",
    ]
    assert _visible_home_shortcuts(shortcuts, set()) == []
