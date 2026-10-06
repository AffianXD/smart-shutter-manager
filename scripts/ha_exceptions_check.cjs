#!/usr/bin/env node
"use strict";
// Test exception configuration in isolated HA; all service calls stay blocked.
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const assert = require("node:assert/strict");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const mode = process.argv[2], agent = process.argv[3];
assert.ok(mode === "test" || mode === "dev" && /^[a-z0-9][a-z0-9_-]{0,47}$/.test(agent || ""));
const status = spawnSync("python3", [path.join(__dirname, "ha_local.py"), mode, "status", ...(agent ? [agent] : [])], { encoding: "utf8" });
assert.equal(status.status, 0, status.stderr);
const instance = JSON.parse(status.stdout);
assert.ok(instance.url && !instance.review, "Use an active, unreserved local instance");
const credentials = JSON.parse(fs.readFileSync(path.join(instance.runtime, "credentials.json")));
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
  const response = await fetch(instance.url + "/auth/token", { method: "POST", body: new URLSearchParams({
    grant_type: "refresh_token", refresh_token: credentials.refresh_token, client_id: credentials.client_id,
  }) });
  assert.ok(response.ok);
  const token = (await response.json()).access_token;
  const browser = await chromium.launch();
  const context = await browser.newContext({ locale: "de-DE", viewport: { width: 1280, height: 1000 }, serviceWorkers: "block" });
  const blocked = [], errors = [], writes = [], pending = new Map(), ownedRules = new Set();
  let verified = false;
  await context.addInitScript(({ token, url }) => {
    delete Navigator.prototype.serviceWorker;
    localStorage.setItem("hassTokens", JSON.stringify({ hassUrl: url, access_token: token,
      token_type: "Bearer", expires_in: 1800, expires: Date.now() + 1800000 }));
  }, { token, url: instance.url });
  await context.route("**/*", route => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin !== instance.url || !["GET", "HEAD"].includes(request.method())) {
      blocked.push(`HTTP ${request.method()} ${url.pathname}`);
      return route.abort();
    }
    return route.continue();
  });
  await context.routeWebSocket(/\/api\/websocket$/, ws => {
    const server = ws.connectToServer();
    ws.onMessage(message => {
      const data = JSON.parse(String(message));
      const rule = data.exception;
      const save = data.type === "smart_shutter/save_temporal_exception" && verified && rule
        && rule.cover_ids.length > 0 && rule.cover_ids.every(id => virtual.has(id)) && rule.area_ids.length === 0
        && (!rule.id || ownedRules.has(rule.id));
      const remove = data.type === "smart_shutter/delete_temporal_exception" && verified && ownedRules.has(data.exception_id);
      if (!reads.has(data.type) && !save && !remove) {
        blocked.push(`WS ${data.type}`);
        if (data.id !== undefined) ws.send(JSON.stringify({ id: data.id, type: "result", success: false,
          error: { code: "local_exception_test_guard", message: "Only verified exception CRUD is enabled; services are blocked" } }));
        return;
      }
      if (save || remove) { pending.set(data.id, data.type); writes.push(data.type); }
      server.send(message);
    });
    server.onMessage(message => {
      const payload = JSON.parse(String(message));
      for (const data of Array.isArray(payload) ? payload : [payload]) {
        if (pending.get(data.id) === "smart_shutter/save_temporal_exception" && data.success && data.result?.success) {
          ownedRules.add(data.result.exception.id);
        }
        pending.delete(data.id);
      }
      ws.send(message);
    });
  });
  const page = await context.newPage();
  await page.clock.install({ time: new Date() });
  page.on("pageerror", err => errors.push(err.message.replaceAll(token, "[redacted]")));
  const output = path.join(instance.runtime, "review-artifacts");
  fs.mkdirSync(output, { recursive: true, mode: 0o700 });
  const checks = [];
  try {
    await page.goto(instance.url + "/smart-shutter", { waitUntil: "domcontentloaded", timeout: 60000 });
    const card = page.locator("smart-shutter-card").first();
    await card.locator('[data-nav="settings"]').waitFor({ timeout: 60000 });
    await page.locator("#ha-launch-screen").waitFor({ state: "hidden", timeout: 30000 });
    const proof = await page.evaluate(async () => {
      const hass = document.querySelector("home-assistant").hass;
      const registry = await hass.callWS({ type: "config/entity_registry/list" });
      const covers = Object.values(hass.states).filter(s => s.entity_id.startsWith("cover."));
      const config = await hass.callWS({ type: "smart_shutter/get_config" });
      const switches = registry.filter(e => e.platform === "smart_shutter" && e.unique_id.startsWith("smart_shutter_global_")
        && /_global_automation_(open|close)$/.test(e.unique_id)).map(e => hass.states[e.entity_id]?.state);
      return { covers: covers.map(s => ({ id: s.entity_id, virtual: s.attributes.ui_test_only,
        platform: registry.find(e => e.entity_id === s.entity_id)?.platform, position: s.attributes.current_position, state: s.state })),
        switches, rules: config.temporal_exceptions };
    });
    assert.equal(proof.covers.length, 3);
    assert.ok(proof.covers.every(c => virtual.has(c.id) && c.virtual === true && c.platform === "codex_ui_test"));
    assert.deepEqual(proof.switches, ["off", "off"]);
    assert.ok(Array.isArray(proof.rules));
    verified = true;
    checks.push("registry-verified virtual covers; global automation disabled; service calls blocked");

    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-exceptions"]').click();
    const globalExceptionToggle = card.locator('[data-toggle-area-section="detail-exceptions-global"]');
    assert.equal(await globalExceptionToggle.count(), 0, "The dedicated Settings page does not use a collapsible section");
    const globalExceptionSection = card.locator('[data-temporal-exception-section]');
    await globalExceptionSection.waitFor({ state: "visible" });
    assert.equal(await globalExceptionSection.getAttribute("class"), null, "The dedicated Settings page has no nested card frame");
    assert.equal(await card.locator('[data-exception-status]').count(), proof.rules.length, "All global exceptions are visible immediately");
    await card.locator('[data-exception-edit="__new__"]').waitFor({ state: "visible" });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await globalExceptionSection.isVisible(), true, "The Settings exception list remains visible on mobile");
    assert.equal(await globalExceptionSection.getAttribute("class"), null, "The Settings exception list stays frameless on mobile");
    assert.equal(await card.locator(".body").evaluate(el => el.scrollWidth <= el.clientWidth), true, "The Settings exception list fits the mobile viewport");
    await page.screenshot({ path: path.join(output, "exceptions-settings-mobile.png"), fullPage: true });
    await page.setViewportSize({ width: 1280, height: 1000 });
    await card.locator('[data-exception-edit="__new__"]').click();
    await card.locator('[data-save-exception]').click();
    assert.ok((await card.locator('[data-exception-status-message]').textContent()).includes("auswählen"));
    assert.equal(writes.length, 0);
    await card.locator('[data-exception-target="cover"][value="cover.codex_ui_test_alpha"]').check();
    const today = await card.locator('[data-exception-field="start_date"]').inputValue();
    await card.locator('[data-exception-field="end_date"]').fill("2000-01-01");
    await card.locator('[data-save-exception]').click();
    assert.ok((await card.locator('[data-exception-status-message]').textContent()).includes("Startdatum"));
    await card.locator('[data-exception-field="end_date"]').fill(today);
    await card.locator('[data-exception-action="close"]').uncheck();
    await card.locator('[data-save-exception]').click();
    await card.locator("[data-exception-form]").waitFor({ state: "detached" });
    const getConfig = () => page.evaluate(() => document.querySelector("home-assistant").hass.callWS({ type: "smart_shutter/get_config" }));
    let config = await getConfig();
    const created = config.temporal_exceptions.find(r => !proof.rules.some(old => old.id === r.id));
    assert.ok(created);
    assert.deepEqual(created.actions, ["open"]);
    assert.equal(await card.locator(`[data-exception-status="${created.id}"]`).textContent(), "Aktiv");
    checks.push("empty targets and inverted dates rejected; active opening-only pause saved");

    await card.locator(`[data-exception-edit="${created.id}"]`).click();
    await card.locator('[data-exception-field="mode"]').selectOption("times");
    await card.locator('[data-save-exception]').click();
    assert.ok((await card.locator('[data-exception-status-message]').textContent()).includes("Fahrzeit"));
    await card.locator('[data-exception-field="open_time"]').fill("10:30");
    assert.equal((await card.locator('[data-exception-status-message]').textContent()).trim(), "",
      "The validation message clears after entering a valid movement time");
    await card.locator('[data-exception-field="mode"]').selectOption("pause");
    await card.locator('[data-exception-field="mode"]').selectOption("times");
    assert.equal(await card.locator('[data-exception-field="open_time"]').inputValue(), "10:30");
    await page.screenshot({ path: path.join(output, "exceptions-desktop.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, "exceptions-mobile.png"), fullPage: true });
    assert.equal(await card.locator(".body").evaluate(el => el.scrollWidth <= el.clientWidth), true,
      JSON.stringify(await card.locator(".body").evaluate(el => ({ width: el.clientWidth, scroll: el.scrollWidth,
        overflow: [...el.querySelectorAll("*")].filter(child => child.getBoundingClientRect().right > el.getBoundingClientRect().right + 1)
          .map(child => ({ tag: child.tagName, field: child.dataset.exceptionField, width: child.getBoundingClientRect().width })) }))));
    await card.locator('[data-save-exception]').click();
    await card.locator("[data-exception-form]").waitFor({ state: "detached" });
    config = await getConfig();
    assert.equal(config.temporal_exceptions.find(r => r.id === created.id).open_time, "10:30");
    assert.equal(config.temporal_exceptions.find(r => r.id === created.id).close_time, null);
    checks.push("alternate-time edit persisted; unchanged closing; mode switch preserves draft; desktop/mobile");

    // Actual HA backend overlap validation, through the same form.
    await card.locator('[data-exception-edit="__new__"]').click();
    await card.locator('[data-exception-target="cover"][value="cover.codex_ui_test_alpha"]').check();
    await card.locator('[data-exception-field="mode"]').selectOption("times");
    await card.locator('[data-exception-field="open_time"]').fill("11:00");
    await card.locator('[data-save-exception]').click();
    await card.locator('[data-exception-status-message]').filter({ hasText: "überschneiden" }).waitFor();
    assert.equal((await getConfig()).temporal_exceptions.length, proof.rules.length + 1);
    await card.locator('[data-exception-back]').click();
    checks.push("backend conflict rejected without mutation");

    page.on("dialog", dialog => dialog.accept());
    await card.locator(`[data-exception-delete="${created.id}"]`).click();
    await card.locator(`[data-exception-edit="${created.id}"]`).waitFor({ state: "detached" });
    assert.deepEqual((await getConfig()).temporal_exceptions, proof.rules);

    await card.locator('[data-exception-edit="__new__"]').click();
    await card.locator('[data-exception-target="cover"][value="cover.codex_ui_test_alpha"]').check();
    const rolloverStart = await card.locator('[data-exception-field="start_date"]').inputValue();
    const rolloverEnd = await card.evaluate((el, start) => el._exceptionDateAfter(start, 1), rolloverStart);
    await card.locator('[data-exception-field="end_date"]').fill(rolloverEnd);
    await card.locator('[data-save-exception]').click();
    await card.locator("[data-exception-form]").waitFor({ state: "detached" });
    const rolloverRule = (await getConfig()).temporal_exceptions.find(r => !proof.rules.some(old => old.id === r.id));
    assert.ok(rolloverRule);
    const futureClock = new Date();
    futureClock.setDate(futureClock.getDate() + 2);
    await page.clock.setFixedTime(futureClock);
    await card.evaluate(el => el._checkTemporalExceptionDate());
    await card.locator(`[data-exception-edit="${rolloverRule.id}"][data-exception-reactivate]`).waitFor({ timeout: 10000 });
    assert.equal(await card.locator(`[data-exception-status="${rolloverRule.id}"]`).textContent(), "Abgelaufen");
    const reactivationDates = await card.evaluate(el => ({ start: el._exceptionToday(), end: el._exceptionDateAfter(el._exceptionToday(), 1) }));
    await card.locator(`[data-exception-edit="${rolloverRule.id}"][data-exception-reactivate]`).click();
    assert.equal(await card.locator('[data-exception-field="start_date"]').inputValue(), reactivationDates.start);
    assert.equal(await card.locator('[data-exception-field="end_date"]').inputValue(), reactivationDates.end);
    await card.locator('[data-save-exception]').click();
    await card.locator("[data-exception-form]").waitFor({ state: "detached" });
    assert.equal((await getConfig()).temporal_exceptions.find(r => r.id === rolloverRule.id).start_date, reactivationDates.start);
    await page.screenshot({ path: path.join(output, "exceptions-reactivated.png"), fullPage: true });
    await card.locator(`[data-exception-delete="${rolloverRule.id}"]`).click();
    await card.locator(`[data-exception-edit="${rolloverRule.id}"]`).waitFor({ state: "detached" });
    checks.push("collapsed list expands; date rollover exposes Reactivate; HA-local dates save; shutter list in Advanced");

    await page.clock.setFixedTime(new Date());
    await card.locator('[data-nav="list"]').click();
    await card.locator('[data-open-detail]').first().click();
    await card.locator('[data-tab="advanced"]').click();
    const shutterExceptions = card.locator(`[data-toggle-area-section="detail-exceptions-${proof.covers[0].id}"]`);
    await shutterExceptions.waitFor({ state: "visible" });
    assert.equal(await card.locator('[data-exception-status]').count(), 0);
    await shutterExceptions.click();
    await card.locator('[data-exception-edit="__new__"]').click();
    assert.equal(await card.locator('[data-exception-target="cover"]:checked').count(), 1);
    await card.locator('[data-exception-back]').click();
    assert.equal(await card.locator('[data-tab="basic"]').count(), 1);
    checks.push("delete restored original rules; shutter preselection and back navigation");

    const after = await page.evaluate(() => Object.values(document.querySelector("home-assistant").hass.states)
      .filter(s => s.entity_id.startsWith("cover.")).map(s => ({ id: s.entity_id, position: s.attributes.current_position, state: s.state })));
    assert.deepEqual(after, proof.covers.map(({ id, position, state }) => ({ id, position, state })));
    assert.deepEqual(errors, []);
    assert.deepEqual(blocked, []);
    const report = { url: instance.url, project: instance.project, source_hash: instance.source_hash,
      checks, exceptionWrites: writes.length, coverServiceCalls: 0, coversUnchanged: true, errors, blocked };
    fs.writeFileSync(path.join(output, "exceptions-result.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    // Own test rules are never left behind, including after a failed assertion.
    if (verified) {
      for (const id of ownedRules) {
        await page.evaluate(async id => {
          const hass = document.querySelector("home-assistant").hass;
          const config = await hass.callWS({ type: "smart_shutter/get_config" });
          if (config.temporal_exceptions.some(r => r.id === id)) await hass.callWS({ type: "smart_shutter/delete_temporal_exception", exception_id: id });
        }, id).catch(() => {});
      }
    }
    await context.close();
    await browser.close();
  }
}
main().catch(error => { console.error("Exception UI check failed: " + error.stack); process.exitCode = 1; });
