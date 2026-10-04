const assert = require("node:assert/strict");
const path = require("node:path");
const { chromium } = require("playwright");
const { buildFixture } = require("./fixtures");

async function main() {
  const fixture = buildFixture();
  for (const entry of [...fixture.entities]) {
    if (!/_(open|close)_(source|type|sun_offset|werktag|werktag_time_source)$/.test(entry.unique_id)) continue;
    for (const season of ["summer", "winter"]) {
      const entityId = `${entry.entity_id}_${season}`;
      fixture.entities.push({ ...entry, entity_id: entityId, unique_id: `${entry.unique_id}_${season}` });
      fixture.states[entityId] = JSON.parse(JSON.stringify(fixture.states[entry.entity_id]));
      fixture.states[entityId].entity_id = entityId;
      if (entityId.startsWith("time.global_close")) fixture.states[entityId].state = season === "summer" ? "23:00:00" : "20:00:00";
    }
  }
  fixture.states["sensor.testroom_next_action"].attributes.active_season = "winter";
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ timezoneId: "Europe/Berlin", locale: "de-DE" });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto("file://" + path.join(__dirname, "test.html"));
    await page.evaluate((fx) => {
      window.__calls = [];
      window.__seasonEnabled = true;
      window.__states = fx.states;
      const hass = {
        states: fx.states, language: "de", user: { is_admin: true },
        callWS: async (msg) => {
          if (msg.type === "config/entity_registry/list") return fx.entities;
          if (msg.type === "config/device_registry/list") return fx.devices;
          if (msg.type === "config/area_registry/list") return fx.areas;
          if (msg.type === "config/floor_registry/list") return fx.floors;
          if (msg.type === "config/auth/list") return [];
          if (msg.type === "smart_shutter/get_config") return {
            seasonal_enabled: window.__seasonEnabled, active_season: "winter",
            basic_settings: { seasonal_enabled: window.__seasonEnabled }, custom_areas: [],
            covers: [{ entity_id: fx.coverEntityId, name: "Test" }, { entity_id: fx.coverEntityId2, name: "Test 2" }],
          };
          if (msg.type === "smart_shutter/save_basic_settings") {
            window.__calls.push(msg);
            window.__seasonEnabled = msg.seasonal_enabled;
            return { success: true };
          }
          return {};
        },
        callService: async (domain, service, data) => {
          window.__calls.push({ domain, service, data });
          fx.states[data.entity_id].state = data.option || data.time || String(data.value);
        },
      };
      window.__hass = hass;
      const card = document.getElementById("card");
      card.setConfig({});
      card.hass = hass;
    }, fixture);
    const card = page.locator("smart-shutter-card");
    await card.locator("[data-overview-stats]").waitFor();
    const view = async (name, tab = "basic") => page.evaluate(({ name, tab }) => {
      const card = document.getElementById("card");
      card._view = name;
      card._detailDeviceId = "dev_testroom";
      card._detailTab = tab;
      card._render();
    }, { name, tab });

    await view("settings-global");
    assert.equal(await card.locator("[data-season-edit]").inputValue(), "winter");
    assert.equal(await card.locator('[data-time-entity="time.global_close_werktag_winter"]').inputValue(), "20:00");
    const before = await page.evaluate(() => window.__calls.length);
    await card.locator("[data-season-edit]").selectOption("summer");
    assert.equal(await page.evaluate(() => window.__calls.length), before, "editing another season must not call HA");
    assert.match(await card.locator("[data-season-status]").innerText(), /Winterzeit/);
    assert.equal(await card.locator('[data-time-entity="time.global_close_werktag_summer"]').inputValue(), "23:00");
    await card.locator('[data-time-entity="time.global_close_werktag_summer"]').fill("22:45");
    await card.locator('[data-time-entity="time.global_close_werktag_summer"]').dispatchEvent("change");
    assert.equal(await page.evaluate(() => window.__calls.at(-1).data.entity_id), "time.global_close_werktag_summer");
    assert.equal(await page.evaluate(() => window.__states["time.global_close_werktag_winter"].state), "20:00:00");
    console.log("OK   - global season editors are independent and never activate the edited season");

    await view("detail");
    const source = card.locator('[data-select-entity="select.testroom_close_werktag_time_source_summer"]');
    assert.equal(await source.evaluate((el) => [...el.closest("tr").querySelectorAll('input[type="time"]')].at(-1).value), "22:45");
    await source.selectOption("local");
    await card.locator('[data-time-entity="time.testroom_close_werktag_summer"]').fill("21:15");
    await card.locator('[data-time-entity="time.testroom_close_werktag_summer"]').dispatchEvent("change");
    await card.locator("[data-season-edit]").selectOption("winter");
    assert.equal(await card.locator('[data-select-entity="select.testroom_close_werktag_time_source_winter"]').inputValue(), "global");
    console.log("OK   - individual seasonal times and global inheritance are independent");
    await page.setViewportSize({ width: 390, height: 844 });
    const mobile = await card.locator(".profile-times").evaluate((el) => {
      const close = el.querySelector('tr:nth-child(2) td:last-child input');
      const bounds = close.getBoundingClientRect();
      const container = el.getBoundingClientRect();
      return { width: el.clientWidth, scroll: el.scrollWidth, fits: bounds.left >= container.left && bounds.right <= container.right };
    });
    assert.equal(mobile.scroll, mobile.width, "individual seasonal times must fit a mobile card");
    assert.equal(mobile.fits, true, "the Close input must stay reachable on mobile");
    await page.setViewportSize({ width: 1280, height: 900 });
    console.log("OK   - mobile individual profile times keep Close controls reachable");

    await view("detail", "advanced");
    await card.locator("[data-advanced-mode-select]").selectOption("local");
    await card.locator('[data-select-entity="select.testroom_close_type_winter"]').selectOption("sunset");
    assert.equal(await page.evaluate(() => window.__calls.at(-1).data.entity_id), "select.testroom_close_type_winter");
    await card.locator("[data-season-edit]").selectOption("summer");
    assert.equal(await page.evaluate(() => window.__states["select.testroom_close_type_summer"].state), "sunset");
    console.log("OK   - seasonal trigger type edits use the selected native entity");

    await card.locator("[data-season-edit]").selectOption("winter");
    await page.evaluate(() => {
      document.getElementById("card")._globalForecast = { stale: true };
      window.__states["sensor.testroom_next_action"].attributes.active_season = "summer";
      document.getElementById("card").hass = window.__hass;
    });
    assert.match(await card.locator("[data-season-status]").innerText(), /Sommerzeit/);
    assert.equal(await card.locator("[data-season-edit]").inputValue(), "winter");
    assert.equal(await page.evaluate(() => document.getElementById("card")._globalForecast), undefined);
    console.log("OK   - active season refresh preserves the editor selection");

    await view("settings-basic");
    await card.locator('[data-basic-field="seasonal_enabled"]').uncheck();
    await card.locator("[data-save-basic]").click();
    await page.waitForFunction(() => window.__seasonEnabled === false);
    const saved = await page.evaluate(() => window.__calls.findLast((call) => call.type === "smart_shutter/save_basic_settings"));
    assert.equal(saved.seasonal_enabled, false);
    await view("settings-global");
    assert.equal(await card.locator("[data-season-edit]").count(), 0);
    assert.equal(await card.locator('[data-time-entity="time.global_close_werktag"]').count(), 1);

    await page.clock.setFixedTime(new Date("2026-10-25T00:00:00+02:00"));
    const buckets = await page.evaluate(() => {
      const card = document.getElementById("card");
      card._globalForecast = { "cover.testroom": [
        { action: "close", ts: "2026-10-25T23:30:00+01:00" },
        { action: "open", ts: "2026-10-26T00:30:00+01:00" },
      ] };
      const template = document.createElement("template");
      template.innerHTML = card._renderGlobalTimeline();
      return [...template.content.querySelectorAll(".native-timeline-day")].slice(0, 2)
        .map((day) => [...day.querySelectorAll(".tl-marker")].map((marker) => marker.title));
    });
    assert.equal(buckets[0].length, 1);
    assert.match(buckets[0][0], /23:30/);
    assert.equal(buckets[1].length, 1);
    assert.match(buckets[1][0], /00:30/);
    console.log("OK   - 25-hour transition days keep timeline events on the correct local day");
    assert.deepEqual(errors, []);
    assert.equal(await page.evaluate(() => window.__calls.some((call) => call.domain === "cover")), false);
    console.log("OK   - disabling restores the existing editor; no cover service calls or browser errors");
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
