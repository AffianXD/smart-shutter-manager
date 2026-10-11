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
        services: { notify: { guest: { name: "Guest phone" }, missing: { name: "Removed before save" } }, cover: { open_cover: {} } }, states: fx.states, language: "de", user: { is_admin: true, id: "guest" },
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
              if (msg.notification_mode === "inherit" && msg.pre_notify_mode === "inherit") delete window.__config.shutter_notifications[msg.entity_id];
              else window.__config.shutter_notifications[msg.entity_id] = { notification_mode: msg.notification_mode, notify_service: msg.notify_service, pre_notify_mode: msg.pre_notify_mode, pre_notify_lead_minutes: msg.pre_notify_lead_minutes };
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
    const recipient = form.locator("[data-notify-control] select");
    const warningInfo = form.locator('[data-pre-notify-hint] .ssm-info-control');
    assert.equal(await warningInfo.locator('.ssm-info-popover').isVisible(), false, 'Warning explanation starts collapsed');
    await warningInfo.locator('[data-info-toggle]').click();
    assert.match(await warningInfo.locator('.ssm-info-popover').textContent(), /Gilt nur für geplante Schließvorwarnungen/);
    assert.equal(await warningInfo.locator('.ssm-info-popover').isVisible(), true);
    await warningInfo.locator('[data-info-toggle]').click();
   const status = form.locator("[data-notification-status]");
    assert.equal(await form.locator(".ssm-info-heading-row h3").count(), 1, "Shutter notifications keep their own title in Advanced");
   assert.equal(await form.locator("button[data-save-shutter-notifications]").count(), 0, "Notification settings autosave");
    assert.equal(await form.locator("[data-info-toggle][aria-expanded=true]").count(), 0, "Hints are collapsed initially");
    const info = form.locator(".ssm-info-control").first();
    await info.locator("[data-info-toggle]").click();
    assert.equal(await info.locator(".ssm-info-popover").isVisible(), true, "The info icon reveals its hint");
    await info.locator("[data-info-toggle]").click();
    assert.equal(await info.locator(".ssm-info-popover").isVisible(), false);
    assert.equal(await mode.inputValue(), "inherit");
    assert.deepEqual(await mode.locator("option").allTextContents(), ["Vererben", "Aus", "Eigener Empfänger"]);
    assert.equal(await recipient.isVisible(), false);
    await mode.selectOption("custom");
    assert.equal(await recipient.isVisible(), true);
    assert.deepEqual(await recipient.locator('option').evaluateAll(options => options.map(o => o.value)), ['', 'notify.guest', 'notify.missing'], 'Recipient choices come from notify services, not entities or other domains');
    assert.match(await recipient.locator('option[value="notify.guest"]').textContent(), /Guest phone.*notify.guest/);
    await assertRecipientSpacing(form);
    assert.equal(await page.evaluate(() => window.__saved.length), 0, "Empty recipient must not save");
    await recipient.selectOption("notify.missing");
    await status.filter({ hasText: "registered notify" }).waitFor();
    assert.equal(await recipient.inputValue(), "notify.missing", "Failure keeps the draft");
    await recipient.selectOption("notify.guest");
    await status.filter({ hasText: "Automatisch gespeichert" }).waitFor();
    assert.deepEqual(await page.evaluate(() => window.__saved.at(-1)), {
      type: "smart_shutter/save_shutter_notifications", entry_id: "entry1", entity_id: "cover.testroom", notification_mode: "custom", notify_service: "notify.guest", pre_notify_mode: "inherit",
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
    await recipient.selectOption("notify.guest");
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

    const preMode = form.locator('[data-pre-notify-mode]');
    const preMinutes = form.locator('[data-pre-notify-minutes]');
    assert.equal(await preMode.inputValue(), 'inherit');
    await preMode.selectOption('off');
    await status.filter({ hasText: 'Automatisch gespeichert' }).waitFor();
    assert.equal(await mode.inputValue(), 'inherit', 'Warning off keeps movement recipient inheritance');
    assert.equal(await page.evaluate(() => window.__config.shutter_notifications['cover.testroom'].pre_notify_mode), 'off');
    await preMode.selectOption('custom');
    await preMinutes.fill('12');
    await status.filter({ hasText: 'Automatisch gespeichert' }).waitFor();
    assert.equal(await page.evaluate(() => window.__config.shutter_notifications['cover.testroom'].pre_notify_lead_minutes), 12);
    await preMinutes.fill('0');
    await page.waitForTimeout(750);
    assert.equal(await page.evaluate(() => window.__config.shutter_notifications['cover.testroom'].pre_notify_lead_minutes), 12, 'Invalid lead does not overwrite saved setting');
    await preMinutes.fill('7');
    await status.filter({ hasText: 'Automatisch gespeichert' }).waitFor();
    await card.locator('[data-back]').click();
    await card.locator('[data-open-detail="dev_testroom"]').click();
    await card.locator('[data-tab="advanced"]').click();
    assert.equal(await preMinutes.inputValue(), '7');
    await preMode.selectOption('inherit');
    await status.filter({ hasText: 'Automatisch gespeichert' }).waitFor();
    assert.equal(await page.evaluate(() => window.__config.shutter_notifications['cover.testroom']), undefined);
    console.log('OK - Independent warning off/custom/inherit, validation and persistence');

    await card.locator('[data-tab="basic"]').click();
    await card.locator('[data-area-edit="south"]').click();
    const areaForm = card.locator("[data-notification-settings]");
    const areaMode = areaForm.locator("[data-notification-mode]");
    const areaRecipient = areaForm.locator("[data-notify-control] select");
   const areaStatus = areaForm.locator("[data-notification-status]");
   assert.equal(await areaForm.locator(".ssm-info-heading-row h3").count(), 0, "Area accordion does not repeat its notification heading inside");
   assert.equal(await areaMode.inputValue(), "custom", "Legacy area recipient is preserved");
   assert.equal(await areaForm.locator("[data-info-toggle][aria-expanded=true]").count(), 0, "Area hints are also collapsed");
    await card.locator('.section-toggle[data-toggle-area-section="notify"]').click();
    assert.equal(await card.locator("[data-notification-settings]").count(), 0, "Collapsing the area notification section hides the whole form");
    await card.locator('.section-toggle[data-toggle-area-section="notify"]').click();
    assert.equal(await card.locator("[data-notification-settings]").count(), 1, "The notification form returns when its own section is expanded");
   await card.locator('[data-area-field="name"]').fill("South draft");
    await areaRecipient.selectOption("notify.missing");
    const membershipWrites = await page.evaluate(() => window.__saved.filter((msg) => msg.type === "smart_shutter/save_shutter_areas").length);
    await areaStatus.filter({ hasText: "registered notify" }).waitFor();
    assert.equal(await areaRecipient.inputValue(), "notify.missing");
    assert.equal(await card.locator('[data-area-field="name"]').inputValue(), "South draft");
    assert.equal(await page.evaluate(() => window.__saved.filter((msg) => msg.type === "smart_shutter/save_shutter_areas").length), membershipWrites, "Invalid settings must not change membership");
    await areaRecipient.selectOption("notify.guest");
    await areaStatus.filter({ hasText: "Automatisch gespeichert" }).waitFor();
    assert.deepEqual(await page.evaluate(() => Object.keys(window.__saved.at(-1).fields).sort()), ["notification_mode", "notify_service", "pre_notify_mode"], "Autosave updates only the area's notification settings");
    const areaPreMode = areaForm.locator('[data-pre-notify-mode]');
    await assertRecipientSpacing(areaForm);
    const areaPreMinutes = areaForm.locator('[data-pre-notify-minutes]');
    await areaPreMode.selectOption('custom');
    await areaStatus.filter({ hasText: "Automatisch gespeichert" }).waitFor();
    assert.equal(await areaPreMinutes.inputValue(), '5', 'Area warnings default to five minutes');
    assert.equal(await page.evaluate(() => window.__config.custom_areas[0].pre_notify_lead_minutes), 5);
    await areaPreMinutes.fill('0');
    await page.waitForTimeout(750);
    assert.equal(await page.evaluate(() => window.__config.custom_areas[0].pre_notify_lead_minutes), 5, 'Invalid area lead cannot replace the saved value');
    await areaPreMinutes.fill('9');
    await areaStatus.filter({ hasText: "Automatisch gespeichert" }).waitFor();
    assert.equal(await page.evaluate(() => window.__config.custom_areas[0].pre_notify_lead_minutes), 9);
    await card.locator('[data-area-save]').click();
    await card.locator('[data-area-edit="south"]').waitFor();
    assert.equal(await page.evaluate(() => window.__config.custom_areas[0].name), "South draft", "The separate area form save still saves its draft");
    assert.equal(await page.evaluate(() => window.__config.custom_areas[0].notification_mode), "custom");
    assert.equal(await page.evaluate(() => window.__config.custom_areas[0].pre_notify_lead_minutes), 9, 'The full area save retains the warning time');
    await card.locator('[data-area-edit="south"]').click();
    assert.equal(await areaPreMode.inputValue(), 'custom');
    assert.equal(await areaPreMinutes.inputValue(), '9', 'Area warning survives navigation');
    await areaPreMode.selectOption('off');
    await areaStatus.filter({ hasText: "Automatisch gespeichert" }).waitFor();
    assert.equal(await areaPreMinutes.isVisible(), false);
    assert.equal(await page.evaluate(() => window.__config.custom_areas[0].notify_service), 'notify.guest', 'Warning off keeps the recipient');
    await areaPreMode.selectOption('inherit');
    await areaStatus.filter({ hasText: "Automatisch gespeichert" }).waitFor();
    assert.equal(await page.evaluate(() => window.__config.custom_areas[0].pre_notify_mode), 'inherit');
    assert.deepEqual(await page.evaluate(() => window.__config.shutter_areas["cover.testroom"]), ["south", "other"], "Saving must preserve area priority");
    console.log("OK - Area autosave is isolated from unsaved name and membership fields");
    await card.locator('[data-settings-back-areas]').click();

    await page.evaluate(() => {
      window.__hass.language = "en";
      window.__hass.user.is_admin = false;
      const card = document.getElementById("card");
      card.hass = window.__hass;
    });
    await card.locator('[data-area-edit="south"]').click();
    const guestAreaForm = card.locator("[data-notification-settings]");
    const guestAreaMode = guestAreaForm.locator("[data-notification-mode]");
    const guestAreaRecipient = guestAreaForm.locator("[data-notify-control] select");
    const guestAreaPreMode = guestAreaForm.locator('[data-pre-notify-mode]');
    const guestAreaPreMinutes = guestAreaForm.locator('[data-pre-notify-minutes]');
    await guestAreaPreMode.selectOption('custom');
    await guestAreaPreMinutes.fill('5');
    await guestAreaForm.locator("[data-notification-status]").filter({ hasText: "Saved automatically" }).waitFor();
    assert.equal(await page.evaluate(() => window.__saved.at(-1).fields.pre_notify_lead_minutes), 5, 'Guests can save their area warning time');
    assert.deepEqual(await guestAreaMode.locator("option").allTextContents(), ["Inherit", "Off", "Custom recipient"]);
    assert.equal(await card.locator('[data-area-field="name"]').count(), 0, "Guest cannot edit the area name");
    await guestAreaMode.selectOption("off");
    await guestAreaForm.locator("[data-notification-status]").filter({ hasText: "Saved automatically" }).waitFor();
    assert.equal(await page.evaluate(() => window.__saved.at(-1).type), "smart_shutter/save_own_area_settings");
    await guestAreaMode.selectOption("custom");
    await assertRecipientSpacing(guestAreaForm);
    await guestAreaRecipient.selectOption("notify.guest");
    await guestAreaForm.locator("[data-notification-status]").filter({ hasText: "Saved automatically" }).waitFor();
    await card.locator('[data-area-save]').click();
    await card.locator('[data-area-edit="south"]').waitFor();
    await card.locator('[data-nav="list"]').first().click();
    await card.locator('[data-open-detail="dev_testroom"]').click();
    await card.locator('[data-tab="advanced"]').click();
    const guestForm = card.locator("[data-notification-settings]");
    const guestMode = guestForm.locator("[data-notification-mode]");
    const guestRecipient = guestForm.locator("[data-notify-control] select");
    await guestMode.selectOption("custom");
    await assertRecipientSpacing(guestForm);
    await guestRecipient.selectOption("notify.guest");
    await guestForm.locator("[data-notification-status]").filter({ hasText: "Saved automatically" }).waitFor();
    await page.setViewportSize({ width: 320, height: 844 });
    assert.equal(await guestForm.evaluate((el) => el.scrollWidth <= el.clientWidth), true);
    await assertRecipientSpacing(guestForm);
    const infoBounds = async (details) => {
      const row = details.locator('..');
      const alignment = await row.evaluate(el => {
        const label = el.querySelector('label, h3');
        const icon = el.querySelector('[data-info-toggle]').getBoundingClientRect();
        const box = el.getBoundingClientRect();
        return { gap: icon.left - label.getBoundingClientRect().right, sameRow: Math.abs((label.getBoundingClientRect().top + label.getBoundingClientRect().bottom) / 2 - (icon.top + icon.bottom) / 2) < 2 };
      });
      assert.ok(alignment.gap >= 0 && alignment.gap <= 8 && alignment.sameRow, 'Info sits directly beside its text');
      await details.locator("[data-info-toggle]").click();
      const bounds = await details.locator(".ssm-info-popover").evaluate((el) => {
        const tip = el.getBoundingClientRect();
        const form = el.getRootNode().querySelector("ha-card").getBoundingClientRect();
        return { left: tip.left, right: tip.right, top: tip.top, bottom: tip.bottom, width: innerWidth, height: innerHeight, formLeft: form.left, formRight: form.right };
      });
      assert.ok(bounds.left >= bounds.formLeft - 1 && bounds.right <= bounds.formRight + 1, "Hint stays within the card: " + JSON.stringify(bounds));
      assert.ok(bounds.left >= 0 && bounds.right <= bounds.width && bounds.top >= 0 && bounds.bottom <= bounds.height, "Hint stays within the viewport");
      await page.keyboard.press("Escape");
      assert.equal(await details.locator(".ssm-info-popover").isHidden(), true);
      assert.equal(await details.locator("[data-info-toggle]").evaluate(el => el.getRootNode().activeElement === el), true);
      await page.keyboard.press("Enter");
      assert.equal(await details.locator(".ssm-info-popover").isVisible(), true);
      await guestMode.click();
      assert.equal(await details.locator(".ssm-info-popover").isHidden(), true);
    };
    await infoBounds(guestForm.locator(".ssm-info-heading-row .ssm-info-control"));
    await infoBounds(guestForm.locator("[data-notification-recipient-hint] .ssm-info-control"));
    await infoBounds(guestForm.locator("[data-pre-notify-hint] .ssm-info-control"));
    await page.setViewportSize({ width: 1280, height: 844 });
    const haCard = card.locator("ha-card");
    await haCard.evaluate((el) => { el.style.width = "260px"; el.style.maxWidth = "260px"; });
    assert.equal(await guestForm.evaluate((el) => el.scrollWidth <= el.clientWidth), true, "Notification form fits a narrow card");
    await infoBounds(guestForm.locator(".ssm-info-heading-row .ssm-info-control"));
    await infoBounds(guestForm.locator("[data-notification-recipient-hint] .ssm-info-control"));
    await infoBounds(guestForm.locator("[data-pre-notify-hint] .ssm-info-control"));
    await haCard.evaluate((el) => { el.style.removeProperty("width"); el.style.removeProperty("max-width"); });

    const writesBeforeRefresh = await page.evaluate(() => window.__saved.length);
    await page.evaluate(() => {
      window.__hass.services = undefined;
      document.getElementById('card').hass = window.__hass;
    });
    assert.equal(await guestRecipient.inputValue(), 'notify.guest');
    assert.match(await guestForm.locator('[data-notify-availability]').textContent(), /Loading notification services/);
    await page.evaluate(() => {
      window.__hass.services = { notify: {} };
      document.getElementById('card').hass = window.__hass;
    });
    assert.equal(await guestRecipient.inputValue(), 'notify.guest');
    assert.match(await guestForm.locator('[data-notify-availability]').textContent(), /notify.guest.*unavailable/);
    await page.evaluate(() => {
      window.__hass.services = { notify: { guest: { name: 'Guest phone' }, late_phone: { name: 'Late phone' } }, cover: { open_cover: {} } };
      document.getElementById('card').hass = window.__hass;
    });
    assert.equal(await guestRecipient.inputValue(), 'notify.guest');
    assert.equal(await guestRecipient.locator('option[value="notify.late_phone"]').count(), 1);
    assert.equal(await page.evaluate(() => window.__saved.length), writesBeforeRefresh, 'Registry refreshes never autosave or overwrite a saved recipient');
    await page.evaluate(() => {
      customElements.define('ha-service-picker', class extends HTMLElement {});
      document.getElementById('card').hass = window.__hass;
    });
    const nativePicker = guestForm.locator('ha-service-picker');
    assert.deepEqual(await nativePicker.evaluate(el => Object.keys(el.hass.services)), ['notify']);
    assert.equal(await nativePicker.evaluate(el => el.value), 'notify.guest', 'Late component upgrade retains value');
    assert.equal(await nativePicker.evaluate(el => el.showServiceId), true);
    await nativePicker.evaluate(el => el.dispatchEvent(new CustomEvent('value-changed', {detail:{value:'cover.open_cover'}, bubbles:true, composed:true})));
    assert.equal(await page.evaluate(() => window.__saved.length), writesBeforeRefresh, 'Reject forged non-notify selections');
    await nativePicker.evaluate(el => el.dispatchEvent(new CustomEvent('value-changed', {detail:{value:'notify.unknown'}, bubbles:true, composed:true})));
    assert.equal(await page.evaluate(() => window.__saved.length), writesBeforeRefresh, 'Reject unknown selections');
    await nativePicker.evaluate(el => {
      el.dispatchEvent(new CustomEvent('value-changed', {detail:{value:undefined}, bubbles:true, composed:true}));
      el.dispatchEvent(new Event('change', {bubbles:true}));
    });
    assert.equal(await page.evaluate(() => window.__saved.length), writesBeforeRefresh, 'Empty custom recipient does not save');
    await nativePicker.evaluate(el => {
      el.dispatchEvent(new CustomEvent('value-changed', {detail:{value:'notify.guest'}, bubbles:true, composed:true}));
      el.dispatchEvent(new Event('change', {bubbles:true}));
    });
    await guestForm.locator('[data-notification-status]').filter({hasText:'Saved automatically'}).waitFor();
    assert.equal(await page.evaluate(() => window.__saved.length), writesBeforeRefresh + 1, 'Native selection autosaves exactly once');
    await page.evaluate(async () => {
      window.__hass.user.is_admin = true;
      const el = document.getElementById('card');
      el.hass = window.__hass;
      await el._loadBackendConfig();
    });
    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-basic"]').click();
    const globalPicker = card.locator('ha-service-picker');
    await globalPicker.evaluate(el => el.dispatchEvent(new CustomEvent('value-changed', {detail:{value:'notify.guest'}, bubbles:true, composed:true})));
    await card.locator('[data-save-basic]').click();
    await card.locator('[data-save-status]').filter({hasText:'Saved'}).waitFor();
    assert.equal(await page.evaluate(() => window.__saved.at(-1).notify_service), 'notify.guest', 'Global save uses the native selection');
    await globalPicker.evaluate(el => el.dispatchEvent(new CustomEvent('value-changed', {detail:{value:undefined}, bubbles:true, composed:true})));
    await card.locator('[data-save-basic]').click();
    await card.locator('[data-save-status]').filter({hasText:'Saved'}).waitFor();
    assert.equal(await page.evaluate(() => window.__saved.at(-1).notify_service), '', 'Global clear disables notifications');
    assert.deepEqual(await page.evaluate(() => window.__services), []);
    assert.deepEqual(errors, []);
    console.log("OK - English, guest area/shutter autosave, mobile fit, no real service calls");
    console.log('OK - Missing/delayed services, late native upgrade, filtering, native autosave and global save/clear');
  } finally {
    await browser.close();
  }
}

async function assertRecipientSpacing(form) {
  const gap = await form.evaluate(el => el.querySelector('[data-notification-recipient-field]').getBoundingClientRect().top
    - el.querySelector('[data-notification-mode]').getBoundingClientRect().bottom);
  assert.ok(gap >= 14 && gap <= 16, `Custom recipient uses the standard 14px form gap: ${gap}`);
}

main().catch((error) => { console.error(error); process.exit(1); });
