#!/usr/bin/env node
"use strict";
// Genuine browser checks on a managed local instance. Tokens stay in memory.
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
if (!process.env.PLAYWRIGHT_BROWSERS_PATH && fs.existsSync(path.join(root, ".playwright-browsers"))) {
  process.env.PLAYWRIGHT_BROWSERS_PATH = path.join(root, ".playwright-browsers");
}
const { chromium } = require("playwright");
const mode = process.argv[2];
const agent = process.argv[3];
if (!["test", "dev"].includes(mode) || (mode === "dev" && !/^[a-z0-9][a-z0-9_-]{0,47}$/.test(agent || ""))) {
  console.error("Usage: node scripts/ha_ui_check.cjs test | dev <agent>");
  process.exit(1);
}
const result = spawnSync("python3", [path.join(__dirname, "ha_local.py"), mode, "status", ...(agent ? [agent] : [])], { encoding: "utf8" });
if (result.status !== 0) { console.error(result.stderr); process.exit(1); }
const state = JSON.parse(result.stdout);
if (!state.url) { console.error("Instance is stopped"); process.exit(1); }
const creds = JSON.parse(fs.readFileSync(path.join(state.runtime, "credentials.json")));
const output = path.join(state.runtime, "review-artifacts");
fs.mkdirSync(output, { recursive: true, mode: 0o700 });
const virtual = new Set(["cover.codex_ui_test_alpha", "cover.codex_ui_test_beta", "cover.codex_ui_test_gamma"]);
const reads = new Set(["auth", "auth/features", "auth/current_user", "http/config", "ping", "get_config", "get_states", "get_services",
  "get_panels", "subscribe_events", "unsubscribe_events", "subscribe_entities", "frontend/get_themes", "frontend/get_translations",
  "frontend/get_user_data", "frontend/subscribe_user_data", "frontend/subscribe_system_data", "config/entity_registry/list",
  "config/entity_registry/list_for_display", "config/device_registry/list", "config/area_registry/list", "config/floor_registry/list",
  "config/label_registry/list", "config/category_registry/list", "config/auth/list", "lovelace/config", "lovelace/dashboards/list",
  "config_entries/get", "supported_features", "repairs/list_issues", "recorder/info", "lovelace/resources", "brands/access_token",
  "labs/subscribe", "persistent_notification/subscribe", "integration_manifest/list", "system_health/info", "assist_pipeline/pipeline/list",
  "smart_shutter/get_config", "smart_shutter/get_available_covers", "smart_shutter/get_forecast", "smart_shutter/get_event_history"]);

