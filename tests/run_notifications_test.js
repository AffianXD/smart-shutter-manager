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
    // The file fixture does not load HA's block-level ha-card component.
    await page.addInitScript(() => customElements.define("ha-card", class extends HTMLElement {
      connectedCallback() { this.style.display = "block"; }
    }));
    await page.goto("file://" + path.join(__dirname, "test.html"));
    await page.evaluate((fx) => {
      window.__saved = [];
      window.__services = [];
      window.__delayNextNotificationSave = false;
      window.__notificationSaveDelayEntered = false;
      window.__config = {
        entry_id: "entry1", basic_settings: {},
        covers: [fx.coverEntityId, fx.coverEntityId2].map((entity_id) => ({ entity_id, name: entity_id })),
        custom_areas: [{ id: "south", name: "South", notify_service: "notify.guest", assigned_ha_user_ids: ["guest"] }],
        shutter_areas: { [fx.coverEntityId]: ["south", "other"], [fx.coverEntityId2]: ["south"] },
        shutter_notifications: {},
      };
      window.__hass = {
        states: fx.states, language: "de", user: { is_admin: true, id: "guest" },
        callService: async (...args) => { window.__services.push(args); throw new Error("Unexpected service call"); },
        callWS: async (msg) => {
          if (msg.type === "config/entity_registry/list") return fx.entities;
          if (msg.type === "config/device_registry/list") return fx.devices;
          if (msg.type === "config/area_registry/list") return fx.areas;
          if (msg.type === "config/floor_registry/list" || msg.type === "config/auth/list") return [];
          if (msg.type === "smart_shutter/get_config") return structuredClone({ ...window.__config, restricted: !window.__hass.user.is_admin });
          if (msg.type === "smart_shutter/get_forecast") return { forecast: {} };
          if (msg.type.startsWith("smart_shutter/save_")) {
            window.__saved.push(msg);
            if (msg.type === "smart_shutter/save_shutter_notifications" && window.__delayNextNotificationSave) {
              window.__delayNextNotificationSave = false;
              window.__notificationSaveDelayEntered = true;
              await new Promise((resolve) => setTimeout(resolve, 350));
            }
            const settings = msg.type === "smart_shutter/save_custom_areas" ? msg.areas.find((area) => area.id === "south") : msg.fields || msg;
            if (settings.notification_mode === "custom" && settings.notify_service !== "notify.guest") throw new Error("Select a registered notify service.");
            if (msg.type === "smart_shutter/save_shutter_notifications") {
              if (msg.notification_mode === "inherit") delete window.__config.shutter_notifications[msg.entity_id];
              else window.__config.shutter_notifications[msg.entity_id] = { notification_mode: msg.notification_mode, notify_service: msg.notify_service };
            }
            if (msg.type === "smart_shutter/save_custom_areas") window.__config.custom_areas = structuredClone(msg.areas);
            if (msg.type === "smart_shutter/save_shutter_areas") window.__config.shutter_areas = structuredClone(msg.shutter_areas);
            if (msg.type === "smart_shutter/save_own_area_settings") Object.assign(window.__config.custom_areas[0], msg.fields);
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
    await card.locator('[data-nav="list"]').first().click();
    await card.locator('[data-open-detail="dev_testroom"]').click();
    assert.equal(await card.locator("[data-notification-settings]").count(), 0, "Shutter notifications belong in Advanced");
    await card.locator('[data-tab="advanced"]').click();
    const form = card.locator("[data-notification-settings]");
    const mode = form.locator("[data-notification-mode]");
    const recipient = form.locator("[data-notification-recipient]");
   const status = form.locator("[data-notification-status]");
    assert.equal(await form.locator(".notification-title h3").count(), 1, "Shutter notifications keep their own title in Advanced");
   assert.equal(await form.locator("button[data-save-shutter-notifications]").count(), 0, "Notification settings autosave");
    assert.equal(await form.locator("details.notification-info[open]").count(), 0, "Hints are collapsed initially");
    const info = form.locator("details.notification-info").first();
    await info.locator("summary").click();
    assert.equal(await info.locator(".notification-info-text").isVisible(), true, "The info icon reveals its hint");
    await info.locator("summary").click();
    assert.equal(await info.locator(".notification-info-text").isVisible(), false);
    assert.equal(await mode.inputValue(), "inherit");
    assert.deepEqual(await mode.locator("option").allTextContents(), ["Vererben", "Aus", "Eigener Empfänger"]);
    assert.equal(await recipient.isVisible(), false);
    await mode.selectOption("custom");
    assert.equal(await recipient.isVisible(), true);
    assert.equal(await page.evaluate(() => window.__saved.length), 0, "Empty recipient must not save");
    await recipient.fill("notify.missing");
    await status.filter({ hasText: "registered notify" }).waitFor();
    assert.equal(await recipient.inputValue(), "notify.missing", "Failure keeps the draft");
    await recipient.fill("notify.guest");
    await status.filter({ hasText: "Automatisch gespeichert" }).waitFor();
    assert.deepEqual(await page.evaluate(() => window.__saved.at(-1)), {
      type: "smart_shutter/save_shutter_notifications", entry_id: "entry1", entity_id: "cover.testroom", notification_mode: "custom", notify_service: "notify.guest",
    });
    await card.locator('[data-back]').click();
    await card.locator('[data-open-detail="dev_testroom"]').click();
    await card.locator('[data-tab="advanced"]').click();
    assert.equal(await mode.inputValue(), "custom", "Saved setting survives navigation");
    await mode.selectOption("off");
    assert.equal(await recipient.isVisible(), false);
    await status.filter({ hasText: "Automatisch gespeichert" }).waitFor();
    assert.equal(await page.evaluate(() => window.__config.shutter_notifications["cover.testroom"].notification_mode), "off");
    await mode.selectOption("inherit");
    await status.filter({ hasText: "Automatisch gespeichert" }).waitFor();
    assert.equal(await page.evaluate(() => window.__config.shutter_notifications["cover.testroom"]), undefined);
    console.log("OK - Advanced placement, collapsed info hints, autosave, validation and persistence");

    await page.evaluate(() => { window.__delayNextNotificationSave = true; });
    await mode.selectOption("off");
    await page.waitForFunction(() => window.__notificationSaveDelayEntered);
    await mode.selectOption("custom");
    await recipient.fill("notify.guest");
    await card.locator('[data-back]').click();
    await page.waitForFunction(() => {
      const settings = window.__config.shutter_notifications["cover.testroom"];
      return settings && settings.notification_mode === "custom" && settings.notify_service === "notify.guest";
    });
    await card.locator('[data-open-detail="dev_testroom"]').click();
    await card.locator('[data-tab="advanced"]').click();
    assert.equal(await mode.inputValue(), "custom", "The latest autosave survives leaving during an earlier save");
    assert.equal(await recipient.inputValue(), "notify.guest");
    await mode.selectOption("inherit");
    await status.filter({ hasText: "Automatisch gespeichert" }).waitFor();
    assert.equal(await page.evaluate(() => window.__config.shutter_notifications["cover.testroom"]), undefined);
    console.log("OK - A newer autosave is flushed after navigating away during an in-flight save");

    await card.locator('[data-tab="basic"]').click();
    await card.locator('[data-area-edit="south"]').click();
    const areaForm = card.locator("[data-notification-settings]");
    const areaMode = areaForm.locator("[data-notification-mode]");
    const areaRecipient = areaForm.locator("[data-notification-recipient]");
   const areaStatus = areaForm.locator("[data-notification-status]");
   assert.equal(await areaForm.locator(".notification-title h3").count(), 0, "Area accordion does not repeat its notification heading inside");
   assert.equal(await areaMode.inputValue(), "custom", "Legacy area recipient is preserved");
   assert.equal(await areaForm.locator("details.notification-info[open]").count(), 0, "Area hints are also collapsed");
    await card.locator('[data-toggle-area-section="notify"]').click();
    assert.equal(await card.locator("[data-notification-settings]").count(), 0, "Collapsing the area notification section hides the whole form");
    await card.locator('[data-toggle-area-section="notify"]').click();
    assert.equal(await card.locator("[data-notification-settings]").count(), 1, "The notification form returns when its own section is expanded");
   await card.locator('[data-area-field="name"]').fill("South draft");
    await areaRecipient.fill("notify.missing");
    const membershipWrites = await page.evaluate(() => window.__saved.filter((msg) => msg.type === "smart_shutter/save_shutter_areas").length);
    await areaStatus.filter({ hasText: "registered notify" }).waitFor();
    assert.equal(await areaRecipient.inputValue(), "notify.missing");
    assert.equal(await card.locator('[data-area-field="name"]').inputValue(), "South draft");
    assert.equal(await page.evaluate(() => window.__saved.filter((msg) => msg.type === "smart_shutter/save_shutter_areas").length), membershipWrites, "Invalid settings must not change membership");
    await areaRecipient.fill("notify.guest");
    await areaStatus.filter({ hasText: "Automatisch gespeichert" }).waitFor();
    assert.deepEqual(await page.evaluate(() => Object.keys(window.__saved.at(-1).fields).sort()), ["notification_mode", "notify_service"], "Autosave updates only the area's notification settings");
    await card.locator('[data-area-save]').click();
    await card.locator('[data-area-edit="south"]').waitFor();
    assert.equal(await page.evaluate(() => window.__config.custom_areas[0].name), "South draft", "The separate area form save still saves its draft");
    assert.equal(await page.evaluate(() => window.__config.custom_areas[0].notification_mode), "custom");
    assert.deepEqual(await page.evaluate(() => window.__config.shutter_areas["cover.testroom"]), ["south", "other"], "Saving must preserve area priority");
    console.log("OK - Area autosave is isolated from unsaved name and membership fields");

    await page.evaluate(() => {
      window.__hass.language = "en";
      window.__hass.user.is_admin = false;
      const card = document.getElementById("card");
      card.hass = window.__hass;
    });
    await card.locator('[data-area-edit="south"]').click();
    const guestAreaForm = card.locator("[data-notification-settings]");
    const guestAreaMode = guestAreaForm.locator("[data-notification-mode]");
    const guestAreaRecipient = guestAreaForm.locator("[data-notification-recipient]");
    assert.deepEqual(await guestAreaMode.locator("option").allTextContents(), ["Inherit", "Off", "Custom recipient"]);
    assert.equal(await card.locator('[data-area-field="name"]').count(), 0, "Guest cannot edit the area name");
    await guestAreaMode.selectOption("off");
    await guestAreaForm.locator("[data-notification-status]").filter({ hasText: "Saved automatically" }).waitFor();
    assert.equal(await page.evaluate(() => window.__saved.at(-1).type), "smart_shutter/save_own_area_settings");
    await guestAreaMode.selectOption("custom");
    await guestAreaRecipient.fill("notify.guest");
    await guestAreaForm.locator("[data-notification-status]").filter({ hasText: "Saved automatically" }).waitFor();
    await card.locator('[data-area-save]').click();
    await card.locator('[data-area-edit="south"]').waitFor();
    await card.locator('[data-nav="list"]').first().click();
    await card.locator('[data-open-detail="dev_testroom"]').click();
    await card.locator('[data-tab="advanced"]').click();
    const guestForm = card.locator("[data-notification-settings]");
    const guestMode = guestForm.locator("[data-notification-mode]");
    const guestRecipient = guestForm.locator("[data-notification-recipient]");
    await guestMode.selectOption("custom");
    await guestRecipient.fill("notify.guest");
    await guestForm.locator("[data-notification-status]").filter({ hasText: "Saved automatically" }).waitFor();
    await page.setViewportSize({ width: 320, height: 844 });
    assert.equal(await guestForm.evaluate((el) => el.scrollWidth <= el.clientWidth), true);
    const infoBounds = async (details) => {
      await details.locator("summary").click();
      const bounds = await details.locator(".notification-info-text").evaluate((el) => {
        const tip = el.getBoundingClientRect();
        const form = el.closest("[data-notification-settings]").getBoundingClientRect();
        return { left: tip.left, right: tip.right, formLeft: form.left, formRight: form.right };
      });
      assert.ok(bounds.left >= bounds.formLeft - 1 && bounds.right <= bounds.formRight + 1, "Hint stays within the form: " + JSON.stringify(bounds));
      await details.locator("summary").click();
    };
    await infoBounds(guestForm.locator(".notification-title .notification-info"));
    await infoBounds(guestForm.locator(".notification-hint .notification-info"));
    await page.setViewportSize({ width: 1280, height: 844 });
    const haCard = card.locator("ha-card");
    await haCard.evaluate((el) => { el.style.width = "260px"; el.style.maxWidth = "260px"; });
    assert.equal(await guestForm.evaluate((el) => el.scrollWidth <= el.clientWidth), true, "Notification form fits a narrow card");
    await infoBounds(guestForm.locator(".notification-title .notification-info"));
    await infoBounds(guestForm.locator(".notification-hint .notification-info"));
    await haCard.evaluate((el) => { el.style.removeProperty("width"); el.style.removeProperty("max-width"); });
    assert.deepEqual(await page.evaluate(() => window.__services), []);
    assert.deepEqual(errors, []);
    console.log("OK - English, guest area/shutter autosave, mobile fit, no real service calls");
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exit(1); });
