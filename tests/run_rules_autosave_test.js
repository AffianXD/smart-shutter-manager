const assert = require("node:assert/strict");
const path = require("node:path");
const { chromium } = require("playwright");
const { buildFixture } = require("./fixtures");

async function main() {
  const browser = await chromium.launch();
  try {
    for (const width of [1280, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 844 } });
      const errors = [];
      let dialogs = 0;
      let acceptDialog = true;
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("dialog", (dialog) => { dialogs += 1; acceptDialog ? dialog.accept() : dialog.dismiss(); });
      await page.goto(`file://${path.join(__dirname, "test.html")}`);
      await page.evaluate((fx) => {
        window.__calls = [];
        window.__fail = null;
        window.__conflict = false;
        window.__serviceCalls = [];
        window.__config = {
          entry_id: "rules-test", onboarding_completed: true,
          covers: [{ entity_id: fx.coverEntityId, name: "Fixture" }],
          custom_areas: [{ id: "fixture-area", name: "Fixture area" }],
          temporal_exceptions: [{ id: "exception-one", start_date: "2026-10-12", end_date: "2026-10-13", mode: "pause", actions: ["open"], cover_ids: [fx.coverEntityId], area_ids: [] }],
          custom_schedules: [{ id: "custom-one", name: "Weekday", weekdays: [0], interval_weeks: 1, reference_date: "2026-10-12", open_time: "08:00" }],
          external_triggers: [{ id: "trigger-one", name: "Outside", entity_id: fx.coverEntityId, area_id: null, action: "close" }],
          shortcuts: [{ id: "shortcut-one", name: "Open", icon: "mdi:window-shutter", kind: "navigate", view: "overview" }],
          schedule_conflicts: {},
        };
        const hass = {
          states: fx.states, language: "en", user: { is_admin: true },
          connection: { subscribeEvents: async () => () => {} },
          callService: async (...args) => window.__serviceCalls.push(args),
          callWS: async (msg) => {
            if (msg.type === "config/entity_registry/list") return fx.entities;
            if (msg.type === "config/device_registry/list") return fx.devices;
            if (msg.type === "config/area_registry/list") return fx.areas;
            if (msg.type === "config/floor_registry/list") return fx.floors;
            if (msg.type === "config/auth/list") return [];
            if (msg.type === "smart_shutter/get_config") return structuredClone(window.__config);
            if (msg.type === "smart_shutter/get_forecast") return { forecast: {} };
            if (msg.type.startsWith("smart_shutter/save_")) {
              window.__calls.push(structuredClone(msg));
              if (window.__fail === msg.type) return { success: false, validation_error: "invalid" };
              if (window.__conflict && msg.type === "smart_shutter/save_custom_schedules" && !msg.force) return {
                success: false, conflicts: [{ rule_id: "custom-one", overlapping_with: [{ id: "custom-peer", name: "Peer" }] }],
              };
              if (msg.type === "smart_shutter/save_temporal_exception") {
                const rule = { ...msg.exception, id: msg.exception.id || "exception-new" };
                const index = window.__config.temporal_exceptions.findIndex((item) => item.id === rule.id);
                if (index >= 0) window.__config.temporal_exceptions[index] = rule;
                else window.__config.temporal_exceptions.push(rule);
                return { success: true, exception: rule };
              }
              const key = {
                "smart_shutter/save_custom_schedules": "custom_schedules",
                "smart_shutter/save_external_triggers": "external_triggers",
                "smart_shutter/save_shortcuts": "shortcuts",
              }[msg.type];
              if (key) window.__config[key] = structuredClone(msg[key === "custom_schedules" ? "schedules" : key === "external_triggers" ? "triggers" : "shortcuts"]);
              return { success: true };
            }
            return {};
          },
        };
        const card = document.getElementById("card");
        card.setConfig({});
        card.hass = hass;
      }, buildFixture());
      await page.locator("smart-shutter-card [data-overview-stats]").waitFor();
      const card = page.locator("smart-shutter-card");
      const edit = async (view, idProperty, id) => page.evaluate(([nextView, property, value]) => {
        const element = document.getElementById("card");
        element[property] = value;
        element._ruleDraftId = null;
        element._ruleDraftSignature = null;
        element._ruleEditorGeneration += 1;
        element._view = nextView;
        element._render();
      }, [view, idProperty, id]);
      const count = (type) => page.evaluate((target) => window.__calls.filter((item) => item.type === target).length, type);
      const waitCount = async (type, n) => page.waitForFunction(([target, expected]) => window.__calls.filter((item) => item.type === target).length >= expected, [type, n]);

      await edit("settings-exception-edit", "_editingExceptionId", "exception-one");
      await card.locator('[data-exception-field="end_date"]').fill("2026-10-14");
      await waitCount("smart_shutter/save_temporal_exception", 1);
      assert.equal(await card.locator('[data-exception-field="end_date"]').inputValue(), "2026-10-14");
      assert.match(await card.locator("[data-exception-status-message]").textContent(), /Saved/);

      await edit("settings-schedule-edit", "_editingScheduleId", null);
      await page.evaluate(() => {
        Object.defineProperty(window.crypto, "randomUUID", { configurable: true, value: undefined });
      });
      await card.locator('[data-schedule-field="name"]').fill("New profile");
      await page.waitForTimeout(850);
      assert.equal(await count("smart_shutter/save_custom_schedules"), 0, "Incomplete new profile stays a draft");
      await card.locator('[data-schedule-weekday="0"]').locator("..").click();
      await card.locator('[data-schedule-field="open_time"]').fill("09:00");
      await waitCount("smart_shutter/save_custom_schedules", 1);
      const savedSchedules = await page.evaluate(() => window.__config.custom_schedules);
      assert.deepEqual(savedSchedules.map((item) => item.name), ["Weekday", "New profile"], "Existing priority order stays intact");
      assert.match(savedSchedules[1].id, /^custom_[0-9a-f]{12}$/,
        "New schedule IDs use Web Crypto randomness when randomUUID is unavailable");

      await edit("settings-schedule-edit", "_editingScheduleId", "custom-one");
      await page.evaluate(() => { window.__conflict = true; });
      await card.locator('[data-schedule-field="name"]').fill("Weekday changed");
      await card.locator("[data-rule-retry]").waitFor({ state: "visible" });
      assert.equal(await page.evaluate(() => window.__config.custom_schedules[0].name), "Weekday", "New conflicts are not silently forced");
      assert.equal(await page.evaluate(() => document.getElementById("card")._ruleConflict), true);
      await card.locator("[data-rule-retry]").click();
      await page.waitForFunction(() => window.__config.custom_schedules[0].name === "Weekday changed");
      assert.deepEqual((await page.evaluate(() => window.__config.custom_schedules)).map((item) => item.name),
        ["Weekday changed", "New profile"], "Confirmed conflict keeps priority order");
      await page.evaluate(() => { window.__conflict = false; });

      await page.evaluate(() => {
        const element = document.getElementById("card");
        element._editReturnAreaId = "fixture-area";
        element._backendConfig.custom_schedules.push({
          id: "area-profile", area_id: "fixture-area", name: "Area profile", weekdays: [1],
          interval_weeks: 1, reference_date: "2026-10-12", close_time: "19:00",
        });
      });
      await edit("settings-schedule-edit", "_editingScheduleId", "area-profile");
      const areaSaveCount = await page.evaluate(() => window.__calls.length);
      await card.locator('[data-schedule-field="name"]').fill("Area profile changed");
      await page.waitForTimeout(850);
      assert.equal(await page.evaluate(() => window.__calls.length), areaSaveCount,
        "Area-scoped schedule editors do not autosave");

      await edit("settings-trigger-edit", "_editingTriggerId", "trigger-one");
      await page.evaluate(() => { window.__fail = "smart_shutter/save_external_triggers"; });
      await card.locator('[data-trigger-field="name"]').fill("Outside changed");
      await waitCount("smart_shutter/save_external_triggers", 1);
      await card.locator("[data-rule-retry]").waitFor({ state: "visible" });
      assert.equal(await card.locator('[data-trigger-field="name"]').inputValue(), "Outside changed");
      await page.evaluate(() => { window.__fail = null; });
      await card.locator("[data-rule-retry]").click();
      await waitCount("smart_shutter/save_external_triggers", 2);
      assert.equal(await page.evaluate(() => window.__config.external_triggers[0].name), "Outside changed");

      await edit("settings-shortcut-edit", "_editingShortcutId", null);
      assert.equal(await card.locator("[data-shortcut-save]").count(), 0, "Shortcut editor uses autosave without a manual save button");
      await card.locator('[data-shortcut-field="name"]').fill("New shortcut");
      await waitCount("smart_shutter/save_shortcuts", 1);
      assert.equal(await page.evaluate(() => window.__config.shortcuts[1].name), "New shortcut");
      assert.equal(await card.locator('[data-shortcut-field="name"]').inputValue(), "New shortcut");
      await page.evaluate(() => { window.__fail = "smart_shutter/save_shortcuts"; });
      await card.locator('[data-shortcut-field="name"]').fill("Shortcut retry");
      await card.locator("[data-rule-retry]").waitFor({ state: "visible" });
      assert.equal(await card.locator('[data-shortcut-field="name"]').inputValue(), "Shortcut retry",
        "Failed shortcut autosave keeps the draft");
      assert.equal(await page.evaluate(() => window.__config.shortcuts[1].name), "New shortcut",
        "Failed shortcut autosave does not overwrite the stored value");
      await page.evaluate(() => { window.__fail = null; });
      await card.locator("[data-rule-retry]").click();
      await waitCount("smart_shutter/save_shortcuts", 3);
      assert.equal(await page.evaluate(() => window.__config.shortcuts[1].name), "Shortcut retry",
        "Retry saves the retained shortcut draft");
      await card.locator('[data-shortcut-field="name"]').fill("Shortcut changed on back");
      await card.locator("[data-shortcut-back]").click();
      assert.equal(await page.evaluate(() => window.__config.shortcuts[1].name), "Shortcut changed on back",
        "Leaving the editor flushes a pending valid draft");
      acceptDialog = false;
      await card.locator('[data-shortcut-delete="shortcut-one"]').click();
      assert.equal(await count("smart_shutter/save_shortcuts"), 4, "Cancelling shortcut deletion keeps it stored");
      acceptDialog = true;
      await card.locator('[data-shortcut-delete="shortcut-one"]').click();
      await waitCount("smart_shutter/save_shortcuts", 5);
      assert.equal(await page.evaluate(() => window.__config.shortcuts.some((item) => item.id === "shortcut-one")), false);
      assert.deepEqual(await page.evaluate(() => window.__serviceCalls), [], "Editors never move covers");
      assert.equal(dialogs, 3, "Profile conflicts and shortcut deletion ask for confirmation");
      assert.deepEqual(errors, [], "No browser errors");
      await page.close();
      console.log(`OK - rule autosave at ${width}px`);
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
