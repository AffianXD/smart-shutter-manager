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
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: "de-DE", serviceWorkers: "block" });
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
    assert.equal(await card.locator("[data-open-detail]").count(), 2);
    const ids = await page.evaluate(() => Object.keys(document.querySelector("home-assistant").hass.states).filter(id => id.startsWith("cover.")));
    assert.equal(ids.every(id => virtual.has(id)) && ids.length === 3, true);
    await card.locator('[data-nav="settings"]').click();
    await card.locator('[data-settings-nav="settings-shutters"]').click();
    await card.locator("[data-managed-cover]").first().waitFor();
    assert.equal(await card.locator("[data-managed-cover]").count(), 3);
    await page.screenshot({ path: path.join(output, "management-desktop.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(400);
    assert.equal(await card.locator(".body").evaluate(el => el.scrollWidth <= el.clientWidth), true);
    await page.screenshot({ path: path.join(output, "management-mobile.png"), fullPage: true });
    assert.deepEqual(errors, []);
    assert.deepEqual(blocked, [], "Baseline should not attempt writes or unknown requests");
    const report = { url: state.url, project: state.project, source_hash: state.source_hash, desktop: true, mobile: true, errors, blocked };
    fs.writeFileSync(path.join(output, "ui-result.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    await context.close();
    await browser.close();
  }
}
main().catch(error => { console.error("UI check failed: " + error.message); process.exitCode = 1; });
