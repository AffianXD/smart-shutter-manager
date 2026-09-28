// Baut Registry-Daten + Hass-States für EINEN Test-Rollladen (cover.testroom)
// plus globales Gerät, passend zu den unique_id-Mustern aus dem Backend.
function buildFixture() {
  const coverEntityId = "cover.testroom";
  const deviceHaId = "dev_testroom";
  const globalHaId = "dev_global";
  const localDeviceKey = `smart_shutter_${coverEntityId}`;
  const globalDeviceKey = "smart_shutter_global_entry1";

  const devices = [
    { id: deviceHaId, identifiers: [["smart_shutter", localDeviceKey]], area_id: "area1", name: "Testrollladen", name_by_user: null },
    { id: globalHaId, identifiers: [["smart_shutter", globalDeviceKey]], area_id: null, name: "Smart Shutter Manager – Global", name_by_user: null },
  ];
  const areas = [{ area_id: "area1", name: "Wohnzimmer", floor_id: null }];
  const floors = [];

  const states = {};
  function reg(entity_id, device_id, unique_id, domain, state, attributes) {
    states[entity_id] = { entity_id, state, attributes: attributes || {} };
    return { entity_id, device_id, platform: "smart_shutter", unique_id };
  }

  const entities = [];
  // Cover selbst (nicht Teil der Integration, aber Zustand wird gebraucht)
  states[coverEntityId] = { entity_id: coverEntityId, state: "closed", attributes: { current_position: 0 } };

  // --- lokal (Rollladen-Gerät) ---
  entities.push(reg("switch.testroom_automation_open", deviceHaId, `${localDeviceKey}_automation_open`, "switch", "on"));
  entities.push(reg("switch.testroom_automation_close", deviceHaId, `${localDeviceKey}_automation_close`, "switch", "on"));

  entities.push(reg("select.testroom_open_source", deviceHaId, `${localDeviceKey}_open_source`, "select", "global", { options: ["global", "local"] }));
  entities.push(reg("select.testroom_close_source", deviceHaId, `${localDeviceKey}_close_source`, "select", "global", { options: ["global", "local"] }));

  entities.push(reg("select.testroom_open_position_source", deviceHaId, `${localDeviceKey}_open_position_source`, "select", "global", { options: ["global", "local"] }));
  entities.push(reg("select.testroom_close_position_source", deviceHaId, `${localDeviceKey}_close_position_source`, "select", "global", { options: ["global", "local"] }));

  entities.push(reg("select.testroom_open_type", deviceHaId, `${localDeviceKey}_open_type`, "select", "sunrise", { options: ["time", "sunrise"] }));
  entities.push(reg("select.testroom_close_type", deviceHaId, `${localDeviceKey}_close_type`, "select", "sunset", { options: ["time", "sunset"] }));

  entities.push(reg("number.testroom_open_sun_offset", deviceHaId, `${localDeviceKey}_open_sun_offset`, "number", "0", { min: -60, max: 60, step: 1 }));
  entities.push(reg("number.testroom_close_sun_offset", deviceHaId, `${localDeviceKey}_close_sun_offset`, "number", "0", { min: -60, max: 60, step: 1 }));

  entities.push(reg("number.testroom_open_position", deviceHaId, `${localDeviceKey}_open_position`, "number", "100", { min: 0, max: 100, step: 1 }));
  entities.push(reg("number.testroom_close_position", deviceHaId, `${localDeviceKey}_close_position`, "number", "0", { min: 0, max: 100, step: 1 }));

  entities.push(reg("select.testroom_open_werktag_time_source", deviceHaId, `${localDeviceKey}_open_werktag_time_source`, "select", "global", { options: ["global", "local"] }));
  entities.push(reg("select.testroom_close_werktag_time_source", deviceHaId, `${localDeviceKey}_close_werktag_time_source`, "select", "global", { options: ["global", "local"] }));
  entities.push(reg("time.testroom_open_werktag", deviceHaId, `${localDeviceKey}_open_werktag`, "time", "07:00:00"));
  entities.push(reg("time.testroom_close_werktag", deviceHaId, `${localDeviceKey}_close_werktag`, "time", "20:00:00"));

  entities.push(reg("sensor.testroom_active_profile", deviceHaId, `${localDeviceKey}_active_profile`, "sensor", "weekday"));
  entities.push(reg("sensor.testroom_next_action", deviceHaId, `${localDeviceKey}_next_action`, "sensor", "Tomorrow 20:00 close", { action: "close", scheduled_at: new Date(Date.now() + 3600000).toISOString() }));

  // --- global (Global-Gerät, gleiche Suffixe) ---
  entities.push(reg("select.global_open_type", globalHaId, `${globalDeviceKey}_open_type`, "select", "time", { options: ["time", "sunrise"] }));
  entities.push(reg("select.global_close_type", globalHaId, `${globalDeviceKey}_close_type`, "select", "time", { options: ["time", "sunset"] }));
  entities.push(reg("switch.global_automation_open", globalHaId, `${globalDeviceKey}_automation_open`, "switch", "on"));
  entities.push(reg("switch.global_automation_close", globalHaId, `${globalDeviceKey}_automation_close`, "switch", "on"));
  entities.push(reg("number.global_open_sun_offset", globalHaId, `${globalDeviceKey}_open_sun_offset`, "number", "0", { min: -60, max: 60, step: 1 }));
  entities.push(reg("number.global_close_sun_offset", globalHaId, `${globalDeviceKey}_close_sun_offset`, "number", "0", { min: -60, max: 60, step: 1 }));
  entities.push(reg("number.global_open_position", globalHaId, `${globalDeviceKey}_open_position`, "number", "100", { min: 0, max: 100, step: 1 }));
  entities.push(reg("number.global_close_position", globalHaId, `${globalDeviceKey}_close_position`, "number", "0", { min: 0, max: 100, step: 1 }));
  entities.push(reg("time.global_open_werktag", globalHaId, `${globalDeviceKey}_open_werktag`, "time", "07:00:00"));
  entities.push(reg("time.global_close_werktag", globalHaId, `${globalDeviceKey}_close_werktag`, "time", "20:00:00"));

  // --- zweiter Rollladen (nur fürs Bulk-Editing gebraucht) ---
  const coverEntityId2 = "cover.testroom2";
  const deviceHaId2 = "dev_testroom2";
  const localDeviceKey2 = `smart_shutter_${coverEntityId2}`;
  devices.push({ id: deviceHaId2, identifiers: [["smart_shutter", localDeviceKey2]], area_id: "area1", name: "Testrollladen 2", name_by_user: null });
  states[coverEntityId2] = { entity_id: coverEntityId2, state: "closed", attributes: { current_position: 0 } };
  entities.push(reg("switch.testroom2_automation_open", deviceHaId2, `${localDeviceKey2}_automation_open`, "switch", "on"));
  entities.push(reg("switch.testroom2_automation_close", deviceHaId2, `${localDeviceKey2}_automation_close`, "switch", "on"));
  entities.push(reg("select.testroom2_open_source", deviceHaId2, `${localDeviceKey2}_open_source`, "select", "global", { options: ["global", "local"] }));
  entities.push(reg("select.testroom2_close_source", deviceHaId2, `${localDeviceKey2}_close_source`, "select", "global", { options: ["global", "local"] }));
  entities.push(reg("select.testroom2_open_position_source", deviceHaId2, `${localDeviceKey2}_open_position_source`, "select", "global", { options: ["global", "local"] }));
  entities.push(reg("select.testroom2_close_position_source", deviceHaId2, `${localDeviceKey2}_close_position_source`, "select", "global", { options: ["global", "local"] }));
  entities.push(reg("select.testroom2_open_type", deviceHaId2, `${localDeviceKey2}_open_type`, "select", "sunrise", { options: ["time", "sunrise"] }));
  entities.push(reg("select.testroom2_close_type", deviceHaId2, `${localDeviceKey2}_close_type`, "select", "sunset", { options: ["time", "sunset"] }));
  entities.push(reg("number.testroom2_open_sun_offset", deviceHaId2, `${localDeviceKey2}_open_sun_offset`, "number", "0", { min: -60, max: 60, step: 1 }));
  entities.push(reg("number.testroom2_close_sun_offset", deviceHaId2, `${localDeviceKey2}_close_sun_offset`, "number", "0", { min: -60, max: 60, step: 1 }));
  entities.push(reg("number.testroom2_open_position", deviceHaId2, `${localDeviceKey2}_open_position`, "number", "100", { min: 0, max: 100, step: 1 }));
  entities.push(reg("number.testroom2_close_position", deviceHaId2, `${localDeviceKey2}_close_position`, "number", "0", { min: 0, max: 100, step: 1 }));
  entities.push(reg("select.testroom2_open_werktag_time_source", deviceHaId2, `${localDeviceKey2}_open_werktag_time_source`, "select", "global", { options: ["global", "local"] }));
  entities.push(reg("select.testroom2_close_werktag_time_source", deviceHaId2, `${localDeviceKey2}_close_werktag_time_source`, "select", "global", { options: ["global", "local"] }));
  entities.push(reg("time.testroom2_open_werktag", deviceHaId2, `${localDeviceKey2}_open_werktag`, "time", "07:00:00"));
  entities.push(reg("time.testroom2_close_werktag", deviceHaId2, `${localDeviceKey2}_close_werktag`, "time", "20:00:00"));
  entities.push(reg("sensor.testroom2_active_profile", deviceHaId2, `${localDeviceKey2}_active_profile`, "sensor", "weekday"));
  entities.push(reg("sensor.testroom2_next_action", deviceHaId2, `${localDeviceKey2}_next_action`, "sensor", "Tomorrow 20:00 close", { action: "close", scheduled_at: new Date(Date.now() + 3600000).toISOString() }));

  // --- Custom-Profile mit einem echten Konflikt (FR15) ---
  const customSchedules = [
    { id: "custom_a", name: "Profil A", weekdays: [0, 1, 2, 3, 4], interval_weeks: 1, open_time: "07:30:00", close_time: "19:00:00" },
    { id: "custom_b", name: "Profil B", weekdays: [0, 1, 2, 3, 4], interval_weeks: 1, open_time: "08:00:00", close_time: "19:30:00" },
  ];
  const scheduleConflicts = { custom_a: ["custom_b"], custom_b: ["custom_a"] };

  // --- Ereignisverlauf-Fixture (FR12/13) ---
  const today = new Date();
  today.setHours(7, 0, 0, 0);
  const eventHistory = {
    [coverEntityId]: [
      { ts: today.toISOString(), action: "open", type: "prenotify", detail: "Vorwarnung gesendet" },
      { ts: new Date(today.getTime() + 5 * 60000).toISOString(), action: "open", type: "executed", detail: "hochgefahren (Sonnenaufgang, Ziel 100%)" },
    ],
  };

  // --- Vorhersage-Fixture (native Zeitleiste, Zukunft-Teil) ---
  const forecastBase = new Date();
  forecastBase.setHours(8, 0, 0, 0);
  const forecast = {
    [coverEntityId]: [
      { action: "open", ts: forecastBase.toISOString() },
      { action: "close", ts: new Date(forecastBase.getTime() + 11 * 3600000).toISOString() },
      { action: "open", ts: new Date(forecastBase.getTime() + 24 * 3600000).toISOString() },
    ],
    [coverEntityId2]: [
      { action: "open", ts: forecastBase.toISOString() },
    ],
  };

  // --- Historie-Fixture (native Zeitleiste, Vergangenheit via
  // history/period-REST-API) ---
  const histBase = new Date();
  histBase.setHours(0, 0, 0, 0);
  histBase.setDate(histBase.getDate() - 2); // vor 2 Tagen, 00:00 Uhr
  const history = {
    [coverEntityId]: [
      { entity_id: coverEntityId, state: "closed", last_changed: histBase.toISOString() },
      { entity_id: coverEntityId, state: "open", last_changed: new Date(histBase.getTime() + 8 * 3600000).toISOString() },
      { entity_id: coverEntityId, state: "closed", last_changed: new Date(histBase.getTime() + 20 * 3600000).toISOString() },
    ],
    [coverEntityId2]: [
      { entity_id: coverEntityId2, state: "open", last_changed: histBase.toISOString() },
    ],
  };

  return {
    entities, devices, areas, floors, states, coverEntityId, coverEntityId2,
    customSchedules, scheduleConflicts, eventHistory, forecast, history,
  };
}
module.exports = { buildFixture };
