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
    await check("Restricted users get a short inline prompt and the full automation explanation behind info", async () => {
      await page.evaluate(() => {
        const card = document.getElementById("card");
        card._restricted = true;
        card._view = "overview";
        card._render();
      });
      const hint = page.locator("smart-shutter-card >> .ssm-inline-hint");
      assert.equal(await hint.locator(":scope > .ssm-inline-hint-label").textContent(), "Use your area's automation switches.");
      const infoButton = hint.locator("[data-info-toggle]");
      const popover = hint.locator('[role="tooltip"]');
      assert.equal(await infoButton.getAttribute("aria-label"), "More information");
      assert.equal(await popover.isHidden(), true);
      await infoButton.click();
      assert.match(await popover.textContent(), /global automation control affects ALL shutters/);
      await page.evaluate(() => {
        const card = document.getElementById("card");
        card._restricted = false;
        card._render();
      });
    });
    await check("State updates keep one registry subscription, removed cards unsubscribe", async () => {
      assert.equal(await page.evaluate(() => window.__registrySubscriptions), 1);
      await page.evaluate(() => document.getElementById("card").remove());
      assert.equal(await page.evaluate(() => window.__deviceRegistryUpdated), null);
    });
    assert.deepEqual(errors, [], "Card must not produce browser errors");
  } finally {
    await browser.close();
  }
  if (failures) process.exitCode = 1;
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
