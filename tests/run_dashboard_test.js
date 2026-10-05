const assert = require("node:assert/strict");
const path = require("node:path");
const { chromium } = require("playwright");
const { buildFixture } = require("./fixtures");

async function main() {
  const browser = await chromium.launch();
  let failures = 0;
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto("file://" + path.join(__dirname, "test.html"));
    const fixture = buildFixture();
    fixture.devices.find((device) => device.id === "dev_testroom").name_by_user = "Küche umbenannt";
    fixture.devices.find((device) => device.id === "dev_testroom2").name_by_user = "Büro umbenannt";
    fixture.states["switch.global_automation_open"].state = "off";
    fixture.states["switch.global_automation_close"].state = "off";
    fixture.states["switch.testroom_automation_open"].state = "off";
    await page.evaluate((fx) => {
      const hass = {
        states: fx.states,
        language: "de",
        user: { is_admin: true },
        connection: {
          subscribeEvents: async (callback, type) => {
            if (type === "device_registry_updated") {
              window.__deviceRegistryUpdated = callback;
              window.__registrySubscriptions = (window.__registrySubscriptions || 0) + 1;
            }
            return () => { window.__deviceRegistryUpdated = null; };
          },
        },
        callWS: async ({ type }) => {
          if (type === "config/entity_registry/list") return fx.entities;
          if (type === "config/device_registry/list") return fx.devices;
          if (type === "config/area_registry/list") return fx.areas;
          if (type === "config/floor_registry/list") return fx.floors;
          if (type === "config/auth/list") return [];
          if (type === "smart_shutter/get_config") return {
            covers: [
              { entity_id: fx.coverEntityId, name: "Küche umbenannt" },
              { entity_id: fx.coverEntityId2, name: "Büro umbenannt" },
            ],
            custom_areas: [],
            onboarding_completed: true,
          };
          if (type === "smart_shutter/get_forecast") return { forecast: {} };
          return {};
        },
        callService: async () => {},
      };
      window.__hass = hass;
      window.__devices = fx.devices;
      const card = document.getElementById("card");
      card.setConfig({});
      card.hass = hass;
    }, fixture);
    await page.waitForSelector("smart-shutter-card >> [data-overview-stats] .ssm-stat-num");

    async function check(name, run) {
      try {
        await run();
        console.log(`OK   - ${name}`);
      } catch (error) {
        failures++;
        console.error(`FAIL - ${name}: ${error.message}`);
      }
    }

    await check("Global automation off counts every shutter and says fully off", async () => {
      const stat = page.locator("smart-shutter-card >> .ssm-stat").nth(1);
      assert.equal(await stat.locator(".ssm-stat-num").textContent(), "2");
      assert.equal(await stat.locator(".ssm-stat-label").textContent(), "Automatik aus");
    });
    await check("User-defined managed device names appear in the shutter list", async () => {
      await page.locator('smart-shutter-card >> [data-nav="list"]').first().click();
      assert.deepEqual(
        (await page.locator("smart-shutter-card >> .name").allTextContents()).sort(),
        ["Büro umbenannt", "Küche umbenannt"]
      );
    });
    await check("Renaming a managed device updates the open list without reloading", async () => {
      const input = page.locator('smart-shutter-card >> input[type="search"]');
      await input.fill("Küche");
      await page.evaluate(() => {
        window.__devices.find((device) => device.id === "dev_testroom").name_by_user = 'Küche <Süd> "Fenster" & Tür';
        if (window.__deviceRegistryUpdated) window.__deviceRegistryUpdated({ data: { action: "update", device_id: "dev_testroom" } });
      });
      await page.waitForTimeout(100);
      assert.ok((await page.locator("smart-shutter-card >> .name").allTextContents()).includes('Küche <Süd> "Fenster" & Tür'));
      assert.equal(await input.inputValue(), "Küche");
      assert.equal(await input.evaluate((element) => element.getRootNode().activeElement === element), true);
      await input.fill("");
    });
    await check("The detail title follows device renames and clearing the user name", async () => {
      await page.locator('smart-shutter-card >> [data-open-detail="dev_testroom"]').click();
      await page.evaluate(() => {
        window.__devices.find((device) => device.id === "dev_testroom").name_by_user = null;
        window.__deviceRegistryUpdated({ data: { action: "update", device_id: "dev_testroom" } });
      });
      await page.waitForFunction(() => document.getElementById("card").shadowRoot
        .querySelector('[data-shutter-name="dev_testroom"]').textContent === "Testrollladen");
      assert.equal(await page.locator('smart-shutter-card >> [data-shutter-name="dev_testroom"]').textContent(), "Testrollladen");
    });

    await page.locator('smart-shutter-card >> [data-nav="overview"]').first().click();
    async function setSwitches(values) {
      await page.evaluate((updates) => {
        for (const [id, state] of Object.entries(updates)) {
          window.__hass.states[id] = { ...window.__hass.states[id], state };
        }
        document.getElementById("card").hass = window.__hass;
      }, values);
    }
    async function assertStat(count, label) {
      const stat = page.locator("smart-shutter-card >> .ssm-stat").nth(1);
      assert.equal(await stat.locator(".ssm-stat-num").textContent(), String(count));
      assert.equal(await stat.locator(".ssm-stat-label").textContent(), label);
    }
    await check("One globally disabled direction is partially off for every shutter", async () => {
      await setSwitches({ "switch.global_automation_open": "on" });
      await assertStat(2, "Automatik teilweise aus");
    });
    await check("Global re-enable preserves individual disabled switches", async () => {
      await setSwitches({ "switch.global_automation_close": "on" });
      await assertStat(1, "Automatik teilweise aus");
    });
    await check("All enabled is displayed correctly on a background state update", async () => {
      await setSwitches({ "switch.testroom_automation_open": "on" });
      await assertStat(0, "Automatik an");
    });
    await check("All individual directions off also displays fully off in English", async () => {
      await setSwitches({
        "switch.testroom_automation_open": "off", "switch.testroom_automation_close": "off",
        "switch.testroom2_automation_open": "off", "switch.testroom2_automation_close": "off",
      });
      await page.evaluate(() => {
        window.__hass.language = "en";
        document.getElementById("card").hass = window.__hass;
      });
      await assertStat(2, "Automation disabled");
    });
    await check("State updates keep one registry subscription, removed cards unsubscribe", async () => {
      assert.equal(await page.evaluate(() => window.__registrySubscriptions), 1);
      await page.evaluate(() => document.getElementById("card").remove());
      assert.equal(await page.evaluate(() => window.__deviceRegistryUpdated), null);
    });
    assert.deepEqual(errors, [], "Card must not produce browser errors");

    const onboardingPage = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const onboardingErrors = [];
    onboardingPage.on("pageerror", (error) => onboardingErrors.push(error.message));
    await onboardingPage.goto("file://" + path.join(__dirname, "test.html"));
    const onboardingFixture = buildFixture();
    onboardingFixture.states["switch.global_automation_open"].state = "off";
    onboardingFixture.states["switch.global_automation_close"].state = "off";
    await onboardingPage.evaluate((fx) => {
      window.__onboardingServiceCalls = [];
      window.__onboardingWsCalls = [];
      window.__onboardingSavedAreas = null;
      window.__onboardingSavedShutterAreas = null;
      window.__onboardingForecastFails = true;
      window.__onboardingServiceFailure = false;
      window.__onboardingAreaSaveFailure = false;
      const hass = {
        states: fx.states,
        language: "de",
        user: { is_admin: true },
        connection: { subscribeEvents: async () => () => {} },
        callWS: async (msg) => {
          const { type, include_disabled } = msg;
          window.__onboardingWsCalls.push(msg);
          if (type === "config/entity_registry/list") return fx.entities;
          if (type === "config/device_registry/list") return fx.devices;
          if (type === "config/area_registry/list") return fx.areas;
          if (type === "config/floor_registry/list") return fx.floors;
          if (type === "config/auth/list") return [];
          if (type === "smart_shutter/get_config") return {
            entry_id: "entry-onboarding",
            covers: [
              { entity_id: fx.coverEntityId, name: "Küche" },
              { entity_id: fx.coverEntityId2, name: "Büro" },
            ],
            custom_areas: [],
            shutter_areas: {},
            basic_settings: { holiday_entity: null },
            onboarding_completed: false,
          };
          if (type === "smart_shutter/get_forecast") {
            if (include_disabled) {
              window.__onboardingIncludedDisabled = true;
              if (window.__onboardingForecastFails) throw new Error("Preview unavailable");
            }
            return {
              forecast: {
                [fx.coverEntityId]: [{ ts: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(), action: "close" }],
              },
            };
          }
          if (type === "smart_shutter/complete_onboarding") return { success: true };
          if (type === "smart_shutter/save_basic_settings") return { success: true };
          if (type === "smart_shutter/save_custom_areas") {
            if (window.__onboardingAreaSaveFailure) return { success: false, message: "Simulated area save failure" };
            window.__onboardingSavedAreas = msg.areas;
            return { success: true };
          }
          if (type === "smart_shutter/save_shutter_areas") {
            window.__onboardingSavedShutterAreas = msg.shutter_areas;
            return { success: true };
          }
          return {};
        },
        callService: async (domain, service, data) => {
          window.__onboardingServiceCalls.push({ domain, service, data });
          if (window.__onboardingServiceFailure) throw new Error("Simulated schedule save failure");
        },
      };
      const card = document.getElementById("card");
      card.setConfig({});
      card.hass = hass;
    }, onboardingFixture);
    await onboardingPage.waitForSelector("smart-shutter-card [data-onboarding]");
    await onboardingPage.locator("smart-shutter-card [data-onboarding-next]").waitFor();
    assert.equal(await onboardingPage.locator("smart-shutter-card [role=progressbar]").getAttribute("aria-valuenow"), "0");
    assert.equal(await onboardingPage.locator("smart-shutter-card [role=progressbar]").getAttribute("aria-valuemax"), "3");
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-field][data-time-entity]").count(), 6);
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-field][data-select-entity]").count(), 2);
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-settings]").count(), 0);
    assert.equal(await onboardingPage.locator('smart-shutter-card input[type="number"][data-number-entity="number.global_open_position"]').inputValue(), "100",
      "A fresh onboarding fixture starts with the fully open target position");
    const saveStatus = onboardingPage.locator("smart-shutter-card [data-onboarding-save-status]");
    assert.equal(await saveStatus.getAttribute("role"), "status");
    assert.equal(await saveStatus.getAttribute("aria-live"), "polite");
    const desktopProfileLayout = await onboardingPage.locator("smart-shutter-card .onboarding-profile-grid").evaluate((element) => ({
      columns: getComputedStyle(element).gridTemplateColumns.trim().split(/\s+/).length,
      timeWidths: [...element.querySelectorAll('input[type="time"]')].map((input) => input.getBoundingClientRect().width),
    }));
    assert.equal(desktopProfileLayout.columns, 2, "Desktop day-type cards use two readable columns");
    assert.ok(Math.min(...desktopProfileLayout.timeWidths) >= 120, "Desktop time inputs have room for localized values");
    const openTime = onboardingPage.locator("smart-shutter-card [data-onboarding-field][data-time-entity]").first();
    await openTime.fill("07:15");
    await onboardingPage.waitForFunction(() => document.getElementById("card").shadowRoot
      .querySelector("[data-onboarding-save-status]")?.textContent === "Änderung gespeichert.");
    assert.ok((await onboardingPage.evaluate(() => window.__onboardingServiceCalls))
      .some((call) => call.domain === "time" && call.service === "set_value" && call.data.time === "07:15"));
    await onboardingPage.evaluate(() => { window.__onboardingServiceFailure = true; });
    await openTime.fill("07:20");
    await onboardingPage.waitForFunction(() => {
      const root = document.getElementById("card").shadowRoot;
      const status = root.querySelector("[data-onboarding-save-status]");
      return status?.getAttribute("role") === "alert" && status.textContent.includes("Simulated schedule save failure");
    });
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-next]").isDisabled(), true);
    await onboardingPage.locator('smart-shutter-card [data-nav="overview"]').click();
    await onboardingPage.locator('smart-shutter-card [data-nav="settings"]').click();
    await onboardingPage.locator('smart-shutter-card [data-settings-nav="onboarding"]').click();
    await onboardingPage.waitForFunction(() => {
      const root = document.getElementById("card").shadowRoot;
      const status = root.querySelector("[data-onboarding-save-status]");
      return status?.getAttribute("role") === "alert" && status.textContent.includes("Simulated schedule save failure");
    });
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-next]").isDisabled(), true,
      "A failed schedule save remains visible and blocks progress after leaving and reopening onboarding");
    await onboardingPage.evaluate(() => { window.__onboardingServiceFailure = false; });
    await openTime.fill("07:25");
    await onboardingPage.waitForFunction(() => {
      const root = document.getElementById("card").shadowRoot;
      const status = root.querySelector("[data-onboarding-save-status]");
      return status?.getAttribute("role") === "status" && status.textContent === "Änderung gespeichert.";
    });
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-next]").isDisabled(), false);
    const openMode = onboardingPage.locator('smart-shutter-card [data-onboarding-field][data-select-entity="select.global_open_type"]');
    await openMode.selectOption("sunrise");
    await onboardingPage.waitForFunction(() => document.getElementById("card").shadowRoot
      .querySelector("[data-onboarding-save-status]")?.textContent === "Änderung gespeichert.");
    assert.equal(await onboardingPage.locator('smart-shutter-card [data-time-entity="time.global_open_werktag"]').isDisabled(), true);
    assert.equal(await onboardingPage.locator('smart-shutter-card [data-number-entity="number.global_open_sun_offset"]').count(), 2);
    const openTrigger = onboardingPage.locator('smart-shutter-card [data-onboarding-trigger="open"]');
    assert.equal(await openTrigger.locator('[data-onboarding-offset-for="open"] input[data-number-entity="number.global_open_sun_offset"]').count(), 2,
      "The sunrise offset stays grouped below its trigger selector");
    const openSunOffset = onboardingPage.locator('smart-shutter-card input[type="number"][data-number-entity="number.global_open_sun_offset"]');
    await openSunOffset.fill("12");
    await openSunOffset.blur();
    await onboardingPage.waitForFunction(() => {
      const root = document.getElementById("card").shadowRoot;
      return root.querySelector("[data-onboarding-save-status]")?.textContent === "Änderung gespeichert."
        && window.__onboardingServiceCalls.some((call) => call.domain === "number" && call.service === "set_value"
          && call.data.entity_id === "number.global_open_sun_offset" && call.data.value === 12);
    });
    await onboardingPage.locator('smart-shutter-card [data-select-entity="select.global_open_type"]').selectOption("time");
    await onboardingPage.waitForFunction(() => document.getElementById("card").shadowRoot
      .querySelector("[data-onboarding-save-status]")?.textContent === "Änderung gespeichert.");
    const closeMode = onboardingPage.locator('smart-shutter-card [data-onboarding-field][data-select-entity="select.global_close_type"]');
    await closeMode.selectOption("sunset");
    await onboardingPage.waitForFunction(() => document.getElementById("card").shadowRoot
      .querySelector("[data-onboarding-save-status]")?.textContent === "Änderung gespeichert.");
    const closeTrigger = onboardingPage.locator('smart-shutter-card [data-onboarding-trigger="close"]');
    assert.equal(await closeTrigger.locator('[data-onboarding-offset-for="close"] input[data-number-entity="number.global_close_sun_offset"]').count(), 2,
      "The sunset offset stays grouped below its trigger selector");
    assert.ok((await closeTrigger.innerText()).includes("Versatz ab Sonnenuntergang"));
    await closeMode.selectOption("time");
    await onboardingPage.waitForFunction(() => document.getElementById("card").shadowRoot
      .querySelector("[data-onboarding-save-status]")?.textContent === "Änderung gespeichert.");
    await onboardingPage.locator("smart-shutter-card [data-onboarding-next]").click();
    assert.equal(await onboardingPage.locator("smart-shutter-card [role=progressbar]").getAttribute("aria-valuenow"), "1");
    await onboardingPage.locator("smart-shutter-card [data-onboarding-new-area]").click();
    await onboardingPage.locator("smart-shutter-card [data-onboarding-new-area-name]").fill("Erdgeschoss");
    await onboardingPage.locator("smart-shutter-card [data-onboarding-new-area-member]").first().check();
    await onboardingPage.locator("smart-shutter-card [data-entity-picker=onboarding_holiday] input").fill("binary_sensor.school_holidays");
    await onboardingPage.evaluate(() => { window.__onboardingAreaSaveFailure = true; });
    await onboardingPage.locator("smart-shutter-card [data-onboarding-save-areas]").click();
    await onboardingPage.waitForFunction(() => {
      const error = document.getElementById("card").shadowRoot.querySelector("[data-onboarding-area-error]");
      return error && !error.hidden && error.textContent.includes("Simulated area save failure");
    });
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-preview-view]").count(), 0);
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-save-areas]").isDisabled(), false);
    await onboardingPage.evaluate(() => { window.__onboardingAreaSaveFailure = false; });
    await onboardingPage.locator("smart-shutter-card [data-onboarding-save-areas]").click();
    await onboardingPage.waitForSelector("smart-shutter-card [data-onboarding-preview-view]");
    const onboardingWsCalls = await onboardingPage.evaluate(() => window.__onboardingWsCalls);
    assert.ok(onboardingWsCalls.some((call) => call.type === "smart_shutter/save_basic_settings" && call.holiday_entity === "binary_sensor.school_holidays"));
    const savedAreas = await onboardingPage.evaluate(() => window.__onboardingSavedAreas);
    assert.equal(savedAreas[0].name, "Erdgeschoss");
    const savedShutterAreas = await onboardingPage.evaluate(() => window.__onboardingSavedShutterAreas);
    assert.ok(Object.values(savedShutterAreas).some((ids) => ids.includes(savedAreas[0].id)));
    await onboardingPage.waitForSelector("smart-shutter-card [data-onboarding-preview-error]");
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-preview-reviewed]").isDisabled(), true);
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-preview-error]").isVisible(), true);
    assert.equal(await onboardingPage.locator("smart-shutter-card .ssm-timeline-card").innerText().then((text) => text.includes("Keine Aktionen")), false);
    await onboardingPage.evaluate(() => { window.__onboardingForecastFails = false; });
    await onboardingPage.locator("smart-shutter-card [data-onboarding-preview-retry]").click();
    await onboardingPage.waitForSelector("smart-shutter-card .tl-marker");
    assert.equal(await onboardingPage.locator("smart-shutter-card .tl-marker").count(), 1);
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-preview-reviewed]").isEnabled(), true);
    assert.equal(await onboardingPage.evaluate(() => window.__onboardingIncludedDisabled), true);
    await onboardingPage.locator("smart-shutter-card [data-onboarding-preview-reviewed]").click();
    assert.equal(await onboardingPage.locator("smart-shutter-card [role=progressbar]").getAttribute("aria-valuenow"), "2");
    await onboardingPage.locator('smart-shutter-card [data-onboarding-enable="open"]').check();
    await onboardingPage.locator("smart-shutter-card [data-onboarding-finish]").click();
    await onboardingPage.waitForSelector("smart-shutter-card [data-overview-stats]");
    const onboardingCalls = await onboardingPage.evaluate(() => window.__onboardingServiceCalls.filter((call) => call.domain === "switch"));
    assert.deepEqual(onboardingCalls, [
      { domain: "switch", service: "turn_on", data: { entity_id: "switch.global_automation_open" } },
      { domain: "switch", service: "turn_off", data: { entity_id: "switch.global_automation_close" } },
    ]);
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-settings-nav=onboarding]").count(), 0);
    await onboardingPage.locator('smart-shutter-card [data-nav="settings"]').click();
    await onboardingPage.locator('smart-shutter-card [data-settings-nav="onboarding"]').click();
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-completed]").count(), 1);
    await onboardingPage.setViewportSize({ width: 390, height: 844 });
    const onboardingBounds = await onboardingPage.locator("smart-shutter-card [data-onboarding]").evaluate((element) => ({
      width: element.getBoundingClientRect().width,
      scrollWidth: element.scrollWidth,
    }));
    assert.ok(onboardingBounds.width <= 390, "Onboarding should fit a mobile viewport");
    assert.ok(onboardingBounds.scrollWidth <= onboardingBounds.width, "Onboarding should not create horizontal overflow");
    await onboardingPage.evaluate(() => {
      const nativeScrollIntoView = Element.prototype.scrollIntoView;
      window.__onboardingDashboardScroll = false;
      Element.prototype.scrollIntoView = function (options) {
        if (this.matches?.("[data-global-timeline]")) window.__onboardingDashboardScroll = options?.block === "start";
        return nativeScrollIntoView && nativeScrollIntoView.call(this, options);
      };
    });
    await onboardingPage.locator("smart-shutter-card [data-onboarding-preview]").click();
    await onboardingPage.waitForSelector("smart-shutter-card [data-global-timeline]");
    await onboardingPage.waitForFunction(() => window.__onboardingDashboardScroll === true);
    assert.equal(await onboardingPage.locator('smart-shutter-card [data-nav="overview"]').getAttribute("class").then((value) => value.includes("active")), true,
      "The completed setup returns to the dashboard");
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding]").count(), 0,
      "The completed setup preview is no longer inside the wizard");
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-onboarding-preview-view]").count(), 0);
    assert.equal(await onboardingPage.locator("smart-shutter-card [data-global-timeline]").count(), 1,
      "The dashboard's seven-day preview is visible after returning from completed setup");
    assert.deepEqual(onboardingErrors, [], "Onboarding must not produce browser errors");
  } finally {
    await browser.close();
  }
  if (failures) process.exitCode = 1;
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
