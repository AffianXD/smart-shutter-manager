const assert = require("node:assert/strict");
const path = require("node:path");
const { chromium } = require("playwright");
const { buildFixture } = require("./fixtures");

async function main() {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("dialog", (dialog) => dialog.accept());
    // HA's real ha-card is a block element; the standalone fixture has no HA frontend.
    await page.addInitScript(() => customElements.define("ha-card", class extends HTMLElement {
      connectedCallback() { this.style.display = "block"; }
    }));
    await page.clock.install({ time: new Date("2026-10-04T00:30:00Z") });
    await page.goto("file://" + path.join(__dirname, "test.html"));
    await page.evaluate((fx) => {
      window.__calls = [];
      window.__services = [];
      window.__failSave = false;
      window.__conflict = false;
      window.__areaConflict = false;
      window.__areaAssignmentWrites = [];
      window.__rules = [
        { id: "active", cover_ids: [fx.coverEntityId], area_ids: [], start_date: "2026-10-03", end_date: "2026-10-05", mode: "pause", actions: ["open"], open_time: null, close_time: null },
        { id: "expired", cover_ids: [], area_ids: ["guest"], start_date: "2026-09-01", end_date: "2026-09-02", mode: "times", actions: [], open_time: "10:00", close_time: null },
      ];
      const area = { id: "guest", name: "Guest area", assigned_ha_user_ids: ["guest-user"] };
      window.__hass = {
        states: fx.states, language: "de", config: { time_zone: "Europe/Berlin" }, user: { is_admin: true },
        connection: { subscribeEvents: async () => () => {} },
        callService: async (...args) => { window.__services.push(args); throw new Error("Unexpected cover service"); },
        callWS: async (msg) => {
          if (msg.type === "config/entity_registry/list") return fx.entities;
          if (msg.type === "config/device_registry/list") return fx.devices;
          if (msg.type === "config/area_registry/list") return fx.areas;
          if (msg.type === "config/floor_registry/list" || msg.type === "config/auth/list") return [];
          if (msg.type === "smart_shutter/get_config") {
            const parts = new Intl.DateTimeFormat("en", { timeZone: "Europe/Berlin", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
            const value = (type) => parts.find((part) => part.type === type).value;
            const today = `${value("year")}-${value("month")}-${value("day")}`;
            const expired = window.__rules.filter((r) => r.end_date < today)
              .sort((a, b) => b.end_date.localeCompare(a.end_date) || b.start_date.localeCompare(a.start_date) || b.id.localeCompare(a.id));
            const retained = new Set(expired.slice(0, 10).map((r) => r.id));
            window.__rules = window.__rules.filter((r) => r.end_date >= today || retained.has(r.id));
            return {
              entry_id: "entry1", restricted: !window.__hass.user.is_admin,
              covers: [{ entity_id: fx.coverEntityId, name: 'Bedroom <South> & "Window"' }, { entity_id: fx.coverEntityId2, name: "Office" }],
              custom_areas: [area], shutter_areas: { [fx.coverEntityId]: ["guest"] },
              temporal_exceptions: window.__hass.user.is_admin ? [...window.__rules] : window.__rules.filter((r) => !r.cover_ids.length && r.area_ids.length === 1 && r.area_ids[0] === "guest"),
              expired_exception_limit: 10,
              custom_schedules: [{ id: "custom_keep", name: "Existing recurring profile", weekdays: [0], interval_weeks: 2, reference_date: "2026-09-01", open_time: "09:00" }],
            };
          }
          if (msg.type === "smart_shutter/get_forecast") return { forecast: {} };
          if (msg.type === "smart_shutter/save_temporal_exception") {
            window.__calls.push(msg);
            if (window.__failSave) throw new Error("Simulated save failure");
            if (window.__conflict) return { success: false, validation_error: "conflicting_times", conflicts: [window.__rules[1]] };
            const rule = { ...msg.exception, id: msg.exception.id || "created" };
            window.__rules = window.__rules.filter((r) => r.id !== rule.id).concat(rule);
            return { success: true, exception: rule };
          }
          if (msg.type === "smart_shutter/delete_temporal_exception") {
            window.__calls.push(msg);
            window.__rules = window.__rules.filter((r) => r.id !== msg.exception_id);
            return { success: true };
          }
          if (msg.type === "smart_shutter/save_custom_areas") return { success: true };
          if (msg.type === "smart_shutter/save_shutter_areas") {
            window.__areaAssignmentWrites.push(msg.shutter_areas);
            return window.__areaConflict
              ? { success: false, validation_error: "conflicting_temporal_exceptions" }
              : { success: true };
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
    await card.locator('[data-settings-nav="settings-exceptions"]').click();
    const globalExceptions = card.locator('[data-toggle-area-section="detail-exceptions-global"]');
    assert.equal(await globalExceptions.count(), 0, "The dedicated Settings page does not use a collapsible section");
    const globalSection = card.locator('[data-temporal-exception-section]');
    assert.equal(await globalSection.getAttribute("class"), null, "The dedicated Settings page does not add a second card frame around its exception list");
    assert.equal((await globalSection.locator("h3").textContent()).trim(), "Zeitliche Ausnahmen");
    assert.equal(await card.locator('[data-exception-status="active"]').textContent(), "Aktiv");
    assert.equal(await card.locator('[data-exception-status="expired"]').textContent(), "Abgelaufen");
    assert.equal(await card.locator('[data-exception-edit="__new__"]').count(), 1, "The add action is always available on the dedicated page");
    assert.ok((await card.locator(".body").textContent()).includes('Bedroom <South> & "Window"'));
    assert.equal(await card.locator("south").count(), 0);
    await card.locator('[data-exception-edit="expired"][data-exception-reactivate]').click();
    assert.equal(await card.locator('[data-exception-field="start_date"]').inputValue(), "2026-10-04");
    assert.equal(await card.locator('[data-exception-field="end_date"]').inputValue(), "2026-10-05", "Reactivation preserves the original inclusive duration");
    assert.equal(await card.locator('[data-exception-field="open_time"]').inputValue(), "10:00");
    assert.ok((await card.locator(".body").textContent()).includes("ab heute"));
    await card.locator('[data-exception-back]').click();

    await card.locator('[data-exception-edit="__new__"]').click();
    assert.equal(await card.locator('[data-exception-field="start_date"]').inputValue(), "2026-10-04", "Dates use HA time zone");
    assert.equal(await card.locator('[data-exception-action="open"]').isChecked(), true);
    assert.equal(await card.locator('[data-exception-action="close"]').isChecked(), true);
    await card.locator('[data-save-exception]').click();
    assert.ok((await card.locator('[data-exception-status-message]').textContent()).includes("auswählen"));
    assert.equal(await page.evaluate(() => window.__calls.length), 0);
    await card.locator('[data-exception-target="cover"][value="cover.testroom"]').check();
    await card.locator('[data-exception-field="end_date"]').fill("2026-10-03");
    await card.locator('[data-save-exception]').click();
    assert.ok((await card.locator('[data-exception-status-message]').textContent()).includes("Startdatum"));
    await card.locator('[data-exception-field="end_date"]').fill("2026-10-08");
    await card.locator('[data-exception-field="mode"]').selectOption("times");
    assert.equal(await card.locator('[data-exception-mode-fields="pause"]').isVisible(), false);
    await card.locator('[data-save-exception]').click();
    assert.ok((await card.locator('[data-exception-status-message]').textContent()).includes("Fahrzeit"));
    await card.locator('[data-exception-field="open_time"]').fill("10:30");
    await page.evaluate(() => { window.__failSave = true; });
    await card.locator('[data-save-exception]').click();
    await card.locator('[data-exception-status-message]').filter({ hasText: "Simulated save failure" }).waitFor();
    assert.equal(await card.locator('[data-exception-field="open_time"]').inputValue(), "10:30");
    await page.evaluate(() => { window.__failSave = false; window.__conflict = true; });
    await card.locator('[data-save-exception]').click();
    await card.locator('[data-exception-status-message]').filter({ hasText: "überschneiden" }).waitFor();
    assert.ok((await card.locator('[data-exception-status-message]').textContent()).includes("Guest area"));
    await card.locator('[data-exception-field="mode"]').selectOption("pause");
    await card.locator('[data-exception-field="mode"]').selectOption("times");
    assert.equal(await card.locator('[data-exception-field="open_time"]').inputValue(), "10:30", "Mode switches preserve the draft");
    assert.equal(await page.evaluate(() => {
      const body = document.getElementById("card").shadowRoot.querySelector(".body");
      return body.scrollWidth <= body.clientWidth;
    }), true, "Narrow forms do not overflow");
    await page.evaluate(() => { window.__conflict = false; });
    await card.locator('[data-save-exception]').click();
    await card.locator('[data-exception-edit="created"]').waitFor();
    assert.equal(await card.locator('[data-exception-status="created"]').textContent(), "Aktiv");
    await card.locator('[data-exception-edit="created"]').click();
    assert.equal(await card.locator('[data-exception-field="open_time"]').inputValue(), "10:30");
    await card.locator('[data-exception-field="open_time"]').fill("11:00");
    await card.locator('[data-save-exception]').click();
    await card.locator('[data-exception-edit="created"]').waitFor();
    assert.equal(await page.evaluate(() => window.__rules.find((r) => r.id === "created").open_time), "11:00");
    await card.locator('[data-exception-delete="created"]').click();
    await card.locator('[data-exception-edit="created"]').waitFor({ state: "detached" });
    assert.equal(await card.locator('[data-toggle-area-section="detail-exceptions-global"]').count(), 0);
    await page.evaluate(() => {
      window.__rules.push(...Array.from({ length: 12 }, (_, index) => {
        const day = String(5 + index).padStart(2, "0");
        const nextDay = String(6 + index).padStart(2, "0");
        return { id: `rolling_${index}`, cover_ids: ["cover.testroom"], area_ids: [], start_date: `2026-10-${day}`,
          end_date: `2026-10-${nextDay}`, mode: "pause", actions: ["open"], open_time: null, close_time: null };
      }));
    });
    await page.clock.fastForward(17 * 24 * 60 * 60 * 1000);
    await card.locator('[data-exception-edit="rolling_11"][data-exception-reactivate]').waitFor({ timeout: 5000 });
    assert.equal(await card.locator('[data-exception-edit="rolling_0"]').count(), 0, "Midnight refresh reflects the ten-entry backend history cap");
    assert.equal(await card.locator('[data-exception-status^="rolling_"]').count(), 10);
    assert.equal(await card.locator('[data-exception-status="rolling_11"]').textContent(), "Abgelaufen");
    await card.locator('[data-exception-edit="rolling_11"][data-exception-reactivate]').click();
    assert.equal(await card.locator('[data-exception-field="start_date"]').inputValue(), "2026-10-21");
    assert.equal(await card.locator('[data-exception-field="end_date"]').inputValue(), "2026-10-22");
    await card.locator('[data-save-exception]').click();
    await card.locator("[data-exception-form]").waitFor({ state: "detached" });
    assert.equal((await page.evaluate(() => window.__rules.find((r) => r.id === "rolling_11").start_date)), "2026-10-21");
    console.log("OK - date rollover refreshes the list, retains only ten expired rules, and reactivates one");
    console.log("OK - dates, status, escaped names, validation, mode changes, failure/retry, conflicts, edit/delete, narrow form");

    await card.locator('[data-settings-nav="settings-schedules"]').click();
    assert.equal(await card.locator("h2").textContent(), "Wiederkehrende Zeitprofile");
    assert.ok((await card.locator(".body").textContent()).includes("Existing recurring profile"));
    await card.locator('[data-nav="list"]').click();
    await card.locator('[data-open-detail="dev_testroom"]').click();
    await card.locator('[data-tab="advanced"]').click();
    const shutterExceptions = card.locator('.section-toggle[data-toggle-area-section="detail-exceptions-cover.testroom"]');
    assert.equal(await shutterExceptions.count(), 1, "Per-shutter exceptions live in Advanced settings");
    assert.equal(await card.locator('[data-temporal-exception-section][data-temporal-cover="cover.testroom"]').getAttribute("class"), null, "Per-shutter exceptions share the flat accordion style");
    const advancedOrder = await card.evaluate((el) => {
      const root = el.shadowRoot;
      const inherited = [...root.querySelectorAll("h3")].find((heading) => heading.textContent.includes("Übernommen von Global"));
      const exceptions = root.querySelector('[data-temporal-exception-section][data-temporal-cover="cover.testroom"]');
      const profiles = root.querySelector('[data-toggle-area-section="detail-profiles-cover.testroom"]');
      const follows = (first, second) => !!(first && second && (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING));
      return { inheritedBeforeExceptions: follows(inherited, exceptions), exceptionsBeforeProfiles: follows(exceptions, profiles) };
    });
    assert.deepEqual(advancedOrder, { inheritedBeforeExceptions: true, exceptionsBeforeProfiles: true }, "Inherited summary is high in Advanced, with exceptions directly above own profiles");
    assert.equal(await card.locator('[data-exception-status="active"]').count(), 0, "Per-shutter exception list starts collapsed");
    await shutterExceptions.click();
    await card.locator('[data-exception-edit="__new__"]').click();
    assert.equal(await card.locator('[data-exception-target="cover"][value="cover.testroom"]').isChecked(), true);
    await card.locator('[data-exception-back]').click();
    assert.equal(await card.locator('[data-tab="basic"]').count(), 1);

    await page.evaluate(async () => {
      window.__hass.language = "en";
      window.__hass.user.is_admin = false;
      const card = document.getElementById("card");
      await card._loadBackendConfig();
      card._view = "settings";
      card._render();
    });
    await card.locator('[data-settings-nav="settings-exceptions"]').click();
    const guestGlobalExceptions = card.locator('[data-toggle-area-section="detail-exceptions-global"]');
    assert.equal(await guestGlobalExceptions.count(), 0, "The guest Settings page also displays exceptions without an accordion");
    assert.match(await card.locator('[data-temporal-exception-section] h3').textContent(), /Zeitliche Ausnahmen|Temporal exceptions/);
    assert.equal(await card.locator('[data-exception-edit="active"]').count(), 0, "Host exceptions are hidden from guests");
    await card.locator('[data-exception-edit="__new__"]').click();
    assert.equal(await card.locator('[data-exception-target="cover"]').count(), 0);
    await card.locator('[data-exception-target="area"][value="guest"]').check();
    await card.locator('[data-exception-action="close"]').uncheck();
    await card.locator('[data-save-exception]').click();
    await card.locator('[data-exception-edit="created"]').waitFor();
    const saved = await page.evaluate(() => window.__calls.at(-1).exception);
    assert.deepEqual(saved.area_ids, ["guest"]);
    assert.deepEqual(saved.cover_ids, []);
    assert.deepEqual(saved.actions, ["open"]);
    await page.evaluate(async () => {
      window.__hass.user.is_admin = true;
      const card = document.getElementById("card");
      await card._loadBackendConfig();
      card._render();
    });
    await card.locator('[data-settings-back]').click();
    await card.locator('[data-settings-nav="settings-areas"]').click();
    await card.locator('[data-area-edit="guest"]').click();
    const areaExceptions = card.locator('[data-toggle-area-section="detail-exceptions-guest"]');
    assert.equal(await card.locator('[data-temporal-exception-section][data-temporal-area="guest"]').getAttribute("class"), null, "Area exceptions share the flat accordion style");
    assert.equal(await card.locator('[data-exception-edit="__new__"]').count(), 0, "Area exception actions also start inside the collapsed section");
    await areaExceptions.click();
    await card.locator('[data-exception-edit="__new__"]').click();
    assert.equal(await card.locator('[data-exception-target="area"][value="guest"]').isChecked(), true);
    await card.locator('[data-exception-back]').click();
    await card.locator('[data-area-member]:not(:checked)').first().check();
    await page.evaluate(() => { window.__areaConflict = true; });
    await card.locator('[data-area-save]').click();
    const areaStatus = card.locator('[data-save-status]');
    await areaStatus.filter({ hasText: "overlapping timed exceptions" }).waitFor();
    assert.equal(await page.evaluate(() => window.__areaAssignmentWrites.length), 1,
      "The area editor submits the changed membership before displaying the conflict");
    assert.deepEqual(await page.evaluate(() => window.__services), []);
    assert.deepEqual(errors, []);
    console.log("OK - existing profiles, shutter/area entrypoints, preselection, English, guest scope, area conflict message; no cover services");
  } finally { await browser.close(); }
}

main().catch((error) => { console.error(error); process.exit(1); });
