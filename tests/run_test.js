const path = require("path");
const { chromium } = require("playwright");
const { buildFixture } = require("./fixtures");

let failures = 0;
function check(name, cond) {
  if (cond) {
    console.log(`OK   - ${name}`);
  } else {
    console.log(`FAIL - ${name}`);
    failures++;
  }
}

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on("pageerror", (err) => console.log("PAGEERROR:", err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") console.log("CONSOLE ERROR:", msg.text());
  });
  page.on("dialog", (dialog) => dialog.accept());

  await page.goto("file://" + path.join(__dirname, "test.html"));

  const fixture = buildFixture();

  // Fake hass-Objekt in der Seite installieren und der Karte zuweisen.
  await page.evaluate((fx) => {
    if (!customElements.get("ha-icon-picker")) {
      customElements.define("ha-icon-picker", class extends HTMLElement {
        get value() { return this.getAttribute("value") || ""; }
        set value(value) { this.setAttribute("value", value); }
      });
    }
    window.__serviceCalls = [];
    window.__shortcutSaveEntryIds = [];
    const states = fx.states;
    const hass = {
      states,
      language: "de",
      user: { is_admin: true },
      callWS: async (msg) => {
        if (msg.type === "config/entity_registry/list") return fx.entities;
        if (msg.type === "config/device_registry/list") return fx.devices;
        if (msg.type === "config/area_registry/list") return fx.areas;
        if (msg.type === "config/floor_registry/list") return fx.floors;
        if (msg.type === "config/auth/list") return [];
        if (msg.type === "smart_shutter/get_config")
          return {
            entry_id: "test-entry",
            covers: [fx.coverEntityId, fx.coverEntityId2],
            custom_schedules: fx.customSchedules,
            schedule_conflicts: fx.scheduleConflicts,
            external_triggers: [],
            custom_areas: window.__customAreas || [],
            shutter_areas: window.__shutterAreas || {},
            shortcuts: window.__homeShortcuts || [
              { id: "default-open", name: "All up", icon: "mdi:arrow-up-bold-circle-outline", kind: "cover", target: "all", action: "open" },
              { id: "default-stop", name: "Stop", icon: "mdi:stop-circle-outline", kind: "cover", target: "all", action: "stop" },
              { id: "default-close", name: "All down", icon: "mdi:arrow-down-bold-circle-outline", kind: "cover", target: "all", action: "close" },
            ],
          };
        if (msg.type === "smart_shutter/save_shortcuts") {
          window.__shortcutSaveEntryIds.push(msg.entry_id);
          window.__homeShortcuts = msg.shortcuts;
          return { success: true, shortcuts: msg.shortcuts };
        }
        if (msg.type === "smart_shutter/save_custom_areas") {
          for (const a of msg.areas) if (!a.id) a.id = "area_" + Math.random().toString(16).slice(2, 8);
          window.__customAreas = msg.areas;
          return { success: true };
        }
        if (msg.type === "smart_shutter/save_shutter_areas") {
          window.__shutterAreas = msg.shutter_areas;
          return { success: true };
        }
        if (msg.type === "smart_shutter/get_event_history") {
          const events = {};
          events[msg.entity_id] = fx.eventHistory[msg.entity_id] || [];
          return { events };
        }
        if (msg.type === "smart_shutter/get_forecast") {
          if (msg.entity_id) {
            return { forecast: { [msg.entity_id]: fx.forecast[msg.entity_id] || [] } };
          }
          return { forecast: fx.forecast };
        }
        return {};
      },
      callService: async (domain, service, data) => {
        window.__serviceCalls.push({ domain, service, data });
      },
      callApi: async (method, path) => {
        // Simuliert die offizielle HA-REST-History-API
        // (history/period/<start>?filter_entity_id=...&end_time=...).
        if (method === "GET" && path.startsWith("history/period/")) {
          const match = path.match(/filter_entity_id=([^&]+)/);
          const ids = match ? decodeURIComponent(match[1]).split(",") : [];
          return ids.map((id) => fx.history[id] || []);
        }
        return [];
      },
    };
    window.__hass = hass;
    const card = document.getElementById("card");
    card.setConfig({});
    card.hass = hass;
  }, fixture);

  await page.waitForTimeout(300);

  // ---------------------------------------------------------------
  // Bug 1: Stop-Button darf nur waehrend Fahrt aktiv sein UND muss
  // bei einem reinen Hintergrund-Update (kein Re-Render) sofort
  // reagieren, sobald der Cover-State auf "opening" wechselt.
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-nav="list"]').click();
  });
  await page.waitForTimeout(100);

  let stopDisabled = await page.evaluate(() => {
    const card = document.getElementById("card");
    return card.shadowRoot.querySelector('[data-quick="stop"]').disabled;
  });
  check("Bug1: Stop-Button initial deaktiviert (Cover steht/closed)", stopDisabled === true);

  await page.evaluate(() => {
    const card = document.getElementById("card");
    // Simuliert ein reines Hintergrund-Update (KEIN neues hass-Objekt-Setup,
    // nur State-Aenderung + erneuter hass-Setter, wie es HA im Betrieb tut).
    window.__hass.states["cover.testroom"] = { ...window.__hass.states["cover.testroom"], state: "opening" };
    card.hass = window.__hass;
  });
  await page.waitForTimeout(100);

  stopDisabled = await page.evaluate(() => {
    const card = document.getElementById("card");
    return card.shadowRoot.querySelector('[data-quick="stop"]').disabled;
  });
  check("Bug1: Stop-Button live aktiviert waehrend Fahrt (ohne Navigation)", stopDisabled === false);

  // ---------------------------------------------------------------
  // Bug 2: Sonnenversatz verschwindet sofort, wenn Quelle/Typ auf
  // "Uhrzeit" (effektiv nicht mehr sonnenbasiert) wechselt.
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-open-detail]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-tab="advanced"]').click();
  });
  await page.waitForTimeout(100);

  // Modus zunaechst auf "Individuell" stellen, damit die Detail-Regler sichtbar sind.
  await page.evaluate(() => {
    const card = document.getElementById("card");
    const sel = card.shadowRoot.querySelector("[data-advanced-mode-select]");
    sel.value = "local";
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(100);

  let sunOffsetVisibleBefore = await page.evaluate(() => {
    const card = document.getElementById("card");
    return !!card.shadowRoot.querySelector('h3'); // Platzhalter, echte Pruefung unten
  });

  let sunOffsetHtmlBefore = await page.evaluate(() => {
    return document.getElementById("card").shadowRoot.querySelector(".body").innerHTML.includes("<h3>Sonnenversatz</h3>");
  });
  check("Bug2: Sonnenversatz sichtbar solange Typ Sonnenaufgang (Vorbedingung)", sunOffsetHtmlBefore === true);

  await page.evaluate(() => {
    const card = document.getElementById("card");
    const typeSelect = card.shadowRoot.querySelector('select[data-type-select][data-select-entity="select.testroom_open_type"]');
    typeSelect.value = "time";
    typeSelect.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(100);
  // Auch close-Typ auf Uhrzeit, damit Abschnitt komplett verschwindet.
  await page.evaluate(() => {
    const card = document.getElementById("card");
    const typeSelect = card.shadowRoot.querySelector('select[data-type-select][data-select-entity="select.testroom_close_type"]');
    if (typeSelect) {
      typeSelect.value = "time";
      typeSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });
  await page.waitForTimeout(100);

  let sunOffsetHtmlAfter = await page.evaluate(() => {
    return document.getElementById("card").shadowRoot.querySelector(".body").innerHTML.includes("<h3>Sonnenversatz</h3>");
  });
  check("Bug2: Sonnenversatz verschwindet sofort nach Wechsel auf Uhrzeit", sunOffsetHtmlAfter === false);

  // ---------------------------------------------------------------
  // FR5: Global/Individuell-Modus-Select setzt alle 4 Quelle-Selects
  // gemeinsam und blendet Detail-Regler entsprechend ein/aus.
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    const card = document.getElementById("card");
    const sel = card.shadowRoot.querySelector("[data-advanced-mode-select]");
    sel.value = "global";
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(100);

  const globalModeState = await page.evaluate(() => {
    const hass = window.__hass;
    return {
      openSource: hass.states["select.testroom_open_source"].state,
      closeSource: hass.states["select.testroom_close_source"].state,
      openPosSource: hass.states["select.testroom_open_position_source"].state,
      closePosSource: hass.states["select.testroom_close_position_source"].state,
      showsSummary: document.getElementById("card").shadowRoot.querySelector(".body").innerHTML.includes("Übernommen von Global"),
      showsDetailSelects: !!document.getElementById("card").shadowRoot.querySelector('[data-select-entity="select.testroom_open_type"]'),
    };
  });
  check("FR5: Modus 'Global' setzt alle 4 Quelle-Selects auf Global",
    globalModeState.openSource === "global" &&
    globalModeState.closeSource === "global" &&
    globalModeState.openPosSource === "global" &&
    globalModeState.closePosSource === "global"
  );
  check("FR5: Modus 'Global' zeigt schreibgeschützte Zusammenfassung", globalModeState.showsSummary === true);
  check("FR5: Modus 'Global' blendet Detail-Regler (Typ-Select) aus", globalModeState.showsDetailSelects === false);

  // ---------------------------------------------------------------
  // FR1: Positions-Quelle + Zielposition zusammen im Advanced-Tab,
  // Zielposition editierbar bei Individuell / schreibgeschuetzt bei Global.
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    const card = document.getElementById("card");
    const sel = card.shadowRoot.querySelector("[data-advanced-mode-select]");
    sel.value = "local";
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(100);

  const fr1State = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    return {
      hasPositionSourceHeading: body.innerHTML.includes("Positions-Quelle"),
      hasEditableSlider: !!body.querySelector('input[type="range"][data-number-entity="number.testroom_open_position"]'),
    };
  });
  check("FR1: Positions-Quelle & Zielposition gemeinsam im Advanced-Tab", fr1State.hasPositionSourceHeading === true);
  check("FR1: Zielposition editierbar bei Quelle=Individuell", fr1State.hasEditableSlider === true);

  await page.evaluate(() => {
    const card = document.getElementById("card");
    const posSourceSelect = card.shadowRoot.querySelector('select[data-select-entity="select.testroom_open_position_source"]');
    posSourceSelect.value = "global";
    posSourceSelect.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(100);

  const fr1AfterGlobal = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    const readonly = body.querySelector('input[type="text"][disabled]');
    return { readonlyShown: !!readonly, readonlyValue: readonly ? readonly.value : null };
  });
  check("FR1: Zielposition schreibgeschützt (globaler Wert) bei Quelle=Global", fr1AfterGlobal.readonlyShown === true && fr1AfterGlobal.readonlyValue === "100%");

  // ---------------------------------------------------------------
  // FR3/FR4: Bulk-Postpone/-Skip vom Dashboard aus.
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-nav="overview"]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-toggle-dash-more]').click();
  });
  await page.waitForTimeout(50);

  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-bulk-postpone="close"][data-minutes="15"]').click();
  });
  await page.waitForTimeout(50);
  let calls = await page.evaluate(() => window.__serviceCalls);
  let postponeCloseCalls = calls.filter(
    (c) => c.domain === "smart_shutter" && c.service === "postpone_action" && c.data.action === "close" && c.data.minutes === 15 && c.data.source === "Bulk: all close" && !("quelle" in c.data)
  );
  check("FR3: Feste Minuten-Verschiebung (Schließen) ruft postpone_action für ALLE Rollläden auf",
    postponeCloseCalls.length === 2 &&
    postponeCloseCalls.some((c) => c.data.entity_id === "cover.testroom") &&
    postponeCloseCalls.some((c) => c.data.entity_id === "cover.testroom2")
  );

  await page.evaluate(() => {
    const card = document.getElementById("card");
    card.shadowRoot.querySelector('[data-bulk-minutes-input="open"]').value = "42";
    card.shadowRoot.querySelector('[data-bulk-postpone-custom="open"]').click();
  });
  await page.waitForTimeout(50);
  calls = await page.evaluate(() => window.__serviceCalls);
  const postponeOpenCalls = calls.filter(
    (c) => c.service === "postpone_action" && c.data.action === "open" && c.data.minutes === 42 && c.data.source === "Bulk: all open" && !("quelle" in c.data)
  );
  check("FR4: Freie Minutenangabe (Öffnen) ruft postpone_action für ALLE Rollläden auf", postponeOpenCalls.length === 2);

  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-bulk-skip="close"]').click();
  });
  await page.waitForTimeout(50);
  calls = await page.evaluate(() => window.__serviceCalls);
  const skipCalls = calls.filter((c) => c.service === "skip_action" && c.data.action === "close" && c.data.source === "Bulk: all close" && !("quelle" in c.data));
  check("FR3: 'Heute überspringen' ruft skip_action für ALLE Rollläden auf", skipCalls.length === 2);

  // ---------------------------------------------------------------
  // FR12/13: Vorhersage-Zeitstrahl (Zukunft, eigene Berechnung, siehe
  // scheduler.compute_forecast) + Ereignisverlauf im 'Verlauf'-Tab.
  // HINWEIS: native Vergangenheits-Historie wurde in v0.15.2 komplett
  // entfernt (schlechte/unuebersichtliche Optik, siehe README
  // Changelog) - nur noch Vorhersage + Ereignisverlauf-Tabelle.
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-nav="list"]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector("[data-open-detail]").click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-tab="verlauf"]').click();
  });
  await page.waitForTimeout(300); // 2 Ladeaufrufe (Verlauf-Events + Vorhersage) + Re-Render abwarten

  const historyState = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    return {
      hasTimeline: !!body.querySelector(".native-forecast-section .timeline"),
      hasMarker: !!body.querySelector(".native-forecast-section .tl-marker"),
      hasTable: body.innerHTML.includes("Ereignisverlauf"),
      hasPrenotifyRow: body.innerHTML.includes("Vorwarnung"),
      hasExecutedRow: body.innerHTML.includes("Ausgeführt"),
    };
  });
  check("FR12: Vorhersage-Zeitstrahl mit Marker(n) für kommende Termine gerendert", historyState.hasTimeline && historyState.hasMarker);
  check("FR13: Ereignisverlauf-Tabelle mit Vorwarnung- und Ausführungs-Eintrag", historyState.hasTable && historyState.hasPrenotifyRow && historyState.hasExecutedRow);

  // Regressionstest: Vorhersage-Marker im Verlauf-Tab muessen anklickbar
  // sein und Detailtext anzeigen (Bugreport: "Verlauf ist nicht anklickbar").
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector("[data-shutter-tl-marker]").click();
  });
  const shutterTlDetailHtml = await page.evaluate(
    () => document.getElementById("card").shadowRoot.querySelector(".body").innerHTML
  );
  check(
    "Vorhersage-Marker im Verlauf-Tab anklickbar, zeigt Detail (Regressionstest)",
    /Öffnen|Schließen/.test(shutterTlDetailHtml) &&
      !!(await page.evaluate(() =>
        document.getElementById("card").shadowRoot.querySelector(".tl-marker.tl-selected")
      ))
  );

  // ---------------------------------------------------------------
  // Vorhersage-Zeitstrahl - Dashboard: eigene Vorhersage-Sektion
  // (7 Tages-Spalten). Native Historie hier ebenfalls entfernt.
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-nav="overview"]').click();
  });
  await page.waitForTimeout(300); // WS-Ladeaufruf smart_shutter/get_forecast + Re-Render abwarten

  const dashboardState = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    return {
      hasForecastDayColumns: body.querySelectorAll(".native-forecast-section .native-timeline-day").length,
      hasMarker: !!body.querySelector(".native-forecast-section .tl-marker"),
    };
  });
  check("Dashboard: 7 Vorhersage-Tages-Spalten gerendert", dashboardState.hasForecastDayColumns === 7);
  check("Dashboard: mindestens ein Vorhersage-Marker gerendert", dashboardState.hasMarker);

  // ---------------------------------------------------------------
  // Dashboard-Redesign: "Alle Rollläden"-Liste entfernt, dafür
  // Schnellzugriff-Kacheln (Hoch/Stopp/Runter, globale Automatik,
  // Bereiche-Shortcut).
  // ---------------------------------------------------------------
  const dashRedesignState = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    return {
      hasOldShutterList: !!body.querySelector("[data-overview-shutter-list]"),
      hasQuickOpen: !!body.querySelector('.ssm-shortcut-grid [data-custom-shortcut="default-open"]'),
      hasQuickStop: !!body.querySelector('.ssm-shortcut-grid [data-custom-shortcut="default-stop"]'),
      hasQuickClose: !!body.querySelector('.ssm-shortcut-grid [data-custom-shortcut="default-close"]'),
      hasAutomationToggle: !!body.querySelector(".ssm-automation-card .switch-toggle"),
      hasAreasShortcut: !!body.querySelector('[data-settings-nav="settings-areas"].ssm-nav-card'),
      hasListShortcut: !!body.querySelector('[data-nav="list"].ssm-nav-card'),
    };
  });
  check("Dashboard-Redesign: alte 'Alle Rollläden'-Liste ist weg", !dashRedesignState.hasOldShutterList);
  check("Dashboard-Redesign: Hoch/Stopp/Runter-Schnellzugriff vorhanden", dashRedesignState.hasQuickOpen && dashRedesignState.hasQuickStop && dashRedesignState.hasQuickClose);
  check("Dashboard-Redesign: globaler Automatik-Toggle direkt sichtbar", dashRedesignState.hasAutomationToggle);
  check("Dashboard-Redesign: Bereiche-Shortcut vorhanden", dashRedesignState.hasAreasShortcut);
  check("Dashboard-Redesign: 'Alle Rollläden'-Shortcut zur Liste vorhanden", dashRedesignState.hasListShortcut);

  await page.evaluate(() => {
    const root = document.getElementById("card").shadowRoot;
    root.querySelector('[data-settings-nav="settings-shortcuts"]').click();
    root.querySelector('[data-shortcut-edit="__new__"]').click();
    window.__shortcutIconPickerTag = root.querySelector('[data-shortcut-field="icon"]').tagName;
    const action = root.querySelector('[data-shortcut-field="action"]');
    action.value = "stop";
    const kind = root.querySelector('[data-shortcut-field="kind"]');
    kind.value = "skip";
    kind.dispatchEvent(new Event("change", { bubbles: true }));
    window.__shortcutActionAfterTypeChange = {
      value: action.value,
      hasStop: Array.from(action.options).some((option) => option.value === "stop"),
    };
    root.querySelector("[data-shortcut-back]").click();
    root.querySelector('[data-shortcut-edit="__new__"]').click();
    root.querySelector('[data-shortcut-field="name"]').value = "Test shortcut";
    root.querySelector('[data-shortcut-field="icon"]').value = "mdi:weather-sunny";
    root.querySelector('[data-shortcut-save]').click();
  });
  await page.waitForTimeout(150);
  const shortcutActionChange = await page.evaluate(() => window.__shortcutActionAfterTypeChange);
  check("Startseiten-Shortcuts: Typwechsel setzt unzulässige Aktion zurück", shortcutActionChange.value === "open" && !shortcutActionChange.hasStop);
  const customShortcutSaved = await page.evaluate(() => {
    const card = document.getElementById("card");
    return window.__homeShortcuts.length === 4 && window.__homeShortcuts.at(-1).icon === "mdi:weather-sunny" &&
      card._view === "settings-shortcuts" &&
      window.__shortcutSaveEntryIds.at(-1) === "test-entry";
  });
  check("Startseiten-Shortcuts: neuen Shortcut in der HA-Instanz-Konfiguration speichern", customShortcutSaved);
  check("Startseiten-Shortcuts: MDI-Icon als auswählbarer Home-Assistant-Picker", await page.evaluate(() => window.__shortcutIconPickerTag === "HA-ICON-PICKER"));
  await page.evaluate(() => {
    const root = document.getElementById("card").shadowRoot;
    root.querySelector('[data-nav="overview"]').click();
  });
  await page.waitForTimeout(50);
  const customShortcutButton = await page.evaluate(() => !!document.getElementById("card").shadowRoot.querySelector('.ssm-shortcut-grid [data-custom-shortcut][aria-label="Test shortcut"]'));
  check("Startseiten-Shortcuts: gespeicherter Shortcut erscheint dynamisch auf der Startseite", customShortcutButton);
  const staleShortcutTarget = await page.evaluate(() => {
    const card = document.getElementById("card");
    const saved = card._backendConfig.shortcuts;
    card._backendConfig.shortcuts = [...saved, {
      id: "stale-area-shortcut", name: "Old area", icon: "mdi:home", kind: "cover",
      target: "deleted-area", action: "open",
    }];
    card._view = "settings-shortcuts";
    card._render();
    card.shadowRoot.querySelector('[data-shortcut-edit="stale-area-shortcut"]').click();
    const target = card.shadowRoot.querySelector('[data-shortcut-field="target"]');
    const state = { value: target.value, unavailable: target.selectedOptions[0].textContent };
    card._backendConfig.shortcuts = saved;
    card._view = "overview";
    card._render();
    return state;
  });
  check("Startseiten-Shortcuts: gelöschter Bereich wird beim Bearbeiten nicht zu Alle umgedeutet",
    staleShortcutTarget.value === "deleted-area" && staleShortcutTarget.unavailable.includes("nicht mehr verfügbar"));

  // Verschieben/Überspringen-Blöcke standardmäßig eingeklappt, per
  // Klick aufklappbar. Zustand explizit zurücksetzen (ein früherer
  // Testblock - FR3/FR4 - hat ihn bereits aufgeklappt, um die
  // Bulk-Postpone-Buttons zu erreichen).
  await page.evaluate(() => {
    const card = document.getElementById("card");
    card._dashMoreActionsExpanded = false;
    card._render();
  });
  const moreActionsHiddenInitially = await page.evaluate(
    () => !document.getElementById("card").shadowRoot.querySelector('[data-bulk-postpone="close"]')
  );
  check("Dashboard-Redesign: 'Weitere Aktionen' initial eingeklappt", moreActionsHiddenInitially);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector("[data-toggle-dash-more]").click();
  });
  await page.waitForTimeout(50);
  const moreActionsShownAfterToggle = await page.evaluate(
    () => !!document.getElementById("card").shadowRoot.querySelector('[data-bulk-postpone="close"]')
  );
  check("Dashboard-Redesign: 'Weitere Aktionen' nach Klick sichtbar", moreActionsShownAfterToggle);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector("[data-toggle-dash-more]").click();
  });
  await page.waitForTimeout(50);

  // ---------------------------------------------------------------
  // Aufklappbare Termin-Liste (Ergänzung zur Zeitleiste bei eng
  // beieinander liegenden Terminen, z.B. Bereich mit 10-Min-Versatz).
  // ---------------------------------------------------------------
  const listInitiallyHidden = await page.evaluate(
    () => !document.getElementById("card").shadowRoot.querySelector(".forecast-list-table")
  );
  check("Dashboard: Termin-Liste initial eingeklappt", listInitiallyHidden);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-toggle-forecast-list="global"]').click();
  });
  await page.waitForTimeout(50);
  const dashboardListState = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    const table = body.querySelector(".forecast-list-table");
    return { hasTable: !!table, rowCount: table ? table.querySelectorAll("tr").length - 1 : 0 };
  });
  check("Dashboard: Klick auf Toggle zeigt Termin-Liste mit Zeilen", dashboardListState.hasTable && dashboardListState.rowCount > 0);

  // Per-Rollladen Verlauf-Tab: dieselbe Liste, eigener Toggle-Zustand.
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-nav="list"]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector("[data-open-detail]").click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-tab="verlauf"]').click();
  });
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-toggle-forecast-list="shutter"]').click();
  });
  await page.waitForTimeout(50);
  const shutterListState = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    const table = body.querySelector(".forecast-list-table");
    return { hasTable: !!table, rowCount: table ? table.querySelectorAll("tr").length - 1 : 0 };
  });
  check("Verlauf-Tab: Klick auf Toggle zeigt Termin-Liste mit Zeilen", shutterListState.hasTable && shutterListState.rowCount > 0);

  // ---------------------------------------------------------------
  // Gestaffelte Befehlsausgabe: "Alle Rollläden hoch/runter/Stopp".
  // Default (stagger_delay_ms=0): unveraendert EIN Sammel-Call mit
  // allen entity_ids. Mit gesetztem Delay: einzelne Calls gestaffelt.
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-nav="list"]').click();
  });
  await page.waitForTimeout(100);
  let callsBeforeBulkAll = (await page.evaluate(() => window.__serviceCalls)).length;
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-bulk="open"]').click();
  });
  await page.waitForTimeout(50);
  let bulkAllCalls = (await page.evaluate(() => window.__serviceCalls)).slice(callsBeforeBulkAll);
  check(
    "Gestaffelte Ausgabe AUS (Default): 'Alle hoch' ist EIN Sammel-Call mit allen entity_ids",
    bulkAllCalls.length === 1 && Array.isArray(bulkAllCalls[0].data.entity_id) && bulkAllCalls[0].data.entity_id.length === 2
  );

  await page.evaluate(() => {
    const card = document.getElementById("card");
    card._backendConfig.basic_settings = card._backendConfig.basic_settings || {};
    card._backendConfig.basic_settings.stagger_delay_ms = 150;
    for (const id of ["cover.testroom", "cover.testroom2"]) {
      window.__hass.states[id] = {
        ...window.__hass.states[id],
        state: "open",
        attributes: { ...window.__hass.states[id].attributes, current_position: 100 },
      };
    }
    card.hass = window.__hass;
  });
  callsBeforeBulkAll = (await page.evaluate(() => window.__serviceCalls)).length;
  const staggerStart = Date.now();
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-bulk="close"]').click();
  });
  await page.waitForTimeout(400); // 2 Rollläden x 150ms + Puffer abwarten
  const staggerElapsed = Date.now() - staggerStart;
  bulkAllCalls = (await page.evaluate(() => window.__serviceCalls)).slice(callsBeforeBulkAll);
  check(
    "Gestaffelte Ausgabe AN (150ms): 'Alle runter' erzeugt EINZELNE Calls (einer je Rollladen), nicht einen Sammel-Call",
    bulkAllCalls.length === 2 && bulkAllCalls.every((c) => !Array.isArray(c.data.entity_id))
  );
  check(
    "Gestaffelte Ausgabe AN: es wird tatsächlich gewartet (>=140ms verstrichen, nicht sofort)",
    staggerElapsed >= 140
  );
  await page.evaluate(() => {
    document.getElementById("card")._backendConfig.basic_settings.stagger_delay_ms = 0;
  });
  await page.waitForTimeout(50);

  // ---------------------------------------------------------------
  // FR15: Dauerhafte Konfliktanzeige bei Custom-Profilen.
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-nav="settings"]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-settings-nav="settings-exceptions"]').click();
    document.getElementById("card").shadowRoot.querySelector('[data-settings-nav="settings-schedules"]').click();
  });
  await page.waitForTimeout(100);

  const conflictState = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    const badges = body.querySelectorAll(".conflict-badge");
    return { badgeCount: badges.length };
  });
  check("FR15: Beide sich überschneidenden Custom-Profile zeigen dauerhafte Konflikt-Badge", conflictState.badgeCount === 2);

  // ---------------------------------------------------------------
  // FR16: Bulk-Editing von Einstellungen mehrerer Rollläden.
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-nav="list"]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector("[data-bulk-edit-toggle]").click();
  });
  await page.waitForTimeout(100);

  const checkboxCount = await page.evaluate(() => {
    return document.getElementById("card").shadowRoot.querySelectorAll("[data-bulk-select]").length;
  });
  check("FR16: Checkboxen erscheinen für beide Rollläden im Bulk-Edit-Modus", checkboxCount === 2);

  await page.evaluate(async () => {
    const card = document.getElementById("card");
    // Nach jedem Klick rendert die Karte komplett neu (structural
    // render), die vorherige NodeList wäre also stale - deshalb nach
    // jedem Klick frisch abfragen statt einmal zu iterieren.
    for (let i = 0; i < 2; i++) {
      const unchecked = [...card.shadowRoot.querySelectorAll("[data-bulk-select]")].find((cb) => !cb.checked);
      if (unchecked) unchecked.click();
      await new Promise((r) => setTimeout(r, 20));
    }
  });
  await page.waitForTimeout(100);

  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-bulk-set-automation="close"][data-value="off"]').click();
  });
  await page.waitForTimeout(100);
  calls = await page.evaluate(() => window.__serviceCalls);
  const switchCalls = calls.filter((c) => c.domain === "switch" && c.service === "turn_off");
  check("FR16: Automatik-Bulk-Aktion schaltet BEIDE ausgewählten Rollläden aus",
    switchCalls.some((c) => c.data.entity_id === "switch.testroom_automation_close") &&
    switchCalls.some((c) => c.data.entity_id === "switch.testroom2_automation_close")
  );

  await page.evaluate(() => {
    const card = document.getElementById("card");
    card.shadowRoot.querySelector('[data-bulk-position-input="open"]').value = "77";
    card.shadowRoot.querySelector('[data-bulk-apply-position="open"]').click();
  });
  await page.waitForTimeout(100);
  calls = await page.evaluate(() => window.__serviceCalls);
  const numberCalls = calls.filter((c) => c.domain === "number" && c.service === "set_value" && c.data.value === 77);
  check("FR16: Zielposition-Bulk-Aktion setzt Wert 77% für BEIDE Rollläden",
    numberCalls.some((c) => c.data.entity_id === "number.testroom_open_position") &&
    numberCalls.some((c) => c.data.entity_id === "number.testroom2_open_position")
  );
  const selectCalls = calls.filter((c) => c.domain === "select" && c.service === "select_option");
  check("FR16: Positions-Quelle wird automatisch auf 'Individuell' umgestellt, damit der Wert wirkt",
    selectCalls.some((c) => c.data.entity_id === "select.testroom_open_position_source" && c.data.option === "local") &&
    selectCalls.some((c) => c.data.entity_id === "select.testroom2_open_position_source" && c.data.option === "local")
  );

  // ---------------------------------------------------------------
  // Bereiche (Custom Areas): anlegen, Mitglied zuordnen, anwenden.
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-nav="settings"]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-settings-nav="settings-areas"]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-area-edit="__new__"]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-toggle-area-section="sun"]').click();
  });
  await page.waitForTimeout(50);

  // --- Vereinfachte Sonnenstand-UI: Himmelsrichtung statt Azimuth-Rohwerte ---
  const sunDefaultState = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    const dirSel = body.querySelector("[data-sun-direction-select]");
    const from = body.querySelector('[data-area-field="sun_azimuth_from"]');
    const to = body.querySelector('[data-area-field="sun_azimuth_to"]');
    return {
      dirValue: dirSel ? dirSel.value : null,
      fromType: from ? from.type : null,
      fromValue: from ? from.value : null,
      toValue: to ? to.value : null,
      hasAdvancedFields: !!body.querySelector('[data-area-field="sun_elevation_hysteresis"]'),
    };
  });
  check("Sonnenstand-UI: Neuer Bereich hat sinnvollen Default 'Süd' vorausgewählt", sunDefaultState.dirValue === "south");
  check("Sonnenstand-UI: Azimuth-Felder bei Kompass-Richtung ausgeblendet (type=hidden)", sunDefaultState.fromType === "hidden");
  check("Sonnenstand-UI: 'Süd' füllt Azimuth automatisch mit 135/225", sunDefaultState.fromValue === "135" && sunDefaultState.toValue === "225");
  check("Sonnenstand-UI: erweiterte Optionen (Hysterese etc.) initial eingeklappt", !sunDefaultState.hasAdvancedFields);

  await page.evaluate(() => {
    const sel = document.getElementById("card").shadowRoot.querySelector("[data-sun-direction-select]");
    sel.value = "east";
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(50);
  const sunOstState = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    return {
      from: body.querySelector('[data-area-field="sun_azimuth_from"]').value,
      to: body.querySelector('[data-area-field="sun_azimuth_to"]').value,
    };
  });
  check("Sonnenstand-UI: Wechsel auf 'Ost' aktualisiert Azimuth automatisch auf 45/135", sunOstState.from === "45" && sunOstState.to === "135");

  await page.evaluate(() => {
    const sel = document.getElementById("card").shadowRoot.querySelector("[data-sun-direction-select]");
    sel.value = "custom";
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(50);
  const sunCustomState = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    const from = body.querySelector('[data-area-field="sun_azimuth_from"]');
    return { fromType: from ? from.type : null };
  });
  check("Sonnenstand-UI: 'Benutzerdefiniert' macht Azimuth-Felder editierbar (type=number)", sunCustomState.fromType === "number");

  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector("[data-toggle-sun-advanced]").click();
  });
  await page.waitForTimeout(50);
  const sunAdvancedState = await page.evaluate(() =>
    !!document.getElementById("card").shadowRoot.querySelector('[data-area-field="sun_elevation_hysteresis"]')
  );
  check("Sonnenstand-UI: 'Erweiterte Optionen' Klick blendet Hysterese-Feld ein", sunAdvancedState);

  // Zurueck auf eine Kompass-Richtung wechseln, bevor der Bereich unten
  // gespeichert wird, damit der bestehende Speicher-Test (weiter unten)
  // einen bekannten, aus der Richtung abgeleiteten Azimuth-Wert prueft.
  await page.evaluate(() => {
    const sel = document.getElementById("card").shadowRoot.querySelector("[data-sun-direction-select]");
    sel.value = "south";
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(50);

  await page.evaluate(() => {
    const card = document.getElementById("card");
    const body = card.shadowRoot.querySelector(".body");
    body.querySelector('[data-area-field="name"]').value = "Hinten";
    body.querySelector('[data-area-field="close_sun_offset"]').value = "20";
    body.querySelector('[data-area-member="cover.testroom"]').click();
  });
  await page.waitForTimeout(50);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector("[data-area-save]").click();
  });
  await page.waitForTimeout(150);

  const areaState = await page.evaluate(() => ({
    areas: window.__customAreas,
    shutterAreas: window.__shutterAreas,
    consoleOk: true,
  }));
  check("Bereiche: neuer Bereich 'Hinten' mit Sonnenversatz-20min gespeichert",
    areaState.areas && areaState.areas.length === 1 && areaState.areas[0].name === "Hinten" && areaState.areas[0].close_sun_offset === 20
  );
  check("Sonnenstand-UI: Kompass-Richtung 'Süd' wird als Azimuth 135/225 gespeichert",
    areaState.areas[0].sun_azimuth_from === 135 && areaState.areas[0].sun_azimuth_to === 225
  );
  check("Bereiche: Rollladen 'cover.testroom' dem Bereich zugeordnet",
    areaState.shutterAreas && Array.isArray(areaState.shutterAreas["cover.testroom"]) &&
      areaState.shutterAreas["cover.testroom"].includes(areaState.areas[0].id)
  );

  // ---------------------------------------------------------------
  // Mehrfach-Zuordnung: derselbe Rollladen bekommt einen ZWEITEN
  // Bereich ("Wohnräume") zusätzlich zu "Hinten" - beide Zuordnungen
  // müssen danach nebeneinander bestehen bleiben. Nach dem Speichern
  // des ersten Bereichs ist man bereits automatisch auf der
  // Bereichs-Liste (_saveAreas navigiert dorthin zurück).
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-area-edit="__new__"]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    const card = document.getElementById("card");
    const body = card.shadowRoot.querySelector(".body");
    body.querySelector('[data-area-field="name"]').value = "Wohnräume";
    body.querySelector('[data-area-member="cover.testroom"]').click();
  });
  await page.waitForTimeout(50);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector("[data-area-save]").click();
  });
  await page.waitForTimeout(150);

  const multiAreaState = await page.evaluate(() => ({
    areas: window.__customAreas,
    shutterAreas: window.__shutterAreas,
  }));
  const testroomAreaIds = (multiAreaState.shutterAreas && multiAreaState.shutterAreas["cover.testroom"]) || [];
  check(
    "Mehrfachzuordnung: 'cover.testroom' gehört jetzt BEIDEN Bereichen an ('Hinten' + 'Wohnräume')",
    testroomAreaIds.length === 2 &&
      multiAreaState.areas.length === 2 &&
      multiAreaState.areas.every((a) => testroomAreaIds.includes(a.id))
  );

  // Im Bearbeiten-Formular von "Hinten" muss die Checkbox fuer
  // cover.testroom weiterhin angehakt sein (Mitgliedschaft blieb beim
  // Anlegen von "Wohnräume" unangetastet) UND der Hinweis "(auch:
  // Wohnräume)" muss erscheinen.
  const hintenAreaId = multiAreaState.areas.find((a) => a.name === "Hinten").id;
  await page.evaluate((id) => {
    document.getElementById("card").shadowRoot.querySelector(`[data-area-edit="${id}"]`).click();
  }, hintenAreaId);
  await page.waitForTimeout(100);
  const hintenFormState = await page.evaluate(() => {
    const body = document.getElementById("card").shadowRoot.querySelector(".body");
    const cb = body.querySelector('[data-area-member="cover.testroom"]');
    return { checked: cb ? cb.checked : null, html: body.innerHTML };
  });
  check("Mehrfachzuordnung: Checkbox in 'Hinten' bleibt angehakt, obwohl 'Wohnräume' neu angelegt wurde", hintenFormState.checked === true);
  check("Mehrfachzuordnung: Formular zeigt Hinweis auf die andere Bereichszugehörigkeit ('auch: Wohnräume')", hintenFormState.html.includes("auch: Wohnräume"));

  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-settings-back-areas]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-area-edit]').click();
  });
  await page.waitForTimeout(100);
  const applyBtnExists = await page.evaluate(() => !!document.getElementById("card").shadowRoot.querySelector("[data-area-apply]"));
  check("Bereiche: 'Auf Mitglieder anwenden'-Button erscheint bei bestehendem Bereich", applyBtnExists);

  const callsBeforeApply = (await page.evaluate(() => window.__serviceCalls)).length;
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector("[data-area-apply]").click();
  });
  await page.waitForTimeout(100);
  calls = (await page.evaluate(() => window.__serviceCalls)).slice(callsBeforeApply);
  const offsetApplyCalls = calls.filter(
    (c) => c.domain === "number" && c.data.entity_id === "number.testroom_close_sun_offset" && c.data.value === 20
  );
  check("Bereiche: 'Anwenden' setzt den Sonnenversatz beim Mitglied korrekt", offsetApplyCalls.length >= 1);
  // Regressionstest fuer den Bug "Bereich zeigt trotzdem den globalen
  // Sonnenversatz": open_source/close_source steuert Typ UND
  // Sonnenversatz gemeinsam - muss auch OHNE close_type-Override auf
  // 'Individuell' umgeschaltet werden, sonst bleibt der lokal gesetzte
  // Wert wirkungslos (Scheduler liest weiterhin den globalen Wert).
  // WICHTIG: nur Calls SEIT dem Anwenden-Klick zaehlen (calls-Array
  // akkumuliert ueber den GESAMTEN Testlauf, siehe __serviceCalls) -
  // sonst kann ein frueherer Testschritt (z.B. Bug2), der close_source
  // aus anderem Grund bereits auf Individuell geschaltet hat, einen
  // False Positive erzeugen.
  const sourceApplyCalls = calls.filter(
    (c) => c.domain === "select" && c.service === "select_option" &&
      c.data.entity_id === "select.testroom_close_source" && c.data.option === "local"
  );
  check(
    "Bereiche: 'Anwenden' schaltet close_source auf 'Individuell' auch OHNE close_type-Override (Regressionstest)",
    sourceApplyCalls.length >= 1
  );
  // Regressionstest fuer den Folgebug: wird NUR der Sonnenversatz
  // ueberschrieben (Trigger-Typ bleibt "Nicht ueberschreiben"), muss
  // der lokale Typ-Select auf den AKTUELL global aktiven Wert gespiegelt
  // werden (hier global close_type = "Uhrzeit") - sonst faellt er auf
  // den Select-Default "Uhrzeit" OHNE gesetzten Wert zurueck und die
  // Aktion verschwindet komplett aus dem Zeitplan (kritische
  // Fehlerklasse, siehe resolve_fixed_time-Bug in der Bugliste).
  const localTypeMirrorCalls = calls.filter(
    (c) => c.domain === "select" && c.service === "select_option" &&
      c.data.entity_id === "select.testroom_close_type" && c.data.option === "time"
  );
  check(
    "Bereiche: 'Anwenden' spiegelt bei reinem Sonnenversatz-Override den aktuellen globalen Typ auf lokal (Regressionstest)",
    localTypeMirrorCalls.length >= 1
  );

  // ---------------------------------------------------------------
  // Regressionstest: Basic/Advanced-UI-Modus wurde entfernt
  // ("aufweichen" - kein Onboarding, kein Account-Setting mehr, der
  // Advanced-Tab ist für jeden Nutzer sofort und immer voll nutzbar).
  // ---------------------------------------------------------------
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-nav="list"]').click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector("[data-open-detail]").click();
  });
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-tab="advanced"]').click();
  });
  await page.waitForTimeout(100);
  const advancedTabHtml = await page.evaluate(() =>
    document.getElementById("card").shadowRoot.querySelector(".body").innerHTML
  );
  check(
    "Kein Basic/Advanced-Modus mehr: Advanced-Tab direkt mit Modus-Select nutzbar, kein Onboarding/Hinweis",
    advancedTabHtml.includes("data-advanced-mode-select") &&
      !advancedTabHtml.includes("data-choose-ui-mode") &&
      !advancedTabHtml.includes("data-switch-to-advanced")
  );

  const settingsHtmlAfterUiModeRemoval = await page.evaluate(() => {
    document.getElementById("card").shadowRoot.querySelector('[data-nav="settings"]').click();
    return document.getElementById("card").shadowRoot.querySelector(".body").innerHTML;
  });
  check(
    "Kein Basic/Advanced-Modus mehr: kein Anzeige-Modus-Select in den Einstellungen",
    !settingsHtmlAfterUiModeRemoval.includes("data-ui-mode-select")
  );

  // English is the default for the card; German follows Home Assistant's language.
  const englishOverview = await page.evaluate(() => {
    const card = document.getElementById("card");
    window.__hass.language = "en";
    card._view = "overview";
    card._render();
    return card.shadowRoot.querySelector(".body").textContent;
  });
  check("English card: dashboard labels use English", englishOverview.includes("Quick Access") && englishOverview.includes("All Shutters") && !englishOverview.includes("Schnellzugriff"));

  const englishArea = await page.evaluate(() => {
    const card = document.getElementById("card");
    card._view = "settings-areas";
    card._render();
    return card.shadowRoot.querySelector(".body").textContent;
  });
  check("English card: area labels use English", englishArea.includes("Areas") && englishArea.includes("Apply to members") && !englishArea.includes("Bereiche verwalten"));

  const germanOverview = await page.evaluate(() => {
    const card = document.getElementById("card");
    window.__hass.language = "de";
    card._view = "overview";
    card._render();
    return card.shadowRoot.querySelector(".body").textContent;
  });
  check("German card: dashboard labels use German", germanOverview.includes("Schnellzugriff") && germanOverview.includes("Alle Rollläden"));
  const messages = await page.evaluate(() => {
    const card = document.getElementById("card");
    window.__hass.language = "en";
    const en = [card._message("overrideNotice", "20:00", "Guest"), card._message("sunValuesRequired")];
    window.__hass.language = "de";
    const de = [card._message("overrideNotice", "20:00", "Gast"), card._message("sunValuesRequired")];
    return { en, de };
  });
  check("English card: dynamic notices use English", messages.en[0].includes("source: Guest") && messages.en[1].startsWith("Please"));
  check("German card: dynamic notices use German", messages.de[0].includes("Quelle: Gast") && messages.de[1].startsWith("Für"));

  if (process.env.AUDIT_LOCALE) {
    const leftovers = await page.evaluate(() => {
      const card = document.getElementById("card");
      window.__hass.language = "en";
      const result = {};
      for (const view of ["overview", "list", "detail", "settings", "settings-basic", "settings-schedules", "settings-schedule-edit", "settings-triggers", "settings-trigger-edit", "settings-rename", "settings-areas", "settings-area-edit", "settings-global"]) {
        try {
          card._view = view;
          card._render();
          result[view] = card.shadowRoot.querySelector(".body").textContent
            .split(/\n/).map((line) => line.trim()).filter((line) => /[äöüßÄÖÜ]|\b(Rollladen|Bereich|Ferien|Schließen|Öffnen|Einstellungen|Auslöser|Speichern|Zurück|Verwalten)\b/.test(line));
        } catch (error) {
          result[view] = ["ERROR: " + error.message];
        }
      }
      card._view = "detail";
      for (const tab of ["basic", "advanced", "verlauf"]) {
        card._detailTab = tab;
        card._render();
        result["detail-" + tab] = card.shadowRoot.querySelector(".body").textContent
          .split(/\n/).map((line) => line.trim()).filter((line) => /[äöüßÄÖÜ]|\b(Rollladen|Bereich|Ferien|Schließen|Öffnen|Einstellungen|Auslöser|Speichern|Zurück|Verwalten)\b/.test(line));
      }
      return result;
    });
    console.log("Locale audit:", JSON.stringify(leftovers, null, 2));
  }

  await browser.close();
  console.log(`\n${failures === 0 ? "ALLE TESTS OK" : failures + " FEHLGESCHLAGEN"}`);
  process.exit(failures === 0 ? 0 : 1);
}

main();
