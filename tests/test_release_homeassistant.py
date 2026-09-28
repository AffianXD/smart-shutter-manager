"""Exercise the release migration with Home Assistant's real config entry API."""

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from homeassistant.core import State

from custom_components.smart_shutter import async_migrate_entry
from custom_components.smart_shutter.const import DATA_COORDINATOR, DOMAIN
from custom_components.smart_shutter.websocket_api import _allowed_area_ids


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_v0202_entry_migrates_without_losing_other_options(hass):
    entry = MockConfigEntry(
        domain="smart_shutter",
        version=1,
        data={"cover_selection": ["cover.kitchen"]},
        options={
            "ferien_wochentage": ["0", "1", "2", "3", "4"],
            "notify_service": "notify.owner",
            "custom_schedules": [{"id": "custom_1", "name": "Guests"}],
        },
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2
    assert entry.options == {
        "holiday_weekdays": ["0", "1", "2", "3", "4"],
        "notify_service": "notify.owner",
        "custom_schedules": [{"id": "custom_1", "name": "Guests"}],
    }
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_both_languages_load_select_states_and_service_labels(hass):
    for language, expected in (("en", "Individual"), ("de", "Individuell")):
        entity_labels = await async_get_translations(
            hass, language, "entity", integrations={"smart_shutter"}
        )
        service_labels = await async_get_translations(
            hass, language, "services", integrations={"smart_shutter"}
        )
        selector_labels = await async_get_translations(
            hass, language, "selector", integrations={"smart_shutter"}
        )
        device_labels = await async_get_translations(
            hass, language, "device", integrations={"smart_shutter"}
        )
        assert device_labels["component.smart_shutter.device.managed_shutter.name"] == (
            "{name} Shutter" if language == "en" else "{name} Rollladen"
        )
        assert entity_labels["component.smart_shutter.entity.select.open_source.state.local"] == expected
        assert entity_labels["component.smart_shutter.entity.sensor.active_profile.state.weekday"] == ("Weekday" if language == "en" else "Arbeitstag")
        assert "component.smart_shutter.services.skip_action.name" in service_labels
        assert "component.smart_shutter.selector.custom_weekday.options.mon" in selector_labels
        assert selector_labels["component.smart_shutter.selector.schedule_action.options.edit"] == ("Edit" if language == "en" else "Bearbeiten")


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_fresh_entry_registers_entities_services_and_websocket(hass, hass_client):
    hass.config.language = "de"
    hass.states.async_set(
        "cover.kitchen",
        "closed",
        {"friendly_name": "Kitchen shutter", "supported_features": 11, "current_position": 0},
    )
    entry = MockConfigEntry(
        domain="smart_shutter",
        version=2,
        data={"covers": ["cover.kitchen"], "names": {}},
        options={},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service("smart_shutter", "skip_action")
    assert hass.data.get("smart_shutter_ws_registered") is True
    assert hass.data.get("smart_shutter_frontend_registered") is True
    client = await hass_client()
    response = await client.get("/smart_shutter_frontend/smart-shutter-card.js")
    assert response.status == 200
    assert "smart-shutter-card" in await response.text()
    profile_entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_cover.kitchen_active_profile"
    )
    assert profile_entity_id is not None
    assert hass.states.get(profile_entity_id) is not None
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, f"{DOMAIN}_cover.kitchen"), entry.entry_id
    )
    assert device is not None
    assert device.name == "Kitchen Rollladen"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_v0202_upgrade_keeps_registered_profile_entity_id(hass):
    hass.states.async_set("cover.kitchen", "closed", {"supported_features": 11})
    hass.states.async_set("cover.dining", "closed", {"supported_features": 11})
    old_schedule = {
        "id": "guest_schedule", "name": "Guest schedule", "weekdays": [0, 1, 2, 3, 4],
        "interval_weeks": 1, "open_time": "08:00:00", "close_time": "20:00:00",
    }
    old_trigger = {"id": "wake_up", "name": "Wake up", "area_id": "guest_area", "action": "open"}
    entry = MockConfigEntry(
        domain="smart_shutter",
        version=1,
        data={"covers": ["cover.kitchen", "cover.dining"], "names": {}},
        options={
            "ferien_wochentage": ["0", "1", "2", "3", "4"],
            "notify_service": "notify.owner",
            "custom_schedules": [old_schedule],
            "external_triggers": [old_trigger],
            "custom_areas": [{
                "id": "guest_area", "name": "Guest area", "assigned_ha_user_ids": ["guest-user"],
                "notify_service": "notify.guest",
            }],
            "shutter_areas": {"cover.kitchen": ["guest_area"], "cover.dining": ["guest_area"]},
        },
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    previous = registry.async_get_or_create(
        "time",
        "smart_shutter",
        "smart_shutter_cover.kitchen_open_werktag",
        suggested_object_id="my_existing_weekday_open_time",
        config_entry=entry,
    )
    previous_select = registry.async_get_or_create(
        "select", "smart_shutter", "smart_shutter_cover.kitchen_open_source",
        suggested_object_id="my_existing_open_source", config_entry=entry,
    )
    mock_restore_cache(hass, [State(previous_select.entity_id, "Individuell", {"options": ["Global", "Individuell"]})])

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.options["holiday_weekdays"] == ["0", "1", "2", "3", "4"]
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    assert coordinator.custom_schedules == [old_schedule]
    assert coordinator.get_external_trigger_by_name("Wake up") == old_trigger
    assert coordinator.effective_notify_service("cover.kitchen") == "notify.guest"
    guest = type("Guest", (), {"user": type("User", (), {"id": "guest-user", "is_admin": False})()})()
    assert _allowed_area_ids(coordinator, guest) == {"guest_area"}
    retained = registry.async_get_entity_id(
        "time", "smart_shutter", "smart_shutter_cover.kitchen_open_werktag"
    )
    assert retained == previous.entity_id
    assert hass.states.get(retained) is not None
    assert registry.async_get_entity_id(
        "select", "smart_shutter", "smart_shutter_cover.kitchen_open_source"
    ) == previous_select.entity_id
    assert hass.states.get(previous_select.entity_id).state == "local"
