"""Exercise managing covers through options and admin WebSocket commands."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from homeassistant.exceptions import Unauthorized
from homeassistant.data_entry_flow import InvalidData
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_shutter.const import DOMAIN, DATA_COORDINATOR, DATA_SCHEDULER_MANAGER
from custom_components.smart_shutter import websocket_api as ws


def connection(admin=True):
    return SimpleNamespace(user=SimpleNamespace(is_admin=admin, id="user"), send_result=Mock(), send_error=Mock(), async_handle_exception=Mock())


async def invoke(hass, handler, connection, msg):
    handler(hass, connection, {"id": 1, **msg})
    await hass.async_block_till_done()
    connection.async_handle_exception.assert_not_called()


def entry_with_covers(hass):
    hass.states.async_set("cover.kitchen", "closed", {"supported_features": 11, "friendly_name": "Kitchen"})
    hass.states.async_set("cover.office", "closed", {"supported_features": 11, "friendly_name": "Office"})
    hass.states.async_set("cover.unsupported", "closed", {"supported_features": 1})
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={"covers": ["cover.kitchen", "cover.missing"], "names": {"cover.kitchen": "Küche", "cover.missing": "Missing"}}, options={"notify_service": "notify.owner", "custom_areas": [{"id": "south"}], "custom_schedules": [{"id": "custom_1"}], "shutter_areas": {"cover.kitchen": ["south"], "cover.missing": ["south"]}, "shutter_notes": {"cover.kitchen": "keep", "cover.missing": "remove"}, "external_triggers": [{"id": "keep", "entity_id": "cover.kitchen"}, {"id": "remove", "entity_id": "cover.missing"}]})
    entry.add_to_hass(hass)
    hass.data[DOMAIN] = {entry.entry_id: {DATA_COORDINATOR: SimpleNamespace(entry=entry)}}
    return entry


async def test_available_covers_include_existing_missing_but_not_unsupported(hass):
    entry = entry_with_covers(hass)
    conn = connection()
    await invoke(hass, ws.handle_get_available_covers, conn, {"type": "smart_shutter/get_available_covers", "entry_id": entry.entry_id})
    result = conn.send_result.call_args.args[1]
    assert {c["entity_id"] for c in result["covers"]} == {"cover.kitchen", "cover.office", "cover.missing"}
    assert result["selected"] == ["cover.kitchen", "cover.missing"]


async def test_save_preserves_kept_settings_and_prunes_removed_cover_data(hass):
    entry = entry_with_covers(hass)
    conn = connection()
    await invoke(hass, ws.handle_save_covers, conn, {"type": "smart_shutter/save_covers", "entry_id": entry.entry_id, "covers": ["cover.kitchen", "cover.office", "cover.office"]})
    assert entry.data == {"covers": ["cover.kitchen", "cover.office"], "names": {"cover.kitchen": "Küche"}}
    assert entry.options["shutter_areas"] == {"cover.kitchen": ["south"]}
    assert entry.options["shutter_notes"] == {"cover.kitchen": "keep"}
    assert entry.options["external_triggers"] == [{"id": "keep", "entity_id": "cover.kitchen"}]
    assert entry.options["notify_service"] == "notify.owner"
    assert entry.options["custom_areas"] == [{"id": "south"}]
    assert entry.options["custom_schedules"] == [{"id": "custom_1"}]


@pytest.mark.parametrize("covers", [["cover.unsupported"], ["cover.unknown"], ["light.kitchen"]])
async def test_invalid_new_cover_is_rejected_without_mutation(hass, covers):
    entry = entry_with_covers(hass)
    before = (dict(entry.data), dict(entry.options))
    conn = connection()
    await invoke(hass, ws.handle_save_covers, conn, {"type": "smart_shutter/save_covers", "covers": covers})
    assert conn.send_error.call_args.args[1] == "invalid_selection"
    assert (dict(entry.data), dict(entry.options)) == before


async def test_existing_missing_can_be_kept_and_all_covers_can_be_removed(hass):
    entry = entry_with_covers(hass)
    conn = connection()
    await invoke(hass, ws.handle_save_covers, conn, {"type": "smart_shutter/save_covers", "covers": ["cover.missing"]})
    assert entry.data["covers"] == ["cover.missing"]
    await invoke(hass, ws.handle_save_covers, conn, {"type": "smart_shutter/save_covers", "covers": []})
    assert entry.data["covers"] == []
    assert hass.states.get("cover.kitchen") is not None


async def test_guest_cannot_discover_or_change_covers(hass):
    entry_with_covers(hass)
    for handler, msg in [(ws.handle_get_available_covers, {"type": "smart_shutter/get_available_covers"}), (ws.handle_save_covers, {"type": "smart_shutter/save_covers", "covers": []})]:
        with pytest.raises(Unauthorized):
            handler(hass, connection(False), {"id": 1, **msg})


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_options_menu_adds_management_and_validates_selection(hass):
    entry = entry_with_covers(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "manage_shutters" in result["menu_options"]
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "manage_shutters"})
    assert result["step_id"] == "manage_shutters"
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(result["flow_id"], {"cover_selection": ["cover.unsupported"]})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"cover_selection": ["cover.kitchen", "cover.office"]})
    assert result["type"] == "create_entry"
    assert entry.data["covers"] == ["cover.kitchen", "cover.office"]
    assert entry.options["notify_service"] == "notify.owner"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_add_remove_reload_keeps_source_cover_and_remaining_entity_ids(hass):
    hass.states.async_set("cover.kitchen", "closed", {"supported_features": 11, "current_position": 0})
    hass.states.async_set("cover.office", "closed", {"supported_features": 11, "current_position": 0})
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={"covers": ["cover.kitchen"], "names": {}}, options={"catch_up_window_minutes": 0})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    original = registry.async_get_entity_id("sensor", DOMAIN, "smart_shutter_cover.kitchen_next_action")
    assert original
    conn = connection()
    await invoke(hass, ws.handle_save_covers, conn, {"type": "smart_shutter/save_covers", "covers": ["cover.kitchen", "cover.office"]})
    assert registry.async_get_entity_id("sensor", DOMAIN, "smart_shutter_cover.office_next_action")
    assert registry.async_get_entity_id("sensor", DOMAIN, "smart_shutter_cover.kitchen_next_action") == original
    await invoke(hass, ws.handle_save_covers, conn, {"type": "smart_shutter/save_covers", "covers": ["cover.kitchen"]})
    assert registry.async_get_entity_id("sensor", DOMAIN, "smart_shutter_cover.office_next_action") is None
    assert hass.states.get("cover.office") is not None
    assert registry.async_get_entity_id("sensor", DOMAIN, "smart_shutter_cover.kitchen_next_action") == original
    assert all((DOMAIN, "smart_shutter_cover.office") not in d.identifiers for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id))
    await invoke(hass, ws.handle_save_covers, conn, {"type": "smart_shutter/save_covers", "covers": []})
    assert not [d for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id) if any(value.startswith("smart_shutter_cover.") for domain, value in d.identifiers if domain == DOMAIN)]
    assert hass.states.get("cover.kitchen") is not None
    assert hass.states.get("cover.office") is not None



async def test_removal_clears_only_removed_shutter_overrides_and_pause(hass):
    entry = entry_with_covers(hass)
    clear_override = Mock()
    clear_pause = Mock()
    runtime = hass.data[DOMAIN][entry.entry_id]
    runtime[DATA_COORDINATOR].clear_action_override = clear_override
    runtime[DATA_SCHEDULER_MANAGER] = SimpleNamespace(manual_intervention_guard=SimpleNamespace(clear_pause=clear_pause))
    conn = connection()
    await invoke(hass, ws.handle_save_covers, conn, {"type": "smart_shutter/save_covers", "covers": ["cover.kitchen"]})
    assert clear_override.call_args_list == [(("cover.missing", "open"),), (("cover.missing", "close"),)]
    clear_pause.assert_called_once_with("cover.missing")
