const assert = require("node:assert/strict");
const path = require("node:path");
const { chromium } = require("playwright");
const { buildFixture } = require("./fixtures");

async function main() {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    let acceptRemoval = false;
    page.on("dialog", async (dialog) => acceptRemoval ? dialog.accept() : dialog.dismiss());
    await page.goto("file://" + path.join(__dirname, "test.html"));
    await page.evaluate((fx) => {
      const third = "cover.newroom";
      const thirdDevice = JSON.parse(JSON.stringify(fx.devices.find((d) => d.id === "dev_testroom2")).replaceAll("testroom2", "newroom"));
      thirdDevice.name = 'New <South> & "Window"';
      const thirdEntities = fx.entities.filter((e) => e.device_id === "dev_testroom2").map((e) => JSON.parse(JSON.stringify(e).replaceAll("testroom2", "newroom")));
      const selected = [fx.coverEntityId, fx.coverEntityId2, "cover.missing"];
      window.__saved = [];
      window.__services = [];
      window.__rejectSave = false;
      window.__reloadReads = 0;
      const devices = [...fx.devices, thirdDevice];
      const entities = [...fx.entities, ...thirdEntities];
      const byCover = new Map([[fx.coverEntityId, "dev_testroom"], [fx.coverEntityId2, "dev_testroom2"], [third, "dev_newroom"]]);
      for (const id of Object.keys(fx.states).filter((id) => id.includes("testroom2"))) {
        const newId = id.replaceAll("testroom2", "newroom");
        fx.states[newId] = { ...fx.states[id], entity_id: newId };
      }
      window.__selected = selected;
      window.__registrySelected = [fx.coverEntityId, fx.coverEntityId2];
      window.__failAvailable = false;
      window.__hass = {
        states: fx.states, language: "de", user: { is_admin: true },
        callService: async (...args) => { window.__services.push(args); throw new Error("Unexpected cover service"); },
        callWS: async (msg) => {
          const ids = new Set(window.__registrySelected.map((id) => byCover.get(id)));
          if (msg.type === "config/entity_registry/list") return entities.filter((e) => e.device_id === "dev_global" || ids.has(e.device_id));
          if (msg.type === "config/device_registry/list") return devices.filter((d) => d.id === "dev_global" || ids.has(d.id));
          if (msg.type === "config/area_registry/list") return fx.areas;
          if (msg.type === "config/floor_registry/list" || msg.type === "config/auth/list") return [];
          if (msg.type === "smart_shutter/get_config") return { entry_id: "entry1", restricted: !window.__hass.user.is_admin, covers: window.__registrySelected.map((id) => ({ entity_id: id, name: id })), custom_areas: [] };
          if (msg.type === "smart_shutter/get_forecast") return { forecast: {} };
          if (msg.type === "smart_shutter/get_available_covers") {
            if (window.__failAvailable) throw new Error("Loading failed");
            return { entry_id: "entry1", selected: [...window.__selected], covers: [fx.coverEntityId, fx.coverEntityId2, third, "cover.missing"].map((id) => ({ entity_id: id, name: id === third ? thirdDevice.name : id })) };
          }
          if (msg.type === "smart_shutter/save_covers") {
            window.__saved.push(msg);
            if (window.__rejectSave) throw new Error("Save failed");
            window.__selected = [...msg.covers];
            setTimeout(() => { window.__registrySelected = [...msg.covers]; }, 450);
            return { success: true };
          }
          return {};
        },
      };
      const card = document.getElementById("card");
      card.setConfig({});
      card.hass = window.__hass;
    }, buildFixture());
    const card = page.locator("smart-shutter-card");
    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-shutters"]').click();
    await card.locator('[data-save-covers]').waitFor();
    assert.equal(await card.locator("h2").textContent(), "Rollläden verwalten");
    assert.equal(await card.locator('[data-managed-cover="cover.missing"]').isChecked(), true);
    assert.equal(await card.locator('[data-managed-cover="cover.newroom"]').isChecked(), false);
    assert.ok((await card.locator(".body").textContent()).includes('New <South> & "Window"'));
    assert.equal(await card.locator("south").count(), 0);
    await card.locator('[data-managed-cover="cover.testroom2"]').uncheck();
    await card.locator('[data-managed-cover="cover.missing"]').uncheck();
    await card.locator('[data-managed-cover="cover.newroom"]').check();
    await card.locator('[data-save-covers]').click();
    assert.equal(await page.evaluate(() => window.__saved.length), 0, "Cancel must not save");
    console.log("OK - German management, missing covers, escaped names, cancel removal");

    acceptRemoval = true;
    await page.evaluate(() => { window.__rejectSave = true; });
    await card.locator('[data-save-covers]').click();
    await page.waitForFunction(() => document.getElementById("card").shadowRoot.querySelector('[data-managed-covers-status]').textContent.includes("Save failed"));
    assert.equal(await card.locator('[data-managed-cover="cover.newroom"]').isChecked(), true);
    assert.equal(await card.locator('[data-managed-cover="cover.testroom2"]').isChecked(), false);
    await page.evaluate(() => { window.__rejectSave = false; });
    await card.locator('[data-save-covers]').click();
    await page.waitForFunction(() => document.getElementById("card").shadowRoot.querySelector('[data-managed-covers-status]').textContent.includes("Rollladenliste aktualisiert"));
    assert.deepEqual(await page.evaluate(() => window.__saved.at(-1)), { type: "smart_shutter/save_covers", entry_id: "entry1", covers: ["cover.testroom", "cover.newroom"] });
    await card.locator('[data-nav="list"]').click();
    assert.equal(await card.locator('[data-open-detail="dev_testroom2"]').count(), 0);
    assert.equal(await card.locator('[data-open-detail="dev_newroom"]').count(), 1);
    console.log("OK - Save failure preserves draft; retry waits for reload and refreshes list");

    await page.evaluate(() => { window.__hass.language = "en"; document.getElementById("card").hass = window.__hass; });
    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-shutters"]').click();
    await card.locator('[data-save-covers]').waitFor();
    assert.equal(await card.locator("h2").textContent(), "Manage shutters");
    assert.equal(await card.locator('[data-save-covers]').textContent(), "Save");
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await card.locator('.body').evaluate((el) => el.scrollWidth <= el.clientWidth), true, "Mobile view must fit");
    console.log("OK - English management and mobile layout");

    await page.evaluate(() => { window.__failAvailable = true; });
    await card.locator('[data-settings-back]').click();
    await card.locator('[data-settings-nav="settings-shutters"]').click();
    await card.locator('.hint.error').waitFor();
    assert.ok((await card.locator(".body").textContent()).includes("Loading failed"));
    assert.equal(await card.locator('[data-save-covers]').count(), 0);
    await page.evaluate(async () => {
      window.__hass.user.is_admin = false;
      await document.getElementById("card")._loadBackendConfig();
      document.getElementById("card")._view = "settings";
      document.getElementById("card")._render();
    });
    assert.equal(await card.locator('[data-settings-nav="settings-shutters"]').count(), 0);
    assert.deepEqual(await page.evaluate(() => window.__services), []);
    assert.deepEqual(errors, []);
    console.log("OK - Loading errors and non-admin menu; zero cover service calls");
  } finally {
    await browser.close();
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