async function main() {
  const response = await fetch(state.url + "/auth/token", { method: "POST", body: new URLSearchParams({
    grant_type: "refresh_token", refresh_token: creds.refresh_token, client_id: creds.client_id,
  }) });
  assert.equal(response.ok, true, "Local token refresh succeeds");
  const token = (await response.json()).access_token;
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: "de-DE", hasTouch: true, serviceWorkers: "block" });
  const blocked = [], errors = [];
  await context.addInitScript(({ token, url }) => {
    delete Navigator.prototype.serviceWorker;
    localStorage.setItem("hassTokens", JSON.stringify({ hassUrl: url, access_token: token, token_type: "Bearer",
      expires_in: 1800, expires: Date.now() + 1800000 }));
  }, { token, url: state.url });
  await context.route("**/*", route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== state.url || !["GET", "HEAD"].includes(request.method())) {
      blocked.push({ transport: "http", method: request.method(), path: url.pathname });
      return route.abort();
    }
    return route.continue();
  });
  await context.routeWebSocket(/\/api\/websocket$/, ws => {
    const server = ws.connectToServer();
    ws.onMessage(message => {
      let data;
      try { data = JSON.parse(String(message)); } catch { return; }
      // This default check is read-only. Interactive movement checks must explicitly
      // validate registry platform + virtual IDs before enabling any service writes.
      if (!reads.has(data.type)) {
        blocked.push({ transport: "ws", type: data.type });
        if (data.id !== undefined) ws.send(JSON.stringify({ id: data.id, type: "result", success: false,
          error: { code: "local_review_read_only", message: "Writes disabled in baseline UI check" } }));
        return;
      }
      server.send(message);
    });
    server.onMessage(message => ws.send(message));
  });
  const page = await context.newPage();
  page.on("pageerror", err => errors.push(String(err.message).replaceAll(token, "[redacted]")));
  try {
    await page.goto(state.url + "/smart-shutter", { waitUntil: "domcontentloaded", timeout: 60000 });
    const card = page.locator("smart-shutter-card").first();
    await card.locator('[data-nav="settings"]').waitFor({ timeout: 60000 });
    await page.locator("#ha-launch-screen").waitFor({ state: "hidden", timeout: 30000 });
    await page.screenshot({ path: path.join(output, "overview-desktop.png"), fullPage: true });
    await card.locator('[data-nav="list"]').first().click();
    const configuredShutters = await card.evaluate(el => el._model.shutters.length);
    assert.ok(configuredShutters > 0 && configuredShutters <= 3);
    assert.equal(await card.locator("[data-open-detail]").count(), configuredShutters);
    const ids = await page.evaluate(() => Object.keys(document.querySelector("home-assistant").hass.states).filter(id => id.startsWith("cover.")));
    assert.equal(ids.every(id => virtual.has(id)) && ids.length === 3, true);
    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-shutters"]').click();
    await card.locator("[data-managed-cover]").first().waitFor();
    assert.equal(await card.locator("[data-managed-cover]").count(), 3);
    await verifyInfoPopover(page, card, "Rollläden auswählen", path.join(output, "info-popover-desktop.png"));
    await page.screenshot({ path: path.join(output, "management-desktop.png"), fullPage: true });

    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-exceptions"]').click();
    const globalToggle = card.locator('.section-toggle[data-toggle-area-section="detail-exceptions-global"]');
    assert.equal(await globalToggle.count(), 0, "The dedicated Settings page shows exceptions without an accordion");
    const globalSection = card.locator('[data-temporal-exception-section]');
    await globalSection.locator("h3").waitFor();
    assert.match(await globalSection.locator("h3").textContent(), /Zeitliche Ausnahmen|Temporal exceptions/);
    const addException = card.locator('[data-exception-edit="__new__"]');
    await addException.waitFor();
    await page.screenshot({ path: path.join(output, "exceptions-settings-desktop.png"), fullPage: true });

    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-triggers"]').click();
    const externalTriggerInfo = card.locator("[data-info-toggle]").first();
    await assertInfoBesideHeading(externalTriggerInfo, "Externe Auslöser");
    await externalTriggerInfo.click();
    assert.equal(await externalTriggerInfo.getAttribute("aria-expanded"), "true");
    await assertPopoverInViewport(card.locator('[role="tooltip"]').first());
    await page.screenshot({ path: path.join(output, "external-triggers-desktop.png"), fullPage: true });
    await page.keyboard.press("Escape");
    assert.equal(await externalTriggerInfo.getAttribute("aria-expanded"), "false");

    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(400);
    assert.equal(await card.locator(".body").evaluate(el => el.scrollWidth <= el.clientWidth), true);
    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-exceptions"]').click();
    await page.screenshot({ path: path.join(output, "exceptions-settings-mobile.png"), fullPage: true });

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.waitForTimeout(300);
    await card.locator('[data-nav="list"]').first().click();
    await card.locator("[data-open-detail]").first().click();
    await card.locator('[data-tab="advanced"]').click();
    const shutterExceptions = card.locator('.section-toggle[data-toggle-area-section^="detail-exceptions-cover."]');
    assert.equal(await shutterExceptions.count(), 1, "Per-shutter exceptions are available in Advanced settings");
    assert.equal(await card.locator('[data-exception-edit="__new__"]').count(), 0, "Per-shutter exceptions start collapsed too");
    await shutterExceptions.click();
    await card.locator('[data-exception-edit="__new__"]').waitFor();
    await shutterExceptions.click();
    assert.equal(await card.locator('[data-exception-edit="__new__"]').count(), 0, "Per-shutter exception actions collapse with the list");
    await page.screenshot({ path: path.join(output, "shutter-exceptions-desktop.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(400);
    assert.equal(await card.locator(".body").evaluate(el => el.scrollWidth <= el.clientWidth), true);
    await shutterExceptions.click();
    await card.locator('[data-exception-edit="__new__"]').waitFor();
    await shutterExceptions.click();
    assert.equal(await card.locator('[data-exception-edit="__new__"]').count(), 0);
    await page.screenshot({ path: path.join(output, "shutter-exceptions-mobile.png"), fullPage: true });

    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-triggers"]').click();
    const mobileTriggerInfo = card.locator("[data-info-toggle]").first();
    await assertInfoBesideHeading(externalTriggerInfo, "Externe Auslöser");
    await assertInfoBesideHeading(mobileTriggerInfo, "Externe Auslöser");
    await mobileTriggerInfo.tap();
    assert.equal(await mobileTriggerInfo.getAttribute("aria-expanded"), "true");
    await assertPopoverInViewport(card.locator('[role="tooltip"]').first());
    await page.screenshot({ path: path.join(output, "external-triggers-mobile.png"), fullPage: true });
    await card.locator("h2").tap();
    assert.equal(await card.locator('[role="tooltip"]').first().isHidden(), true);

    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-shutters"]').click();
    await card.locator("[data-managed-cover]").first().waitFor();
    const mobileTrigger = card.locator("[data-info-toggle]").first();
    const mobilePopover = card.locator('[role="tooltip"]').first();
    await mobileTrigger.tap();
    assert.equal(await mobileTrigger.getAttribute("aria-expanded"), "true");
    await assertPopoverInViewport(mobilePopover);
    await page.screenshot({ path: path.join(output, "info-popover-mobile.png"), fullPage: true });
    await card.locator("h2").tap();
    assert.equal(await mobilePopover.isHidden(), true, "Outside tap closes the information popover");
    await page.screenshot({ path: path.join(output, "management-mobile.png"), fullPage: true });

    await card.evaluate(el => { el._restricted = true; el._view = "overview"; el._render(); });
    const guestHint = card.locator(".ssm-inline-hint");
    const guestInfo = guestHint.locator("[data-info-toggle]");
    const guestPopover = guestHint.locator('[role="tooltip"]');
    assert.equal(await guestHint.locator(".ssm-inline-hint-label").textContent(), "Nutze die Automatikschalter in deinem Bereich.");
    assert.equal(await guestInfo.getAttribute("aria-label"), "Weitere Informationen");
    await guestInfo.tap();
    assert.equal(await guestInfo.getAttribute("aria-expanded"), "true");
    assert.match(await guestPopover.textContent(), /globale Automatiksteuerung wirkt sich auf ALLE Rollläden/);
    await assertPopoverInViewport(guestPopover);
    await page.screenshot({ path: path.join(output, "restricted-info-mobile.png"), fullPage: true });
    await card.locator(".ssm-title").tap();
    assert.equal(await guestPopover.isHidden(), true);

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.waitForTimeout(300);
    await guestInfo.click();
    assert.equal(await guestInfo.getAttribute("aria-expanded"), "true");
    await assertPopoverInViewport(guestPopover);
    await page.screenshot({ path: path.join(output, "restricted-info-desktop.png"), fullPage: true });
    await card.locator(".ssm-title").click();
    assert.equal(await guestPopover.isHidden(), true);

    assert.deepEqual(errors, []);
    assert.deepEqual(blocked, [], "Baseline should not attempt writes or unknown requests");
    const report = { url: state.url, project: state.project, source_hash: state.source_hash,
      desktop: true, mobile: true, global_exceptions_always_visible: true, shutter_exceptions_collapsed: true, errors, blocked };
    fs.writeFileSync(path.join(output, "ui-result.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    await context.close();
    await browser.close();
  }
}

async function verifyInfoPopover(page, card, expectedText, screenshotPath) {
  const trigger = card.locator("[data-info-toggle]").first();
  const popover = card.locator('[role="tooltip"]').first();
  assert.equal(await trigger.getAttribute("aria-label"), "Weitere Informationen");
  assert.equal(await trigger.getAttribute("aria-expanded"), "false");
  assert.equal(await popover.isHidden(), true);
  await trigger.click();
  assert.equal(await trigger.getAttribute("aria-expanded"), "true");
  assert.ok((await popover.textContent()).includes(expectedText));
  await assertPopoverInViewport(popover);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await page.keyboard.press("Escape");
  assert.equal(await trigger.getAttribute("aria-expanded"), "false");
  assert.equal(await popover.isHidden(), true);
  assert.equal(await trigger.evaluate((el) => el.getRootNode().activeElement === el), true);
  await trigger.click();
  await card.locator("h2").click();
  assert.equal(await popover.isHidden(), true, "Outside click closes the information popover");
}

async function assertInfoBesideHeading(trigger, expectedHeading) {
  const layout = await trigger.evaluate((button) => {
    const row = button.closest(".ssm-info-heading-row-h2");
    const heading = row && row.querySelector("h2");
    if (!heading) return null;
    const headingRect = heading.getBoundingClientRect();
    const buttonRect = button.getBoundingClientRect();
    return { text: heading.textContent.trim(), headingRight: headingRect.right, buttonLeft: buttonRect.left };
  });
  assert.ok(layout, "The info icon is grouped with the page heading");
  assert.equal(layout.text, expectedHeading);
  assert.ok(layout.buttonLeft >= layout.headingRight, "The info icon appears to the right of the heading on the same row");
}

async function assertPopoverInViewport(popover) {
  const bounds = await popover.evaluate((el) => {
    const rect = el.getBoundingClientRect();
    const cardRect = el.getRootNode().querySelector("ha-card").getBoundingClientRect();
    return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom,
      width: window.innerWidth, height: window.innerHeight,
      cardLeft: cardRect.left, cardRight: cardRect.right };
  });
  assert.ok(bounds.left >= 0 && bounds.right <= bounds.width, "Popover stays within the viewport horizontally");
  assert.ok(bounds.top >= 0 && bounds.bottom <= bounds.height, "Popover stays within the viewport vertically");
  assert.ok(bounds.left >= bounds.cardLeft && bounds.right <= bounds.cardRight, "Popover stays within its card");
}

main().catch(error => { console.error("UI check failed: " + error.message); process.exitCode = 1; });
