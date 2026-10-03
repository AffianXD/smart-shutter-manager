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
      fx.devices.find((d) => d.id === "dev_testroom").name_by_user = 'Kitchen <East> & "Door"';
      const thirdEntities = fx.entities.filter((e) => e.device_id === "dev_testroom2").map((e) => JSON.parse(JSON.stringify(e).replaceAll("testroom2", "newroom")));
      const selected = [fx.coverEntityId, fx.coverEntityId2, "cover.missing"];
      window.__saved = [];
      window.__services = [];
      window.__rejectSave = false;
      window.__reloadReads = 0;
      window.__names = { [fx.coverEntityId]: "Kitchen", [fx.coverEntityId2]: "Office", "cover.missing": "Missing" };
      window.__saveDelay = 0;
      window.__activeSaves = 0;
      window.__maxSaves = 0;
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
            return { entry_id: "entry1", selected: [...window.__selected], names: { ...window.__names }, covers: [fx.coverEntityId, fx.coverEntityId2, third, "cover.missing"].map((id) => ({ entity_id: id, name: id === third ? thirdDevice.name : id })) };
          }
          if (msg.type === "smart_shutter/save_covers") {
            window.__saved.push(msg);
            window.__activeSaves++;
            window.__maxSaves = Math.max(window.__maxSaves, window.__activeSaves);
            await new Promise((resolve) => setTimeout(resolve, window.__saveDelay));
            window.__activeSaves--;
            if (window.__rejectSave) throw new Error("Save failed");
            window.__selected = [...msg.covers];
            for (const [id, value] of Object.entries(msg.names)) {
              window.__names[id] = value.trim();
              const device = devices.find((d) => d.id === byCover.get(id));
              if (device) {
                device.name_by_user = value.trim() || null;
                device.name = value.trim() || id;
              }
            }
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
    const name = (id) => card.locator('[data-managed-cover-name="' + id + '"]');
    const checkbox = (id) => card.locator('[data-managed-cover="' + id + '"]');
    const savedCount = () => page.evaluate(() => window.__saved.length);
    const idle = () => page.waitForFunction(() => {
      const c = document.getElementById("card");
      return !c._savingManagedCovers && !c._managedCoversSavePending && !c._managedCoversSaveTimer && !c._managedCoversSaveError;
    });
    await card.locator('[data-nav="settings"]').click();
    assert.equal(await card.locator('[data-settings-nav="settings-rename"]').count(), 0);
    await card.locator('[data-settings-nav="settings-shutters"]').click();
    await name("cover.testroom").waitFor();
    assert.equal(await card.locator("h2").textContent(), "Rollläden verwalten");
    assert.equal(await card.locator("[data-save-covers], [data-save-rename]").count(), 0);
    assert.equal(await checkbox("cover.missing").isChecked(), true);
    assert.equal(await name("cover.newroom").isDisabled(), true);
    assert.equal(await name("cover.testroom").inputValue(), 'Kitchen <East> & "Door"');
    assert.ok((await card.locator(".body").textContent()).includes('New <South> & "Window"'));
    assert.equal(await card.locator("south, east").count(), 0);
    await checkbox("cover.testroom2").click();
    assert.equal(await checkbox("cover.testroom2").isChecked(), true);
    assert.equal(await savedCount(), 0, "Cancelled removal must restore the checkbox and not save");
    acceptRemoval = true;
    await checkbox("cover.missing").uncheck();
    await page.waitForFunction(() => window.__saved.length === 1);
    await idle();
    assert.deepEqual(await page.evaluate(() => window.__selected), ["cover.testroom", "cover.testroom2"]);
    console.log("OK - One management view, missing covers, HA names, escaped names, confirmed removal autosave");

    await page.evaluate(() => { window.__rejectSave = true; });
    await checkbox("cover.newroom").check();
    await card.locator("[data-retry-covers]").waitFor({ state: "visible" });
    await name("cover.newroom").fill('Büro <Süd> & "Fenster"');
    await page.waitForFunction(() => window.__saved.length === 3);
    await card.locator("[data-retry-covers]").waitFor({ state: "visible" });
    await card.locator("[data-settings-back]").click();
    await card.locator('[data-settings-nav="settings-shutters"]').click();
    assert.equal(await name("cover.newroom").inputValue(), 'Büro <Süd> & "Fenster"');
    assert.equal(await checkbox("cover.newroom").isChecked(), true);
    await page.evaluate(() => { window.__rejectSave = false; });
    await card.locator("[data-retry-covers]").click();
    await idle();
    assert.deepEqual(await page.evaluate(() => window.__saved.at(-1)), {
      type: "smart_shutter/save_covers", entry_id: "entry1",
      covers: ["cover.testroom", "cover.testroom2", "cover.newroom"],
      names: { "cover.newroom": 'Büro <Süd> & "Fenster"' },
    });
    console.log("OK - Autosave errors keep selection and names across navigation; retry saves both");

    const before = await savedCount();
    await name("cover.testroom").fill("");
    await name("cover.testroom").pressSequentially("Kitchen renamed", { delay: 30 });
    await page.waitForTimeout(400);
    assert.equal(await savedCount(), before, "Typing must debounce saves");
    await page.waitForFunction((count) => window.__saved.length > count, before);
    await idle();
    assert.equal(await savedCount(), before + 1);
    assert.equal(await name("cover.testroom").evaluate((el) => el.getRootNode().activeElement === el), true);
    assert.equal(await name("cover.testroom").inputValue(), "Kitchen renamed");
    console.log("OK - Names autosave once after typing pauses and retain focus through reload");

    await page.evaluate(() => { window.__saveDelay = 1200; });
    const serialBefore = await savedCount();
    await name("cover.testroom").fill("First draft");
    await page.waitForFunction((count) => window.__saved.length > count, serialBefore);
    await name("cover.testroom").fill("Latest draft");
    await page.waitForFunction(() => window.__names["cover.testroom"] === "Latest draft");
    await idle();
    assert.equal(await name("cover.testroom").inputValue(), "Latest draft");
    assert.equal(await page.evaluate(() => window.__maxSaves), 1);
    assert.equal(await name("cover.testroom").evaluate((el) => el.getRootNode().activeElement === el), true);
    await page.evaluate(() => { window.__saveDelay = 0; });
    console.log("OK - Edits during an in-flight save are serialized without losing text or focus");

    await name("cover.testroom").fill("Saved after navigation");
    await card.locator('[data-nav="list"]').click();
    await page.waitForFunction(() => window.__names["cover.testroom"] === "Saved after navigation");
    await idle();
    assert.ok((await card.locator(".name").allTextContents()).includes("Saved after navigation"));
    assert.equal(await card.locator('[data-open-detail="dev_newroom"]').count(), 1);
    console.log("OK - Pending autosave survives navigation and updates the shutter list");

    await page.evaluate(() => { window.__hass.language = "en"; document.getElementById("card").hass = window.__hass; });
    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-shutters"]').click();
    await name("cover.newroom").waitFor();
    assert.equal(await card.locator("h2").textContent(), "Manage shutters");
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await card.locator(".body").evaluate((el) => el.scrollWidth <= el.clientWidth), true);
    await name("cover.testroom").fill("");
    await page.waitForFunction(() => window.__names["cover.testroom"] === "");
    await idle();
    assert.ok((await card.locator("[data-managed-covers-status]").textContent()).includes("Saved automatically"));
    console.log("OK - English autosave, clearing a name, mobile layout");

    await page.evaluate(() => { window.__failAvailable = true; });
    await card.locator("[data-settings-back]").click();
    await card.locator('[data-settings-nav="settings-shutters"]').click();
    await card.locator(".hint.error").waitFor();
    assert.ok((await card.locator(".body").textContent()).includes("Loading failed"));
    assert.equal(await card.locator("[data-managed-cover-name]").count(), 0);
    await page.evaluate(async () => {
      window.__hass.user.is_admin = false;
      await document.getElementById("card")._loadBackendConfig();
      document.getElementById("card")._view = "settings";
      document.getElementById("card")._render();
    });
    assert.equal(await card.locator('[data-settings-nav="settings-shutters"]').count(), 0);
    assert.deepEqual(await page.evaluate(() => window.__services), []);
    assert.deepEqual(errors, []);
    console.log("OK - Loading errors, admin-only menu, and zero cover service calls");
  } finally {
    await browser.close();
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
