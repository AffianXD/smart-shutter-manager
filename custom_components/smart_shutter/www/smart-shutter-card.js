/**
 * Smart Shutter Manager dashboard card.
 *
 * The integration serves this file at
 * /smart_shutter_frontend/smart-shutter-card.js and attempts to register it
 * as a dashboard resource. See the root README for installation and the
 * manual resource-registration fallback. Add it as
 * `type: custom:smart-shutter-card` on a dashboard.
 */
(() => {
  const DOMAIN = "smart_shutter";
  // Static card text uses English in the markup; the German table is applied
  // after each render. Legacy German strings still produced by dynamic
  // branches are translated by the English table during the transition.
  const CARD_TEXT = {
    en: {
      "\"Global\" übernimmt Trigger-Typ, Sonnenversatz und Zielposition vollständig von den globalen Einstellungen. \"Individuell\" erlaubt eigene Werte für diesen Rollladen (weiterhin pro Öffnen/Schließen und Aspekt getrennt einstellbar).": "\"Global\" takes over trigger type, sun offset, and target position completely from the global settings. \"Individual\" allows custom values for this shutter (still separable per open/close and aspect).",
      "0° = Sonne am Horizont, 90° = Sonne im Zenit (mittags im Sommer). Faustregel: vormittags/nachmittags meist 15-35°, mittags im Sommer bis 60°+.": "0° = Sun on the horizon, 90° = Sun at zenith (noon in summer). Rule of thumb: in the morning/afternoon usually 15-35°, at noon in summer up to 60°+.",
      "Ablaufdatum (optional)": "Expiry date (optional)",
      "Aktion": "Action",
      "Aktivieren": "Enable",
      "Alle Rollläden": "All Shutters",
      "Alle hoch": "All up",
      "Alle runter": "All down",
      "Alle wie viele Wochen? (1 = jede Woche)": "Repeat every how many weeks? (1 = every week)",
      "Automatik (global, für alle Rollläden)": "Automation (global, for all shutters)",
      "Automatik (individuell)": "Automation (individual)",
      "Automatik Schließen: An": "Close automation: On",
      "Automatik Schließen: Aus": "Close automation: Off",
      "Automatik teilweise aus": "Automation partially off",
      "Automatik Öffnen: An": "Open automation: On",
      "Automatik Öffnen: Aus": "Open automation: Off",
      "Basis-Einstellungen": "Basic Settings",
      "Benachrichtigung senden, wenn diese Regel auslöst": "Send notification when this rule triggers",
      "Benachrichtigungen": "Notifications",
      "Benannte Regeln, deren Zielzeit per Service (smart_shutter.set_external_trigger) aus einer externen Automation gesetzt wird. Gewinnt immer gegenüber Profilen/Custom-Profilen. Kann einen einzelnen Rollladen ODER gleich einen ganzen Bereich (alle Mitglieder) ansteuern.": "Named rules whose target time is set via service (smart_shutter.set_external_trigger) from an external automation. Always takes precedence over profiles/custom profiles. Can control a single shutter OR an entire area (all members).",
      "Bereich": "Area",
      "Bereiche": "Areas",
      "Bereiche verwalten": "Manage Areas",
      "Betrifft": "Applies to",
      "Bis Uhrzeit": "Until Time",
      "Custom-Profile": "Custom profiles",
      "Custom-Profile verwalten (falls diese Aktion zeitgesteuert über ein Profil kommt)": "Manage custom profiles (if this action uses a scheduled profile)",
      "Die globale Automatik-Steuerung betrifft ALLE Rollläden im Haus und ist daher nur für Administratoren sichtbar. Nutze die Automatik-Schalter in deinem Bereich weiter unten.": "The global automation control affects ALL shutters in the house and is therefore only visible to administrators. Use the automation switches in your area below.",
      "Eigene Gruppen (z.B. Vorne/Hinten/Nord/Süd) mit Voreinstellungen. Ein Rollladen kann mehreren Bereichen gleichzeitig angehören. Über \"Auf Mitglieder anwenden\" werden die Werte auf die individuellen Einstellungen der zugeordneten Rollläden übertragen. Hoch/Stopp/Runter und der Automatik-Schalter wirken sofort auf alle Mitglieder.": "Custom groups (e.g. Front/Back/North/South) with preset settings. A shutter can belong to multiple areas at the same time. By using \"Apply to members\", the values are transferred to the individual settings of the assigned shutters. Up/Stop/Down and the automation switch take effect immediately on all members.",
      "Eigener Benachrichtigungs-Empfänger NUR für Ereignisse dieses Bereichs (Bewegungen, Frostschutz, Sonnenstand-Regel) - z.B. das Handy eines Gastes statt deines eigenen. Leer = die globale Basis-Einstellung wird verwendet.": "Custom notification recipient ONLY for events in this area (movements, frost protection, sun position rule) - e.g. a guest's phone instead of your own. Empty = the global base setting is used.",
      "Ein Rollladen kann mehreren Bereichen gleichzeitig angehören (z.B. \"Hinten\" UND \"Wohnräume\") - beim Anwenden gewinnt bei sich widersprechenden Einstellungen der zuletzt angewendete Bereich.": "A shutter can belong to multiple areas at the same time (e.g. \"Back\" AND \"Living rooms\") - when applying, the last applied area takes precedence in case of conflicting settings.",
      "Einstellungen": "Settings",
      "Einzelner Rollladen": "Single Shutter",
      "Ereignisverlauf": "Event Log",
      "Erweiterte Einstellungen": "Advanced Settings",
      "Es wurden keine vom Smart Shutter Manager verwalteten Rollläden gefunden.": "No shutters managed by the Smart Shutter Manager were found.",
      "Externe Trigger": "External Triggers",
      "Externe Trigger für diesen Rollladen": "External Triggers for this Shutter",
      "Ferien-/Frost-Entity, Benachrichtigungen": "Holiday/Frost Entity, Notifications",
      "Fährt alle Mitglieder dieses Bereichs automatisch auf die Zielposition, sobald die Sonne von der gewählten Richtung hereinscheint UND mindestens die angegebene Höhe erreicht hat - z.B. gezielte Verschattung, wenn die Sonne genau auf diese Fassade scheint. Läuft unabhängig vom normalen Öffnen-/Schließen-Zeitplan.": "Automatically moves all members of this area to the target position as soon as the sun shines in from the selected direction AND reaches at least the specified height - e.g. targeted shading when the sun shines directly on this facade. Runs independently of the normal open/close schedule.",
      "Für diesen Rollladen bearbeiten": "Edit for this Shutter",
      "Ganzer Bereich (alle Mitglieder)": "Entire Area (all members)",
      "Gelten für ALLE Rollläden (zentrale Zeit-Ausnahmen) - hier direkt bearbeitbar, ohne die Ansicht zu wechseln.": "Apply to ALL shutters (central time exceptions) - editable here directly, without switching views.",
      "Geschätzte Vorwarnzeit, keine exakte Vorausberechnung (die Sonnenposition wird laufend beobachtet, nicht wie beim Zeitplan zu einem fest bekannten Zeitpunkt) - basiert auf der aktuellen Änderungsrate der Sonnenhöhe.": "Estimated warning time, no exact prediction (the sun position is continuously monitored, not like in the schedule to a fixed known time) - based on the current rate of change in sun height.",
      "Globale Entities": "Global Entities",
      "Globale Zeiten je Profil": "Global Times per Profile",
      "Globale Zielposition": "Global Target Position",
      "HA-Nutzer, die NUR diesen Bereich sehen/bedienen dürfen (z.B. Airbnb-/Mieter-Zugang) - typischer Einsatz: eigener, nicht-Admin HA-Nutzer pro vermieteter Wohnung, dem in HA selbst zusätzlich (Einstellungen → Personen → Nutzer) nur die Entities dieser Wohnung freigegeben sind. Diese Bereichs-Zuordnung allein ersetzt HAs eigene Nutzer-Berechtigung NICHT - sie steuert nur, was die Smart-Shutter-Karte anzeigt/liefert.": "HA users who are allowed to see/operate ONLY this area (e.g. Airbnb/tenant access) - typical use case: own, non-admin HA user per rented apartment, who in HA itself is additionally granted (Settings → People → Users) only the entities of that apartment. This area assignment alone does NOT replace HA's own user permissions - it only controls what the Smart-Shutter card displays/provides.",
      "Heute überspringen": "Skip Today",
      "Hoch": "Up",
      "Jetzt auf alle Mitglieder anwenden": "Apply to all members now",
      "Kein Externer Trigger für diesen Rollladen angelegt.": "No external trigger set for this shutter.",
      "Keine HA-Nutzer gefunden.": "No HA users found.",
      "Lade Ereignisverlauf ...": "Loading event history ...",
      "Lade Smart Shutter Manager Daten…": "Loading Smart Shutter Manager data…",
      "Lade Vorhersage ...": "Loading forecast ...",
      "Mein Bereich": "My Area",
      "Mitglieder": "Members",
      "Modus": "Mode",
      "Neuen Externen Trigger anlegen": "Create new external trigger",
      "Neuen Externen Trigger für diesen Rollladen": "Create new external trigger for this shutter",
      "Neuer Bereich": "New Area",
      "Neuer Zeitplan für diesen Bereich": "New schedule for this area",
      "Neues eigenes Zeitprofil": "New custom profile",
      "Nicht überschreiben": "Do not override",
      "Noch keine Bereiche angelegt.": "No areas created yet.",
      "Noch keine Custom-Profile angelegt.": "No custom profiles created yet.",
      "Noch keine Ereignisse aufgezeichnet.": "No events recorded yet.",
      "Noch keine Externen Trigger angelegt.": "No external triggers created yet.",
      "Noch keine eigenen Zeitpläne für diesen Bereich.": "No schedules for this area yet.",
      "Benachrichtigungsdienst für diesen Bereich": "Notification service for this area",
      "Notiz (warum individuelle Einstellungen?)": "Note (why individual settings?)",
      "Notiz speichern": "Save note",
      "Nächste Aktion:": "Next action:",
      "Ohne eigenen Sensor wird automatisch ein Temperatursensor aus demselben Raum verwendet, falls eindeutig zuordenbar - sonst gilt der globale Innentemperatur-Sensor (Einstellungen → Basis-Einstellungen).": "Without a custom sensor, a temperature sensor from the same room is used automatically if uniquely assignable - otherwise, the global indoor temperature sensor is used (Settings → Basic Settings).",
      "Override jetzt aufheben": "Cancel override now",
      "Pause jetzt aufheben": "End pause now",
      "Profil": "Profile",
      "Quelle Schließen": "Close source",
      "Quelle Öffnen": "Open source",
      "Referenzdatum": "Reference date",
      "Rollladen nicht gefunden.": "Shutter not found.",
      "Rollladen-Position, auf die gefahren wird, wenn die Regel auslöst (0% = ganz zu, 100% = ganz auf).": "Shutter position to which the rule drives when triggered (0% = fully closed, 100% = fully open).",
      "Rollläden": "Shutters",
      "Rollläden umbenennen": "Rename shutters",
      "Runter": "Down",
      "Schließen": "Close",
      "Schließen (alle Rollläden)": "Close (all shutters)",
      "Schließen-Uhrzeit (optional)": "Close Time (optional)",
      "Schnellzugriff": "Quick Access",
      "Sonnenversatz": "Sun offset",
      "Sonnenversatz (optional)": "Sun offset (optional)",
      "Speichern": "Save",
      "Stopp": "Stop",
      "Trigger-Typ": "Trigger Type",
      "Trigger-Typ (Uhrzeit / Sonnenstand)": "Trigger Type (Time / Solar Position)",
      "Trigger-Typ (optional)": "Trigger Type (optional)",
      "Typ": "Type",
      "Verhindert wiederholtes Auslösen, wenn die Sonnenhöhe nur knapp um die Schwelle pendelt (erst nach ausreichendem Abstand darunter wird erneut \"scharf\" geschaltet).": "Prevents repeated triggering when the sun's elevation only slightly fluctuates around the threshold (it will only be reactivated after sufficient distance below the threshold).",
      "Verlauf": "History",
      "Verschieben": "Shift",
      "Von Automationen ansteuerbare Zeit-Trigger": "Time Triggers that can be triggered by Automations",
      "Von welcher Richtung scheint die Sonne auf diesen Bereich?": "From which direction is the sun shining on this area?",
      "Vorwarnung senden, BEVOR diese Regel auslöst": "Send a warning BEFORE this rule is triggered",
      "Weitere Entities": "More Entities",
      "Wiederkehrende Zeit-Ausnahmen NUR für die Rollläden dieses Bereichs (z.B. \"Urlaub der Ferienwohnung\"). Wirkt sich nie auf andere Bereiche oder deinen eigenen Host-Bereich aus. Reihenfolge = Priorität bei Überschneidungen - die erste Regel gewinnt.": "Recurring Time Exceptions ONLY for the shutters in this area (e.g. \"Vacation of the holiday home\"). Never affects other areas or your own host area. Order = Priority in case of overlaps - the first rule wins.",
      "Wiederkehrende Zeit-Ausnahmen verwalten": "Manage Recurring Time Exceptions",
      "Wiederkehrende Zeit-Ausnahmen, gelten für alle Rollläden (pro Rollladen lokal überschreibbar). Reihenfolge = Priorität bei Überschneidungen - die erste Regel gewinnt.": "Recurring Time Exceptions, apply to all shutters (can be overwritten locally per shutter). Order = Priority in case of overlaps - the first rule wins.",
      "Wird im Service smart_shutter.set_external_trigger als Referenz benutzt.": "Used as a reference in the service smart_shutter.set_external_trigger.",
      "Wochentage": "Weekdays",
      "Zeiten je Profil": "Times per Profile",
      "Zeiten, Sonnenstand-Regel, Frostschutz für deinen Bereich": "Times, Sun Position Rule, Frost Protection for your area",
      "Zeiten, Sonnenversatz, Zielposition (global)": "Times, Sun Offset, Target Position (global)",
      "Zeitpunkt": "Time",
      "Zeitstrahl": "Timeline",
      "Ziel": "Target",
      "Zielposition": "Target Position",
      "Zielposition (optional)": "Target Position (optional)",
      "Zurück": "Back",
      "Zurück zum Einstellungsmenü": "Back to Settings Menu",
      "Zurück zur Liste": "Back to List",
      "Zurück zur Übersicht": "Back to Overview",
      "bearbeiten": "edit",
      "einzeln steuern": "control individually",
      "nicht konfiguriert": "not configured",
      "z.B. Vorne/Hinten/Nord/Süd - eigene Gruppen mit Voreinstellungen": "e.g. Front/Back/North/South - own groups with presets",
      "Änderungen gelten sofort für alle oben angehakten Rollläden.": "Changes apply immediately to all checked shutters above.",
      "Öffnen": "Open",
      "Öffnen (alle Rollläden)": "Open (all shutters)",
      "Öffnen-Uhrzeit (optional)": "Open Time (optional)",
      "Übernehmen": "Apply",
      "Übernommen von Global": "Inherited from global",
      "☀ Sonnenstand": "☀ Sun position",
      "⚠ Konflikt": "⚠ Conflict",
      "Automatik Öffnen (alle Rollläden)": "Open automation (all shutters)",
      "Automatik Schließen (alle Rollläden)": "Close automation (all shutters)",
      "▾ Liste ausblenden": "▾ Hide list",
      "▸ Weitere Aktionen (Verschieben, Überspringen)": "▸ More actions (postpone, skip)",
      "Öffnen-Quelle (Typ/Sonnenversatz)": "Open source (type/sun offset)",
      "Öffnen: Uhrzeit oder Sonnenaufgang/-untergang": "Open: time or sunrise/sunset",
      "Schließen-Quelle (Typ/Sonnenversatz)": "Close source (type/sun offset)",
      "Schließen: Uhrzeit oder Sonnenaufgang/-untergang": "Close: time or sunrise/sunset",
      "Öffnen-Quelle": "Open source",
      "Schließen-Quelle": "Close source",
      "Typ Öffnen": "Open type",
      "Typ Schließen": "Close type",
      "Sonnenversatz Öffnen": "Open sun offset",
      "Sonnenversatz Schließen": "Close sun offset",
      "'an' = Ferien aktiv": "'on' = holiday active",
      "Außentemperatur-Sensor": "Outdoor temperature sensor",
      "Global, fließt in Frostschutz + Sonnenstand-Zusatzbedingung (als 'outside_temp') ein": "Global sensor used for frost protection and sun position conditions (as 'outside_temp')",
      "Fallback, falls ein Bereich keinen eigenen Sensor hat (manuell oder automatisch erkannt, siehe Bereiche)": "Fallback when an area has no own sensor (manually configured or detected; see Areas)",
      "Automatik pausiert (wie bei manuellem Eingriff), sobald Innen- oder Außentemperatur diesen Wert unterschreitet. Pro Bereich überschreibbar.": "Automation pauses when indoor or outdoor temperature falls below this value. Can be overridden per area.",
      "Vorwarnung vor dem Schließen (Minuten)": "Warning before closing (minutes)",
      "Erkennt Bewegungen, die NICHT von der Automatik kommen (Wandschalter, Fernbedienung, andere Automation) und pausiert die Automatik für diesen Rollladen entsprechend lange.": "Detects movements outside this automation (wall switch, remote, or another automation) and pauses this shutter's automation for the configured duration.",
      "Verzögerung zwischen den einzelnen Rollläden bei Mehrfachaktionen (globaler Zeitplan, Bereich, 'Alle hoch/runter/Stopp') - Funk-Kollisionsschutz für funkbasierte Motoren. Bei WLAN-Geräten (z.B. Shelly) normalerweise nicht nötig.": "Delay between shutters for group actions (global schedule, area, all up/down/stop) to reduce radio collisions. Usually unnecessary for Wi-Fi devices.",
      "Vorlage: Bewegungsbenachrichtigung": "Movement notification template",
      "Vorlage: Frostschutzbenachrichtigung": "Frost protection notification template",
      "Vorlage: Vorwarnung vor dem Schließen": "Pre-closing warning template",
      "bereits erfolgt": "already occurred",
      "zum Bearbeiten antippen": "tap to edit",
      "Rollladen": "Shutter",
      "Ab welcher Sonnenhöhe auslösen": "Trigger above this sun elevation",
      "Eigene Zeitpläne für diesen Bereich": "Schedules for this area"
    },
    de: {
      "Advanced": "Erweitert",
      "Basic": "Grundlagen",
      "Dashboard": "Übersicht",
      "Detail": "Details",
      "Weekday": "Arbeitstage",
      "Weekend": "Wochenende",
      "Holiday": "Ferien",
      "Frost protection entity": "Frostschutz-Entität",
      "Holiday entity": "Ferien-Entität",
      "Notification service": "Benachrichtigungsdienst",
      "e.g. notify.notify, empty = off": "z. B. notify.notify, leer = aus",
      "Global trigger type & sun offset": "Globaler Auslösertyp und Sonnenversatz",
      "Azimuth from": "Azimut von",
      "Azimuth to": "Azimut bis",
      "New external trigger": "Neuer externer Auslöser",
      "Timing and delays": "Zeitverhalten und Verzögerungen",
      "Warning button validity (minutes, 0 = unlimited)": "Gültigkeitsdauer der Vorwarnungsschaltflächen (Minuten, 0 = unbegrenzt)",
      "\"Global\" takes over trigger type, sun offset, and target position completely from the global settings. \"Individual\" allows custom values for this shutter (still separable per open/close and aspect).": "\"Global\" übernimmt Auslösertyp, Sonnenversatz und Zielposition vollständig von den globalen Einstellungen. \"Individuell\" erlaubt eigene Werte für diesen Rollladen (weiterhin getrennt für Öffnen/Schließen und den jeweiligen Aspekt einstellbar).",
      "0° = Sun on the horizon, 90° = Sun at zenith (noon in summer). Rule of thumb: in the morning/afternoon usually 15-35°, at noon in summer up to 60°+.": "0° = Sonne am Horizont, 90° = Sonne im Zenit (mittags im Sommer). Faustregel: vormittags/nachmittags meist 15-35°, mittags im Sommer bis 60°+.",
      "Expiry date (optional)": "Ablaufdatum (optional)",
      "Action": "Aktion",
      "Enable": "Aktivieren",
      "All Shutters": "Alle Rollläden",
      "All up": "Alle hoch",
      "All down": "Alle runter",
      "Repeat every how many weeks? (1 = every week)": "Alle wie viele Wochen? (1 = jede Woche)",
      "Automation (global, for all shutters)": "Automatik (global, für alle Rollläden)",
      "Automation (individual)": "Automatik (individuell)",
      "Close automation: On": "Automatik Schließen: An",
      "Close automation: Off": "Automatik Schließen: Aus",
      "Automation partially off": "Automatik teilweise aus",
      "Automation disabled": "Automatik aus",
      "Automation enabled": "Automatik an",
      "Open automation: On": "Automatik Öffnen: An",
      "Open automation: Off": "Automatik Öffnen: Aus",
      "Basic Settings": "Basis-Einstellungen",
      "Send notification when this rule triggers": "Benachrichtigung senden, wenn diese Regel auslöst",
      "Notifications": "Benachrichtigungen",
      "Named rules whose target time is set via service (smart_shutter.set_external_trigger) from an external automation. Always takes precedence over profiles/custom profiles. Can control a single shutter OR an entire area (all members).": "Benannte Regeln, deren Zielzeit über den Home-Assistant-Dienst smart_shutter.set_external_trigger aus einer externen Automation festgelegt wird. Sie haben Vorrang vor Profilen und eigenen Zeitprofilen und können einen einzelnen Rollladen oder einen ganzen Bereich steuern.",
      "Area": "Bereich",
      "Areas": "Bereiche",
      "Manage Areas": "Bereiche verwalten",
      "Applies to": "Betrifft",
      "Until Time": "Bis Uhrzeit",
      "Custom profiles": "Eigene Zeitprofile",
      "Manage custom profiles (if this action uses a scheduled profile)": "Eigene Zeitprofile verwalten (wenn diese Aktion über ein Profil zeitgesteuert wird)",
      "The global automation control affects ALL shutters in the house and is therefore only visible to admins. Use the automation switches in your area below.": "Die globale Automatik-Steuerung betrifft ALLE Rollläden im Haus und ist daher nur für Administratoren sichtbar. Nutze die Automatik-Schalter in deinem Bereich weiter unten.",
      "Custom groups (e.g. Front/Back/North/South) with preset settings. A shutter can belong to multiple areas at the same time. By using \"Apply to members\", the values are transferred to the individual settings of the assigned shutters. Up/Stop/Down and the automation switch take effect immediately on all members.": "Eigene Gruppen (z.B. Vorne/Hinten/Nord/Süd) mit Voreinstellungen. Ein Rollladen kann mehreren Bereichen gleichzeitig angehören. Über \"Auf Mitglieder anwenden\" werden die Werte auf die individuellen Einstellungen der zugeordneten Rollläden übertragen. Hoch/Stopp/Runter und der Automatik-Schalter wirken sofort auf alle Mitglieder.",
      "Custom notification recipient ONLY for events in this area (movements, frost protection, sun position rule) - e.g. a guest's phone instead of your own. Empty = the global base setting is used.": "Eigener Benachrichtigungs-Empfänger NUR für Ereignisse dieses Bereichs (Bewegungen, Frostschutz, Sonnenstand-Regel) - z.B. das Handy eines Gastes statt deines eigenen. Leer = die globale Basis-Einstellung wird verwendet.",
      "A shutter can belong to multiple areas at the same time (e.g. \"Back\" AND \"Living rooms\") - when applying, the last applied area takes precedence in case of conflicting settings.": "Ein Rollladen kann mehreren Bereichen gleichzeitig angehören (z.B. \"Hinten\" UND \"Wohnräume\") - beim Anwenden gewinnt bei sich widersprechenden Einstellungen der zuletzt angewendete Bereich.",
      "Settings": "Einstellungen",
      "Single Shutter": "Einzelner Rollladen",
      "Event Log": "Ereignisverlauf",
      "Advanced Settings": "Erweiterte Einstellungen",
      "No shutters managed by the Smart Shutter Manager were found.": "Es wurden keine vom Smart Shutter Manager verwalteten Rollläden gefunden.",
      "External Triggers": "Externe Auslöser",
      "External Triggers for this Shutter": "Externe Auslöser für diesen Rollladen",
      "Holiday/Frost Entity, Notifications": "Ferien-/Frostschutz-Entität, Benachrichtigungen",
      "Automatically moves all members of this area to the target position as soon as the sun shines in from the selected direction AND reaches at least the specified height - e.g. targeted shading when the sun shines directly on this facade. Runs independently of the normal open/close schedule.": "Fährt alle Mitglieder dieses Bereichs automatisch auf die Zielposition, sobald die Sonne von der gewählten Richtung hereinscheint UND mindestens die angegebene Höhe erreicht hat - z.B. gezielte Verschattung, wenn die Sonne genau auf diese Fassade scheint. Läuft unabhängig vom normalen Öffnen-/Schließen-Zeitplan.",
      "Edit for this Shutter": "Für diesen Rollladen bearbeiten",
      "Entire Area (all members)": "Ganzer Bereich (alle Mitglieder)",
      "Apply to ALL shutters (central time exceptions) - editable here directly, without switching views.": "Gelten für ALLE Rollläden (zentrale Zeit-Ausnahmen) - hier direkt bearbeitbar, ohne die Ansicht zu wechseln.",
      "Estimated warning time, no exact prediction (the sun position is continuously monitored, not like in the schedule to a fixed known time) - based on the current rate of change in sun height.": "Geschätzte Vorwarnzeit, keine exakte Vorausberechnung (die Sonnenposition wird laufend beobachtet, nicht wie beim Zeitplan zu einem fest bekannten Zeitpunkt) - basiert auf der aktuellen Änderungsrate der Sonnenhöhe.",
      "Global Entities": "Globale Entitäten",
      "Global Times per Profile": "Globale Zeiten je Profil",
      "Global Target Position": "Globale Zielposition",
      "HA users who are allowed to see/operate ONLY this area (e.g. Airbnb/tenant access) - typical use case: own, non-admin HA user per rented apartment, who in HA itself is additionally granted (Settings → People → Users) only the entities of that apartment. This area assignment alone does NOT replace HA's own user permissions - it only controls what the Smart-Shutter card displays/provides.": "HA-Nutzer, die nur diesen Bereich sehen und bedienen dürfen (z. B. für Airbnb- oder Mieterzugänge). Typischerweise erhält ein eigener, nicht administrativer HA-Nutzer für die vermietete Wohnung in Home Assistant nur Zugriff auf deren Entitäten (Einstellungen → Personen → Nutzer). Die Bereichszuordnung allein ersetzt die Nutzerberechtigungen von Home Assistant nicht; sie steuert nur, was die Smart-Shutter-Karte anzeigt und bereitstellt.",
      "Skip Today": "Heute überspringen",
      "Up": "Hoch",
      "Apply to all members now": "Jetzt auf alle Mitglieder anwenden",
      "No external trigger set for this shutter.": "Für diesen Rollladen ist noch kein externer Auslöser angelegt.",
      "No HA users found.": "Keine HA-Nutzer gefunden.",
      "Loading event history ...": "Lade Ereignisverlauf ...",
      "Loading Smart Shutter Manager data…": "Lade Smart Shutter Manager Daten…",
      "Loading forecast ...": "Lade Vorhersage ...",
      "My Area": "Mein Bereich",
      "Members": "Mitglieder",
      "Mode": "Modus",
      "Create new external trigger": "Neuen externen Auslöser anlegen",
      "Create new external trigger for this shutter": "Neuen externen Auslöser für diesen Rollladen anlegen",
      "New Area": "Neuer Bereich",
      "New schedule for this area": "Neuer Zeitplan für diesen Bereich",
      "New custom profile": "Neues eigenes Zeitprofil",
      "Do not override": "Nicht überschreiben",
      "No areas created yet.": "Noch keine Bereiche angelegt.",
      "No custom profiles created yet.": "Noch keine eigenen Zeitprofile angelegt.",
      "No events recorded yet.": "Noch keine Ereignisse aufgezeichnet.",
      "No external triggers created yet.": "Noch keine externen Auslöser angelegt.",
      "No schedules for this area yet.": "Noch keine eigenen Zeitpläne für diesen Bereich.",
      "Notification service for this area": "Benachrichtigungsdienst für diesen Bereich",
      "Note (why individual settings?)": "Notiz (warum individuelle Einstellungen?)",
      "Save note": "Notiz speichern",
      "Next action:": "Nächste Aktion:",
      "Without a custom sensor, a temperature sensor from the same room is used automatically if uniquely assignable - otherwise, the global indoor temperature sensor is used (Settings → Basic Settings).": "Ohne eigenen Sensor wird automatisch ein Temperatursensor aus demselben Raum verwendet, falls eindeutig zuordenbar - sonst gilt der globale Innentemperatur-Sensor (Einstellungen → Basis-Einstellungen).",
      "Cancel override now": "Manuelle Änderung jetzt aufheben",
      "End pause now": "Pause jetzt aufheben",
      "Profile": "Profil",
      "Close source": "Quelle Schließen",
      "Open source": "Quelle Öffnen",
      "Reference date": "Referenzdatum",
      "Shutter not found.": "Rollladen nicht gefunden.",
      "Shutter position to which the rule drives when triggered (0% = fully closed, 100% = fully open).": "Rollladen-Position, auf die gefahren wird, wenn die Regel auslöst (0% = ganz zu, 100% = ganz auf).",
      "Shutters": "Rollläden",
      "Rename shutters": "Rollläden umbenennen",
      "Down": "Runter",
      "Close": "Schließen",
      "Close (all shutters)": "Schließen (alle Rollläden)",
      "Close Time (optional)": "Schließen-Uhrzeit (optional)",
      "Quick Access": "Schnellzugriff",
      "Sun offset": "Sonnenversatz",
      "Sun offset (optional)": "Sonnenversatz (optional)",
      "Save": "Speichern",
      "Stop": "Stopp",
      "Trigger Type": "Auslösertyp",
      "Trigger Type (Time / Solar Position)": "Auslösertyp (Uhrzeit / Sonnenstand)",
      "Trigger Type (optional)": "Auslösertyp (optional)",
      "Type": "Typ",
      "Prevents repeated triggering when the sun's elevation only slightly fluctuates around the threshold (it will only be reactivated after sufficient distance below the threshold).": "Verhindert wiederholtes Auslösen, wenn die Sonnenhöhe nur knapp um die Schwelle pendelt (erst nach ausreichendem Abstand darunter wird erneut \"scharf\" geschaltet).",
      "History": "Verlauf",
      "Shift": "Verschieben",
      "Time Triggers that can be triggered by Automations": "Zeit-Auslöser, die von Automationen gesteuert werden können",
      "From which direction is the sun shining on this area?": "Von welcher Richtung scheint die Sonne auf diesen Bereich?",
      "Send a warning BEFORE this rule is triggered": "Vorwarnung senden, BEVOR diese Regel auslöst",
      "More Entities": "Weitere Entitäten",
      "Recurring Time Exceptions ONLY for the shutters in this area (e.g. \"Vacation of the holiday home\"). Never affects other areas or your own host area. Order = Priority in case of overlaps - the first rule wins.": "Wiederkehrende Zeit-Ausnahmen nur für die Rollläden dieses Bereichs (z. B. \"Urlaub der Ferienwohnung\"). Sie wirken sich nicht auf andere Bereiche oder den eigenen Gastgeberbereich aus. Bei Überschneidungen gewinnt die zuerst gelistete Regel.",
      "Manage Recurring Time Exceptions": "Wiederkehrende Zeit-Ausnahmen verwalten",
      "Recurring Time Exceptions, apply to all shutters (can be overwritten locally per shutter). Order = Priority in case of overlaps - the first rule wins.": "Wiederkehrende Zeit-Ausnahmen, gelten für alle Rollläden (pro Rollladen lokal überschreibbar). Reihenfolge = Priorität bei Überschneidungen - die erste Regel gewinnt.",
      "Used as a reference in the service smart_shutter.set_external_trigger.": "Wird beim Aufruf des Dienstes smart_shutter.set_external_trigger als Kennung verwendet.",
      "Weekdays": "Wochentage",
      "Times per Profile": "Zeiten je Profil",
      "Times, Sun Position Rule, Frost Protection for your area": "Zeiten, Sonnenstand-Regel, Frostschutz für deinen Bereich",
      "Times, Sun Offset, Target Position (global)": "Zeiten, Sonnenversatz, Zielposition (global)",
      "Time": "Zeitpunkt",
      "Timeline": "Zeitstrahl",
      "Target": "Ziel",
      "Target Position": "Zielposition",
      "Target Position (optional)": "Zielposition (optional)",
      "Back": "Zurück",
      "Back to Settings Menu": "Zurück zum Einstellungsmenü",
      "Back to List": "Zurück zur Liste",
      "Back to Overview": "Zurück zur Übersicht",
      "edit": "bearbeiten",
      "control individually": "einzeln steuern",
      "not configured": "nicht konfiguriert",
      "e.g. Front/Back/North/South - own groups with presets": "z.B. Vorne/Hinten/Nord/Süd - eigene Gruppen mit Voreinstellungen",
      "Changes apply immediately to all checked shutters above.": "Änderungen gelten sofort für alle oben angehakten Rollläden.",
      "Open": "Öffnen",
      "Open (all shutters)": "Öffnen (alle Rollläden)",
      "Open Time (optional)": "Öffnen-Uhrzeit (optional)",
      "Apply": "Übernehmen",
      "Inherited from global": "Übernommen von Global",
      "☀ Sun position": "☀ Sonnenstand",
      "⚠ Conflict": "⚠ Konflikt",
      "Notification text (optional, Jinja template)": "Benachrichtigungstext (optional, Jinja-Vorlage)",
      "Variables: {{ area }}, {{ count }}, {{ position }}, {{ names }}. Empty = default text. Uses the configured notification service.": "Variablen: {{ area }}, {{ count }}, {{ position }}, {{ names }}. Leer = Standardtext. Nutzt den konfigurierten Benachrichtigungsdienst.",
      "Warning text (optional, Jinja template)": "Vorwarnungstext (optional, Jinja-Vorlage)",
      "Variables: {{ area }}, {{ count }}, {{ position }}, {{ minutes }}. Empty = default text.": "Variablen: {{ area }}, {{ count }}, {{ position }}, {{ minutes }}. Leer = Standardtext.",
      "{{ area }}: moved {{ count }} shutters to {{ position }}%.": "{{ area }}: {{ count }} Rollläden auf {{ position }}% gefahren.",
      "{{ area }}: shutters will move to {{ position }}% in about {{ minutes }} minutes.": "{{ area }}: Rollläden fahren in ca. {{ minutes }} Minuten auf {{ position }}%."
    },
  };
  const CARD_MESSAGES = {
    en: {
      bulkPostpone: (action, minutes) => `${action} for all shutters postponed by ${minutes} min`,
      bulkSkip: (action) => `${action} for all shutters skipped today`,
      overrideCleared: "Override cleared; regular schedule is active again",
      overrideNotice: (until, source) => `A manual postpone/skip is active until ${until}${source ? ` (source: ${source})` : ""} and currently takes priority over the regular schedule. Changes to individual times will take effect after it expires.`,
      manualPauseNotice: (until) => `Movement outside this automation was detected (wall switch, remote control, or another automation). Automation for this shutter is paused until ${until}.`,
      areaAutomation: (count, on) => `Automation ${on ? "enabled" : "disabled"} for ${count} ${count === 1 ? "shutter" : "shutters"}`,
      areaApplying: (name, count) => `Applying "${name}" to ${count} ${count === 1 ? "shutter" : "shutters"} …`,
      areaNameRequired: "Please enter an area name.",
      sunValuesRequired: "Please enter all four sun position values (azimuth from/to, minimum elevation, target position).",
      manualPauseCleared: "Manual pause ended",
      saved: "✓ Saved",
      savedReload: "✓ Saved; shutters are reloading…",
      errorPrefix: "Error: ",
      invalidInput: "Invalid input.",
      confirmDeleteProfile: "Delete this custom profile?",
      confirmDeleteTrigger: "Delete this external trigger?",
      confirmScheduleConflict: (names) => `Overlaps with: ${names}. Save this rule anyway so it takes priority over the listed rules?`,
      confirmApplyOverrides: (count, name, details) => `${count} ${count === 1 ? "shutter already has" : "shutters already have"} individual settings that "${name}" would override:\n\n${details}\n\nApply to ALL members anyway, including those settings?`,
      validationNoName: "Please enter a name.",
      validationNoWeekdays: "Select at least one weekday.",
      validationNoTime: "Enter at least one time.",
      validationDuplicateName: "This name is already in use.",
      validationNoEntity: "Select a shutter.",
      conflictReasonTrigger: "Trigger type / sun offset",
      conflictReasonPosition: "Target position",
      notePrefix: "Note",
    },
    de: {
      bulkPostpone: (action, minutes) => `${action} für alle Rollläden um ${minutes} Min. verschoben`,
      bulkSkip: (action) => `${action} für alle Rollläden heute übersprungen`,
      overrideCleared: "Manuelle Änderung aufgehoben – der reguläre Zeitplan gilt wieder",
      overrideNotice: (until, source) => `Ein manuelles Verschieben oder Auslassen ist bis ${until} aktiv${source ? ` (Quelle: ${source})` : ""} und hat derzeit Vorrang vor dem regulären Zeitplan. Individuelle Zeitänderungen greifen wieder, sobald die Änderung abläuft.`,
      manualPauseNotice: (until) => `Es wurde eine Bewegung erkannt, die nicht von der Automatik kam (Wandschalter, Fernbedienung oder andere Automation). Die Automatik für diesen Rollladen ist bis ${until} pausiert.`,
      areaAutomation: (count, on) => `Automatik für ${count} ${count === 1 ? "Rollladen" : "Rollläden"} ${on ? "eingeschaltet" : "ausgeschaltet"}`,
      areaApplying: (name, count) => `"${name}" wird auf ${count} ${count === 1 ? "Rollladen" : "Rollläden"} angewendet …`,
      areaNameRequired: "Bitte einen Namen für den Bereich angeben.",
      sunValuesRequired: "Für die Sonnenstandregel bitte alle vier Werte (Azimut von/bis, Mindesthöhe, Zielposition) angeben.",
      manualPauseCleared: "Automatik-Pause aufgehoben",
      saved: "✓ Gespeichert",
      savedReload: "✓ Gespeichert - Rollläden werden neu geladen…",
      errorPrefix: "Fehler: ",
      invalidInput: "Ungültige Eingabe.",
      confirmDeleteProfile: "Dieses eigene Zeitprofil wirklich löschen?",
      confirmDeleteTrigger: "Diesen externen Auslöser wirklich löschen?",
      confirmScheduleConflict: (names) => `Überschneidung mit: ${names}. Diese Regel trotzdem so speichern (gewinnt zukünftig gegenüber den genannten Regeln)?`,
      confirmApplyOverrides: (count, name, details) => `${count} ${count === 1 ? "Rollladen hat" : "Rollläden haben"} bereits individuelle Einstellungen für Felder, die "${name}" jetzt überschreiben würde:\n\n${details}\n\nTrotzdem auf ALLE Mitglieder anwenden (inkl. dieser individuellen Einstellungen)?`,
      validationNoName: "Bitte einen Namen vergeben.",
      validationNoWeekdays: "Bitte mindestens einen Wochentag auswählen.",
      validationNoTime: "Bitte mindestens eine Uhrzeit angeben.",
      validationDuplicateName: "Dieser Name wird bereits verwendet.",
      validationNoEntity: "Bitte einen Rollladen auswählen.",
      conflictReasonTrigger: "Auslösertyp/Sonnenversatz",
      conflictReasonPosition: "Zielposition",
      notePrefix: "Notiz",
    },
  };
  const GLOBAL_PREFIX = `${DOMAIN}_global_`;
  const DEVICE_PREFIX = `${DOMAIN}_`;

  const STATIC_PROFILE_LABELS = {
    weekday: "Weekday",
    weekend: "Weekend",
    holiday: "Holiday",
  };
  const STATIC_PROFILE_ORDER = ["weekday", "weekend", "holiday"];
  const LEGACY_PROFILE_IDS = { werktag: "weekday", wochenende: "weekend", ferien: "holiday" };

  const SOURCE_OPTION_LOCAL = "local";
  const SELECT_OPTION_LABELS = {
    en: { global: "Global", local: "Individual", time: "Time", sunrise: "Sunrise", sunset: "Sunset" },
    de: { global: "Global", local: "Individuell", time: "Uhrzeit", sunrise: "Sonnenaufgang", sunset: "Sonnenuntergang" },
  };

  // Simplified input for the solar position rule: Direction instead of
  // raw azimuth degree numbers. 90°-wide window per direction (generous
  // selected, "the sun comes roughly from here" instead of precise value) -
  // those who need more precision select "Custom" and enter the
  // Enter azimuth values yourself. [from, to] - "from" > "to" means
  // Wrap-around over 360°/0° (already supported by the backend logic).
  const COMPASS_PRESETS = {
    north: [315, 45],
    northeast: [0, 90],
    east: [45, 135],
    southeast: [90, 180],
    south: [135, 225],
    southwest: [180, 270],
    west: [225, 315],
    northwest: [270, 0],
  };
  const CUSTOM_DIRECTION_KEY = "custom";
  const COMPASS_LABELS = {
    en: { north: "North", northeast: "Northeast", east: "East", southeast: "Southeast", south: "South", southwest: "Southwest", west: "West", northwest: "Northwest", custom: "Custom (enter azimuth manually)" },
    de: { north: "Nord", northeast: "Nordost", east: "Ost", southeast: "Südost", south: "Süd", southwest: "Südwest", west: "West", northwest: "Nordwest", custom: "Benutzerdefiniert (Azimut manuell)" },
  };

  function detectCompassDirection(from, to) {
    if (from === null || from === undefined || to === null || to === undefined) return null;
    for (const [key, [f, t]] of Object.entries(COMPASS_PRESETS)) {
      if (f === Number(from) && t === Number(to)) return key;
    }
    return CUSTOM_DIRECTION_KEY;
  }

  // Order must exactly match const.WEEKDAY_KEYS in Python
  // (Index = datetime.weekday(), 0=Monday...6=Sunday).
  const WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
  const WEEKDAY_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

  function fireEvent(node, type, detail) {
    const event = new Event(type, { bubbles: true, composed: true });
    event.detail = detail;
    node.dispatchEvent(event);
  }

  function navigate(hass, root, path) {
    window.history.pushState(null, "", path);
    fireEvent(root, "location-changed", { replace: false });
  }

  class SmartShutterCard extends HTMLElement {
    setConfig(config) {
      this._config = config || {};
      this._view = "overview"; // overview | list | detail | settings
      this._detailDeviceId = null;
      this._detailTab = "basic";
      this._editingSeason = null;
      this._search = "";
      // Optimistic state overlay for Select changes: independent
      // from the volatile hass-object (which is completely reloaded with EVERY update
      // is set and therefore direct mutations of hass.states
      // discards again on the next tick) - survives even if
      // the real backend confirmation arrives only with a delay.
      // Will be automatically cleaned up as soon as the real state follows.
      this._optimisticState = {};
      this._editReturnView = null;
      this._editReturnDetailDeviceId = null;
      this._prefillTriggerCover = null;
      this._globalTimelineSelectedIdx = null;
      this._globalTimelineGroups = [];
      this._editingAreaId = null;
      this._sunAdvancedExpanded = false;
      this._areaSectionExpanded = {};
      this._sunDirectionOverride = undefined;
      this._bulkEditMode = false;
      this._bulkSelection = new Set();
      this._loaded = false;
      this._loadError = null;
      this._model = null;
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      this._renderShell();
    }

    getCardSize() {
      return 8;
    }

    set hass(hass) {
      this._hass = hass;
      this._subscribeDeviceRegistry();
      this._subscribeSeasonRegistry();
      if (!this._loaded) {
        this._loaded = true;
        this._loadRegistries(); // ruft am Ende einmalig _render() auf
      } else if (this._model) {
        // IMPORTANT: deliberately only update values here, not the
        // rebuild the complete structure from scratch (body.innerHTML = ...) - otherwise
        // would trigger every single tiny State update (and there are plenty of them per
        // ~20 entities per shutter constantly updating) a currently running
        // Input (tap time, drag slider, focus in search field) in the middle
        // in the interaction destroy. A complete re-structure gives
        // it only happens during navigation (see _onClick).
        this._updateValues();
      }
    }

    connectedCallback() {
      this._subscribeDeviceRegistry();
      this._subscribeSeasonRegistry();
    }

    disconnectedCallback() {
      this._stopDeviceRegistrySubscription();
      this._deviceRegistryConnection = null;
      this._stopSeasonRegistrySubscription();
      this._seasonRegistryConnection = null;
      clearTimeout(this._seasonRegistryTimer);
      if (this._managedCoversSaveTimer) {
        clearTimeout(this._managedCoversSaveTimer);
        this._managedCoversSaveTimer = null;
        this._saveManagedCovers();
      }
    }

    _stopDeviceRegistrySubscription() {
      const unsubscribe = this._unsubscribeDeviceRegistry;
      this._unsubscribeDeviceRegistry = null;
      if (unsubscribe) unsubscribe();
    }

    async _subscribeDeviceRegistry() {
      const connection = this._hass && this._hass.connection;
      if (!this.isConnected || !connection || !connection.subscribeEvents ||
          connection === this._deviceRegistryConnection) return;
      this._stopDeviceRegistrySubscription();
      this._deviceRegistryConnection = connection;
      try {
        const unsubscribe = await connection.subscribeEvents((event) => {
          const devices = this._model && (this._model.allShutters || this._model.shutters);
          if (devices && event.data && devices.some((s) => s.deviceId === event.data.device_id)) {
            this._refreshDeviceNames();
          }
        }, "device_registry_updated");
        if (this._deviceRegistryConnection === connection) this._unsubscribeDeviceRegistry = unsubscribe;
        else unsubscribe();
      } catch (err) {
        if (this._deviceRegistryConnection === connection) this._deviceRegistryConnection = null;
      }
    }

    _stopSeasonRegistrySubscription() {
      const unsubscribe = this._unsubscribeSeasonRegistry;
      this._unsubscribeSeasonRegistry = null;
      if (unsubscribe) unsubscribe();
    }

    async _refreshSeasonRegistry() {
      try {
        const entities = await this._hass.callWS({ type: "config/entity_registry/list" });
        if (!this.isConnected) return;
        const ids = entities.filter((e) => e.platform === "smart_shutter" && /_(summer|winter)$/.test(e.unique_id || ""))
          .map((e) => e.entity_id).sort().join(",");
        if (ids !== this._seasonRegistryIds) await this._loadRegistries();
      } catch (err) {
        // Keep open editors intact if registry refresh is temporarily unavailable.
      }
    }

    async _subscribeSeasonRegistry() {
      const connection = this._hass && this._hass.connection;
      if (!this.isConnected || !connection || !connection.subscribeEvents ||
          connection === this._seasonRegistryConnection) return;
      this._stopSeasonRegistrySubscription();
      this._seasonRegistryConnection = connection;
      try {
        const unsubscribe = await connection.subscribeEvents((event) => {
          if (!event.data || !["create", "remove"].includes(event.data.action)) return;
          clearTimeout(this._seasonRegistryTimer);
          this._seasonRegistryTimer = setTimeout(() => this._refreshSeasonRegistry(), 200);
        }, "entity_registry_updated");
        if (this._seasonRegistryConnection === connection) this._unsubscribeSeasonRegistry = unsubscribe;
        else unsubscribe();
      } catch (err) {
        if (this._seasonRegistryConnection === connection) this._seasonRegistryConnection = null;
      }
    }

    async _refreshDeviceNames() {
      try {
        const devices = await this._hass.callWS({ type: "config/device_registry/list" });
        if (!this._model || !this.isConnected) return;
        const byId = new Map(devices.map((device) => [device.id, device]));
        for (const shutter of this._model.allShutters || this._model.shutters) {
          const device = byId.get(shutter.deviceId);
          if (device) {
            shutter.name = device.name_by_user || device.name || shutter.coverEntityId;
            shutter.userName = device.name_by_user;
          }
        }
        this._updateValues();
      } catch (err) {
        // Keep the last registry names if Home Assistant is temporarily unavailable.
      }
    }

    async _loadRegistries(render = true) {
      const hass = this._hass;
      try {
        const [entities, devices, areas] = await Promise.all([
          hass.callWS({ type: "config/entity_registry/list" }),
          hass.callWS({ type: "config/device_registry/list" }),
          hass.callWS({ type: "config/area_registry/list" }),
        ]);
        let floors = [];
        try {
          floors = await hass.callWS({ type: "config/floor_registry/list" });
        } catch (err) {
          floors = []; // ältere HA-Version ohne Floor-Registry - kein Problem, Fallback greift
        }
        // HA-User list (v0.18, guest access per area) - ONLY for
        // Admins can retrieve (config/auth/list requires admin rights in
        // HA-Core). Non-admins don't need them anyway: they can
        // cannot edit access assignments, only their own,
        // see/control the already assigned area.
        let haUsers = [];
        if (this._isAdmin()) {
          try {
            haUsers = await hass.callWS({ type: "config/auth/list" });
          } catch (err) {
            haUsers = []; // Older HA versions may lack this API; hide access controls.
          }
        }
        this._seasonRegistryIds = entities.filter((e) => e.platform === "smart_shutter" && /_(summer|winter)$/.test(e.unique_id || ""))
          .map((e) => e.entity_id).sort().join(",");
        this._buildModel(entities, devices, areas, floors, haUsers);
        await this._loadBackendConfig();
        this._loadError = null;
      } catch (err) {
        this._loadError =
          "Registry-Daten konnten nicht geladen werden: " + (err && err.message ? err.message : String(err));
      }
      if (render) this._render();
    }

    _isAdmin() {
      return !!(this._hass && this._hass.user && this._hass.user.is_admin);
    }

    _language() {
      return String((this._hass && this._hass.language) || "en").toLowerCase().startsWith("de") ? "de" : "en";
    }

    _message(key, ...args) {
      const value = CARD_MESSAGES[this._language()][key];
      return typeof value === "function" ? value(...args) : value;
    }

    _actionLabel(action) {
      if (action === "open") return this._language() === "de" ? "öffnen" : "open";
      if (action === "close") return this._language() === "de" ? "schließen" : "close";
      return action || "";
    }

    _profileStateLabel(profile) {
      const normalized = LEGACY_PROFILE_IDS[profile] || profile;
      if (normalized === "weekday" || profile === "Arbeitstage") return this._language() === "de" ? "Arbeitstag" : "Weekday";
      if (normalized === "weekend" || profile === "Wochenende") return this._language() === "de" ? "Wochenende" : "Weekend";
      if (normalized === "holiday" || profile === "Ferien") return this._language() === "de" ? "Ferien" : "Holiday";
      return profile || "-";
    }

    _nextActionLabel(state) {
      if (!state) return "-";
      const action = state.attributes && state.attributes.action;
      const scheduledAt = state.attributes && state.attributes.scheduled_at;
      if (!action || !scheduledAt) return state.state;
      const time = new Date(scheduledAt).toLocaleTimeString(this._language() === "de" ? "de-DE" : "en-GB", {
        hour: "2-digit", minute: "2-digit", hour12: false,
      });
      return this._language() === "de"
        ? `${this._actionLabel(action)} um ${time} Uhr`
        : `${this._actionLabel(action)} at ${time}`;
    }

    _localizeDom() {
      const labels = CARD_TEXT[this._language()];
      const walker = document.createTreeWalker(this.shadowRoot, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const node = walker.currentNode;
        if (node.parentElement && ["STYLE", "SCRIPT"].includes(node.parentElement.tagName)) continue;
        const original = node.nodeValue;
        const normalized = original.replace(/\s+/g, " ").trim();
        const translated = labels[normalized] || (this._language() === "en" ? this._translateDynamicText(normalized) : null);
        if (translated && translated !== normalized) {
          node.nodeValue = original.replace(original.trim(), translated);
        }
      }
      this.shadowRoot.querySelectorAll("[title], [placeholder], [aria-label]").forEach((element) => {
        for (const attribute of ["title", "placeholder", "aria-label"]) {
          const original = element.getAttribute(attribute);
          if (original && labels[original]) element.setAttribute(attribute, labels[original]);
        }
      });
    }

    _translateDynamicText(text) {
      let match = text.match(/^Vorhersage \(nächste (\d+) Tage\)$/);
      if (match) return `Forecast (next ${match[1]} days)`;
      match = text.match(/^Alle \((\d+)\) Rollläden:$/);
      if (match) return `All (${match[1]}) shutters:`;
      match = text.match(/^(\d+) ausgewählt$/);
      if (match) return `${match[1]} selected`;
      match = text.match(/^(\d+) Rollladen zugeordnet$/);
      if (match) return `${match[1]} ${Number(match[1]) === 1 ? "shutter" : "shutters"} assigned`;
      match = text.match(/^(\d+) Rollladen$/);
      if (match) return `${match[1]} ${Number(match[1]) === 1 ? "shutter" : "shutters"}`;
      return null;
    }

    async _loadBackendConfig() {
      // Basic settings, Custom profiles, and External triggers - all,
      // what was previously only accessible via the options dialog (see
      // websocket_api.py). It is reset with every page reload and after
      // reloaded from their own storage each time, so the map is never loaded from the
      // deviates from the actual option.
      try {
        this._backendConfig = await this._hass.callWS({ type: "smart_shutter/get_config" });
        this._backendError = null;
      } catch (err) {
        this._backendConfig = null;
        this._backendError =
          "Einstellungen konnten nicht geladen werden: " + (err && err.message ? err.message : String(err));
      }
      this._applyAccessRestriction();
    }

    _applyAccessRestriction() {
      // v0.18 SECURITY FIX: this._model.shutters is used in _buildModel(),
      // built directly from the HA-Entity-/Device-Registry - completely
      // INDEPENDENT of the server-side filtering in get_config. Without
      // this method would have a guest restricted to a specific area
      // in the dashboard, in "All up/stop/down" and in the shutter tab
      // nevertheless, all shutters can be seen and operated, even though
      // The backend for it has long since only provided its own area.
      // this._model.shutters is therefore handled here - after EVERY get_config-
      // Fetch - truncated to the roller shutters allowed by the server.
      if (!this._model) return;
      this._model.allShutters = this._model.allShutters || this._model.shutters;
      const restricted = !!(this._backendConfig && this._backendConfig.restricted);
      this._restricted = restricted;
      if (!restricted) {
        this._model.shutters = this._model.allShutters;
        return;
      }
      const allowedIds = new Set(
        ((this._backendConfig && this._backendConfig.covers) || []).map((c) => c.entity_id)
      );
      this._model.shutters = this._model.allShutters.filter((s) => allowedIds.has(s.coverEntityId));
    }

    _isRestricted() {
      return !!this._restricted;
    }

    _buildModel(entities, devices, areas, floors, haUsers) {
      const areaById = Object.fromEntries(areas.map((a) => [a.area_id, a]));
      const floorById = Object.fromEntries(floors.map((f) => [f.floor_id, f]));

      const ourDevices = devices.filter((d) =>
        (d.identifiers || []).some(([dom]) => dom === DOMAIN)
      );

      let globalDevice = null;
      const shutterDevices = [];
      for (const d of ourDevices) {
        const ident = (d.identifiers || []).find(([dom]) => dom === DOMAIN);
        const rawId = ident ? ident[1] : "";
        if (rawId.startsWith(GLOBAL_PREFIX)) {
          globalDevice = d;
        } else if (rawId.startsWith(DEVICE_PREFIX)) {
          const coverEntityId = rawId.slice(DEVICE_PREFIX.length);
          shutterDevices.push({ device: d, coverEntityId });
        }
      }

      const entitiesByDevice = {};
      for (const e of entities) {
        if (e.platform !== DOMAIN) continue;
        (entitiesByDevice[e.device_id] = entitiesByDevice[e.device_id] || []).push(e);
      }

      const shutters = shutterDevices.map(({ device, coverEntityId }) => {
        const regEntries = entitiesByDevice[device.id] || [];
        const area = device.area_id ? areaById[device.area_id] : null;
        const floor = area && area.floor_id ? floorById[area.floor_id] : null;
        return {
          deviceId: device.id,
          coverEntityId,
          name: device.name_by_user || device.name || coverEntityId,
          userName: device.name_by_user,
          areaName: area ? area.name : null,
          floorName: floor ? floor.name : "Ohne Geschoss",
          floorLevel: floor && typeof floor.level === "number" ? floor.level : 9999,
          entities: this._categorizeEntities(regEntries),
        };
      });

      shutters.sort((a, b) => {
        if (a.floorLevel !== b.floorLevel) return a.floorLevel - b.floorLevel;
        if (a.floorName !== b.floorName) return a.floorName.localeCompare(b.floorName, "de");
        return a.name.localeCompare(b.name, "de");
      });

      const globalEntities = globalDevice
        ? this._categorizeEntities(entitiesByDevice[globalDevice.id] || [])
        : this._categorizeEntities([]);

      this._model = {
        shutters,
        globalEntities,
        haUsers: (haUsers || []).map((u) => ({ id: u.id, name: u.name })),
      };
    }

    _categorizeEntities(regEntries, includeSeasons = true) {
      const seasonalEntries = {};
      if (includeSeasons) {
        for (const season of ["summer", "winter"]) {
          seasonalEntries[season] = this._categorizeEntities(
            regEntries.filter((e) => (e.unique_id || "").endsWith(`_${season}`))
              .map((e) => ({ ...e, unique_id: e.unique_id.slice(0, -season.length - 1) })),
            false
          );
        }
        regEntries = regEntries.filter((e) => !/_(summer|winter)$/.test(e.unique_id || ""));
      }
      const model = {
        seasons: seasonalEntries,
        automation: {},
        sourceSelect: {},
        positionSourceSelect: {},
        localType: {},
        sunOffset: {},
        position: {},
        profileTimeSource: {},
        profileTime: {},
        activeProfile: null,
        nextAction: null,
        other: [],
      };
      for (const e of regEntries) {
        const domain = e.entity_id.split(".")[0];
        const uid = e.unique_id || "";
        let m;

        if (domain === "sensor") {
          if (uid.endsWith("_active_profile")) model.activeProfile = e;
          else if (uid.endsWith("_next_action")) model.nextAction = e;
          else model.other.push(e);
          continue;
        }
        if (domain === "switch") {
          if ((m = uid.match(/(?:^|_)automation_(open|close)$/))) {
            model.automation[m[1]] = e;
          } else {
            model.other.push(e);
          }
          continue;
        }
        if (domain === "select") {
          if ((m = uid.match(/_(open|close)_position_source$/))) {
            model.positionSourceSelect[m[1]] = e;
          } else if ((m = uid.match(/_(open|close)_(.+)_time_source$/))) {
            const profile = LEGACY_PROFILE_IDS[m[2]] || m[2];
            (model.profileTimeSource[profile] = model.profileTimeSource[profile] || {})[m[1]] = e;
          } else if ((m = uid.match(/_(open|close)_type$/))) {
            model.localType[m[1]] = e;
          } else if ((m = uid.match(/_(open|close)_source$/))) {
            model.sourceSelect[m[1]] = e;
          } else {
            model.other.push(e);
          }
          continue;
        }
        if (domain === "number") {
          if ((m = uid.match(/_(open|close)_sun_offset$/))) {
            model.sunOffset[m[1]] = e;
          } else if ((m = uid.match(/_(open|close)_position$/))) {
            model.position[m[1]] = e;
          } else {
            model.other.push(e);
          }
          continue;
        }
        if (domain === "time") {
          if ((m = uid.match(/_(open|close)_(.+)$/))) {
            const profile = LEGACY_PROFILE_IDS[m[2]] || m[2];
            (model.profileTime[profile] = model.profileTime[profile] || {})[m[1]] = e;
          } else {
            model.other.push(e);
          }
          continue;
        }
        model.other.push(e);
      }
      return model;
    }

    // ---------------------------------------------------------------
    // Helper functions for state/display
    // ---------------------------------------------------------------

    _state(entityId) {
      if (!this._hass || !entityId) return undefined;
      const real = this._hass.states[entityId];
      const override = this._optimisticState && this._optimisticState[entityId];
      if (override === undefined) return real;
      if (real && real.state === override) {
        delete this._optimisticState[entityId]; // echter State hat nachgezogen
        return real;
      }
      return real ? { ...real, state: override } : { entity_id: entityId, state: override, attributes: {} };
    }

    _friendlyName(regEntry) {
      if (!regEntry) return "";
      const st = this._state(regEntry.entity_id);
      return (st && st.attributes && st.attributes.friendly_name) || regEntry.entity_id;
    }

    _seasonalEnabled() {
      return !!(this._backendConfig && this._backendConfig.seasonal_enabled);
    }

    _activeSeason() {
      const entries = [
        this._model && this._model.globalEntities.nextAction,
        ...((this._model && this._model.shutters) || []).map((s) => s.entities.nextAction),
      ];
      for (const entry of entries) {
        const state = entry && this._state(entry.entity_id);
        if (state && state.attributes && state.attributes.active_season) return state.attributes.active_season;
      }
      return (this._backendConfig && this._backendConfig.active_season) || "winter";
    }

    _seasonEntities(entities, requestedSeason = null) {
      if (!this._seasonalEnabled()) return entities;
      const season = requestedSeason || this._editingSeason || this._activeSeason();
      const selected = entities.seasons && entities.seasons[season];
      if (!selected) return entities;
      const result = { ...entities };
      for (const key of ["sourceSelect", "localType", "sunOffset", "profileTimeSource", "profileTime"]) {
        result[key] = { ...entities[key], ...selected[key] };
      }
      return result;
    }

    _renderSeasonPicker() {
      if (!this._seasonalEnabled()) return "";
      const de = this._language() === "de";
      const labels = de ? { summer: "Sommerzeit", winter: "Winterzeit" } : { summer: "Summer time", winter: "Winter time" };
      const active = this._activeSeason();
      const selected = this._editingSeason || active;
      this._editingSeason = selected;
      return `<div class="hint" data-season-status>${de ? "Automatisch aktiv" : "Automatically active"}: ${labels[active]}</div>
        <div class="control-row"><label>${de ? "Profil bearbeiten" : "Edit profile"}</label>
          <select data-season-edit aria-label="${de ? "Saisonprofil bearbeiten" : "Edit seasonal profile"}">
            ${["summer", "winter"].map((season) => `<option value="${season}"${season === selected ? " selected" : ""}>${labels[season]}</option>`).join("")}
          </select>
        </div>`;
    }

    _profileIds(shutter) {
      const ids = new Set([...STATIC_PROFILE_ORDER]);
      Object.keys(shutter.entities.profileTime).forEach((id) => ids.add(id));
      Object.keys(shutter.entities.profileTimeSource).forEach((id) => ids.add(id));
      // Static first (fixed order), Custom-Profiles afterwards
      return [
        ...STATIC_PROFILE_ORDER.filter((id) => ids.has(id)),
        ...[...ids].filter((id) => !STATIC_PROFILE_ORDER.includes(id)).sort(),
      ];
    }

    _profileLabel(profileId, shutter) {
      if (STATIC_PROFILE_LABELS[profileId]) return this._profileStateLabel(profileId);
      // custom profile: the name given by the user from the
      // "friendly_name" derived from an associated Entity (it is
      // already built in via translation placeholders).
      const timeEntry =
        (shutter.entities.profileTime[profileId] && shutter.entities.profileTime[profileId].open) ||
        (shutter.entities.profileTime[profileId] && shutter.entities.profileTime[profileId].close);
      if (timeEntry) {
        const name = this._friendlyName(timeEntry);
        const match = name.match(/\(([^)]+)\)\s*$/);
        if (match) return match[1];
        return name;
      }
      return profileId;
    }

    // ---------------------------------------------------------------
    // Service calls
    // ---------------------------------------------------------------

    _toggleSwitch(entry) {
      if (!entry) return;
      this._haptic("light");
      const st = this._state(entry.entity_id);
      const isOn = st && st.state === "on";
      this._hass.callService("switch", isOn ? "turn_off" : "turn_on", {
        entity_id: entry.entity_id,
      });
    }

    _selectOption(entry, option) {
      if (!entry) return Promise.resolve();
      this._haptic("selection");
      return this._hass.callService("select", "select_option", {
        entity_id: entry.entity_id,
        option,
      });
    }

    _selectOptionLabel(option) {
      const language = (this._hass && this._hass.language || "en").startsWith("de") ? "de" : "en";
      return SELECT_OPTION_LABELS[language][option] || option;
    }

    _setTime(entry, value) {
      if (!entry || !value) return;
      this._haptic("light");
      this._hass.callService("time", "set_value", {
        entity_id: entry.entity_id,
        time: value,
      });
    }

    _setNumber(entry, value) {
      if (!entry) return;
      this._haptic("light");
      this._hass.callService("number", "set_value", {
        entity_id: entry.entity_id,
        value: Number(value),
      });
    }

    _showToast(message) {
      const container = this.shadowRoot.querySelector(".toast-container");
      if (!container) return;
      container.innerHTML = "";
      const toast = document.createElement("div");
      toast.className = "toast";
      toast.textContent = message;
      container.appendChild(toast);
      requestAnimationFrame(() => toast.classList.add("toast-visible"));
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => {
        toast.classList.remove("toast-visible");
        setTimeout(() => toast.remove(), 250);
      }, 2200);
    }

    _haptic(type) {
      // "success" | "warning" | "failure" | "light" | "medium" | "heavy" | "selection"
      // Is caught by the HA Companion App (iOS + Android) and converted into
      // real haptic feedback translated. On platforms without
      // Support (z.B. normal desktop browser) happens simply
      // nothing - completely not critical.
      try {
        window.dispatchEvent(new CustomEvent("haptic", { detail: type }));
      } catch (err) {
        /* uncritical, if not supported at all */
      }
    }

    _escapeHtml(text) {
      // Only needed for freely entered text that is NOT via its own
      // Options Flow comes (z.B. the "source" field from
      // smart_shutter.postpone_action/skip_action that every automation
      // can set arbitrarily) - protects against HTML/script injection via
      // Third-party service calls.
      const div = document.createElement("div");
      div.textContent = String(text);
      return div.innerHTML;
    }

    _coverAction(coverEntityId, action) {
      if (!coverEntityId) return;
      this._haptic("medium");
      if (action === "stop") {
        this._hass.callService("cover", "stop_cover", { entity_id: coverEntityId });
        return;
      }
      // Respects a configured position limit (see
      // _effectiveTargetPosition) also during manual individual operation -
      // z.B. Flower pot on the windowsill, gap for the cat to enter open
      // leave them out.
      const target = this._effectiveTargetPosition(coverEntityId, action);
      if (target === null) {
        this._hass.callService("cover", action === "open" ? "open_cover" : "close_cover", {
          entity_id: coverEntityId,
        });
      } else {
        this._hass.callService("cover", "set_cover_position", {
          entity_id: coverEntityId,
          position: target,
        });
      }
    }

    async _bulkApplySwitch(action, turnOn) {
      this._haptic("success");
      for (const deviceId of this._bulkSelection) {
        const s = this._shutterByDeviceId(deviceId);
        const entry = s && s.entities.automation[action];
        if (entry) {
          await this._hass.callService("switch", turnOn ? "turn_on" : "turn_off", {
            entity_id: entry.entity_id,
          });
        }
      }
    }

    async _bulkApplyPosition(action, value) {
      this._haptic("success");
      for (const deviceId of this._bulkSelection) {
        const s = this._shutterByDeviceId(deviceId);
        if (!s) continue;
        const sourceEntry = s.entities.positionSourceSelect[action];
        const sourceState = sourceEntry && this._state(sourceEntry.entity_id);
        if (sourceEntry && sourceState && sourceState.state !== SOURCE_OPTION_LOCAL) {
          // Without Source=Individual, the set value would be overridden by the backend
          // ignored (see scheduler.py/executor.py: Global takes precedence) -
          // therefore automatically switch here.
          await this._selectOption(sourceEntry, SOURCE_OPTION_LOCAL);
        }
        const entry = s.entities.position[action];
        if (entry) {
          await this._hass.callService("number", "set_value", { entity_id: entry.entity_id, value });
        }
      }
    }

    async _bulkPostponeAll(action, minutes) {
      this._haptic("success");
      const actionLabel = this._language() === "de" ? (action === "open" ? "Öffnen" : "Schließen") : (action === "open" ? "Open" : "Close");
      this._showToast(this._message("bulkPostpone", actionLabel, minutes));
      this._invalidateForecastCache();
      const ids = this._model.shutters.map((s) => s.coverEntityId);
      await Promise.all(
        ids.map((id) =>
          this._hass.callService(DOMAIN, "postpone_action", {
            entity_id: id,
            action,
            minutes,
            source: `Bulk: ${action === "open" ? "all open" : "all close"}`,
          })
        )
      );
    }

    async _bulkSkipAll(action) {
      this._haptic("success");
      const actionLabel = this._language() === "de" ? (action === "open" ? "Öffnen" : "Schließen") : (action === "open" ? "Open" : "Close");
      this._showToast(this._message("bulkSkip", actionLabel));
      this._invalidateForecastCache();
      const ids = this._model.shutters.map((s) => s.coverEntityId);
      await Promise.all(
        ids.map((id) =>
          this._hass.callService(DOMAIN, "skip_action", {
            entity_id: id,
            action,
            source: `Bulk: ${action === "open" ? "all open" : "all close"}`,
          })
        )
      );
    }

    _shutterByCoverId(coverEntityId) {
      return this._model && this._model.shutters.find((s) => s.coverEntityId === coverEntityId);
    }

    // v0.20.1: Position limit (z.B. "not further than 20% down because
    // flower pot on the windowsill") has so far ONLY been controlled by the
    // automatic time control respected (executor.py uses
    // set_cover_position with the configured value) - manual clicks
    // on "Down"/"Up" (individually, area, dashboard, list) have
    // instead send a raw close_cover/open_cover-Befehl cleverly,
    // the one that ignores the limit and drives to 0%/100%. This helper
    // provides the EFFECTIVE target position for a shutter (local
    // Override if "Individual", otherwise use the global default value) -
    // null, if no limit is configured (then the simple
    // open_cover/close_cover-Befehl remain unchanged).
    _effectiveTargetPosition(coverEntityId, action) {
      const s = this._shutterByCoverId(coverEntityId);
      if (!s) return null;
      const sourceEntry = s.entities.positionSourceSelect[action];
      const sourceState = sourceEntry && this._state(sourceEntry.entity_id);
      const useIndividual = sourceState && sourceState.state === SOURCE_OPTION_LOCAL;
      const posEntry = useIndividual
        ? s.entities.position[action]
        : this._model.globalEntities.position[action];
      if (!posEntry) return null;
      const st = this._state(posEntry.entity_id);
      if (!st) return null;
      const value = Number(st.state);
      if (Number.isNaN(value)) return null;
      const trivialDefault = action === "close" ? 0 : 100;
      return value === trivialDefault ? null : value;
    }

    // Groups a list of shutters according to their effective
    // Target position for "open"/"close" - shutters without limit (null)
    // end up in a group together (classic open_cover/
    // close_cover-Sammel-Call, unchanged behavior), shutters WITH
    // different limits get their own
    // set_cover_position-Call per individual value.
    _groupByEffectiveTarget(coverEntityIds, action) {
      const groups = new Map();
      for (const id of coverEntityIds) {
        const target = action === "stop" ? null : this._effectiveTargetPosition(id, action);
        if (!groups.has(target)) groups.set(target, []);
        groups.get(target).push(id);
      }
      return groups;
    }

    async _bulkCoverAction(coverEntityIds, action) {
      if (!coverEntityIds || !coverEntityIds.length) return;
      this._haptic("medium");
      const delayMs =
        (this._backendConfig && this._backendConfig.basic_settings &&
          this._backendConfig.basic_settings.stagger_delay_ms) || 0;

      if (action === "stop") {
        if (delayMs <= 0) {
          this._hass.callService("cover", "stop_cover", { entity_id: coverEntityIds });
        } else {
          (async () => {
            for (let i = 0; i < coverEntityIds.length; i++) {
              if (i > 0) await new Promise((resolve) => setTimeout(resolve, delayMs));
              this._hass.callService("cover", "stop_cover", { entity_id: coverEntityIds[i] });
            }
          })();
        }
        return;
      }

      // Group by effective target position (see
      // _groupByEffectiveTarget) - shutters without configured limit
      // (target === null) still get the simple
      // open_cover/close_cover-Befehl, shutters WITH limit a
      // set_cover_position-Aufruf to this exact value so that z.B. can
      // flower pot on the windowsill never moves even during manual operation
      // overridden.
      const groups = this._groupByEffectiveTarget(coverEntityIds, action);
      const calls = [];
      for (const [target, ids] of groups) {
        if (target === null) {
          calls.push({ domain: "cover", service: action === "open" ? "open_cover" : "close_cover", ids });
        } else {
          calls.push({ domain: "cover", service: "set_cover_position", ids, extra: { position: target } });
        }
      }

      if (delayMs <= 0) {
        for (const call of calls) {
          this._hass.callService("cover", call.service, { entity_id: call.ids, ...(call.extra || {}) });
        }
        return;
      }
      // Staggered command output (RF collision protection): individual
      // Service calls with delays between them instead of a
      // Collect calls, so that the commands are not all at the same time
      // exit. Deliberately not on the completion of the delay
      // waited (no "await" on the entire sequence), so the map
      // remains operable during this time.
      (async () => {
        const allIds = calls.flatMap((c) => c.ids.map((id) => ({ id, call: c })));
        for (let i = 0; i < allIds.length; i++) {
          if (i > 0) await new Promise((resolve) => setTimeout(resolve, delayMs));
          const { id, call } = allIds[i];
          this._hass.callService("cover", call.service, { entity_id: id, ...(call.extra || {}) });
        }
      })();
    }

    // ---------------------------------------------------------------
    // Rendering
    // ---------------------------------------------------------------

    _renderShell() {
      this.shadowRoot.innerHTML = `
        <style>${this._css()}</style>
        <ha-card>
          <div class="nav">
            <button data-nav="overview"><ha-icon icon="mdi:view-dashboard-outline"></ha-icon><span>Dashboard</span></button>
            <button data-nav="list"><ha-icon icon="mdi:window-shutter"></ha-icon><span>Shutters</span></button>
            <button data-nav="settings" class="nav-icon-only" title="Einstellungen" aria-label="Einstellungen"><ha-icon icon="mdi:cog-outline"></ha-icon></button>
          </div>
          <div class="body"></div>
          <div class="toast-container"></div>
        </ha-card>
      `;
      this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
      this.shadowRoot.addEventListener("change", (ev) => this._onChange(ev));
      this.shadowRoot.addEventListener("input", (ev) => this._onInput(ev));
      this.shadowRoot.addEventListener("dragstart", (ev) => this._onDragStart(ev));
      this.shadowRoot.addEventListener("dragover", (ev) => this._onDragOver(ev));
      this.shadowRoot.addEventListener("drop", (ev) => this._onDrop(ev));
      this.shadowRoot.addEventListener("dragend", (ev) => this._onDragEnd(ev));
    }

    // Aggregates the motion state of multiple roller shutters into one
    // shared "can open/stop/close" for Multi-Rollershutter-
    // Controls (Dashboard quick access, area quick access)
    // - just like with a single shutter (see data-quick-actions
    // further down), only via the group: a button is active as soon as
    // MINDESTENS EIN shutter of the group to perform the action meaningfully
    // would (z.B. "On" remains active as long as not ALL are already open).
    _groupMotionState(coverEntityIds) {
      let canOpen = false;
      let canClose = false;
      let canStop = false;
      for (const coverEntityId of coverEntityIds || []) {
        const { isFullyOpen, isFullyClosed, isOpening, isClosing } = this._coverMotionState(coverEntityId);
        if (!(isFullyOpen || isOpening)) canOpen = true;
        if (!(isFullyClosed || isClosing)) canClose = true;
        if (isOpening || isClosing) canStop = true;
      }
      return { canOpen, canClose, canStop };
    }

    _coverMotionState(coverEntityId) {
      const st = this._state(coverEntityId);
      const position = st && st.attributes ? st.attributes.current_position : undefined;
      const isOpening = !!(st && st.state === "opening");
      const isClosing = !!(st && st.state === "closing");
      const isMoving = isOpening || isClosing;
      // Some covers keep reporting the old endpoint position until their
      // first movement update. While the state says opening/closing, ignore
      // that stale endpoint so the user can stop or reverse the movement.
      return {
        isOpening,
        isClosing,
        isMoving,
        isFullyOpen: !isMoving && (position !== undefined ? position === 100 : !!(st && st.state === "open")),
        isFullyClosed: !isMoving && (position !== undefined ? position === 0 : !!(st && st.state === "closed")),
      };
    }

    _syncGroupMotionButtons(root) {
      // Dashboard quick access (all visible/allowed shutters).
      const dashGroup = root.querySelector(".ssm-shortcut-grid");
      if (dashGroup && this._model) {
        const ids = this._model.shutters.map((s) => s.coverEntityId);
        const { canOpen, canClose, canStop } = this._groupMotionState(ids);
        const openBtn = dashGroup.querySelector('[data-bulk="open"]');
        const stopBtn = dashGroup.querySelector('[data-bulk="stop"]');
        const closeBtn = dashGroup.querySelector('[data-bulk="close"]');
        if (openBtn) openBtn.disabled = !canOpen;
        if (stopBtn) stopBtn.disabled = !canStop;
        if (closeBtn) closeBtn.disabled = !canClose;
      }
      // area quick access - data-area-ids is already in the markup,
      // no separate lookup of area members needed.
      root.querySelectorAll(".area-quick-actions").forEach((group) => {
        const openBtn = group.querySelector('[data-area-bulk="open"]');
        if (!openBtn) return;
        const ids = (openBtn.getAttribute("data-area-ids") || "").split(",").filter(Boolean);
        const { canOpen, canClose, canStop } = this._groupMotionState(ids);
        const stopBtn = group.querySelector('[data-area-bulk="stop"]');
        const closeBtn = group.querySelector('[data-area-bulk="close"]');
        openBtn.disabled = !canOpen;
        if (stopBtn) stopBtn.disabled = !canStop;
        if (closeBtn) closeBtn.disabled = !canClose;
      });
      // Shutter tab: Collection bar "All (N) Shutter" - same
      // Motion-state logic like in the dashboard quick access, was previously
      // forgotten (see bug report - missing here as the only
      // Set the grayed-out display
      const listGroup = root.querySelector('.bulk-actions[data-bulk-group="list"]');
      if (listGroup && this._model) {
        const ids = this._filteredShutters().map((s) => s.coverEntityId);
        const { canOpen, canClose, canStop } = this._groupMotionState(ids);
        const openBtn = listGroup.querySelector('[data-bulk="open"]');
        const stopBtn = listGroup.querySelector('[data-bulk="stop"]');
        const closeBtn = listGroup.querySelector('[data-bulk="close"]');
        if (openBtn) openBtn.disabled = !canOpen;
        if (stopBtn) stopBtn.disabled = !canStop;
        if (closeBtn) closeBtn.disabled = !canClose;
      }
    }

    _css() {
      return `
        :host {
          --ssm-radius: 12px;
          --ssm-radius-sm: 8px;
          --ssm-border: var(--divider-color, #e4e4e7);
          --ssm-card-bg: var(--ha-card-background, var(--card-background-color, #fff));
          --ssm-muted: var(--secondary-text-color, rgba(0,0,0,0.6));
          --ssm-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.05);
          --ssm-shadow-hover: 0 4px 10px rgba(0,0,0,0.08), 0 1px 3px rgba(0,0,0,0.06);
          font-size: 15px; line-height: 1.5; /* etwas großzügiger als HA-Default - besser lesbar/antippbar */
        }
        ha-card {
          padding: 0; position: relative;
          max-width: 880px; margin: 0 auto; /* Seite nicht mehr edge-to-edge, wenn als volles Panel genutzt */
        }
        /* Generic base style for all buttons that (still) have no
           have own class - z.B. "+10 min", "Take over",
           "Save" in various forms. Intentionally as
           :not([class]), so that specifically styled buttons (.ssm-*,
           .nav button, .quick-actions button, ...) untouched
           remain - a simple "button { ... }" rule would override the
           Specificity otherwise overrides. */
        .body button:not([class]) {
          font: inherit; cursor: pointer; border: 1px solid var(--ssm-border); border-radius: var(--ssm-radius-sm);
          background: var(--ssm-card-bg); color: var(--primary-text-color); padding: 8px 14px;
          transition: background 0.15s ease, border-color 0.15s ease;
        }
        @media (hover: hover) and (pointer: fine) { .body button:not([class]):hover { border-color: var(--primary-color); } }
        .body button:not([class]):disabled { opacity: 0.4; cursor: default; }
        .toast-container { position: absolute; bottom: 10px; left: 0; right: 0; display: flex; justify-content: center; pointer-events: none; z-index: 20; }
        .toast {
          background: var(--primary-text-color, #212121); color: var(--primary-background-color, #fff);
          padding: 8px 16px; border-radius: 20px; font-size: 0.85em; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
          opacity: 0; transform: translateY(8px); transition: opacity 0.25s ease, transform 0.25s ease;
          max-width: 90%; text-align: center;
        }
        .toast.toast-visible { opacity: 1; transform: translateY(0); }
        .nav { display: flex; align-items: stretch; gap: 4px; padding: 12px 12px 0 12px; }
        .nav button {
          flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
          padding: 8px; border: none; border-radius: 8px;
          background: var(--secondary-background-color, #eee);
          color: var(--primary-text-color); font-weight: 500; cursor: pointer; font: inherit;
        }
        .nav button ha-icon { --mdc-icon-size: 20px; }
        .nav button.active { background: var(--primary-color); color: var(--text-primary-color, #fff); }
        .nav button.nav-icon-only { flex: 0 0 auto; width: 42px; }
        .body { padding: 12px; }
        h2 { font-size: 1.15em; font-weight: 700; letter-spacing: -0.01em; margin: 0 0 12px 0; }
        h3 {
          font-size: 0.72em; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
          color: var(--ssm-muted); margin: 22px 0 10px 0;
        }
        .floor { margin-bottom: 16px; }
        .floor-title { font-weight: 700; margin: 18px 0 8px 0; font-size: 0.95em; }
        .area-title { font-size: 0.72em; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ssm-muted); margin: 12px 0 6px 4px; }
        .row {
          display: flex; align-items: center; gap: 10px; padding: 12px; margin-bottom: 8px; cursor: pointer;
          background: var(--ssm-card-bg); border: 1px solid var(--ssm-border); border-radius: var(--ssm-radius);
          box-shadow: var(--ssm-shadow); transition: box-shadow 0.15s ease, border-color 0.15s ease;
        }
        @media (hover: hover) and (pointer: fine) { .row:hover { box-shadow: var(--ssm-shadow-hover); border-color: var(--primary-color); } }
        .row .main { flex: 1; min-width: 0; }
        .row .name { font-weight: 600; }
        .row .meta { font-size: 0.8em; color: var(--ssm-muted); margin-top: 1px; }
        .quick-actions { display: flex; gap: 4px; flex-shrink: 0; }
        .quick-actions button {
          border: 1px solid var(--ssm-border); background: var(--ssm-card-bg); border-radius: var(--ssm-radius-sm);
          width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
          cursor: pointer; color: var(--primary-text-color);
        }
        .quick-actions button:disabled { opacity: 0.3; cursor: default; }
        @media (hover: hover) and (pointer: fine) { .quick-actions button:hover:not(:disabled) { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); } }
        .quick-actions ha-icon { --mdc-icon-size: 18px; }
        .clickable-title { cursor: pointer; }
        @media (hover: hover) and (pointer: fine) { .clickable-title:hover { text-decoration: underline; } }
        .bulk-actions {
          display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
          margin-bottom: 12px; padding: 10px 12px; border-radius: var(--ssm-radius);
          background: var(--ssm-card-bg); border: 1px solid var(--ssm-border);
        }
        .bulk-label { font-size: 0.85em; color: var(--ssm-muted); margin-right: 4px; font-weight: 600; }
        .bulk-actions button {
          display: flex; align-items: center; gap: 4px; border: 1px solid var(--ssm-border); border-radius: var(--ssm-radius-sm);
          padding: 7px 12px; cursor: pointer; background: var(--ssm-card-bg);
          color: var(--primary-text-color); font: inherit; transition: background 0.15s ease, border-color 0.15s ease;
        }
        @media (hover: hover) and (pointer: fine) { .bulk-actions button:hover:not(:disabled) { border-color: var(--primary-color); } }
        .bulk-actions button:disabled { opacity: 0.4; cursor: default; }
        .bulk-actions ha-icon { --mdc-icon-size: 18px; }
        .pill {
          font-size: 0.75em; padding: 2px 8px; border-radius: 12px;
          background: var(--secondary-background-color, #eee);
        }
        .search {
          width: 100%; box-sizing: border-box; padding: 10px 12px; margin-bottom: 12px;
          border-radius: var(--ssm-radius-sm); border: 1px solid var(--ssm-border);
          background: var(--ssm-card-bg); color: inherit; font: inherit;
        }
        .tabs { display: flex; gap: 4px; margin-bottom: 16px; background: var(--secondary-background-color, #eee); padding: 4px; border-radius: var(--ssm-radius-sm); }
        .tabs button {
          flex: 1; padding: 7px 14px; border: none; border-radius: 6px; cursor: pointer; font: inherit; font-weight: 600;
          background: transparent; color: var(--primary-text-color);
        }
        .tabs button.active { background: var(--ssm-card-bg); box-shadow: var(--ssm-shadow); }
        .back {
          display: inline-flex; align-items: center; gap: 4px;
          background: none; border: none; cursor: pointer; color: var(--primary-color);
          padding: 0 0 12px 0; font-weight: 600; font: inherit;
        }
        .back ha-icon { --mdc-icon-size: 18px; }
        .section-toggle {
          display: flex; align-items: center; justify-content: space-between; width: 100%; box-sizing: border-box;
          padding: 10px 2px; margin: 18px 0 4px; border: none; border-top: 1px solid var(--ssm-border);
          background: none; cursor: pointer; font: inherit; text-align: left;
          font-size: 0.95em; font-weight: 700; color: var(--primary-text-color);
        }
        .section-toggle ha-icon { --mdc-icon-size: 20px; color: var(--ssm-muted); }
        @media (hover: hover) and (pointer: fine) { .section-toggle:hover span { color: var(--primary-color); } }
        table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
        table th, table td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--ssm-border); font-size: 0.9em; }
        .profile-times { container-type: inline-size; }
        @container (max-width: 600px) {
          .profile-times-table, .profile-times-table tbody { display: block; }
          .profile-times-table tr { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); padding-bottom: 12px; }
          .profile-times-table tr:first-child { display: none; }
          .profile-times-table td { min-width: 0; border-bottom: 0; }
          .profile-times-table td:first-child { grid-column: 1 / -1; font-weight: 600; border-top: 1px solid var(--ssm-border); }
          .profile-times-table td[data-label]::before { content: attr(data-label); display: block; margin-bottom: 6px; color: var(--secondary-text-color); }
          .profile-times-table select, .profile-times-table input { width: 100%; min-width: 0; box-sizing: border-box; }
        }
        .control-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
        .control-row label { min-width: 140px; font-size: 0.92em; }
        input[type="time"], input[type="number"], input[type="text"], select {
          background: var(--ssm-card-bg); color: inherit; border: 1px solid var(--ssm-border);
          border-radius: var(--ssm-radius-sm); padding: 7px 9px; font: inherit;
        }
        input:disabled, select:disabled {
          opacity: 0.55; background: var(--secondary-background-color, #eee);
          cursor: not-allowed; font-style: italic;
        }
        input[type="range"] { flex: 1; min-width: 100px; }
        input.number-exact {
          width: 60px; text-align: right; -moz-appearance: textfield;
        }
        input.number-exact::-webkit-outer-spin-button,
        input.number-exact::-webkit-inner-spin-button { margin-left: 4px; }
        .control-row .unit { font-size: 0.85em; opacity: 0.75; min-width: 28px; }
        .switch-toggle { position: relative; display: inline-block; width: 46px; height: 26px; flex-shrink: 0; }
        .switch-toggle input { display: none; }
        .switch-toggle .slider {
          position: absolute; inset: 0; background: var(--ssm-border, #ccc);
          border-radius: 26px; cursor: pointer; transition: 0.15s;
        }
        .switch-toggle .slider::before {
          content: ""; position: absolute; width: 20px; height: 20px; left: 3px; top: 3px;
          background: white; border-radius: 50%; transition: 0.15s; box-shadow: 0 1px 2px rgba(0,0,0,0.2);
        }
        .switch-toggle input:checked + .slider { background: var(--primary-color); }
        .switch-toggle input:checked + .slider::before { transform: translateX(20px); }
        .hint {
          font-size: 0.85em; color: var(--ssm-muted); background: var(--ssm-card-bg);
          border: 1px solid var(--ssm-border); border-radius: var(--ssm-radius-sm); padding: 10px 12px; margin: 12px 0;
        }
        .notification-info { display: inline-block; vertical-align: middle; margin-left: 4px; }
        .notification-info summary {
          display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px;
          border: 1px solid var(--ssm-border); border-radius: 50%; color: var(--ssm-muted); cursor: pointer;
          font-size: 0.88em; font-weight: 700; line-height: 1; list-style: none;
        }
        .notification-info summary::-webkit-details-marker { display: none; }
        .notification-info summary:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
        .notification-info-text {
          position: absolute; z-index: 5; top: 32px; left: 0; width: min(280px, 100%); box-sizing: border-box;
          padding: 10px 12px; border: 1px solid var(--ssm-border); border-radius: var(--ssm-radius-sm);
          background: var(--ssm-card-bg); box-shadow: var(--ssm-shadow); color: var(--primary-text-color);
          font-size: 0.82em; font-weight: 400; line-height: 1.4;
        }
        .notification-title { position: relative; display: flex; align-items: center; gap: 2px; }
        .notification-title h3 { margin-right: 0; }
        .notification-title .notification-info { margin-left: auto; flex-shrink: 0; }
        .notification-title .notification-info-text { left: auto; right: 0; }
        .notification-hint { position: relative; display: block; width: 100%; }
        .notification-status { display: block; min-height: 1.2em; margin: 4px 0 10px; font-size: 0.8em; color: var(--ssm-muted); }
        .error { color: var(--error-color, #c62828); }
        .settings-menu { display: flex; flex-direction: column; gap: 8px; }
        .settings-menu-item {
          display: flex; align-items: center; gap: 12px; padding: 14px; text-align: left;
          border: 1px solid var(--ssm-border); border-radius: var(--ssm-radius); background: var(--ssm-card-bg);
          box-shadow: var(--ssm-shadow); color: var(--primary-text-color); cursor: pointer; width: 100%; box-sizing: border-box;
          transition: box-shadow 0.15s ease, border-color 0.15s ease;
        }
        @media (hover: hover) and (pointer: fine) { .settings-menu-item:hover { box-shadow: var(--ssm-shadow-hover); border-color: var(--primary-color); } }
        .settings-menu-item ha-icon {
          --mdc-icon-size: 20px; flex-shrink: 0; color: var(--primary-color);
          width: 38px; height: 38px; display: flex; align-items: center; justify-content: center;
          border-radius: var(--ssm-radius-sm); background: color-mix(in srgb, var(--primary-color) 12%, transparent);
        }
        .settings-menu-item .name { font-weight: 600; font-size: 0.95em; }
        .settings-menu-item .meta { font-size: 0.78em; color: var(--ssm-muted); }

        .area-quick-actions { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
        .area-quick-actions button {
          width: 36px; height: 36px; border-radius: var(--ssm-radius-sm); border: 1px solid var(--ssm-border);
          background: var(--ssm-card-bg); color: var(--primary-text-color); cursor: pointer;
          display: flex; align-items: center; justify-content: center;
        }
        .area-quick-actions button:disabled { opacity: 0.35; cursor: default; }
        @media (hover: hover) and (pointer: fine) { .area-quick-actions button:hover:not(:disabled) { border-color: var(--primary-color); color: var(--primary-color); } }
        .area-quick-actions ha-icon { --mdc-icon-size: 18px; }
        .area-quick-actions .area-toggle-divider {
          display: inline-flex; align-items: center; margin-left: 10px; padding-left: 10px; border-left: 1px solid var(--ssm-border);
        }
        .form-grid { display: flex; flex-direction: column; gap: 14px; margin-bottom: 16px; }
        .form-field label { display: block; font-size: 0.82em; font-weight: 600; margin-bottom: 5px; color: var(--ssm-muted); }
        .form-field input, .form-field textarea, .form-field select {
          width: 100%; box-sizing: border-box; padding: 9px 10px; border-radius: var(--ssm-radius-sm);
          border: 1px solid var(--ssm-border); background: var(--ssm-card-bg); color: inherit; font-family: inherit;
        }
        .entity-picker-slot ha-entity-picker { width: 100%; display: block; }
        .managed-cover-row { margin-bottom: 20px; min-width: 0; overflow-wrap: anywhere; }
        .managed-cover-row .control-row { margin-bottom: 6px; flex-wrap: nowrap; align-items: flex-start; }
        .managed-cover-row .control-row span { flex: 1; min-width: 0; }
        .managed-cover-row input[type="checkbox"] { flex-shrink: 0; margin-top: 3px; }
        .form-field textarea { min-height: 60px; resize: vertical; }
        .form-field .meta, .meta { font-size: 0.8em; color: var(--ssm-muted); margin-top: 4px; }
        .save-btn {
          padding: 11px 22px; border: 1px solid var(--primary-color); border-radius: var(--ssm-radius-sm); cursor: pointer;
          background: var(--primary-color); color: var(--text-primary-color, #fff); font-weight: 600; font: inherit;
        }
        .save-btn:disabled { opacity: 0.5; cursor: default; }
        .list-item {
          display: flex; align-items: center; gap: 8px; padding: 12px; border-radius: var(--ssm-radius);
          background: var(--ssm-card-bg); border: 1px solid var(--ssm-border); box-shadow: var(--ssm-shadow); margin-bottom: 8px;
        }
        .list-item.dragging { opacity: 0.4; }
        .list-item.drag-over { outline: 2px dashed var(--primary-color); }
        .drag-handle {
          border: none; background: transparent; cursor: grab; color: var(--primary-text-color);
          opacity: 0.6; display: flex; align-items: center; justify-content: center; width: 28px; height: 28px; flex-shrink: 0;
        }
        .list-item .main { flex: 1; }
        .list-item .name { font-weight: 600; }
        .list-item .meta { font-size: 0.8em; color: var(--ssm-muted); margin-top: 1px; }
        .list-item .actions { display: flex; gap: 4px; }
        .list-item .actions button {
          border: 1px solid var(--ssm-border); background: var(--ssm-card-bg); cursor: pointer; color: var(--primary-text-color);
          width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; border-radius: var(--ssm-radius-sm);
        }
        @media (hover: hover) and (pointer: fine) { .list-item .actions button:hover { border-color: var(--primary-color); color: var(--primary-color); } }
        .add-btn {
          display: flex; align-items: center; justify-content: center; gap: 6px; padding: 12px; border-radius: var(--ssm-radius);
          border: 1.5px dashed var(--ssm-border); background: transparent; color: var(--primary-color); font-weight: 600; font: inherit;
          cursor: pointer; width: 100%; margin-top: 4px; margin-bottom: 12px; transition: border-color 0.15s ease;
        }
        @media (hover: hover) and (pointer: fine) { .add-btn:hover { border-color: var(--primary-color); } }
        .weekday-picker { display: flex; gap: 4px; flex-wrap: wrap; }
        .weekday-picker label {
          display: flex; align-items: center; justify-content: center; width: 38px; height: 38px;
          border-radius: 50%; background: var(--ssm-card-bg); border: 1px solid var(--ssm-border); cursor: pointer; font-size: 0.8em;
        }
        .weekday-picker input { display: none; }
        .weekday-picker label:has(input:checked) { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); }
        .conflict-box {
          display: flex; align-items: flex-start; gap: 8px;
          background: color-mix(in srgb, var(--warning-color, #ff9800) 12%, var(--ssm-card-bg));
          border: 1px solid var(--warning-color, #ff9800); color: var(--primary-text-color);
          border-radius: var(--ssm-radius-sm); padding: 10px 12px; margin-bottom: 12px;
        }
        .conflict-badge {
          background: var(--warning-color, #ff9800); color: #fff; border-radius: 6px; padding: 1px 6px;
          font-size: 0.75em; margin-left: 6px; cursor: help;
        }
        .timeline { position: relative; height: 34px; background: var(--secondary-background-color, #eee); border-radius: 6px; margin: 8px 0 22px; }
        .tl-tick { position: absolute; top: 0; bottom: 0; width: 1px; background: var(--divider-color, #ccc); opacity: 0.45; }
        .tl-tick.tl-tick-hour { opacity: 0.8; }
        .tl-tick-label { position: absolute; top: 100%; left: 0; transform: translateX(-50%); font-size: 0.65em; opacity: 0.75; white-space: nowrap; margin-top: 3px; }
        .tl-marker {
          position: absolute; top: 50%; width: 14px; height: 14px; border-radius: 50%;
          transform: translate(-50%, -50%); cursor: pointer;
        }
        .tl-marker::after {
          /* Increases the actually clickable area to ~30px
             without appearing visually larger - small markers would otherwise
             hard to hit with touch. */
          content: ""; position: absolute; top: -8px; left: -8px; right: -8px; bottom: -8px;
        }
        .tl-marker.tl-open { background: var(--info-color, #2196f3); }
        .tl-marker.tl-past { opacity: 0.4; }
        .forecast-list-toggle {
          display: block; width: 100%; text-align: left; background: none; border: none;
          color: var(--primary-color); cursor: pointer; padding: 4px 0; font: inherit;
        }
        .forecast-list-table { margin-top: 4px; }
        .forecast-list-table tr.tl-row-past { opacity: 0.5; }
        .tl-marker.tl-close { background: var(--primary-color, #ff5722); }
        .tl-marker.tl-selected { outline: 2px solid var(--text-primary-color, #000); outline-offset: 1px; }
        .tl-legend { display: inline-block; width: 10px; height: 10px; border-radius: 2px; vertical-align: middle; }
        .tl-legend.tl-past { border-radius: 50%; opacity: 0.4; }
        .tl-legend.tl-open { background: var(--info-color, #2196f3); }
        .tl-legend.tl-close { background: var(--primary-color, #ff5722); }
        .native-timeline-scroll {
          display: flex; gap: 14px; overflow-x: auto; padding-bottom: 6px; margin-bottom: 4px;
          scroll-snap-type: x proximity;
        }
        .native-timeline-day {
          flex: 0 0 auto; width: 220px; scroll-snap-align: start;
        }
        .native-timeline-day-label {
          font-size: 0.8em; font-weight: 600; opacity: 0.8; margin-bottom: 4px;
        }
        .native-timeline-day-today .native-timeline-day-label { color: var(--primary-color); }
        .native-timeline-day .timeline { margin: 4px 0 18px; height: 30px; }
        .empty { opacity: 0.7; font-style: italic; }
        a.link-btn, button.link-btn { display: inline-block; margin-top: 6px; color: var(--primary-color); cursor: pointer; background: none; border: none; padding: 0; font: inherit; }

        /* ---------------------------------------------------------------
           Dashboard redesign (preview, style inspired by shadcn/ui
           (Shelly Manager) - own class namespace (prefix "ssm-"),
           consciously separated from the above, which are still used elsewhere
           used classes. Maps with real border+shadow instead of
           flatter --secondary-background-color blocks, clear
           Typo hierarchy is based on weight instead of just Opacity, subtle instead
           vividly colored hover states. Still uses HAs
           own --primary-color/--card-background-color etc., so that it
           fits into every HA theme (light/dark) instead of being
           own, fixed color scheme to bring along.
        --------------------------------------------------------------- */
        .ssm-title { font-size: 1.15em; font-weight: 700; letter-spacing: -0.01em; margin: 0 0 14px 0; }
        .ssm-detail-header { padding: 16px; margin-bottom: 16px; }
        .ssm-detail-header h2 { margin-bottom: 6px; }
        .ssm-detail-header .meta { color: var(--ssm-muted); font-size: 0.88em; margin-bottom: 12px; }
        .ssm-detail-header .quick-actions button { width: 40px; height: 40px; }
        .ssm-section-label {
          font-size: 0.72em; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
          color: var(--ssm-muted); margin: 22px 0 10px 2px;
        }
        .ssm-card {
          background: var(--ssm-card-bg); border: 1px solid var(--ssm-border); border-radius: var(--ssm-radius);
          box-shadow: var(--ssm-shadow);
        }
        .ssm-stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px,1fr)); gap: 10px; margin-bottom: 6px; }
        .ssm-stat {
          display: flex; flex-direction: column; align-items: center; gap: 4px; text-align: center;
          background: var(--ssm-card-bg, #fff); border: 1px solid var(--ssm-border); border-radius: var(--ssm-radius);
          box-shadow: var(--ssm-shadow); padding: 16px 8px;
        }
        .ssm-stat ha-icon { --mdc-icon-size: 24px; color: var(--primary-color); margin-bottom: 2px; }
        .ssm-stat-num { font-size: 1.5em; font-weight: 700; letter-spacing: -0.02em; line-height: 1.1; }
        .ssm-stat-label { font-size: 0.8em; font-weight: 600; color: var(--ssm-muted); }
        .ssm-next-action {
          display: flex; align-items: center; gap: 8px; font-size: 0.85em; color: var(--ssm-muted);
          margin: 12px 2px 0; padding: 10px 12px; background: var(--ssm-card-bg); border: 1px solid var(--ssm-border);
          border-radius: var(--ssm-radius-sm);
        }
        .ssm-next-action ha-icon { --mdc-icon-size: 18px; flex-shrink: 0; }
        .ssm-next-action strong { color: var(--primary-text-color); font-weight: 600; }
        .ssm-shortcut-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        .ssm-shortcut-btn {
          display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 16px 8px;
          background: var(--ssm-card-bg); color: var(--primary-text-color); border: 1px solid var(--ssm-border);
          border-radius: var(--ssm-radius); box-shadow: var(--ssm-shadow); cursor: pointer;
          font-size: 0.88em; font-weight: 600; transition: box-shadow 0.15s ease, transform 0.15s ease, border-color 0.15s ease;
        }
        .ssm-shortcut-btn ha-icon { --mdc-icon-size: 26px; color: var(--primary-color); }
        .ssm-shortcut-btn-muted ha-icon { color: var(--ssm-muted); }
        @media (hover: hover) and (pointer: fine) {
          .ssm-shortcut-btn:hover { box-shadow: var(--ssm-shadow-hover); border-color: var(--primary-color); transform: translateY(-1px); }
        }
        .ssm-shortcut-btn:active { transform: translateY(0); box-shadow: var(--ssm-shadow); }
        .ssm-shortcut-btn:disabled {
          opacity: 0.4; cursor: default; box-shadow: none; transform: none;
        }
        .ssm-shortcut-btn:disabled:hover { box-shadow: none; border-color: var(--ssm-border); transform: none; }
        .ssm-automation-card { padding: 4px 14px; margin-top: 14px; }
        .ssm-automation-card .control-row { margin: 10px 0; }
        .ssm-inline-hint {
          display: flex; align-items: flex-start; gap: 8px; padding: 12px 2px; font-size: 0.85em; color: var(--ssm-muted);
        }
        .ssm-inline-hint ha-icon { --mdc-icon-size: 18px; flex-shrink: 0; margin-top: 1px; }
        .ssm-nav-grid { display: flex; flex-direction: column; gap: 8px; margin-top: 14px; }
        .ssm-nav-card {
          display: flex; align-items: center; gap: 12px; padding: 12px 14px; text-align: left;
          background: var(--ssm-card-bg); color: var(--primary-text-color); border: 1px solid var(--ssm-border);
          border-radius: var(--ssm-radius); box-shadow: var(--ssm-shadow); cursor: pointer; width: 100%; box-sizing: border-box;
          transition: box-shadow 0.15s ease, border-color 0.15s ease;
        }
        @media (hover: hover) and (pointer: fine) { .ssm-nav-card:hover { box-shadow: var(--ssm-shadow-hover); border-color: var(--primary-color); } }
        .ssm-nav-icon {
          display: flex; align-items: center; justify-content: center; width: 38px; height: 38px; flex-shrink: 0;
          border-radius: var(--ssm-radius-sm); background: color-mix(in srgb, var(--primary-color) 12%, transparent);
        }
        .ssm-nav-icon ha-icon { --mdc-icon-size: 20px; color: var(--primary-color); }
        .ssm-nav-text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
        .ssm-nav-title { font-weight: 600; font-size: 0.95em; }
        .ssm-nav-meta { font-size: 0.78em; color: var(--ssm-muted); }
        .ssm-nav-chevron { --mdc-icon-size: 20px; color: var(--ssm-muted); flex-shrink: 0; }
        .ssm-timeline-card { padding: 14px; margin-top: 2px; }
        .ssm-link-btn {
          display: inline-block; margin-top: 14px; background: none; border: none; cursor: pointer;
          color: var(--primary-color); font-size: 0.85em; font-weight: 600; padding: 4px 0; font-family: inherit;
        }
      `;
    }

    _onClick(ev) {
      const navBtn = ev.target.closest("[data-nav]");
      if (navBtn) {
        this._haptic("selection");
        this._view = navBtn.getAttribute("data-nav");
        this._render();
        return;
      }
      const tabBtn = ev.target.closest("[data-tab]");
      if (tabBtn) {
        this._haptic("selection");
        this._detailTab = tabBtn.getAttribute("data-tab");
        if (this._detailTab === "verlauf") {
          const s = this._shutterByDeviceId(this._detailDeviceId);
          if (s) {
            this._loadHistory(s.coverEntityId);
            this._loadForecast(s.coverEntityId);
          }
        }
        this._render();
        return;
      }
      const backBtn = ev.target.closest("[data-back]");
      if (backBtn) {
        this._haptic("selection");
        this._view = "list";
        this._render();
        return;
      }
      const settingsNavBtn = ev.target.closest("[data-settings-nav]");
      if (settingsNavBtn) {
        this._haptic("selection");
        this._view = settingsNavBtn.getAttribute("data-settings-nav");
        if (this._view === "settings-shutters") this._loadManagedCovers();
        this._render();
        return;
      }
      const settingsBackBtn = ev.target.closest("[data-settings-back]");
      if (settingsBackBtn) {
        this._haptic("selection");
        this._view = "settings";
        this._render();
        return;
      }
      const saveBasicBtn = ev.target.closest("[data-save-basic]");
      if (saveBasicBtn) {
        this._saveBasicSettings();
        return;
      }
      const saveShutterNoteBtn = ev.target.closest("[data-save-shutter-note]");
      if (saveShutterNoteBtn) {
        const coverEntityId = saveShutterNoteBtn.getAttribute("data-save-shutter-note");
        const textarea = this.shadowRoot.querySelector(`[data-shutter-note="${coverEntityId}"]`);
        this._saveShutterNote(coverEntityId, textarea ? textarea.value : "");
        return;
      }
      const settingsBackSchedulesBtn = ev.target.closest("[data-settings-back-schedules]");
      if (settingsBackSchedulesBtn) {
        this._haptic("selection");
        this._editingScheduleId = null;
        this._exitEditor("settings-schedules");
        this._render();
        return;
      }

      const settingsBackAreasBtn = ev.target.closest("[data-settings-back-areas]");
      if (settingsBackAreasBtn) {
        this._haptic("selection");
        this._editingAreaId = null;
        this._view = "settings-areas";
        this._render();
        return;
      }
      const toggleDashMoreBtn = ev.target.closest("[data-toggle-dash-more]");
      if (toggleDashMoreBtn) {
        this._haptic("selection");
        this._dashMoreActionsExpanded = !this._dashMoreActionsExpanded;
        this._render();
        return;
      }
      const toggleForecastListBtn = ev.target.closest("[data-toggle-forecast-list]");
      if (toggleForecastListBtn) {
        this._haptic("selection");
        const key = `_forecastListExpanded_${toggleForecastListBtn.getAttribute("data-toggle-forecast-list")}`;
        this[key] = !this[key];
        this._render();
        return;
      }
      const toggleSunAdvancedBtn = ev.target.closest("[data-toggle-sun-advanced]");
      if (toggleSunAdvancedBtn) {
        this._haptic("selection");
        this._sunAdvancedExpanded = !this._sunAdvancedExpanded;
        this._render();
        return;
      }
      const toggleAreaSectionBtn = ev.target.closest("[data-toggle-area-section]");
      if (toggleAreaSectionBtn) {
        this._haptic("selection");
        const key = toggleAreaSectionBtn.getAttribute("data-toggle-area-section");
        this._areaSectionExpanded[key] = !this._areaSectionExpanded[key];
        this._render();
        return;
      }
      const areaEditBtn = ev.target.closest("[data-area-edit]");
      if (areaEditBtn) {
        this._haptic("selection");
        const id = areaEditBtn.getAttribute("data-area-edit");
        this._editingAreaId = id === "__new__" ? null : id;
        this._sunAdvancedExpanded = false;
        this._areaSectionExpanded = {};
        this._sunDirectionOverride = undefined;
        this._view = "settings-area-edit";
        this._render();
        return;
      }
      const areaDeleteBtn = ev.target.closest("[data-area-delete]");
      if (areaDeleteBtn) {
        this._haptic("warning");
        const id = areaDeleteBtn.getAttribute("data-area-delete");
        const areas = ((this._backendConfig && this._backendConfig.custom_areas) || []).filter((a) => a.id !== id);
        this._saveAreas(areas);
        return;
      }
      const areaApplyBtn = ev.target.closest("[data-area-apply]");
      if (areaApplyBtn) {
        this._haptic("success");
        this._applyAreaToMembers(areaApplyBtn.getAttribute("data-area-apply"));
        return;
      }
      const areaSaveBtn = ev.target.closest("[data-area-save]");
      if (areaSaveBtn) {
        this._haptic("selection");
        this._collectAndSaveArea().catch((err) => {
          const status = this.shadowRoot.querySelector("[data-save-status]");
          if (status) status.textContent = this._message("errorPrefix") + (err.message || String(err));
          this._haptic("failure");
        });
        return;
      }
      const scheduleEditBtn = ev.target.closest("[data-schedule-edit]");
      if (scheduleEditBtn) {
        this._haptic("selection");
        const id = scheduleEditBtn.getAttribute("data-schedule-edit");
        this._editingScheduleId = id === "__new__" ? null : id;
        const editReturn = scheduleEditBtn.getAttribute("data-edit-return");
        if (editReturn === "detail") {
          this._editReturnView = "detail";
          this._editReturnDetailDeviceId = this._detailDeviceId;
          this._editReturnAreaId = null;
        } else if (editReturn === "area") {
          this._editReturnView = "area";
          this._editReturnAreaId = scheduleEditBtn.getAttribute("data-edit-return-area-id");
          this._editReturnDetailDeviceId = null;
        } else {
          this._editReturnView = null;
          this._editReturnDetailDeviceId = null;
          this._editReturnAreaId = null;
        }
        this._view = "settings-schedule-edit";
        this._render();
        return;
      }
      const scheduleDeleteBtn = ev.target.closest("[data-schedule-delete]");
      if (scheduleDeleteBtn) {
        this._deleteSchedule(scheduleDeleteBtn.getAttribute("data-schedule-delete"));
        return;
      }
      const saveScheduleBtn = ev.target.closest("[data-save-schedule]");
      if (saveScheduleBtn) {
        this._saveSchedule();
        return;
      }
      const settingsBackTriggersBtn = ev.target.closest("[data-settings-back-triggers]");
      if (settingsBackTriggersBtn) {
        this._haptic("selection");
        this._editingTriggerId = null;
        this._exitEditor("settings-triggers");
        this._render();
        return;
      }
      const triggerEditBtn = ev.target.closest("[data-trigger-edit]");
      if (triggerEditBtn) {
        this._haptic("selection");
        const id = triggerEditBtn.getAttribute("data-trigger-edit");
        this._editingTriggerId = id === "__new__" ? null : id;
        this._triggerTargetMode = null;
        this._prefillTriggerCover = triggerEditBtn.getAttribute("data-prefill-cover") || null;
        if (triggerEditBtn.getAttribute("data-edit-return") === "detail") {
          this._editReturnView = "detail";
          this._editReturnDetailDeviceId = this._detailDeviceId;
        } else {
          this._editReturnView = null;
          this._editReturnDetailDeviceId = null;
        }
        this._view = "settings-trigger-edit";
        this._render();
        return;
      }
      const triggerDeleteBtn = ev.target.closest("[data-trigger-delete]");
      if (triggerDeleteBtn) {
        this._deleteTrigger(triggerDeleteBtn.getAttribute("data-trigger-delete"));
        return;
      }
      const saveTriggerBtn = ev.target.closest("[data-save-trigger]");
      if (saveTriggerBtn) {
        this._saveTrigger();
        return;
      }
      if (ev.target.closest("[data-retry-covers]")) {
        this._saveManagedCovers();
        return;
      }
      // Keep these actions ahead of the containing row click handler.
      const quickBtn = ev.target.closest("[data-quick]");
      if (quickBtn) {
        ev.stopPropagation();
        const container = ev.target.closest("[data-quick-actions]");
        const coverEntityId = container && container.getAttribute("data-quick-actions");
        const action = quickBtn.getAttribute("data-quick");
        this._coverAction(coverEntityId, action);
        return;
      }
      const moreInfoEl = ev.target.closest("[data-open-more-info]");
      if (moreInfoEl) {
        const entityId = moreInfoEl.getAttribute("data-open-more-info");
        this.dispatchEvent(
          new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true })
        );
        return;
      }
      const globalTlMarker = ev.target.closest("[data-global-tl-marker]");
      if (globalTlMarker) {
        this._haptic("selection");
        const idx = parseInt(globalTlMarker.getAttribute("data-global-tl-marker"), 10);
        this._globalTimelineSelectedIdx = this._globalTimelineSelectedIdx === idx ? null : idx;
        this._render();
        return;
      }
      const shutterTlMarker = ev.target.closest("[data-shutter-tl-marker]");
      if (shutterTlMarker) {
        this._haptic("selection");
        const idx = parseInt(shutterTlMarker.getAttribute("data-shutter-tl-marker"), 10);
        this._shutterTlSelectedIdx = this._shutterTlSelectedIdx === idx ? null : idx;
        this._render();
        return;
      }
      const globalTlEditShutterBtn = ev.target.closest("[data-global-tl-edit-shutter]");
      if (globalTlEditShutterBtn) {
        this._haptic("selection");
        this._detailDeviceId = globalTlEditShutterBtn.getAttribute("data-global-tl-edit-shutter");
        this._detailTab = "basic";
        this._view = "detail";
        this._globalTimelineSelectedIdx = null;
        this._render();
        return;
      }
      const globalTlEditProfilesBtn = ev.target.closest("[data-global-tl-edit-profiles]");
      if (globalTlEditProfilesBtn) {
        this._haptic("selection");
        this._globalTimelineSelectedIdx = null;
        this._view = "settings-schedules";
        this._render();
        return;
      }
      const clearOverrideBtn = ev.target.closest("[data-clear-override]");
      if (clearOverrideBtn) {
        this._haptic("success");
        this._showToast(this._message("overrideCleared"));
        this._invalidateForecastCache();
        this._hass.callService("smart_shutter", "clear_override", {
          entity_id: clearOverrideBtn.getAttribute("data-cover"),
          action: clearOverrideBtn.getAttribute("data-clear-override"),
        });
        return;
      }
      const clearManualPauseBtn = ev.target.closest("[data-clear-manual-pause]");
      if (clearManualPauseBtn) {
        this._haptic("success");
        this._showToast(this._message("manualPauseCleared"));
        this._hass.callService("smart_shutter", "clear_manual_pause", {
          entity_id: clearManualPauseBtn.getAttribute("data-clear-manual-pause"),
        });
        return;
      }
      const bulkBtn = ev.target.closest("[data-bulk]");
      if (bulkBtn) {
        const action = bulkBtn.getAttribute("data-bulk");
        const ids = this._filteredShutters().map((s) => s.coverEntityId);
        this._bulkCoverAction(ids, action);
        bulkBtn.blur();
        return;
      }
      const bulkPostponeBtn = ev.target.closest("[data-bulk-postpone]");
      if (bulkPostponeBtn) {
        const action = bulkPostponeBtn.getAttribute("data-bulk-postpone");
        const minutes = parseInt(bulkPostponeBtn.getAttribute("data-minutes"), 10);
        this._bulkPostponeAll(action, minutes);
        return;
      }
      const bulkPostponeCustomBtn = ev.target.closest("[data-bulk-postpone-custom]");
      if (bulkPostponeCustomBtn) {
        const action = bulkPostponeCustomBtn.getAttribute("data-bulk-postpone-custom");
        const input = this.shadowRoot.querySelector(`[data-bulk-minutes-input="${action}"]`);
        const minutes = input && parseInt(input.value, 10);
        if (minutes && minutes > 0) this._bulkPostponeAll(action, minutes);
        return;
      }
      const bulkPostponeUntilBtn = ev.target.closest("[data-bulk-postpone-until]");
      if (bulkPostponeUntilBtn) {
        const action = bulkPostponeUntilBtn.getAttribute("data-bulk-postpone-until");
        const input = this.shadowRoot.querySelector(`[data-bulk-until-input="${action}"]`);
        if (input && input.value) {
          const [h, m] = input.value.split(":").map(Number);
          const target = new Date();
          target.setHours(h, m, 0, 0);
          if (target.getTime() <= Date.now()) target.setDate(target.getDate() + 1);
          const minutes = Math.round((target.getTime() - Date.now()) / 60000);
          if (minutes > 0) this._bulkPostponeAll(action, minutes);
        }
        return;
      }
      const bulkSkipBtn = ev.target.closest("[data-bulk-skip]");
      if (bulkSkipBtn) {
        const action = bulkSkipBtn.getAttribute("data-bulk-skip");
        this._bulkSkipAll(action);
        return;
      }
      const bulkCheckbox = ev.target.closest("[data-bulk-select]");
      if (bulkCheckbox) {
        // Prevents the click on the checkbox from also triggering the
        // enclosing [data-open-detail] is triggered and the detail view
        // opens, instead of just switching the selection.
        const deviceId = bulkCheckbox.getAttribute("data-bulk-select");
        if (bulkCheckbox.checked) this._bulkSelection.add(deviceId);
        else this._bulkSelection.delete(deviceId);
        this._render();
        return;
      }
      const bulkEditToggle = ev.target.closest("[data-bulk-edit-toggle]");
      if (bulkEditToggle) {
        this._bulkEditMode = !this._bulkEditMode;
        this._bulkSelection.clear();
        this._render();
        return;
      }
      const bulkSetAutomationBtn = ev.target.closest("[data-bulk-set-automation]");
      if (bulkSetAutomationBtn) {
        const action = bulkSetAutomationBtn.getAttribute("data-bulk-set-automation");
        const value = bulkSetAutomationBtn.getAttribute("data-value");
        this._bulkApplySwitch(action, value === "on");
        return;
      }
      const bulkApplyPositionBtn = ev.target.closest("[data-bulk-apply-position]");
      if (bulkApplyPositionBtn) {
        const action = bulkApplyPositionBtn.getAttribute("data-bulk-apply-position");
        const input = this.shadowRoot.querySelector(`[data-bulk-position-input="${action}"]`);
        const value = input && parseInt(input.value, 10);
        if (value !== null && value !== undefined && !isNaN(value) && value >= 0 && value <= 100) {
          this._bulkApplyPosition(action, value);
        }
        return;
      }
      const row = ev.target.closest("[data-open-detail]");
      if (row) {
        this._haptic("selection");
        this._detailDeviceId = row.getAttribute("data-open-detail");
        this._detailTab = "basic";
        this._view = "detail";
        this._render();
        return;
      }
      const toggle = ev.target.closest("[data-toggle-entity]");
      if (toggle) {
        const entry = this._findEntry(toggle.getAttribute("data-toggle-entity"));
        this._toggleSwitch(entry);
        return;
      }
      const areaBulkBtn = ev.target.closest("[data-area-bulk]");
      if (areaBulkBtn) {
        const action = areaBulkBtn.getAttribute("data-area-bulk");
        const ids = (areaBulkBtn.getAttribute("data-area-ids") || "").split(",").filter(Boolean);
        this._bulkCoverAction(ids, action);
        areaBulkBtn.blur();
        return;
      }
      const areaAutomationToggle = ev.target.closest("[data-area-automation-toggle]");
      if (areaAutomationToggle) {
        const areaId = areaAutomationToggle.getAttribute("data-area-automation-toggle");
        const members = this._areaMembers(areaId);
        const turnOn = !this._areaAutomationAllOn(members);
        this._setAreaAutomation(areaId, turnOn);
        return;
      }
      const settingsLink = ev.target.closest("[data-open-integration]");
      if (settingsLink) {
        navigate(this._hass, this, "/config/integrations/integration/smart_shutter");
      }
    }

    _onChange(ev) {
      const seasonSelect = ev.target.closest("[data-season-edit]");
      if (seasonSelect) {
        this._editingSeason = seasonSelect.value;
        this._render();
        return;
      }
      const notificationMode = ev.target.closest("[data-notification-mode]");
      if (notificationMode) {
        const form = notificationMode.closest("[data-notification-settings]");
        form.querySelector("[data-notification-recipient-field]").style.display = notificationMode.value === "custom" ? "" : "none";
        form.querySelector("[data-notification-recipient]").required = notificationMode.value === "custom";
        const status = form.querySelector("[data-notification-status]");
        if (status) status.textContent = "";
        const recipient = form.querySelector("[data-notification-recipient]");
        if (form.getAttribute("data-notification-autosave") === "true" &&
            (notificationMode.value !== "custom" || recipient.value.trim())) {
          this._queueNotificationSave(form, 0);
        } else {
          this._cancelNotificationSave(form);
        }
        return;
      }
      const notificationRecipient = ev.target.closest("[data-notification-recipient]");
      if (notificationRecipient) {
        const form = notificationRecipient.closest("[data-notification-settings]");
        if (form.getAttribute("data-notification-autosave") === "true" &&
            form.querySelector("[data-notification-mode]").value === "custom") {
          if (notificationRecipient.value.trim()) this._queueNotificationSave(form, 0);
          else this._cancelNotificationSave(form);
        }
        return;
      }
      const managedCover = ev.target.closest("[data-managed-cover]");
      if (managedCover) {
        const id = managedCover.getAttribute("data-managed-cover");
        const de = this._language() === "de";
        if (!managedCover.checked && !window.confirm(de
          ? "Rollladen aus Smart Shutter entfernen? Seine Smart-Shutter-Einstellungen werden gelöscht. Die ursprüngliche cover-Entität bleibt erhalten."
          : "Remove this shutter from Smart Shutter? Its Smart Shutter settings will be deleted. The original cover entity remains available.")) {
          managedCover.checked = true;
          return;
        }
        this._managedCoverSelection = managedCover.checked
          ? [...new Set([...this._managedCoverSelection, id])]
          : this._managedCoverSelection.filter((selected) => selected !== id);
        if (managedCover.checked) this._managedCoverNameChanges[id] = this._managedCoverNames[id] || "";
        const nameInput = managedCover.closest("[data-managed-cover-row]").querySelector("[data-managed-cover-name]");
        nameInput.disabled = !managedCover.checked;
        this._queueManagedCoverSave(0);
        return;
      }
      const triggerTargetModeSel = ev.target.closest("select[data-trigger-target-mode]");
      if (triggerTargetModeSel) {
        this._haptic("selection");
        this._triggerTargetMode = triggerTargetModeSel.value;
        this._render();
        return;
      }
      const sunDirSel = ev.target.closest("select[data-sun-direction-select]");
      if (sunDirSel) {
        this._haptic("selection");
        this._sunDirectionOverride = sunDirSel.value;
        this._render();
        return;
      }
      const modeSel = ev.target.closest("select[data-advanced-mode-select]");
      if (modeSel) {
        const s = this._shutterByDeviceId(modeSel.getAttribute("data-advanced-mode-select"));
        if (s) {
          const value = modeSel.value;
          for (const entry of this._advancedModeEntries(s)) {
            if (!entry) continue;
            this._selectOption(entry, value);
            this._optimisticState[entry.entity_id] = value;
          }
          this._render();
        }
        return;
      }
      const sel = ev.target.closest("select[data-select-entity]");
      if (sel) {
        const entry = this._findEntry(sel.getAttribute("data-select-entity"));
        this._selectOption(entry, sel.value);
        if (sel.hasAttribute("data-time-source-select") || sel.hasAttribute("data-type-select")) {
          // Optimistic overlay (see _state()): the real hate-
          // Roundtrip comes back asynchronously, but the cell
          // (editable vs. read-only/global) or the
          // Solar offset visibility (data-type-select: Source/Type
          // determine the effective type, see _effectiveType) must
          // SWITCH IMMEDIATELY, not only on the next background-
          // Update. Only for THESE selects trigger a full re-render
          // (not generally on every Select, otherwise incomplete
          // Inputs in other forms such as "Custom Profile
          // edit" lost).
          this._optimisticState[entry.entity_id] = sel.value;
          this._render();
        }
        return;
      }
      const timeInput = ev.target.closest("input[type='time'][data-time-entity]");
      if (timeInput) {
        const entry = this._findEntry(timeInput.getAttribute("data-time-entity"));
        this._setTime(entry, timeInput.value);
        return;
      }
      const numberInput = ev.target.closest("input[data-number-entity]");
      if (numberInput) {
        const entry = this._findEntry(numberInput.getAttribute("data-number-entity"));
        this._setNumber(entry, numberInput.value);
        return;
      }
    }

    _onInput(ev) {
      const notificationRecipient = ev.target.closest("[data-notification-recipient]");
      if (notificationRecipient) {
        const form = notificationRecipient.closest("[data-notification-settings]");
        if (form.getAttribute("data-notification-autosave") === "true" &&
            form.querySelector("[data-notification-mode]").value === "custom") {
          if (notificationRecipient.value.trim()) this._queueNotificationSave(form, 650);
          else this._cancelNotificationSave(form);
        }
        return;
      }
      const managedName = ev.target.closest("[data-managed-cover-name]");
      if (managedName) {
        const id = managedName.getAttribute("data-managed-cover-name");
        this._managedCoverNames[id] = managedName.value;
        this._managedCoverNameChanges[id] = managedName.value;
        this._queueManagedCoverSave(700);
        return;
      }
      const slider = ev.target.closest("[data-slider-group]");
      if (slider) {
        // Immediate live coupling between slider and number field, WITHOUT
        // on hass to wait (this would noticeably lag behind) - the
        // actual service call still happens only at
        // "change" (see _onChange), so when released/confirmed.
        const group = slider.getAttribute("data-slider-group");
        this.shadowRoot.querySelectorAll(`[data-slider-group="${group}"]`).forEach((el) => {
          if (el !== slider) el.value = slider.value;
        });
        return;
      }

      const search = ev.target.closest("[data-search]");
      if (search) {
        this._search = search.value;
        const cursorPos = search.selectionStart;
        this._render();
        const restored = this.shadowRoot.querySelector("[data-search]");
        if (restored) {
          restored.focus();
          try {
            restored.setSelectionRange(cursorPos, cursorPos);
          } catch (err) {
            /* some browsers do not always allow setSelectionRange for type=search - not critical */
          }
        }
      }
    }

    _exitEditor(defaultView) {
      if (this._editReturnView === "detail" && this._editReturnDetailDeviceId) {
        this._view = "detail";
        this._detailDeviceId = this._editReturnDetailDeviceId;
        this._detailTab = "advanced";
      } else if (this._editReturnView === "area" && this._editReturnAreaId) {
        this._view = "settings-area-edit";
        this._editingAreaId = this._editReturnAreaId;
      } else {
        this._view = defaultView;
      }
      this._editReturnView = null;
      this._editReturnDetailDeviceId = null;
      this._editReturnAreaId = null;
      this._prefillTriggerCover = null;
    }

    _findEntry(entityId) {
      // We know the registry entries only indirectly through the model -
      // for service calls, just entity_id is sufficient.
      return { entity_id: entityId };
    }

    _updateValues() {
      const scheduleSignature = ((this._model && this._model.shutters) || []).map((shutter) => {
        const state = shutter.entities.nextAction && this._state(shutter.entities.nextAction.entity_id);
        const attrs = (state && state.attributes) || {};
        return [attrs.next_open, attrs.next_close, attrs.open_automation_enabled,
          attrs.close_automation_enabled, attrs.seasonal_enabled, attrs.active_season].join("|");
      }).join(";");
      if (scheduleSignature !== this._scheduleSignature) {
        this._scheduleSignature = scheduleSignature;
        this._invalidateForecastCache();
      }
      this.shadowRoot.querySelectorAll("[data-season-status]").forEach((el) => {
        const de = this._language() === "de";
        const active = this._activeSeason();
        el.textContent = de ? `Automatisch aktiv: ${active === "summer" ? "Sommerzeit" : "Winterzeit"}`
          : `Automatically active: ${active === "summer" ? "Summer time" : "Winter time"}`;
      });
      const body = this.shadowRoot.querySelector(".body");
      if (!body) return;
      body.querySelectorAll("[data-shutter-name]").forEach((el) => {
        const shutter = this._shutterByDeviceId(el.getAttribute("data-shutter-name"));
        if (shutter) el.textContent = shutter.name;
      });
      this._syncControlValues(body);
      this._mountEntityPickers(body);

      body.querySelectorAll("[data-row-meta]").forEach((el) => {
        const s = this._shutterByDeviceId(el.getAttribute("data-row-meta"));
        if (s) el.innerHTML = this._rowMetaHtml(s);
      });

      // Refresh quick-action button availability on every Home Assistant state
      // update without rebuilding the controls while the user interacts.
      body.querySelectorAll("[data-quick-actions]").forEach((el) => {
        const coverEntityId = el.getAttribute("data-quick-actions");
        const { isFullyOpen, isFullyClosed, isOpening, isClosing, isMoving } = this._coverMotionState(coverEntityId);
        const openBtn = el.querySelector('[data-quick="open"]');
        const stopBtn = el.querySelector('[data-quick="stop"]');
        const closeBtn = el.querySelector('[data-quick="close"]');
        if (openBtn) openBtn.disabled = !!isFullyOpen || !!isOpening;
        if (stopBtn) stopBtn.disabled = !isMoving;
        if (closeBtn) closeBtn.disabled = !!isFullyClosed || !!isClosing;
      });

      const statsEl = body.querySelector("[data-overview-stats]");
      if (statsEl && this._model) statsEl.innerHTML = this._overviewStatsHtml();

      this._syncGroupMotionButtons(body);

      const timelineEl = body.querySelector("[data-global-timeline]");
      if (timelineEl && this._model) timelineEl.innerHTML = this._renderGlobalTimeline();

      const stateEl = body.querySelector("[data-detail-state]");
      if (stateEl) {
        const s = this._shutterByDeviceId(stateEl.getAttribute("data-detail-state"));
        if (s) stateEl.textContent = this._detailStateText(s);
      }
      this._localizeDom();
    }

    _render() {
      const body = this.shadowRoot.querySelector(".body");
      const isSettingsSubview = this._view.startsWith("settings-");
      this.shadowRoot.querySelectorAll("[data-nav]").forEach((btn) => {
        const navId = btn.getAttribute("data-nav");
        const active =
          navId === this._view ||
          (this._view === "detail" && navId === "list") ||
          (isSettingsSubview && navId === "settings");
        btn.classList.toggle("active", active);
      });

      if (this._loadError) {
        body.innerHTML = `<p class="error">${this._loadError}</p>`;
        this._localizeDom();
        return;
      }
      if (!this._model) {
        body.innerHTML = `<p>Loading Smart Shutter Manager data…</p>`;
        this._localizeDom();
        return;
      }

      if (this._view === "overview") {
        body.innerHTML = this._renderOverview();
      } else if (this._view === "list") {
        body.innerHTML = this._renderList();
      } else if (this._view === "detail") {
        body.innerHTML = this._renderDetail();
      } else if (this._view === "settings") {
        body.innerHTML = this._renderSettings();
      } else if (this._view === "settings-global") {
        body.innerHTML = this._renderSettingsGlobal();
      } else if (this._view === "settings-basic") {
        body.innerHTML = this._renderSettingsBasic();
      } else if (this._view === "settings-schedules") {
        body.innerHTML = this._renderSettingsSchedules();
      } else if (this._view === "settings-schedule-edit") {
        body.innerHTML = this._renderScheduleEdit();
      } else if (this._view === "settings-triggers") {
        body.innerHTML = this._renderSettingsTriggers();
      } else if (this._view === "settings-trigger-edit") {
        body.innerHTML = this._renderTriggerEdit();
      } else if (this._view === "settings-shutters") {
        body.innerHTML = this._renderSettingsShutters();
      } else if (this._view === "settings-areas") {
        body.innerHTML = this._renderSettingsAreas();
      } else if (this._view === "settings-area-edit") {
        body.innerHTML = this._renderAreaEdit();
      }

      // Sets current values in form controls (no re-render on every key press)
      this._syncControlValues(body);
      this._mountEntityPickers(body);
      this._localizeDom();
    }

    _syncControlValues(root) {
      root.querySelectorAll("[data-select-entity]").forEach((el) => {
        const st = this._state(el.getAttribute("data-select-entity"));
        if (st) el.value = st.state;
      });
      root.querySelectorAll("[data-time-entity]").forEach((el) => {
        const st = this._state(el.getAttribute("data-time-entity"));
        if (st && this.shadowRoot.activeElement !== el) el.value = (st.state || "").slice(0, 5);
      });
      root.querySelectorAll("[data-number-entity]").forEach((el) => {
        const st = this._state(el.getAttribute("data-number-entity"));
        if (!st) return;
        const active = this.shadowRoot.activeElement;
        // For coupled slider + number field pairs (data-slider-group)
        // checking only "this single element" for focus is not sufficient -
        // otherwise a Hass update in the middle of dragging the slider would
        // Reset non-focused number field (or vice versa).
        const group = el.getAttribute("data-slider-group");
        const groupIsActive = group && active && active.getAttribute("data-slider-group") === group;
        if (active !== el && !groupIsActive) el.value = st.state;
      });
      root.querySelectorAll("[data-toggle-entity]").forEach((el) => {
        const st = this._state(el.getAttribute("data-toggle-entity"));
        const input = el.querySelector("input");
        if (st && input) input.checked = st.state === "on";
      });
      // area master switch (automatic for all members of an
      // area) is not made up of a single entity, but from
      // the AND across multiple Switch entities (see
      // _areaAutomationAllOn). Without this block, the checkbox would remain after
      // a click in the purely visual browser state hangs, because
      // _render() (which recalculates the value correctly) only when
      // Navigation runs, not on every background update.
      root.querySelectorAll("[data-area-automation-toggle]").forEach((el) => {
        const areaId = el.getAttribute("data-area-automation-toggle");
        const members = this._areaMembers(areaId);
        const input = el.querySelector("input");
        if (input) input.checked = this._areaAutomationAllOn(members);
      });
    }

    _overviewStatsHtml() {
      const shutters = this._model.shutters;
      const total = shutters.length;
      let automationOff = 0;
      let automationFullyOff = 0;
      const globalAutomation = this._model.globalEntities.automation;
      const globalOpen = this._state(globalAutomation.open && globalAutomation.open.entity_id);
      const globalClose = this._state(globalAutomation.close && globalAutomation.close.entity_id);
      const groups = new Map();
      for (const s of shutters) {
        const openSw = this._state(s.entities.automation.open && s.entities.automation.open.entity_id);
        const closeSw = this._state(s.entities.automation.close && s.entities.automation.close.entity_id);
        const openOff = (globalOpen && globalOpen.state === "off") || (openSw && openSw.state === "off");
        const closeOff = (globalClose && globalClose.state === "off") || (closeSw && closeSw.state === "off");
        if (openOff || closeOff) automationOff += 1;
        if (openOff && closeOff) automationFullyOff += 1;
        const na = this._state(s.entities.nextAction && s.entities.nextAction.entity_id);
        if (na && na.attributes && na.attributes.scheduled_at) {
          const ts = Date.parse(na.attributes.scheduled_at);
          if (!isNaN(ts)) {
            // Group by the nearest minute: multiple roller shutters with
            // the same trigger (z.B. global automation) end up in the
            // same timestamp and are aggregated instead of
            // falsely give the impression that only ONE shutter
            // would be affected.
            const minuteTs = Math.floor(ts / 60000) * 60000;
            const action = na.attributes.action || na.state;
            const key = `${action}|${minuteTs}`;
            if (!groups.has(key)) groups.set(key, { action, ts: minuteTs, shutters: [] });
            groups.get(key).shutters.push({ name: s.name, nextActionId: s.entities.nextAction.entity_id });
          }
        }
      }
      let nextLabel = null;
      if (groups.size) {
        const soonest = [...groups.values()].sort((a, b) => a.ts - b.ts)[0];
        if (soonest.shutters.length > 1) {
          const timeStr = new Date(soonest.ts).toLocaleTimeString(this._language() === "de" ? "de-DE" : "en-GB", { hour: "2-digit", minute: "2-digit", hour12: false });
          nextLabel = this._language() === "de"
            ? `${soonest.shutters.length} Rollläden ${this._actionLabel(soonest.action)} um ${timeStr} Uhr.`
            : `${soonest.shutters.length} shutters ${this._actionLabel(soonest.action)} at ${timeStr}.`;
        } else {
          nextLabel = `${soonest.shutters[0].name}: ${this._nextActionLabel(this._state(soonest.shutters[0].nextActionId))}`;
        }
      }
      return `
        <div class="ssm-stat-grid">
          <div class="ssm-stat">
            <ha-icon icon="mdi:window-shutter"></ha-icon>
            <div class="ssm-stat-num">${total}</div>
            <div class="ssm-stat-label">Shutters</div>
          </div>
          <div class="ssm-stat">
            <ha-icon icon="mdi:toggle-switch-off-outline"></ha-icon>
            <div class="ssm-stat-num">${automationOff}</div>
            <div class="ssm-stat-label">${total > 0 && automationFullyOff === total
              ? "Automation disabled" : automationOff > 0 ? "Automation partially off" : "Automation enabled"}</div>
          </div>
        </div>
        ${
          nextLabel
            ? `<div class="ssm-next-action"><ha-icon icon="mdi:clock-outline"></ha-icon><span>Next action: <strong>${this._escapeHtml(nextLabel)}</strong></span></div>`
            : ""
        }
      `;
    }

    _renderOverview() {
      const ge = this._model.globalEntities;
      const areas = (this._backendConfig && this._backendConfig.custom_areas) || [];
      const moreExpanded = !!this._dashMoreActionsExpanded;
      const dashMotion = this._groupMotionState(this._model.shutters.map((s) => s.coverEntityId));
      return `
        <div class="ssm-dashboard">
          <h2 class="ssm-title">Smart Shutter Manager</h2>
          <div data-overview-stats>${this._overviewStatsHtml()}</div>

          <div class="ssm-section-label">Quick Access</div>
          <div class="ssm-shortcut-grid">
            <button data-bulk="open" class="ssm-shortcut-btn" ${dashMotion.canOpen ? "" : "disabled"}><ha-icon icon="mdi:arrow-up-bold-circle-outline"></ha-icon><span>All up</span></button>
            <button data-bulk="stop" class="ssm-shortcut-btn ssm-shortcut-btn-muted" ${dashMotion.canStop ? "" : "disabled"}><ha-icon icon="mdi:stop-circle-outline"></ha-icon><span>Stop</span></button>
            <button data-bulk="close" class="ssm-shortcut-btn" ${dashMotion.canClose ? "" : "disabled"}><ha-icon icon="mdi:arrow-down-bold-circle-outline"></ha-icon><span>All down</span></button>
          </div>

          <div class="ssm-card ssm-automation-card">
            ${
              this._isRestricted()
                ? `<div class="ssm-inline-hint"><ha-icon icon="mdi:information-outline"></ha-icon><span>The global automation control affects ALL shutters in the house and is therefore only visible to admins. Use the automation switches in your area below.</span></div>`
                : `
                  ${this._renderAutomationToggle(ge.automation.open, "Automatik Öffnen (alle Rollläden)")}
                  ${this._renderAutomationToggle(ge.automation.close, "Automatik Schließen (alle Rollläden)")}
                `
            }
          </div>

          <div class="ssm-nav-grid">
            <button class="ssm-nav-card" data-settings-nav="settings-areas">
              <span class="ssm-nav-icon"><ha-icon icon="mdi:home-group"></ha-icon></span>
              <span class="ssm-nav-text"><span class="ssm-nav-title">Areas</span><span class="ssm-nav-meta">${areas.length ? `${areas.length} angelegt` : "verwalten"}</span></span>
              <ha-icon class="ssm-nav-chevron" icon="mdi:chevron-right"></ha-icon>
            </button>
            <button class="ssm-nav-card" data-nav="list">
              <span class="ssm-nav-icon"><ha-icon icon="mdi:window-shutter"></ha-icon></span>
              <span class="ssm-nav-text"><span class="ssm-nav-title">All Shutters</span><span class="ssm-nav-meta">control individually</span></span>
              <ha-icon class="ssm-nav-chevron" icon="mdi:chevron-right"></ha-icon>
            </button>
          </div>

          <div class="ssm-section-label">Timeline</div>
          <div class="ssm-card ssm-timeline-card" data-global-timeline>${this._renderGlobalTimeline()}</div>

          <button class="ssm-link-btn" type="button" data-toggle-dash-more>${
            moreExpanded ? "▾ Weitere Aktionen ausblenden" : "▸ Weitere Aktionen (Verschieben, Überspringen)"
          }</button>
          ${moreExpanded ? `
          <h3>Close (all shutters)</h3>
          <div class="bulk-actions">
            <button data-bulk-postpone="close" data-minutes="10">+10 min</button>
            <button data-bulk-postpone="close" data-minutes="15">+15 min</button>
            <button data-bulk-postpone="close" data-minutes="30">+30 min</button>
            <input type="number" min="1" max="1440" class="bulk-minutes" data-bulk-minutes-input="close" placeholder="Min." />
            <button data-bulk-postpone-custom="close">Shift</button>
            <input type="time" data-bulk-until-input="close" />
            <button data-bulk-postpone-until="close">Until Time</button>
          <button data-bulk-skip="close">Skip Today</button>
        </div>
        <h3>Open (all shutters)</h3>
        <div class="bulk-actions">
          <button data-bulk-postpone="open" data-minutes="15">+15 min</button>
          <button data-bulk-postpone="open" data-minutes="30">+30 min</button>
          <input type="number" min="1" max="1440" class="bulk-minutes" data-bulk-minutes-input="open" placeholder="Min." />
          <button data-bulk-postpone-custom="open">Shift</button>
          <input type="time" data-bulk-until-input="open" />
          <button data-bulk-postpone-until="open">Until Time</button>
          <button data-bulk-skip="open">Skip Today</button>
        </div>
        ` : ""}
        </div>
      `;
    }

    _renderTimelineTicks(startMs, spanMs) {
      const intervalMs = 30 * 60000; // alle 30 Minuten ein Tick
      const count = Math.floor(spanMs / intervalMs);
      let html = "";
      for (let i = 0; i <= count; i++) {
        const t = startMs + i * intervalMs;
        const leftPct = (i * intervalMs / spanMs) * 100;
        const isFullHour = new Date(t).getMinutes() === 0;
        // Label only every 3 hours, otherwise it becomes too crowded on narrow
        // screens unreadable - ticks still occur every
        // half an hour.
        const showLabel = isFullHour && new Date(t).getHours() % 3 === 0;
        const timeStr = new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        html += `<div class="tl-tick${isFullHour ? " tl-tick-hour" : ""}" style="left:${leftPct}%">${
          showLabel ? `<span class="tl-tick-label">${timeStr}</span>` : ""
        }</div>`;
      }
      return html;
    }

    _renderForecastListToggle(scopeKey, entries) {
      // Supplement to the timeline for days with many/closely spaced events
      // lying events (z.B. an area that is 10 minutes earlier
      // drives) - there, individual markers are barely
      // distinguishable/achievable. The list shows the same dates
      // instead as uniquely tappable lines.
      if (!entries.length) return "";
      const expandedKey = `_forecastListExpanded_${scopeKey}`;
      const expanded = !!this[expandedKey];
      const sorted = entries.slice().sort((a, b) => a.ts - b.ts);
      const nowMs = Date.now();
      const toggleLabel = expanded
        ? "▾ Liste ausblenden"
        : `▸ Alle Termine als Liste anzeigen (${sorted.length})`;
      let html = `<button class="forecast-list-toggle" type="button" data-toggle-forecast-list="${scopeKey}">${toggleLabel}</button>`;
      if (expanded) {
        html += `<table class="forecast-list-table"><tr><th>Time</th><th>Action</th>${scopeKey === "global" ? "<th>Applies to</th>" : ""}</tr>`;
        sorted.forEach((e) => {
          const t = new Date(e.ts);
          const timeStr = t.toLocaleString([], {
            weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
          });
          const actionLabel = e.action === "open" ? "Öffnen" : "Schließen";
          const pastCls = e.ts < nowMs ? " tl-row-past" : "";
          const clickAttr =
            scopeKey === "global"
              ? `data-global-tl-marker="${e.idx}"`
              : `data-shutter-tl-marker="${e.idx}"`;
          html += `<tr class="${pastCls.trim()}" ${clickAttr} style="cursor:pointer;"><td>${timeStr}</td><td>${actionLabel}</td>${
            scopeKey === "global" ? `<td>${e.label}</td>` : ""
          }</tr>`;
        });
        html += `</table>`;
      }
      return html;
    }

    _dayColumnHtml(dayStartMs, markersHtml) {
      const dayEnd = new Date(dayStartMs);
      dayEnd.setDate(dayEnd.getDate() + 1);
      const isToday = new Date(dayStartMs).toDateString() === new Date().toDateString();
      const dayLabel = new Date(dayStartMs).toLocaleDateString([], {
        weekday: "short",
        day: "2-digit",
        month: "2-digit",
      });
      return `
        <div class="native-timeline-day${isToday ? " native-timeline-day-today" : ""}">
          <div class="native-timeline-day-label">${dayLabel}${isToday ? " · heute" : ""}</div>
          <div class="timeline">
            ${this._renderTimelineTicks(dayStartMs, dayEnd.getTime() - dayStartMs)}
            ${markersHtml}
          </div>
        </div>
      `;
    }

    _renderGlobalTimeline() {
      const shutters = this._model.shutters;
      const days = 7;

      if (this._globalForecast === undefined) {
        this._loadGlobalForecast(days);
        this._globalTimelineGroups = [];
        return `<p class="empty">Loading forecast ...</p>`;
      }

      const events = [];
      for (const s of shutters) {
        const entries = this._globalForecast[s.coverEntityId] || [];
        entries.forEach((entry) => {
          const ts = Date.parse(entry.ts);
          if (!isNaN(ts)) {
            events.push({ s, ts, action: entry.action });
          }
        });
      }

      if (!events.length) {
        this._globalTimelineGroups = [];
        return `<p class="empty">Keine Aktionen in den nächsten ${days} Tagen geplant.</p>`;
      }

      // Group by the nearest minute (multiple roller shutters with
      // the same trigger end up on the same marker) - for the click
      // the full list of affected shutters is retained.
      const groups = new Map();
      events.forEach((e) => {
        const minuteTs = Math.floor(e.ts / 60000) * 60000;
        const key = `${e.action}|${minuteTs}`;
        if (!groups.has(key)) groups.set(key, { action: e.action, ts: minuteTs, shutters: [] });
        groups.get(key).shutters.push(e.s);
      });
      this._globalTimelineGroups = [...groups.values()].sort((a, b) => a.ts - b.ts);

      // Bucket by calendar day, so that each day has its own
      // horizontal scrollable column gets (see .native-timeline-scroll).
      const dayStart = new Date();
      dayStart.setHours(0, 0, 0, 0);

      let columnsHtml = "";
      const nowMs = Date.now();
      for (let i = 0; i < days; i++) {
        const colStart = new Date(dayStart);
        colStart.setDate(dayStart.getDate() + i);
        const colEnd = new Date(colStart);
        colEnd.setDate(colStart.getDate() + 1);
        const colStartMs = colStart.getTime();
        const colEndMs = colEnd.getTime();
        const markers = this._globalTimelineGroups
          .map((g, idx) => ({ g, idx }))
          .filter(({ g }) => g.ts >= colStartMs && g.ts < colEndMs)
          .map(({ g, idx }) => {
            const leftPct = ((g.ts - colStartMs) / (colEndMs - colStartMs)) * 100;
            const cls = g.action === "open" ? "tl-open" : "tl-close";
            const timeStr = new Date(g.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            const actionLabel = g.action === "open" ? "Öffnen" : "Schließen";
            const selected = this._globalTimelineSelectedIdx === idx ? " tl-selected" : "";
            const past = g.ts < nowMs ? " tl-past" : "";
            return `<div class="tl-marker ${cls}${selected}${past}" style="left:${leftPct}%" data-global-tl-marker="${idx}" title="${g.shutters.length} Rollladen · ${actionLabel} · ${timeStr}${past ? " (bereits erfolgt)" : ""}"></div>`;
          })
          .join("");
        columnsHtml += this._dayColumnHtml(colStartMs, markers);
      }

      return `
        <h3>Vorhersage (nächste ${days} Tage)</h3>
        <div class="native-forecast-section">
          <div class="native-timeline-scroll">${columnsHtml}</div>
        </div>
        <div class="hint"><span class="tl-legend tl-open"></span> Öffnen &nbsp; <span class="tl-legend tl-close"></span> Schließen &nbsp; <span class="tl-legend tl-open tl-past"></span> bereits erfolgt &nbsp;· zum Bearbeiten antippen &nbsp;· ${days} Tage, horizontal scrollbar</div>
        ${this._renderGlobalTimelineDetail()}
        ${this._renderForecastListToggle(
          "global",
          this._globalTimelineGroups.map((g, idx) => ({
            ts: g.ts,
            action: g.action,
            label: `${g.shutters.length} Rollladen`,
            idx,
          }))
        )}
      `;
    }

    _renderGlobalTimelineDetail() {
      const idx = this._globalTimelineSelectedIdx;
      if (idx === null || idx === undefined) return "";
      const group = (this._globalTimelineGroups || [])[idx];
      if (!group) return "";
      const timeStr = new Date(group.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const actionLabel = group.action === "open" ? "Öffnen" : "Schließen";
      let html = `<div class="list-item" style="flex-direction:column;align-items:stretch;">
        <div class="name">${group.shutters.length} Rollladen · ${actionLabel} um ${timeStr}</div>`;
      group.shutters.forEach((s) => {
        html += `
          <div class="control-row">
            <label data-shutter-name="${s.deviceId}">${this._escapeHtml(s.name)}</label>
            <button data-global-tl-edit-shutter="${s.deviceId}">Edit for this Shutter</button>
          </div>
        `;
      });
      html += `
        <button class="add-btn" data-global-tl-edit-profiles><ha-icon icon="mdi:calendar-sync"></ha-icon> Manage custom profiles (if this action uses a scheduled profile)</button>
      </div>`;
      return html;
    }

    _filteredShutters() {
      const search = (this._search || "").toLowerCase();
      return this._model.shutters.filter(
        (s) =>
          !search ||
          s.name.toLowerCase().includes(search) ||
          (s.areaName || "").toLowerCase().includes(search)
      );
    }

    _renderList() {
      const shutters = this._filteredShutters();

      if (!this._model.shutters.length) {
        return `<p class="empty">No shutters managed by the Smart Shutter Manager were found.</p>`;
      }

      const byFloor = {};
      for (const s of shutters) {
        (byFloor[s.floorName] = byFloor[s.floorName] || []).push(s);
      }

      let html = `<input class="search" type="search" placeholder="Suche nach Name oder Bereich…" value="${this._search || ""}" data-search />`;

      const listMotion = this._groupMotionState(shutters.map((s) => s.coverEntityId));
      html += `
        <div class="bulk-actions" data-bulk-group="list">
          <span class="bulk-label">Alle (${shutters.length}) Rollläden:</span>
          <button data-bulk="open" ${listMotion.canOpen ? "" : "disabled"}><ha-icon icon="mdi:arrow-up"></ha-icon> Up</button>
          <button data-bulk="stop" ${listMotion.canStop ? "" : "disabled"}><ha-icon icon="mdi:stop"></ha-icon> Stop</button>
          <button data-bulk="close" ${listMotion.canClose ? "" : "disabled"}><ha-icon icon="mdi:arrow-down"></ha-icon> Down</button>
          <button data-bulk-edit-toggle>${this._bulkEditMode ? "Mehrfachauswahl beenden" : "Einstellungen für mehrere bearbeiten"}</button>
        </div>
      `;

      if (this._bulkEditMode) {
        html += `
          <div class="bulk-actions">
            <span class="bulk-label">${this._bulkSelection.size} ausgewählt</span>
            <button data-bulk-set-automation="open" data-value="on">Open automation: On</button>
            <button data-bulk-set-automation="open" data-value="off">Open automation: Off</button>
            <button data-bulk-set-automation="close" data-value="on">Close automation: On</button>
            <button data-bulk-set-automation="close" data-value="off">Close automation: Off</button>
          </div>
          <div class="bulk-actions">
            <input type="number" min="0" max="100" class="bulk-minutes" data-bulk-position-input="open" placeholder="Zielposition Öffnen %" />
            <button data-bulk-apply-position="open">Apply</button>
            <input type="number" min="0" max="100" class="bulk-minutes" data-bulk-position-input="close" placeholder="Zielposition Schließen %" />
            <button data-bulk-apply-position="close">Apply</button>
          </div>
          <div class="hint">Changes apply immediately to all checked shutters above.</div>
        `;
      }

      for (const floorName of Object.keys(byFloor)) {
        const byArea = {};
        for (const s of byFloor[floorName]) {
          const key = s.areaName || "Ohne Bereich";
          (byArea[key] = byArea[key] || []).push(s);
        }
        html += `<div class="floor"><div class="floor-title">${floorName}</div>`;
        for (const areaName of Object.keys(byArea)) {
          html += `<div class="area-title">${areaName}</div>`;
          for (const s of byArea[areaName]) {
            html += this._renderShutterRow(s);
          }
        }
        html += `</div>`;
      }
      return html;
    }

    _rowMetaHtml(s) {
      const coverState = this._state(s.coverEntityId);
      const position =
        coverState && coverState.attributes && coverState.attributes.current_position !== undefined
          ? `${coverState.attributes.current_position}%`
          : coverState
          ? coverState.state
          : "unbekannt";
      const profile = this._state(s.entities.activeProfile && s.entities.activeProfile.entity_id);
      const next = this._state(s.entities.nextAction && s.entities.nextAction.entity_id);
      return this._language() === "de"
        ? `${position} · Profil: ${profile ? this._profileStateLabel(profile.state) : "-"} · Nächste Aktion: ${this._nextActionLabel(next)}`
        : `${position} · Profile: ${profile ? this._profileStateLabel(profile.state) : "-"} · Next action: ${this._nextActionLabel(next)}`;
    }

    _quickActionsHtml(coverEntityId) {
      const { isFullyOpen, isFullyClosed, isOpening, isClosing, isMoving } = this._coverMotionState(coverEntityId);
      return `
        <div class="quick-actions" data-quick-actions="${coverEntityId}">
          <button data-quick="open" title="Öffnen" ${isFullyOpen || isOpening ? "disabled" : ""}><ha-icon icon="mdi:arrow-up"></ha-icon></button>
          <button data-quick="stop" title="Stopp" ${isMoving ? "" : "disabled"}><ha-icon icon="mdi:stop"></ha-icon></button>
          <button data-quick="close" title="Schließen" ${isFullyClosed || isClosing ? "disabled" : ""}><ha-icon icon="mdi:arrow-down"></ha-icon></button>
        </div>
      `;
    }

    _renderShutterRow(s) {
      const checkbox = this._bulkEditMode
        ? `<input type="checkbox" class="bulk-select-checkbox" data-bulk-select="${s.deviceId}" ${
            this._bulkSelection.has(s.deviceId) ? "checked" : ""
          } />`
        : "";
      return `
        <div class="row" data-open-detail="${s.deviceId}">
          ${checkbox}
          <div class="main">
            <div class="name" data-shutter-name="${s.deviceId}">${this._escapeHtml(s.name)}</div>
            <div class="meta" data-row-meta="${s.deviceId}">${this._rowMetaHtml(s)}</div>
          </div>
          ${this._quickActionsHtml(s.coverEntityId)}
        </div>
      `;
    }

    _shutterByDeviceId(deviceId) {
      return this._model.shutters.find((s) => s.deviceId === deviceId);
    }

    _detailStateText(s) {
      const coverState = this._state(s.coverEntityId);
      if (!coverState) return "Zustand unbekannt";
      const position =
        coverState.attributes && coverState.attributes.current_position !== undefined
          ? `${coverState.attributes.current_position}% offen`
          : coverState.state;
      return `Zustand: ${position}`;
    }

    _renderDetail() {
      const s = this._shutterByDeviceId(this._detailDeviceId);
      if (!s) return `<p class="empty">Shutter not found.</p><button class="back" data-back><ha-icon icon="mdi:arrow-left"></ha-icon> Back</button>`;

      let html = `<button class="back" data-back><ha-icon icon="mdi:arrow-left"></ha-icon> Back to Overview</button>`;
      html += `<div class="ssm-card ssm-detail-header">`;
      html += `<h2 class="clickable-title" data-open-more-info="${s.coverEntityId}" title="Home-Assistant-Entität öffnen"><span data-shutter-name="${s.deviceId}">${this._escapeHtml(s.name)}</span>${s.areaName ? ` <span class="pill">${s.areaName}</span>` : ""}</h2>`;
      html += `<div class="meta" data-detail-state="${s.deviceId}">${this._detailStateText(s)}</div>`;
      html += this._quickActionsHtml(s.coverEntityId);
      html += `</div>`;
      html += `
        <div class="tabs">
          <button data-tab="basic" class="${this._detailTab === "basic" ? "active" : ""}">Basic</button>
          <button data-tab="advanced" class="${this._detailTab === "advanced" ? "active" : ""}">Advanced</button>
          <button data-tab="verlauf" class="${this._detailTab === "verlauf" ? "active" : ""}">History</button>
        </div>
      `;

      if (this._detailTab === "basic") {
        html += this._renderBasicTab(s);
      } else if (this._detailTab === "advanced") {
        html += this._renderAdvancedTab(s);
      } else {
        html += this._renderHistoryTab(s);
      }
      return html;
    }

    _renderAutomationToggle(entry, label) {
      if (!entry) return "";
      const st = this._state(entry.entity_id);
      const checked = st && st.state === "on" ? "checked" : "";
      return `
        <div class="control-row">
          <label>${label}</label>
          <span class="switch-toggle" data-toggle-entity="${entry.entity_id}">
            <input type="checkbox" ${checked} />
            <span class="slider"></span>
          </span>
        </div>
      `;
    }

    _renderSelect(entry, label, extraAttr = "") {
      if (!entry) return "";
      const st = this._state(entry.entity_id);
      const options = (st && st.attributes && st.attributes.options) || [];
      return `
        <div class="control-row">
          <label>${label}</label>
          <select data-select-entity="${entry.entity_id}" ${extraAttr}>
            ${options.map((o) => `<option value="${o}">${this._selectOptionLabel(o)}</option>`).join("")}
          </select>
        </div>
      `;
    }

    _renderTimeInput(entry, label) {
      if (!entry) return `<div class="control-row"><label>${label}</label><span class="empty">not configured</span></div>`;
      return `
        <div class="control-row">
          <label>${label}</label>
          <input type="time" data-time-entity="${entry.entity_id}" />
        </div>
      `;
    }

    _renderNumberSlider(entry, label, unit) {
      if (!entry) return "";
      const st = this._state(entry.entity_id);
      // Nullish instead of truthy object check: attributes can be (still)
      // if it is an empty object, then st.attributes.min would literally be
      // undefined -> in the rendered HTML min="undefined", which native
      // Makes <input type="range"> unusable in some browsers.
      // Always render valid numbers guaranteed.
      const min = (st && st.attributes && st.attributes.min != null) ? st.attributes.min : 0;
      const max = (st && st.attributes && st.attributes.max != null) ? st.attributes.max : 100;
      const step = (st && st.attributes && st.attributes.step != null) ? st.attributes.step : 1;
      // Group identifier, so that slider + number field + live display
      // the same value can be kept in sync (see _onInput).
      return `
        <div class="control-row">
          <label>${label}</label>
          <input type="range" min="${min}" max="${max}" step="${step}"
                 data-number-entity="${entry.entity_id}" data-slider-group="${entry.entity_id}" />
          <input type="number" min="${min}" max="${max}" step="${step}"
                 class="number-exact" data-number-entity="${entry.entity_id}" data-slider-group="${entry.entity_id}" />
          <span class="unit">${unit || ""}</span>
        </div>
      `;
    }

    _globalOrRuleTime(pid, action) {
      // Provides the GLOBAL time value (HH:MM) for a profile+action -
      // in the three built-in profiles from the global Time-
      // Entity, for custom profiles directly from the rule definition
      // (they have no own global Time-Entity, see Backend).
      if (STATIC_PROFILE_LABELS[pid]) {
        const times = this._seasonEntities(this._model.globalEntities).profileTime;
        const entry = times[pid] && times[pid][action];
        const st = entry && this._state(entry.entity_id);
        return st ? st.state.slice(0, 5) : "";
      }
      const rule = ((this._backendConfig && this._backendConfig.custom_schedules) || []).find((r) => r.id === pid);
      const raw = rule ? rule[`${action}_time`] : null;
      return raw ? raw.slice(0, 5) : "";
    }

    _renderProfileTimeCell(pid, action, sourceEntry, localTimeEntry) {
      const sourceState = sourceEntry && this._state(sourceEntry.entity_id);
      const useIndividual = sourceState && sourceState.state === SOURCE_OPTION_LOCAL;

      if (useIndividual) {
        return localTimeEntry
          ? `<input type="time" data-time-entity="${localTimeEntry.entity_id}" />`
          : "-";
      }

      // Source = Global: display the global value, but read-only -
      // Editing is only possible after switching to "Individual" first.
      const value = this._globalOrRuleTime(pid, action);
      return `<input type="time" value="${value}" disabled title="Global - zum Bearbeiten auf 'Individuell' umstellen" />`;
    }

    async _loadHistory(coverEntityId) {
      this._historyByShutter = this._historyByShutter || {};
      if (this._historyByShutter[coverEntityId]) return;
      try {
        const result = await this._hass.callWS({
          type: "smart_shutter/get_event_history",
          entity_id: coverEntityId,
          limit: 100,
        });
        this._historyByShutter[coverEntityId] = (result && result.events && result.events[coverEntityId]) || [];
      } catch (err) {
        this._historyByShutter[coverEntityId] = [];
      }
      this._render();
    }

    async _loadForecast(coverEntityId, days = 7) {
      this._forecastByShutter = this._forecastByShutter || {};
      if (this._forecastByShutter[coverEntityId]) return;
      try {
        const result = await this._hass.callWS({
          type: "smart_shutter/get_forecast",
          entity_id: coverEntityId,
          days,
        });
        this._forecastByShutter[coverEntityId] =
          (result && result.forecast && result.forecast[coverEntityId]) || [];
      } catch (err) {
        this._forecastByShutter[coverEntityId] = [];
      }
      this._render();
    }

    async _loadGlobalForecast(days = 7) {
      if (this._globalForecastLoading) return;
      this._globalForecastLoading = true;
      try {
        const result = await this._hass.callWS({ type: "smart_shutter/get_forecast", days });
        this._globalForecast = (result && result.forecast) || {};
      } catch (err) {
        this._globalForecast = {};
      }
      this._globalForecastLoading = false;
      this._render();
    }

    // After every action that can change future dates (Bulk-/
    // Single shift/skip, cancel override) must be the
    // cached predictions are discarded, otherwise the timeline
    // outdated dates up to the next full reload of the map.
    _invalidateForecastCache() {
      this._globalForecast = undefined;
      this._forecastByShutter = undefined;
    }

    _eventTypeLabel(type) {
      return (
        {
          prenotify: this._language() === "de" ? "Vorwarnung" : "Warning",
          executed: this._language() === "de" ? "Ausgeführt" : "Executed",
          skipped: this._language() === "de" ? "Übersprungen" : "Skipped",
          postponed: this._language() === "de" ? "Verschoben" : "Postponed",
          sun_position: this._language() === "de" ? "Sonnenstand-Regel" : "Sun position rule",
        }[type] || type
      );
    }

    _eventDetailLabel(detail) {
      if (!detail) return "";
      const legacy = {
        "Vorwarnung gesendet": "Warning sent",
        "Vom Nutzer übersprungen": "Skipped by user",
        "Automatik pausiert (manueller Eingriff)": "Automation paused (manual intervention)",
        "Frostschutz aktiv": "Frost protection active",
        "Globale Automatik aus": "Global automation disabled",
        "Individuelle Automatik aus": "Individual automation disabled",
      };
      const english = legacy[detail] || detail
        .replace(/^Vom Nutzer um (\d+) Min\. verschoben$/, "Postponed by user by $1 min")
        .replace(/^Bereits in Zielposition \((.*?)\)$/, "Already at target position ($1)")
        .replace(/^hochgefahren \((.*?), Ziel (\d+)%\)$/, "opened ($1, target $2%)")
        .replace(/^heruntergefahren \((.*?), Ziel (\d+)%\)$/, "closed ($1, target $2%)")
        .replace(/Sonnenaufgang/g, "Sunrise").replace(/Sonnenuntergang/g, "Sunset")
        .replace(/Zeitsteuerung/g, "Schedule")
        .replace(/^Bereich '(.*?)': auf (\d+)% gefahren \(Sonnenstand-Regel\)$/, "Area '$1': moved to $2% (sun position rule)");
      if (this._language() !== "de") return english;
      const german = Object.fromEntries(Object.entries(legacy).map(([de, en]) => [en, de]));
      return german[english] || english
        .replace(/^Postponed by user by (\d+) min$/, "Vom Nutzer um $1 Min. verschoben")
        .replace(/^Already at target position \((.*?)\)$/, "Bereits in Zielposition ($1)")
        .replace(/^opened \((.*?), target (\d+)%\)$/, "hochgefahren ($1, Ziel $2%)")
        .replace(/^closed \((.*?), target (\d+)%\)$/, "heruntergefahren ($1, Ziel $2%)")
        .replace(/Sunrise/g, "Sonnenaufgang").replace(/Sunset/g, "Sonnenuntergang")
        .replace(/Schedule/g, "Zeitsteuerung")
        .replace(/^Area '(.*?)': moved to (\d+)% \(sun position rule\)$/, "Bereich '$1': auf $2% gefahren (Sonnenstand-Regel)");
    }

    _renderShutterForecastTimeline(coverEntityId, days) {
      this._forecastByShutter = this._forecastByShutter || {};
      const entries = this._forecastByShutter[coverEntityId];
      if (entries === undefined) {
        return `<p class="empty">Loading forecast ...</p>`;
      }
      if (!entries.length) {
        return `<p class="empty">Keine Aktionen in den nächsten ${days} Tagen geplant.</p>`;
      }
      const sorted = entries.slice().sort((a, b) => Date.parse(a.ts) - Date.parse(b.ts));
      const dayStart = new Date();
      dayStart.setHours(0, 0, 0, 0);

      let columnsHtml = "";
      const nowMs = Date.now();
      for (let i = 0; i < days; i++) {
        const colStart = new Date(dayStart);
        colStart.setDate(dayStart.getDate() + i);
        const colEnd = new Date(colStart);
        colEnd.setDate(colStart.getDate() + 1);
        const colStartMs = colStart.getTime();
        const colEndMs = colEnd.getTime();
        const markers = sorted
          .map((e, idx) => ({ e, idx }))
          .filter(({ e }) => {
            const ts = Date.parse(e.ts);
            return !isNaN(ts) && ts >= colStartMs && ts < colEndMs;
          })
          .map(({ e, idx }) => {
            const t = new Date(e.ts);
            const leftPct = ((t.getTime() - colStartMs) / (colEndMs - colStartMs)) * 100;
            const cls = e.action === "open" ? "tl-open" : "tl-close";
            const actionLabel = e.action === "open" ? "Öffnen" : "Schließen";
            const timeStr = t.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            const selected = this._shutterTlSelectedIdx === idx ? " tl-selected" : "";
            const past = t.getTime() < nowMs ? " tl-past" : "";
            return `<div class="tl-marker ${cls}${selected}${past}" style="left:${leftPct}%" data-shutter-tl-marker="${idx}" title="${actionLabel} · ${timeStr}${past ? " (bereits erfolgt)" : ""}"></div>`;
          })
          .join("");
        columnsHtml += this._dayColumnHtml(colStartMs, markers);
      }
      this._shutterTlSorted = sorted;
      return `
        <div class="native-forecast-section">
          <div class="native-timeline-scroll">${columnsHtml}</div>
        </div>
        <div class="hint"><span class="tl-legend tl-open"></span> Öffnen &nbsp; <span class="tl-legend tl-close"></span> Schließen &nbsp; <span class="tl-legend tl-open tl-past"></span> bereits erfolgt &nbsp;· antippen für Details &nbsp;· ${days} Tage, horizontal scrollbar</div>
        ${this._renderShutterForecastDetail()}
        ${this._renderForecastListToggle(
          "shutter",
          sorted.map((e, idx) => ({ ts: Date.parse(e.ts), action: e.action, idx }))
        )}
      `;
    }

    _renderShutterForecastDetail() {
      const idx = this._shutterTlSelectedIdx;
      if (idx === null || idx === undefined) return "";
      const entry = (this._shutterTlSorted || [])[idx];
      if (!entry) return "";
      const t = new Date(entry.ts);
      const actionLabel = entry.action === "open" ? "Öffnen" : "Schließen";
      const dateStr = t.toLocaleString([], {
        weekday: "long", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
      });
      return `<div class="list-item" style="flex-direction:column;align-items:stretch;">
        <div class="name">${actionLabel} · ${dateStr}</div>
      </div>`;
    }

    _renderHistoryTab(s) {
      this._historyByShutter = this._historyByShutter || {};
      const events = this._historyByShutter[s.coverEntityId];
      const days = 7;

      let html = `<h3>Vorhersage (nächste ${days} Tage)</h3>`;
      html += this._renderShutterForecastTimeline(s.coverEntityId, days);

      html += `<h3>Event Log</h3>`;
      if (events === undefined) {
        html += `<p class="empty">Loading event history ...</p>`;
        return html;
      }
      if (!events.length) {
        html += `<p class="empty">No events recorded yet.</p>`;
      } else {
        html += `<table><tr><th>Time</th><th>Action</th><th>Type</th><th>Detail</th></tr>`;
        events.forEach((e) => {
          const t = new Date(e.ts);
          const timeStr = t.toLocaleString([], { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
          const actionLabel = e.action === "open" ? "Open" : e.action === "close" ? "Close" : "-";
          html += `<tr><td>${timeStr}</td><td>${actionLabel}</td><td>${this._escapeHtml(this._eventTypeLabel(e.type))}</td><td>${this._escapeHtml(this._eventDetailLabel(e.detail))}</td></tr>`;
        });
        html += `</table>`;
      }
      return html;
    }

    _renderEmbeddedSchedulesAndTriggers(s) {
      const schedules = (this._backendConfig && this._backendConfig.custom_schedules) || [];
      const conflicts = (this._backendConfig && this._backendConfig.schedule_conflicts) || {};
      const triggers = ((this._backendConfig && this._backendConfig.external_triggers) || []).filter(
        (t) => t.entity_id === s.coverEntityId
      );

      // Reusing the open/close pattern from the area form
      // (v0.19) - Custom-Profiles/External Triggers are less commonly used,
      // advanced features; automatically expanded as soon as
      // ADD THIS shutter already exists an external trigger.
      const profilesKey = `detail-profiles-${s.coverEntityId}`;
      if (this._areaSectionExpanded[profilesKey] === undefined) {
        this._areaSectionExpanded[profilesKey] = false;
      }
      const profilesOpen = this._areaSectionExpanded[profilesKey];
      let html = `
        <button class="section-toggle" data-toggle-area-section="${profilesKey}" type="button">
          <span>Custom profiles</span>
          <ha-icon icon="${profilesOpen ? "mdi:chevron-up" : "mdi:chevron-down"}"></ha-icon>
        </button>
      `;
      if (profilesOpen) {
      html += `
        <div class="hint">Apply to ALL shutters (central time exceptions) - editable here directly, without switching views.</div>
      `;
      if (!schedules.length) {
        html += `<p class="empty">No custom profiles created yet.</p>`;
      } else {
        schedules.forEach((rule, idx) => {
          const conflictingIds = conflicts[rule.id] || [];
          const conflictBadge = conflictingIds.length
            ? `<span class="conflict-badge" title="Überschneidet sich mit: ${conflictingIds
                .map((id) => (schedules.find((r) => r.id === id) || {}).name || id)
                .join(", ")}">⚠ Conflict</span>`
            : "";
          html += `
            <div class="list-item">
              <div class="main">
                <div class="name">${idx + 1}. ${rule.name} ${conflictBadge}</div>
              </div>
              <div class="actions">
                <button data-schedule-edit="${rule.id}" data-edit-return="detail" title="Bearbeiten"><ha-icon icon="mdi:pencil"></ha-icon></button>
              </div>
            </div>
          `;
        });
      }
      html += `<button class="add-btn" data-schedule-edit="__new__" data-edit-return="detail"><ha-icon icon="mdi:plus"></ha-icon> New custom profile</button>`;
      }

      const triggersKey = `detail-triggers-${s.coverEntityId}`;
      if (this._areaSectionExpanded[triggersKey] === undefined) {
        this._areaSectionExpanded[triggersKey] = triggers.length > 0;
      }
      const triggersOpen = this._areaSectionExpanded[triggersKey];
      html += `
        <button class="section-toggle" data-toggle-area-section="${triggersKey}" type="button">
          <span>External Triggers for this Shutter</span>
          <ha-icon icon="${triggersOpen ? "mdi:chevron-up" : "mdi:chevron-down"}"></ha-icon>
        </button>
      `;
      if (triggersOpen) {
      if (!triggers.length) {
        html += `<p class="empty">No external trigger set for this shutter.</p>`;
      } else {
        triggers.forEach((t) => {
          html += `
            <div class="list-item">
              <div class="main">
                <div class="name">${t.name}</div>
                <div class="meta">${t.action === "open" ? "Öffnen" : "Schließen"}</div>
              </div>
              <div class="actions">
                <button data-trigger-edit="${t.id}" data-edit-return="detail" title="Bearbeiten"><ha-icon icon="mdi:pencil"></ha-icon></button>
                <button data-trigger-delete="${t.id}" title="Löschen"><ha-icon icon="mdi:delete"></ha-icon></button>
              </div>
            </div>
          `;
        });
      }
      html += `<button class="add-btn" data-trigger-edit="__new__" data-edit-return="detail" data-prefill-cover="${s.coverEntityId}"><ha-icon icon="mdi:plus"></ha-icon> Create new external trigger for this shutter</button>`;
      }

      return html;
    }

    _renderBasicTab(s) {
      const e = this._seasonEntities(s.entities);
      let html = "";

      const shutterAreas = (this._backendConfig && this._backendConfig.shutter_areas) || {};
      const areas = (this._backendConfig && this._backendConfig.custom_areas) || [];
      const currentAreaIds = shutterAreas[s.coverEntityId] || [];
      const currentAreaObjs = currentAreaIds
        .map((id) => areas.find((a) => a.id === id))
        .filter(Boolean);
      html += `
        <div class="hint">
          ${this._language() === "de" ? "Bereiche:" : "Areas:"} ${
            currentAreaObjs.length
              ? currentAreaObjs
                  .map(
                    (a) =>
                      `<strong>${this._escapeHtml(a.name)}</strong> <a class="link-btn" data-area-edit="${a.id}">edit</a>`
                  )
                  .join(" &nbsp;·&nbsp; ")
              : `${this._language() === "de" ? "keinem Bereich zugeordnet" : "not assigned to an area"} <a class="link-btn" data-settings-nav="settings-areas">Manage Areas</a>`
          }
        </div>
      `;

      const na = this._state(e.nextAction && e.nextAction.entity_id);
      if (na && na.attributes && na.attributes.override_active) {
        const until = na.attributes.override_until ? new Date(na.attributes.override_until) : null;
        const untilStr = until
          ? until.toLocaleString([], { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
          : "";
        const source = na.attributes.override_source;
        html += `
          <div class="conflict-box">
            ${this._escapeHtml(this._message("overrideNotice", untilStr, source))}
            <br><button data-clear-override="${na.attributes.action}" data-cover="${s.coverEntityId}">Cancel override now</button>
          </div>
        `;
      }
      if (na && na.attributes && na.attributes.manual_pause_active) {
        const pauseUntil = na.attributes.manual_pause_until ? new Date(na.attributes.manual_pause_until) : null;
        const pauseUntilStr = pauseUntil
          ? pauseUntil.toLocaleString([], { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
          : "";
        html += `
          <div class="conflict-box">
            ${this._escapeHtml(this._message("manualPauseNotice", pauseUntilStr))}
            <br><button data-clear-manual-pause="${s.coverEntityId}">End pause now</button>
          </div>
        `;
      }

      html += `<h3>Automation (individual)</h3>`;
      html += this._renderAutomationToggle(e.automation.open, "Öffnen");
      html += this._renderAutomationToggle(e.automation.close, "Schließen");

      html += this._renderSeasonPicker();
      html += `<h3>Times per Profile</h3>`;
      const profileIds = this._profileIds(s);
      html += `<div class="profile-times"><table class="profile-times-table"><tr><th>Profile</th><th>Open source</th><th>Open</th><th>Close source</th><th>Close</th></tr>`;
      for (const pid of profileIds) {
        const label = this._profileLabel(pid, s);
        const srcOpen = e.profileTimeSource[pid] && e.profileTimeSource[pid].open;
        const srcClose = e.profileTimeSource[pid] && e.profileTimeSource[pid].close;
        const timeOpen = e.profileTime[pid] && e.profileTime[pid].open;
        const timeClose = e.profileTime[pid] && e.profileTime[pid].close;
        html += `<tr>
          <td>${label}</td>
          <td data-label="${CARD_TEXT[this._language()]["Open source"] || "Open source"}">${srcOpen ? `<select data-select-entity="${srcOpen.entity_id}" data-time-source-select><option value="global">${this._selectOptionLabel("global")}</option><option value="local">${this._selectOptionLabel("local")}</option></select>` : "-"}</td>
          <td data-label="${CARD_TEXT[this._language()]["Open"] || "Open"}">${this._renderProfileTimeCell(pid, "open", srcOpen, timeOpen)}</td>
          <td data-label="${CARD_TEXT[this._language()]["Close source"] || "Close source"}">${srcClose ? `<select data-select-entity="${srcClose.entity_id}" data-time-source-select><option value="global">${this._selectOptionLabel("global")}</option><option value="local">${this._selectOptionLabel("local")}</option></select>` : "-"}</td>
          <td data-label="${CARD_TEXT[this._language()]["Close"] || "Close"}">${this._renderProfileTimeCell(pid, "close", srcClose, timeClose)}</td>
        </tr>`;
      }
      html += `</table></div>`;

      return html;
    }

    _effectiveType(s, action) {
      // Determines the ACTUALLY effective trigger type (time of day/sun)
      // for an action: when Source=Individual, the local Type-Select,
      // otherwise the global (both share the same internally
      // Model key "localType", depending on which device it is from
      // Entities originate - see _categorizeEntities).
      const sourceEntry = this._seasonEntities(s.entities).sourceSelect[action];
      const sourceState = sourceEntry && this._state(sourceEntry.entity_id);
      const useIndividual = sourceState && sourceState.state === SOURCE_OPTION_LOCAL;
      const typeEntry = useIndividual
        ? this._seasonEntities(s.entities).localType[action]
        : this._seasonEntities(this._model.globalEntities).localType[action];
      const st = typeEntry && this._state(typeEntry.entity_id);
      return st ? st.state : "time";
    }

    _globalValueText(entry, unit) {
      const st = entry && this._state(entry.entity_id);
      return st ? `${st.state}${unit || ""}` : "-";
    }

    _advancedModeEntries(s) {
      const e = this._seasonEntities(s.entities);
      return [e.sourceSelect.open, e.sourceSelect.close, e.positionSourceSelect.open, e.positionSourceSelect.close];
    }

    _advancedMode(s) {
      // Combined mode over all four underlying source selects
      // (Trigger type open/close + Position source open/close) across:
      // "Global" only if TRULY all four are set to Global - otherwise
      // "Individually", since then at least one aspect differs.
      const allGlobal = this._advancedModeEntries(s).every((entry) => {
        const st = entry && this._state(entry.entity_id);
        return !st || st.state !== SOURCE_OPTION_LOCAL;
      });
      return allGlobal ? "global" : SOURCE_OPTION_LOCAL;
    }

    _renderAdvancedTab(s) {
      const e = this._seasonEntities(s.entities);

      const mode = this._advancedMode(s);
      let html = this._renderSeasonPicker() + `
        <h3>Mode</h3>
        <div class="control-row">
          <label>Advanced Settings</label>
          <select data-advanced-mode-select="${s.deviceId}">
            <option value="global"${mode === "global" ? " selected" : ""}>${this._selectOptionLabel("global")}</option>
            <option value="local"${mode === SOURCE_OPTION_LOCAL ? " selected" : ""}>${this._selectOptionLabel("local")}</option>
          </select>
        </div>
        <div class="hint">
          "Global" takes over trigger type, sun offset, and target position completely from the global settings. "Individual" allows custom values for this shutter (still separable per open/close and aspect).
        </div>
      `;

      const notifications = (this._backendConfig && this._backendConfig.shutter_notifications) || {};
      html += this._renderNotificationSettings(notifications[s.coverEntityId] || {}, s.coverEntityId);

      if (mode === "global") {
        // Only read-only summary - no detail sliders,
        // those that would have no effect anyway (see scheduler.py: at
        // Source=Global exclusively uses the global entities
        // evaluated).
        const ge = this._seasonEntities(this._model.globalEntities);
        html += `<h3>Inherited from global</h3>`;
        html += `<table>
          <tr><th></th><th>Open</th><th>Close</th></tr>
          <tr><td>Trigger Type</td><td>${this._globalValueText(ge.localType.open)}</td><td>${this._globalValueText(ge.localType.close)}</td></tr>
          <tr><td>Sun offset</td><td>${this._globalValueText(ge.sunOffset.open, " min")}</td><td>${this._globalValueText(ge.sunOffset.close, " min")}</td></tr>
          <tr><td>Target Position</td><td>${this._globalValueText(ge.position.open, "%")}</td><td>${this._globalValueText(ge.position.close, "%")}</td></tr>
        </table>`;
      } else {
        html += `<h3>Trigger Type (Time / Solar Position)</h3>`;
        html += this._renderSelect(e.sourceSelect.open, "Öffnen-Quelle (Typ/Sonnenversatz)", "data-type-select");
        const openSourceState = this._state(e.sourceSelect.open && e.sourceSelect.open.entity_id);
        if (openSourceState && openSourceState.state === SOURCE_OPTION_LOCAL) {
          html += this._renderSelect(e.localType.open, "Öffnen: Uhrzeit oder Sonnenaufgang/-untergang", "data-type-select");
        }
        html += this._renderSelect(e.sourceSelect.close, "Schließen-Quelle (Typ/Sonnenversatz)", "data-type-select");
        const closeSourceState = this._state(e.sourceSelect.close && e.sourceSelect.close.entity_id);
        if (closeSourceState && closeSourceState.state === SOURCE_OPTION_LOCAL) {
          html += this._renderSelect(e.localType.close, "Schließen: Uhrzeit oder Sonnenaufgang/-untergang", "data-type-select");
        }

        // Solar offset is only relevant if the ACTUALLY effective type
        // (see _effectiveType) sunrise/sunset is - at
        // "Time" only unnecessary, confusing distraction.
        const openIsSun = this._effectiveType(s, "open") !== "time";
        const closeIsSun = this._effectiveType(s, "close") !== "time";
        if (openIsSun || closeIsSun) {
          html += `<h3>Sun offset</h3>`;
          if (openIsSun) html += this._renderNumberSlider(e.sunOffset.open, "Öffnen", " min");
          if (closeIsSun) html += this._renderNumberSlider(e.sunOffset.close, "Schließen", " min");
        }

        // Position source AND the actual target position value directly
        // next to each other (FR1) instead of being distributed on Basic-/Advanced-tab.
        // The value is editable only if the respective position source
        // on "Individual" stands - otherwise read-only display of the
        // global value (same pattern as for times per profile).
        html += `<h3>Positions-Quelle &amp; Zielposition</h3>`;
        html += this._renderSelect(e.positionSourceSelect.open, "Öffnen-Quelle", "data-type-select");
        const openPosIndividual =
          this._state(e.positionSourceSelect.open && e.positionSourceSelect.open.entity_id) &&
          this._state(e.positionSourceSelect.open.entity_id).state === SOURCE_OPTION_LOCAL;
        html += openPosIndividual
          ? this._renderNumberSlider(e.position.open, "Öffnen", "%")
          : `<div class="control-row"><label>Open</label><input type="text" value="${this._globalValueText(
              this._model.globalEntities.position.open,
              "%"
            )}" disabled title="Global - zum Bearbeiten auf 'Individuell' umstellen" /></div>`;
        html += this._renderSelect(e.positionSourceSelect.close, "Schließen-Quelle", "data-type-select");
        const closePosIndividual =
          this._state(e.positionSourceSelect.close && e.positionSourceSelect.close.entity_id) &&
          this._state(e.positionSourceSelect.close.entity_id).state === SOURCE_OPTION_LOCAL;
        html += closePosIndividual
          ? this._renderNumberSlider(e.position.close, "Schließen", "%")
          : `<div class="control-row"><label>Close</label><input type="text" value="${this._globalValueText(
              this._model.globalEntities.position.close,
              "%"
            )}" disabled title="Global - zum Bearbeiten auf 'Individuell' umstellen" /></div>`;

        // v0.20.1: Note, why individual for this shutter
        // Settings were selected (z.B. "Potted plant on the
        // Window sill, do not close below 20%" - helps first with
        // own reminder, secondly in the confirmation dialog from
        // "Apply to members" displayed before an individual
        // Setting is accidentally overwritten.
        const existingNote = (this._backendConfig && this._backendConfig.shutter_notes &&
          this._backendConfig.shutter_notes[s.coverEntityId]) || "";
        html += `
          <div class="form-field">
            <label>Note (why individual settings?)</label>
            <textarea data-shutter-note="${s.coverEntityId}" placeholder="z.B. Blumentopf auf der Fensterbank, nicht unter 20% schließen">${existingNote}</textarea>
          </div>
          <button data-save-shutter-note="${s.coverEntityId}">Save note</button>
          <span class="save-status" data-save-status></span>
        `;
      }

      if (e.other.length) {
        const otherKey = `detail-other-${s.deviceId}`;
        if (this._areaSectionExpanded[otherKey] === undefined) {
          this._areaSectionExpanded[otherKey] = false;
        }
        const otherOpen = this._areaSectionExpanded[otherKey];
        html += `
          <button class="section-toggle" data-toggle-area-section="${otherKey}" type="button">
            <span>More Entities</span>
            <ha-icon icon="${otherOpen ? "mdi:chevron-up" : "mdi:chevron-down"}"></ha-icon>
          </button>
        `;
        if (otherOpen) {
        html += `<table>`;
        for (const entry of e.other) {
          html += `<tr><td>${this._friendlyName(entry)}</td><td>${entry.entity_id}</td></tr>`;
        }
        html += `</table>`;
        }
      }

      html += this._renderEmbeddedSchedulesAndTriggers(s);
      return html;
    }

    _renderSettings() {
      const backendError = this._backendError
        ? `<div class="hint error">${this._backendError}</div>`
        : "";
      if (this._isRestricted()) {
        // Guest (v0.18): all other menu items are host/device-wide
        // Configuration (Basic Settings, Custom Profiles, External
        // Trigger, Rename, Global Entities) - for him anyway empty
        // or admin-only on the backend side (see websocket_api.py),
        // therefore not displayed at all instead of being empty/confusing
        // Subpages.
        return `
          <h2>Settings</h2>
          ${backendError}
          <div class="settings-menu">
            <button class="settings-menu-item" data-settings-nav="settings-areas">
              <ha-icon icon="mdi:compass-outline"></ha-icon>
              <div><div class="name">My Area</div><div class="meta">Times, Sun Position Rule, Frost Protection for your area</div></div>
            </button>
          </div>
        `;
      }
      return `
        <h2>Settings</h2>
        ${backendError}
        <div class="settings-menu">
          ${this._isAdmin() ? `<button class="settings-menu-item" data-settings-nav="settings-shutters">
            <ha-icon icon="mdi:window-shutter-cog"></ha-icon>
            <div><div class="name">${this._language() === "de" ? "Rollläden verwalten" : "Manage shutters"}</div>
            <div class="meta">${this._language() === "de" ? "Rollläden hinzufügen, entfernen oder umbenennen" : "Add, remove, or rename shutters"}</div></div>
          </button>` : ""}
          <button class="settings-menu-item" data-settings-nav="settings-basic">
            <ha-icon icon="mdi:cog"></ha-icon>
            <div><div class="name">Basic Settings</div><div class="meta">Holiday/Frost Entity, Notifications</div></div>
          </button>
          <button class="settings-menu-item" data-settings-nav="settings-schedules">
            <ha-icon icon="mdi:calendar-clock"></ha-icon>
            <div><div class="name">Custom profiles</div><div class="meta">Manage Recurring Time Exceptions</div></div>
          </button>
          <button class="settings-menu-item" data-settings-nav="settings-triggers">
            <ha-icon icon="mdi:remote"></ha-icon>
            <div><div class="name">External Triggers</div><div class="meta">Time Triggers that can be triggered by Automations</div></div>
          </button>
          <button class="settings-menu-item" data-settings-nav="settings-areas">
            <ha-icon icon="mdi:compass-outline"></ha-icon>
            <div><div class="name">Areas</div><div class="meta">e.g. Front/Back/North/South - own groups with presets</div></div>
          </button>
          <button class="settings-menu-item" data-settings-nav="settings-global">
            <ha-icon icon="mdi:earth"></ha-icon>
            <div><div class="name">Global Entities</div><div class="meta">Times, Sun Offset, Target Position (global)</div></div>
          </button>
        </div>
      `;
    }

    _entityPickerField(key, label, value, domains, dataAttr, hint = "", includeEntities = null) {
      return `
        <div class="form-field">
          <label>${label}</label>
          <div class="entity-picker-slot" data-entity-picker="${key}" data-picker-attr="${dataAttr}"
               data-value="${value || ""}" data-domains="${(domains || []).join(",")}"
               ${includeEntities ? `data-entities="${includeEntities.join(",")}"` : ""}></div>
          ${hint ? `<div class="meta">${hint}</div>` : ""}
        </div>
      `;
    }

    _mountEntityPickers(root) {
      root.querySelectorAll("[data-entity-picker]").forEach((slot) => {
        if (slot.dataset.mounted) {
          const existing = slot.querySelector("ha-entity-picker");
          if (existing) existing.hass = this._hass;
          return;
        }
        slot.dataset.mounted = "1";
        const value = slot.getAttribute("data-value") || "";
        const domains = (slot.getAttribute("data-domains") || "").split(",").filter(Boolean);
        const entities = (slot.getAttribute("data-entities") || "").split(",").filter(Boolean);

        if (customElements.get("ha-entity-picker")) {
          const picker = document.createElement("ha-entity-picker");
          picker.hass = this._hass;
          picker.value = value;
          picker.allowCustomEntity = !entities.length;
          if (entities.length) picker.includeEntities = entities;
          else if (domains.length) picker.includeDomains = domains;
          picker.addEventListener("value-changed", (ev) => {
            slot.setAttribute("data-value", (ev.detail && ev.detail.value) || "");
          });
          slot.appendChild(picker);
        } else {
          // Fallback without ha-entity-picker (z.B. Test environment without real
          // HA-Frontend) - simple selection/text field, functionally equivalent.
          if (entities.length) {
            const select = document.createElement("select");
            entities.forEach((id) => {
              const opt = document.createElement("option");
              opt.value = id;
              opt.textContent = id;
              if (id === value) opt.selected = true;
              select.appendChild(opt);
            });
            select.addEventListener("change", () => slot.setAttribute("data-value", select.value));
            slot.appendChild(select);
          } else {
            const input = document.createElement("input");
            input.type = "text";
            input.value = value;
            input.placeholder = domains.length ? `${domains.join("/")}.…` : "entity_id";
            input.addEventListener("input", () => slot.setAttribute("data-value", input.value));
            slot.appendChild(input);
          }
        }
      });
    }


    _renderSettingsBasic() {
      const bs = (this._backendConfig && this._backendConfig.basic_settings) || {};
      const field = (key, label, value, type = "text", hint = "") => `
        <div class="form-field">
          <label>${label}</label>
          <input type="${type}" data-basic-field="${key}" value="${value != null ? value : ""}" />
          ${hint ? `<div class="meta">${hint}</div>` : ""}
        </div>
      `;
      const entityField = (key, label, value, domains, hint = "") =>
        this._entityPickerField(key, label, value, domains, "data-basic-field", hint);
      const textarea = (key, label, value, hint = "") => `
        <div class="form-field">
          <label>${label}</label>
          <textarea data-basic-field="${key}">${value || ""}</textarea>
          ${hint ? `<div class="meta">${hint}</div>` : ""}
        </div>
      `;

      let html = `<button class="back" data-settings-back><ha-icon icon="mdi:arrow-left"></ha-icon> Back to Settings Menu</button>`;
      html += `<h2>Basic Settings</h2>`;
      html += `<div class="form-grid">`;

      const de = this._language() === "de";
      html += `<h3>${de ? "Sommer- und Winterprofile" : "Summer and winter profiles"}</h3>
        <label class="control-row">
          <input type="checkbox" data-basic-field="seasonal_enabled" ${bs.seasonal_enabled ? "checked" : ""} />
          <span>${de ? "Automatisch mit der Zeitumstellung wechseln" : "Switch automatically with daylight saving time"}</span>
        </label>
        <div class="meta">${de ? "Verwendet die Home-Assistant-Zeitzone. Beim ersten Aktivieren werden die bisherigen Einstellungen in beide Profile übernommen." : "Uses the Home Assistant timezone. First activation copies existing settings into both profiles."}</div>`;

      // v0.19.3 Unification: instead of a single, 14 fields
      // long list is now sorted into three clearly named groups -
      // easier to overview, without hiding a single field.
      html += `<h3>Sensoren &amp; Frostschutz</h3>`;
      html += entityField(
        "holiday_entity", "Holiday entity", bs.holiday_entity,
        ["binary_sensor", "input_boolean", "calendar"], "'an' = Ferien aktiv"
      );
      html += entityField(
        "frost_entity", "Frost protection entity", bs.frost_entity,
        ["binary_sensor", "input_boolean"], "'an' = keine Bewegung"
      );
      html += entityField(
        "outside_temp_sensor", "Außentemperatur-Sensor", bs.outside_temp_sensor,
        ["sensor"], "Global, fließt in Frostschutz + Sonnenstand-Zusatzbedingung (als 'outside_temp') ein"
      );
      html += entityField(
        "inside_temp_sensor", "Innentemperatur-Sensor (Standard)", bs.inside_temp_sensor,
        ["sensor"], "Fallback, falls ein Bereich keinen eigenen Sensor hat (manuell oder automatisch erkannt, siehe Bereiche)"
      );
      html += field(
        "frost_threshold_c", "Frostschutz-Schwelle (°C)",
        bs.frost_threshold_c, "number",
        "Automatik pausiert (wie bei manuellem Eingriff), sobald Innen- oder Außentemperatur diesen Wert unterschreitet. Pro Bereich überschreibbar."
      );

      html += `<h3>Notifications</h3>`;
      html += field("notify_service", "Notification service", bs.notify_service, "text", "e.g. notify.notify, empty = off");
      html += field(
        "pre_notify_lead_minutes", "Vorwarnung vor dem Schließen (Minuten)",
        bs.pre_notify_lead_minutes, "number"
      );
      html += field(
        "notification_max_age_minutes", "Warning button validity (minutes, 0 = unlimited)",
        bs.notification_max_age_minutes, "number"
      );

      const templatesSection = this._sectionToggle("notify-templates", "Nachrichtenvorlagen (optional)", false);
      html += templatesSection.headerHtml;
      if (templatesSection.isOpen) {
      html += textarea(
        "notify_text_moved", "Vorlage: Bewegungsbenachrichtigung",
        bs.notify_text_moved, "Variablen: names, count, action, trigger"
      );
      html += textarea(
        "notify_text_frost", "Vorlage: Frostschutzbenachrichtigung",
        bs.notify_text_frost, "Variablen: names, count"
      );
      html += textarea(
        "notify_text_preclose", "Vorlage: Vorwarnung vor dem Schließen",
        bs.notify_text_preclose, "Variablen: name, time, action"
      );
      }

      html += `<h3>Timing and delays</h3>`;
      html += field(
        "postpone_options_minutes", "Verschieben-Optionen (Minuten, kommagetrennt)",
        bs.postpone_options_minutes, "text", "z.B. 5,10,15"
      );
      html += field(
        "catch_up_window_minutes", "Nachhol-Fenster nach Neustart (Minuten)",
        bs.catch_up_window_minutes, "number"
      );
      html += field(
        "manual_pause_minutes", "Automatik-Pause nach manuellem Eingriff (Minuten, 0 = Erkennung aus)",
        bs.manual_pause_minutes, "number",
        "Erkennt Bewegungen, die NICHT von der Automatik kommen (Wandschalter, Fernbedienung, andere Automation) und pausiert die Automatik für diesen Rollladen entsprechend lange."
      );
      html += field(
        "stagger_delay_ms", "Gestaffelte Befehlsausgabe (Millisekunden, 0 = aus)",
        bs.stagger_delay_ms, "number",
        "Verzögerung zwischen den einzelnen Rollläden bei Mehrfachaktionen (globaler Zeitplan, Bereich, 'Alle hoch/runter/Stopp') - Funk-Kollisionsschutz für funkbasierte Motoren. Bei WLAN-Geräten (z.B. Shelly) normalerweise nicht nötig."
      );

      html += `</div>`;
      html += `<button class="save-btn" data-save-basic>Save</button>`;
      html += `<span class="save-status" data-save-status></span>`;
      return html;
    }

    async _saveBasicSettings() {
      const body = this.shadowRoot.querySelector(".body");
      const payload = { type: "smart_shutter/save_basic_settings" };
      body.querySelectorAll("[data-basic-field]").forEach((el) => {
        const key = el.getAttribute("data-basic-field");
        const isNumber = el.type === "number";
        payload[key] = el.type === "checkbox" ? el.checked : isNumber ? Number(el.value) : el.value;
      });
      body.querySelectorAll('[data-entity-picker][data-picker-attr="data-basic-field"]').forEach((slot) => {
        payload[slot.getAttribute("data-entity-picker")] = slot.getAttribute("data-value") || "";
      });
      const statusEl = body.querySelector("[data-save-status]");
      try {
        await this._hass.callWS(payload);
        await this._loadBackendConfig();
        this._haptic("success");
        if (statusEl) statusEl.textContent = this._message("saved");
      } catch (err) {
        this._haptic("failure");
        if (statusEl) statusEl.textContent = this._message("errorPrefix") + (err && err.message ? err.message : String(err));
      }
    }

    _notificationMode(settings) {
      return settings.notification_mode || ((settings.notify_service || "").trim() ? "custom" : "inherit");
    }

    _renderNotificationSettings(settings, coverEntityId = null, areaId = null) {
      const de = this._language() === "de";
      const area = !coverEntityId;
      const autosave = !area || !!areaId;
      const saveKey = coverEntityId ? `shutter:${coverEntityId}` : areaId ? `area:${areaId}` : null;
      const state = saveKey && this._notificationSaveStates && this._notificationSaveStates.get(saveKey);
      const displaySettings = state && state.draft && state.revision > state.savedRevision
        ? { ...settings, notification_mode: state.draft.mode, notify_service: state.draft.notifyService }
        : settings;
      const mode = this._notificationMode(displaySettings);
      const hintLabel = de ? "Hinweis anzeigen" : "Show information";
      const precedenceHint = area
        ? (de ? "Vererben übernimmt die globale Einstellung. Einstellungen einzelner Rollläden haben Vorrang." : "Inherit uses the global setting. Individual shutter settings take priority.")
        : (de ? "Vererben übernimmt die Bereichseinstellung, sonst die globale Einstellung. Bei mehreren Bereichen gilt für Zeitplanmeldungen der erste ausdrücklich konfigurierte Bereich; Sonnenstandsmeldungen nutzen den auslösenden Bereich." : "Inherit uses the area setting, otherwise the global setting. For schedule notifications, the first explicitly configured area wins; sun notifications use the triggering area.");
     const appliesHint = de
       ? "Gilt für Bewegungen, Frostschutz, Schließvorwarnungen und aktivierte Sonnenstandsmeldungen."
       : "Applies to movements, frost protection, pre-close warnings, and enabled sun notifications.";
      const notificationTitle = area ? "" : `<h3>${de ? "Benachrichtigungen" : "Notifications"}</h3>`;
     return `<div class="notification-settings" data-notification-settings data-notification-autosave="${autosave ? "true" : "false"}" ${coverEntityId ? `data-notification-entity="${this._escapeHtml(coverEntityId)}"` : ""} ${areaId ? `data-notification-area-id="${this._escapeHtml(areaId)}"` : ""}>
        <div class="notification-title">${notificationTitle}<details class="notification-info"><summary aria-label="${hintLabel}" title="${hintLabel}">i</summary><span class="notification-info-text">${appliesHint}</span></details></div>
        <div class="form-field">
          <label>${de ? "Benachrichtigungen empfangen" : "Receive notifications"}
            <select data-notification-mode ${area ? 'data-area-field="notification_mode"' : ""}>
              <option value="inherit" ${mode === "inherit" ? "selected" : ""}>${de ? "Vererben" : "Inherit"}</option>
              <option value="off" ${mode === "off" ? "selected" : ""}>${de ? "Aus" : "Off"}</option>
              <option value="custom" ${mode === "custom" ? "selected" : ""}>${de ? "Eigener Empfänger" : "Custom recipient"}</option>
            </select>
          </label>
        </div>
        <div class="notification-hint"><details class="notification-info"><summary aria-label="${hintLabel}" title="${hintLabel}">i</summary><span class="notification-info-text">${precedenceHint}</span></details></div>
        <div class="form-field" data-notification-recipient-field style="${mode === "custom" ? "" : "display:none"}">
          <label>${de ? "Benachrichtigungsdienst" : "Notification service"}
            <input type="text" data-notification-recipient ${area ? 'data-area-field="notify_service"' : ""} value="${this._escapeHtml(displaySettings.notify_service || "").replace(/"/g, "&quot;")}" placeholder="notify.mobile_app_phone" ${mode === "custom" ? "required" : ""} />
          </label>
        </div>
        <span class="notification-status" data-notification-status role="status" aria-live="polite">${this._escapeHtml(state && state.statusText || "")}</span>
      </div>`;
    }

    _notificationSaveKey(form) {
      const entityId = form.getAttribute("data-notification-entity");
      const areaId = form.getAttribute("data-notification-area-id");
      return entityId ? `shutter:${entityId}` : areaId ? `area:${areaId}` : null;
    }

    _notificationSaveState(key) {
      if (!key) return null;
      if (!this._notificationSaveStates) this._notificationSaveStates = new Map();
      let state = this._notificationSaveStates.get(key);
      if (!state) {
        state = { key, timer: null, saving: false, queued: false, revision: 0, savedRevision: 0, draft: null, statusText: "" };
        this._notificationSaveStates.set(key, state);
      }
      return state;
    }

    _notificationSaveForm(key) {
      if (!this.shadowRoot) return null;
      return [...this.shadowRoot.querySelectorAll("[data-notification-settings]")]
        .find((form) => this._notificationSaveKey(form) === key) || null;
    }

    _setNotificationSaveStatus(state, message) {
      state.statusText = message;
      const form = this._notificationSaveForm(state.key);
      const status = form && form.querySelector("[data-notification-status]");
      if (status) status.textContent = message;
    }

    _notificationDraft(form) {
      return {
        mode: form.querySelector("[data-notification-mode]").value,
        notifyService: form.querySelector("[data-notification-recipient]").value.trim(),
      };
    }

    _notificationDraftIsSavable(draft) {
      return !!draft && (draft.mode !== "custom" || !!draft.notifyService);
    }

    _scheduleNotificationSave(state, delay) {
      if (state.timer) clearTimeout(state.timer);
      if (state.saving) {
        state.queued = true;
        return;
      }
      state.timer = setTimeout(() => {
        state.timer = null;
        this._saveNotificationSettings(state);
      }, delay);
    }

    _queueNotificationSave(form, delay) {
      const key = this._notificationSaveKey(form);
      const state = this._notificationSaveState(key);
      if (!state) return;
      state.revision += 1;
      state.draft = this._notificationDraft(form);
      state.entityId = form.getAttribute("data-notification-entity");
      state.areaId = form.getAttribute("data-notification-area-id");
      state.entryId = this._backendConfig && this._backendConfig.entry_id;
      this._setNotificationSaveStatus(state, this._language() === "de" ? "Wird gespeichert…" : "Saving…");
      if (!this._notificationDraftIsSavable(state.draft)) {
        this._scheduleNotificationSave(state, delay);
        return;
      }
      this._scheduleNotificationSave(state, delay);
    }

    _cancelNotificationSave(form) {
      const key = this._notificationSaveKey(form);
      const state = this._notificationSaveStates && this._notificationSaveStates.get(key);
      if (!state) return;
      state.revision += 1;
      state.draft = this._notificationDraft(form);
      if (state.timer) {
        clearTimeout(state.timer);
        state.timer = null;
      }
      if (state.saving) state.queued = true;
      this._setNotificationSaveStatus(state, "");
    }

    async _saveNotificationSettings(state) {
      if (state.saving) {
        state.queued = true;
        return;
      }
      if (!this._notificationDraftIsSavable(state.draft)) return;
      const revision = state.revision;
      const { mode, notifyService } = state.draft;
      state.saving = true;
      state.queued = false;
      this._setNotificationSaveStatus(state, this._language() === "de" ? "Wird gespeichert…" : "Saving…");
      try {
        if (state.entityId) {
          await this._hass.callWS({
            type: "smart_shutter/save_shutter_notifications",
            entry_id: state.entryId,
            entity_id: state.entityId,
            notification_mode: mode,
            notify_service: mode === "custom" ? notifyService : "",
          });
        } else if (state.areaId) {
          await this._hass.callWS({
            type: "smart_shutter/save_own_area_settings",
            entry_id: state.entryId,
            area_id: state.areaId,
            fields: { notification_mode: mode, notify_service: mode === "custom" ? notifyService : "" },
          });
        } else {
          return;
        }
        await this._loadBackendConfig();
        state.savedRevision = Math.max(state.savedRevision, revision);
        if (revision === state.revision) {
          this._haptic("success");
          this._setNotificationSaveStatus(state, this._language() === "de" ? "Automatisch gespeichert." : "Saved automatically.");
        }
      } catch (err) {
        if (revision === state.revision) {
          this._haptic("failure");
          this._setNotificationSaveStatus(state, this._message("errorPrefix") + (err && err.message ? err.message : String(err)));
        }
      } finally {
        state.saving = false;
        if (state.queued || revision !== state.revision) {
          state.queued = false;
          if (this._notificationDraftIsSavable(state.draft)) this._scheduleNotificationSave(state, 0);
        }
      }
    }

    async _saveShutterNote(coverEntityId, note) {
      const body = this.shadowRoot.querySelector(".body");
      const statusEl = body.querySelector("[data-save-status]");
      try {
        await this._hass.callWS({
          type: "smart_shutter/save_shutter_note",
          entity_id: coverEntityId,
          note: note || "",
        });
        await this._loadBackendConfig();
        this._haptic("success");
        if (statusEl) statusEl.textContent = this._message("saved");
      } catch (err) {
        this._haptic("failure");
        if (statusEl) statusEl.textContent = this._message("errorPrefix") + (err && err.message ? err.message : String(err));
      }
    }

    _areaMembers(areaId) {
      const shutterAreas = (this._backendConfig && this._backendConfig.shutter_areas) || {};
      return this._model.shutters.filter((s) => (shutterAreas[s.coverEntityId] || []).includes(areaId));
    }

    _areaAutomationAllOn(members) {
      if (!members.length) return false;
      return members.every((s) => {
        const openSt = this._state(s.entities.automation.open && s.entities.automation.open.entity_id);
        const closeSt = this._state(s.entities.automation.close && s.entities.automation.close.entity_id);
        return openSt && openSt.state === "on" && closeSt && closeSt.state === "on";
      });
    }

    async _setAreaAutomation(areaId, turnOn) {
      const members = this._areaMembers(areaId);
      const service = turnOn ? "turn_on" : "turn_off";
      members.forEach((s) => {
        if (s.entities.automation.open) {
          this._hass.callService("switch", service, { entity_id: s.entities.automation.open.entity_id });
        }
        if (s.entities.automation.close) {
          this._hass.callService("switch", service, { entity_id: s.entities.automation.close.entity_id });
        }
      });
      this._haptic("success");
      this._showToast(this._message("areaAutomation", members.length, turnOn));
    }

    _renderAreaQuickActions(area, members) {
      if (!members.length) return "";
      const coverIds = members.map((s) => s.coverEntityId);
      const allOn = this._areaAutomationAllOn(members);
      const motion = this._groupMotionState(coverIds);
      return `
        <div class="area-quick-actions">
          <button data-area-bulk="open" data-area-ids="${coverIds.join(",")}" title="Alle hoch" ${motion.canOpen ? "" : "disabled"}><ha-icon icon="mdi:arrow-up"></ha-icon></button>
          <button data-area-bulk="stop" data-area-ids="${coverIds.join(",")}" title="Stopp" ${motion.canStop ? "" : "disabled"}><ha-icon icon="mdi:stop"></ha-icon></button>
          <button data-area-bulk="close" data-area-ids="${coverIds.join(",")}" title="Alle runter" ${motion.canClose ? "" : "disabled"}><ha-icon icon="mdi:arrow-down"></ha-icon></button>
          <span class="area-toggle-divider">
            <span class="switch-toggle" data-area-automation-toggle="${area.id}" title="Automatik für alle Mitglieder">
              <input type="checkbox" ${allOn ? "checked" : ""} />
              <span class="slider"></span>
            </span>
          </span>
        </div>
      `;
    }

    _renderSettingsAreas() {
      const areas = (this._backendConfig && this._backendConfig.custom_areas) || [];
      let html = `<button class="back" data-settings-back><ha-icon icon="mdi:arrow-left"></ha-icon> Back to Settings Menu</button>`;
      html += `<h2>Areas</h2>`;
      html += `<div class="hint">Custom groups (e.g. Front/Back/North/South) with preset settings. A shutter can belong to multiple areas at the same time. By using "Apply to members", the values are transferred to the individual settings of the assigned shutters. Up/Stop/Down and the automation switch take effect immediately on all members.</div>`;

      if (!areas.length) {
        html += `<p class="empty">No areas created yet.</p>`;
      } else {
        areas.forEach((area) => {
          const members = this._areaMembers(area.id);
          const sunBadge = area.sun_position_enabled
            ? `<span class="conflict-badge" style="background:var(--info-color,#2196f3)" title="Sonnenstand-Regel aktiv">☀ Sun position</span>`
            : "";
          html += `
            <div class="list-item">
              <div class="main">
                <div class="name">${area.name} ${sunBadge}</div>
                <div class="meta">${members.length} ${members.length === 1 ? "Rollladen" : "Rollläden"} zugeordnet</div>
                ${this._renderAreaQuickActions(area, members)}
              </div>
              <div class="actions">
                <button data-area-edit="${area.id}" title="Bearbeiten"><ha-icon icon="mdi:pencil"></ha-icon></button>
                <button data-area-delete="${area.id}" title="Löschen"><ha-icon icon="mdi:delete"></ha-icon></button>
              </div>
            </div>
          `;
        });
      }
      html += `<button class="add-btn" data-area-edit="__new__"><ha-icon icon="mdi:plus"></ha-icon> New Area</button>`;
      html += `<span class="save-status" data-save-status></span>`;
      return html;
    }

    // Uniform expand/collapse pattern for long forms (v0.19,
    // used in area form, rollershutter detail, base-
    // Settings) - reduces perceived complexity ("also for
    // technically less experienced users can be easily operated", WITHOUT
    // some function to hide: each section remains one
    // Click to remove, and it is automatically expanded if already
    // something is configured (defaultExpanded parameter) - you lose
    // also never unnoticed overview of already set values.
    // this._areaSectionExpanded is, despite its name, a generic
    // Storage for EACH open/close state of the card, not just for
    // area forms - unique key names (z.B. "detail-profiles-...",
    // "notify-templates") prevent collisions between the views.
    _sectionToggle(key, title, defaultExpanded) {
      if (this._areaSectionExpanded[key] === undefined) {
        this._areaSectionExpanded[key] = !!defaultExpanded;
      }
      const isOpen = this._areaSectionExpanded[key];
      return {
        isOpen,
        headerHtml: `
          <button class="section-toggle" data-toggle-area-section="${key}" type="button">
            <span>${title}</span>
            <ha-icon icon="${isOpen ? "mdi:chevron-up" : "mdi:chevron-down"}"></ha-icon>
          </button>
        `,
      };
    }

    _renderAreaEdit() {
      const areas = (this._backendConfig && this._backendConfig.custom_areas) || [];
      const existing = this._editingAreaId ? areas.find((a) => a.id === this._editingAreaId) : null;
      const shutterAreas = (this._backendConfig && this._backendConfig.shutter_areas) || {};

      let html = `<button class="back" data-settings-back-areas><ha-icon icon="mdi:arrow-left"></ha-icon> Back to List</button>`;
      html += `<h2>${existing ? "Bereich bearbeiten" : "Neuer Bereich"}</h2>`;

      if (this._isAdmin()) {
        html += `
          <div class="form-field">
            <label>Name</label>
            <input type="text" data-area-field="name" value="${existing ? existing.name : ""}" placeholder="z.B. Hinten" />
          </div>
        `;
      } else if (existing) {
        // Guest (v0.18): Name is structural (admin-only) - only
        // Display for orientation, not an editable field.
        html += `<div class="hint">Bereich: ${existing.name}</div>`;
      }

      const typeField = (action, label) => {
        const opts = action === "open" ? ["time", "sunrise"] : ["time", "sunset"];
        const current = existing ? existing[`${action}_type`] : null;
        return `
          <div class="control-row">
            <label>${label}</label>
            <select data-area-field="${action}_type">
              <option value=""${!current ? " selected" : ""}>Do not override</option>
              ${opts
                .map((o) => {
                  return `<option value="${o}"${current === o ? " selected" : ""}>${this._selectOptionLabel(o)}</option>`;
                })
                .join("")}
            </select>
          </div>
        `;
      };
      const numberField = (key, label, unit, min, max, step) => {
        const current = existing ? existing[key] : null;
        return `
          <div class="control-row">
            <label>${label}</label>
            <input type="number" min="${min}" max="${max}" ${step ? `step="${step}"` : ""} data-area-field="${key}" value="${
          current === null || current === undefined ? "" : current
        }" placeholder="nicht überschreiben" />
            <span class="unit">${unit}</span>
          </div>
        `;
      };

      // Uniform expand/collapse pattern for large formular-
      // Sections (unified in v0.19, see _sectionToggle()).
      const sectionToggle = (key, title, defaultExpanded) => this._sectionToggle(key, title, defaultExpanded);

      html += `<h3>Trigger Type (optional)</h3>`;
      html += typeField("open", "Öffnen");
      html += typeField("close", "Schließen");

      html += `<h3>Sun offset (optional)</h3>`;
      html += numberField("open_sun_offset", "Öffnen", "min", -60, 60);
      html += numberField("close_sun_offset", "Schließen", "min", -60, 60);

      html += `<h3>Target Position (optional)</h3>`;
      html += numberField("open_position", "Öffnen", "%", 0, 100);
      html += numberField("close_position", "Schließen", "%", 0, 100);

      const sunEnabled = existing ? !!existing.sun_position_enabled : false;
      const sunSection = sectionToggle(
        "sun",
        "Sonnenstand-Regel (optional)",
        sunEnabled || (existing && existing.sun_azimuth_from !== undefined && existing.sun_azimuth_from !== null)
      );
      html += sunSection.headerHtml;
      if (sunSection.isOpen) {
      html += `
        <div class="hint">
          Automatically moves all members of this area to the target position as soon as the sun shines in from the selected direction AND reaches at least the specified height - e.g. targeted shading when the sun shines directly on this facade. Runs independently of the normal open/close schedule.
        </div>
        <label class="control-row">
          <input type="checkbox" data-area-field="sun_position_enabled" ${sunEnabled ? "checked" : ""} />
          <span>Enable</span>
        </label>
      `;

      const existingFrom = existing ? existing.sun_azimuth_from : null;
      const existingTo = existing ? existing.sun_azimuth_to : null;
      const detectedDirection = detectCompassDirection(existingFrom, existingTo);
      const currentDirection =
        this._sunDirectionOverride !== undefined
          ? this._sunDirectionOverride
          : detectedDirection || "south";
      const isCustomDirection = currentDirection === CUSTOM_DIRECTION_KEY;
      const presetRange = COMPASS_PRESETS[currentDirection];
      const azFrom = isCustomDirection ? existingFrom : (presetRange ? presetRange[0] : existingFrom);
      const azTo = isCustomDirection ? existingTo : (presetRange ? presetRange[1] : existingTo);

      html += `
        <div class="control-row">
          <label>From which direction is the sun shining on this area?</label>
          <select data-sun-direction-select>
            ${Object.keys(COMPASS_PRESETS)
              .map((key) => `<option value="${key}"${currentDirection === key ? " selected" : ""}>${COMPASS_LABELS[this._language()][key]}</option>`)
              .join("")}
            <option value="${CUSTOM_DIRECTION_KEY}"${isCustomDirection ? " selected" : ""}>${COMPASS_LABELS[this._language()].custom}</option>
          </select>
        </div>
      `;
      if (isCustomDirection) {
        html += numberField("sun_azimuth_from", "Azimuth from", "°", 0, 360);
        html += numberField("sun_azimuth_to", "Azimuth to", "°", 0, 360);
      } else {
        // Compass direction selected: Azimuth fields remain part of the
        // Form (Saving reads them unchanged), but
        // hidden + automatically set to the preset - the
        // User sees only the simple direction selection.
        html += `
          <input type="hidden" data-area-field="sun_azimuth_from" value="${azFrom}" />
          <input type="hidden" data-area-field="sun_azimuth_to" value="${azTo}" />
        `;
      }
      html += numberField("sun_elevation_min", "Ab welcher Sonnenhöhe auslösen", "°", 0, 90);
      html += `<div class="meta">0° = Sun on the horizon, 90° = Sun at zenith (noon in summer). Rule of thumb: in the morning/afternoon usually 15-35°, at noon in summer up to 60°+.</div>`;
      html += numberField("sun_position_target", "Zielposition bei Sonnenstand", "%", 0, 100);
      html += `<div class="meta">Shutter position to which the rule drives when triggered (0% = fully closed, 100% = fully open).</div>`;

      const textAreaField = (key, label, hint, placeholder) => {
        const current = existing && existing[key] ? existing[key] : "";
        return `
          <div class="form-field">
            <label>${label}</label>
            <textarea data-area-field="${key}" rows="2" placeholder="${placeholder}">${current}</textarea>
            <div class="meta">${hint}</div>
          </div>
        `;
      };

      html += `<button class="link-btn" data-toggle-sun-advanced type="button">${
        this._sunAdvancedExpanded ? "▾ Erweiterte Optionen ausblenden" : "▸ Erweiterte Optionen (Hysterese, Zusatzbedingung, Benachrichtigung)"
      }</button>`;

      if (this._sunAdvancedExpanded) {
        html += numberField(
          "sun_elevation_hysteresis",
          "Hysterese-Puffer (optional)",
          "°",
          0,
          20
        );
        html += `<div class="meta">Prevents repeated triggering when the sun's elevation only slightly fluctuates around the threshold (it will only be reactivated after sufficient distance below the threshold).</div>`;

        html += textAreaField(
          "sun_condition_template",
          "Zusätzliche Bedingung (optional, Jinja-Template)",
          "Muss zusätzlich zu Richtung/Höhe \"true\" ergeben - z.B. Außen- vs. Innentemperatur. Bei Fehler oder leer: keine Zusatzbedingung (bzw. bei Fehler wird sicherheitshalber NICHT ausgelöst).",
          '{{ states("sensor.aussentemperatur")|float > states("sensor.innentemperatur")|float }}'
        );

        const sunNotifyEnabled = existing ? !!existing.sun_notify_enabled : false;
        html += `
          <label class="control-row">
            <input type="checkbox" data-area-field="sun_notify_enabled" ${sunNotifyEnabled ? "checked" : ""} />
            <span>Send notification when this rule triggers</span>
          </label>
        `;
        html += textAreaField(
          "sun_notify_text",
          "Notification text (optional, Jinja template)",
          "Variables: {{ area }}, {{ count }}, {{ position }}, {{ names }}. Empty = default text. Uses the configured notification service.",
          "{{ area }}: moved {{ count }} shutters to {{ position }}%."
        );

        const sunPrenotifyEnabled = existing ? !!existing.sun_prenotify_enabled : false;
        html += `
          <label class="control-row">
            <input type="checkbox" data-area-field="sun_prenotify_enabled" ${sunPrenotifyEnabled ? "checked" : ""} />
            <span>Send a warning BEFORE this rule is triggered</span>
          </label>
        `;
        html += numberField(
          "sun_prenotify_lead_minutes",
          "Vorlaufzeit (Minuten)",
          "min",
          1,
          60
        );
        html += `<div class="meta">Estimated warning time, no exact prediction (the sun position is continuously monitored, not like in the schedule to a fixed known time) - based on the current rate of change in sun height.</div>`;
        html += textAreaField(
          "sun_prenotify_text",
          "Warning text (optional, Jinja template)",
          this._language() === "de"
            ? "Variablen: {{ area }}, {{ count }}, {{ names }}, {{ position }}, {{ minutes }}. Leer = Standardtext."
            : "Variables: {{ area }}, {{ count }}, {{ names }}, {{ position }}, {{ minutes }}. Empty = default text.",
          "{{ area }}: shutters will move to {{ position }}% in about {{ minutes }} minutes."
        );
      }
      } // Ende sunSection.isOpen

      const notifySection = this._sectionToggle(
        "notify",
        "Benachrichtigungen (optional)",
        !!(existing && this._notificationMode(existing) !== "inherit")
      );
      html += notifySection.headerHtml;
      if (notifySection.isOpen) {
      html += this._renderNotificationSettings(existing || {}, null, existing && existing.id);
      }

      const frostSection = sectionToggle(
        "frost",
        "Frostschutz (optional)",
        !!(existing && (existing.inside_temp_sensor || existing.frost_threshold_c !== undefined && existing.frost_threshold_c !== null))
      );
      html += frostSection.headerHtml;
      if (frostSection.isOpen) {
      html += `
        <div class="hint">
          Without a custom sensor, a temperature sensor from the same room is used automatically if uniquely assignable - otherwise, the global indoor temperature sensor is used (Settings → Basic Settings).
        </div>
      `;
      const autoDetected =
        (this._backendConfig && this._backendConfig.area_auto_temp_sensors && existing
          ? this._backendConfig.area_auto_temp_sensors[existing.id]
          : null) || null;
      html += this._entityPickerField(
        "inside_temp_sensor",
        "Innentemperatur-Sensor (überschreiben)",
        existing ? existing.inside_temp_sensor : "",
        ["sensor"],
        "data-area-field",
        autoDetected
          ? `Automatisch erkannt: ${autoDetected} (wird verwendet, solange hier nichts eingetragen ist)`
          : "Kein passender Sensor automatisch erkannt - manuell auswählen oder globalen Standard-Sensor nutzen"
      );
      html += numberField("frost_threshold_c", "Frostschutz-Schwelle", "°C", -20, 15, 0.5);
      } // Ende frostSection.isOpen

      if (existing) {
        // v0.19: own, private schedule profiles for THIS area -
        // editable for Admin AND Guest (see FEAT "Guests should be able to edit everything
        // for their area can be set"). Deliberately separated from
        // the shared Custom Profiles (Settings → Custom Profiles,
        // admin-only) - a private area profile never affects
        // other areas or the host out (see
        // scheduler.determine_active_profile).
        const allSchedules = (this._backendConfig && this._backendConfig.custom_schedules) || [];
        const areaSchedules = allSchedules.filter((r) => r.area_id === existing.id);
        const conflicts = (this._backendConfig && this._backendConfig.schedule_conflicts) || {};
        const schedulesSection = sectionToggle(
          "schedules",
          "Eigene Zeitpläne für diesen Bereich",
          areaSchedules.length > 0
        );
        html += schedulesSection.headerHtml;
        if (schedulesSection.isOpen) {
        html += `
          <div class="hint">
            Recurring Time Exceptions ONLY for the shutters in this area (e.g. "Vacation of the holiday home"). Never affects other areas or your own host area. Order = Priority in case of overlaps - the first rule wins.
          </div>
        `;
        if (!areaSchedules.length) {
          html += `<p class="empty">No schedules for this area yet.</p>`;
        } else {
          areaSchedules.forEach((rule, idx) => {
            const days = (rule.weekdays || []).map((d) => WEEKDAY_SHORT[d]).join(", ");
            const times = [rule.open_time ? `Auf ${rule.open_time.slice(0, 5)}` : null, rule.close_time ? `Zu ${rule.close_time.slice(0, 5)}` : null]
              .filter(Boolean)
              .join(" · ");
            const conflictingIds = conflicts[rule.id] || [];
            const conflictBadge = conflictingIds.length
              ? `<span class="conflict-badge" title="Überschneidet sich mit: ${conflictingIds
                  .map((id) => (allSchedules.find((r) => r.id === id) || {}).name || id)
                  .join(", ")}">⚠ Conflict</span>`
              : "";
            html += `
              <div class="list-item">
                <div class="main">
                  <div class="name">${idx + 1}. ${rule.name} ${conflictBadge}</div>
                  <div class="meta">${days || "-"} · alle ${rule.interval_weeks || 1} Woche(n) · ${times}</div>
                </div>
                <div class="actions">
                  <button data-schedule-edit="${rule.id}" data-edit-return="area" data-edit-return-area-id="${existing.id}" title="Bearbeiten"><ha-icon icon="mdi:pencil"></ha-icon></button>
                  <button data-schedule-delete="${rule.id}" title="Löschen"><ha-icon icon="mdi:delete"></ha-icon></button>
                </div>
              </div>
            `;
          });
        }
        html += `<button class="add-btn" data-schedule-edit="__new__" data-edit-return="area" data-edit-return-area-id="${existing.id}"><ha-icon icon="mdi:plus"></ha-icon> New schedule for this area</button>`;
        } // Ende schedulesSection.isOpen
      }

      if (this._isAdmin()) {
        const assignedUserIdsForToggle = (existing && existing.assigned_ha_user_ids) || [];
        const accessSection = sectionToggle("access", "Zugriff", assignedUserIdsForToggle.length > 0);
        html += accessSection.headerHtml;
        if (accessSection.isOpen) {
        html += `
          <div class="hint">
            HA users who are allowed to see/operate ONLY this area (e.g. Airbnb/tenant access) - typical use case: own, non-admin HA user per rented apartment, who in HA itself is additionally granted (Settings → People → Users) only the entities of that apartment. This area assignment alone does NOT replace HA's own user permissions - it only controls what the Smart-Shutter card displays/provides.
          </div>
        `;
        const assignedUserIds = (existing && existing.assigned_ha_user_ids) || [];
        if (!this._model.haUsers.length) {
          html += `<div class="hint">No HA users found.</div>`;
        }
        this._model.haUsers.forEach((u) => {
          html += `
            <label class="control-row">
              <input type="checkbox" data-area-user="${u.id}" ${assignedUserIds.includes(u.id) ? "checked" : ""} />
              <span>${u.name}</span>
            </label>
          `;
        });
        } // Ende accessSection.isOpen

        html += `<h3>Members</h3>`;
        html += `<div class="hint">A shutter can belong to multiple areas at the same time (e.g. "Back" AND "Living rooms") - when applying, the last applied area takes precedence in case of conflicting settings.</div>`;
        this._model.shutters.forEach((s) => {
          const memberAreaIds = shutterAreas[s.coverEntityId] || [];
          const checked = existing && memberAreaIds.includes(existing.id);
          const otherAreaNames = memberAreaIds
            .filter((id) => !existing || id !== existing.id)
            .map((id) => (areas.find((a) => a.id === id) || {}).name)
            .filter(Boolean);
          html += `
            <label class="control-row">
              <input type="checkbox" data-area-member="${s.coverEntityId}" ${checked ? "checked" : ""} />
              <span><span data-shutter-name="${s.deviceId}">${this._escapeHtml(s.name)}</span>${otherAreaNames.length ? ` <span class="meta">(${this._language() === "de" ? "auch" : "also"}: ${otherAreaNames.join(", ")})</span>` : ""}</span>
            </label>
          `;
        });
      }

      html += `<button class="add-btn" data-area-save>${
        existing ? '<ha-icon icon="mdi:content-save"></ha-icon> Speichern' : '<ha-icon icon="mdi:plus"></ha-icon> Bereich anlegen'
      }</button>`;
      if (existing) {
        html += `<button class="add-btn" data-area-apply="${existing.id}"><ha-icon icon="mdi:content-save-move-outline"></ha-icon> Apply to all members now</button>`;
      }
      html += `<span class="save-status" data-save-status></span>`;
      return html;
    }

    _renderSettingsSchedules() {
      const schedules = (this._backendConfig && this._backendConfig.custom_schedules) || [];
      const conflicts = (this._backendConfig && this._backendConfig.schedule_conflicts) || {};
      let html = `<button class="back" data-settings-back><ha-icon icon="mdi:arrow-left"></ha-icon> Back to Settings Menu</button>`;
      html += `<h2>Custom profiles</h2>`;
      html += `<div class="hint">Recurring Time Exceptions, apply to all shutters (can be overwritten locally per shutter). Order = Priority in case of overlaps - the first rule wins.</div>`;

      if (!schedules.length) {
        html += `<p class="empty">No custom profiles created yet.</p>`;
      } else {
        schedules.forEach((rule, idx) => {
          const days = (rule.weekdays || []).map((d) => WEEKDAY_SHORT[d]).join(", ");
          const times = [rule.open_time ? `Auf ${rule.open_time.slice(0, 5)}` : null, rule.close_time ? `Zu ${rule.close_time.slice(0, 5)}` : null]
            .filter(Boolean)
            .join(" · ");
          const conflictingIds = conflicts[rule.id] || [];
          const conflictBadge = conflictingIds.length
            ? `<span class="conflict-badge" title="Überschneidet sich mit: ${conflictingIds
                .map((id) => (schedules.find((r) => r.id === id) || {}).name || id)
                .join(", ")}">⚠ Conflict</span>`
            : "";
          html += `
            <div class="list-item" draggable="true" data-schedule-drag="${rule.id}">
              <button class="drag-handle" title="Ziehen zum Sortieren"><ha-icon icon="mdi:drag-vertical"></ha-icon></button>
              <div class="main">
                <div class="name">${idx + 1}. ${rule.name} ${conflictBadge}</div>
                <div class="meta">${days || "-"} · alle ${rule.interval_weeks || 1} Woche(n) · ${times}</div>
              </div>
              <div class="actions">
                <button data-schedule-edit="${rule.id}" title="Bearbeiten"><ha-icon icon="mdi:pencil"></ha-icon></button>
                <button data-schedule-delete="${rule.id}" title="Löschen"><ha-icon icon="mdi:delete"></ha-icon></button>
              </div>
            </div>
          `;
        });
      }
      html += `<button class="add-btn" data-schedule-edit="__new__"><ha-icon icon="mdi:plus"></ha-icon> New custom profile</button>`;
      html += `<span class="save-status" data-save-status></span>`;
      return html;
    }

    _renderScheduleEdit() {
      const schedules = (this._backendConfig && this._backendConfig.custom_schedules) || [];
      const editingId = this._editingScheduleId;
      const existing = editingId ? schedules.find((r) => r.id === editingId) : null;

      let html = `<button class="back" data-settings-back-schedules><ha-icon icon="mdi:arrow-left"></ha-icon> Zurück${
        this._editReturnView === "detail" ? " zum Rollladen" : this._editReturnView === "area" ? " zum Bereich" : " zur Liste"
      }</button>`;
      html += `<h2>${existing ? existing.name : "New custom profile"}</h2>`;
      html += `<div class="form-grid">`;
      html += `
        <div class="form-field">
          <label>Name</label>
          <input type="text" data-schedule-field="name" value="${existing ? existing.name : ""}" />
        </div>
        <div class="form-field">
          <label>Weekdays</label>
          <div class="weekday-picker">
            ${WEEKDAY_KEYS.map(
              (key, i) => `
              <label>
                <input type="checkbox" data-schedule-weekday="${i}" ${existing && (existing.weekdays || []).includes(i) ? "checked" : ""} />
                <span>${WEEKDAY_SHORT[i]}</span>
              </label>`
            ).join("")}
          </div>
        </div>
        <div class="form-field">
          <label>Repeat every how many weeks? (1 = every week)</label>
          <input type="number" min="1" max="52" data-schedule-field="interval_weeks" value="${existing ? existing.interval_weeks || 1 : 1}" />
        </div>
        <div class="form-field">
          <label>Reference date</label>
          <input type="date" data-schedule-field="reference_date" value="${existing ? existing.reference_date || "" : new Date().toISOString().slice(0, 10)}" />
        </div>
        <div class="form-field">
          <label>Expiry date (optional)</label>
          <input type="date" data-schedule-field="end_date" value="${existing && existing.end_date ? existing.end_date : ""}" />
        </div>
        <div class="form-field">
          <label>Open Time (optional)</label>
          <input type="time" data-schedule-field="open_time" value="${existing && existing.open_time ? existing.open_time.slice(0, 5) : ""}" />
        </div>
        <div class="form-field">
          <label>Close Time (optional)</label>
          <input type="time" data-schedule-field="close_time" value="${existing && existing.close_time ? existing.close_time.slice(0, 5) : ""}" />
        </div>
      `;
      html += `</div>`;
      html += `<button class="save-btn" data-save-schedule>Save</button>`;
      html += `<span class="save-status" data-save-status></span>`;
      return html;
    }

    _onDragStart(ev) {
      const item = ev.target.closest("[data-schedule-drag]");
      if (!item) return;
      this._dragRuleId = item.getAttribute("data-schedule-drag");
      ev.dataTransfer.effectAllowed = "move";
      item.classList.add("dragging");
    }

    _onDragOver(ev) {
      const item = ev.target.closest("[data-schedule-drag]");
      if (!item || !this._dragRuleId) return;
      ev.preventDefault();
      this.shadowRoot.querySelectorAll("[data-schedule-drag]").forEach((el) => el.classList.remove("drag-over"));
      if (item.getAttribute("data-schedule-drag") !== this._dragRuleId) item.classList.add("drag-over");
    }

    async _onDrop(ev) {
      const item = ev.target.closest("[data-schedule-drag]");
      if (!item || !this._dragRuleId) return;
      ev.preventDefault();
      const targetId = item.getAttribute("data-schedule-drag");
      const draggedId = this._dragRuleId;
      this._dragRuleId = null;
      if (targetId === draggedId) return;

      const schedules = [...((this._backendConfig && this._backendConfig.custom_schedules) || [])];
      const fromIdx = schedules.findIndex((r) => r.id === draggedId);
      const toIdx = schedules.findIndex((r) => r.id === targetId);
      if (fromIdx === -1 || toIdx === -1) return;
      const [moved] = schedules.splice(fromIdx, 1);
      schedules.splice(toIdx, 0, moved);

      this._haptic("light");
      // force=true: pure reordering does not change, WHICH rules
      // overlap - only who wins in case of a conflict. A redefinition
      // Conflict confirmation question would be disruptive here.
      await this._submitSchedules(schedules, true, null);
    }

    _onDragEnd(ev) {
      this._dragRuleId = null;
      this.shadowRoot.querySelectorAll("[data-schedule-drag]").forEach((el) => {
        el.classList.remove("dragging", "drag-over");
      });
    }

    async _deleteSchedule(ruleId) {
      if (!window.confirm(this._message("confirmDeleteProfile"))) return;
      const allSchedules = (this._backendConfig && this._backendConfig.custom_schedules) || [];
      const rule = allSchedules.find((r) => r.id === ruleId);
      const schedules = allSchedules.filter((r) => r.id !== ruleId);
      this._haptic("light");
      if (rule && rule.area_id) {
        await this._submitAreaSchedules(
          rule.area_id,
          schedules.filter((r) => r.area_id === rule.area_id),
          true,
          null
        );
      } else {
        await this._submitSchedules(schedules, true, null);
      }
    }

    async _saveSchedule() {
      const body = this.shadowRoot.querySelector(".body");
      const statusEl = body.querySelector("[data-save-status]");
      const editingId = this._editingScheduleId;
      const areaId = this._editReturnAreaId;

      const weekdays = [...body.querySelectorAll("[data-schedule-weekday]:checked")].map((el) =>
        Number(el.getAttribute("data-schedule-weekday"))
      );
      const field = (key) => {
        const el = body.querySelector(`[data-schedule-field="${key}"]`);
        return el ? el.value : "";
      };
      const rule = {
        id: editingId || "",
        name: field("name").trim(),
        weekdays,
        interval_weeks: Number(field("interval_weeks")) || 1,
        reference_date: field("reference_date") || null,
        end_date: field("end_date") || null,
        open_time: field("open_time") || null,
        close_time: field("close_time") || null,
      };

      if (areaId) {
        // area-specific profile (v0.19, see FEAT "Guests should be able to access everything
        // for their area can be set") - ONLY the rules of this
        // a area is sent along, save_own_area_schedules
        // leaves all shared + foreign area rules untouched.
        const allSchedules = (this._backendConfig && this._backendConfig.custom_schedules) || [];
        const areaSchedules = allSchedules.filter((r) => r.area_id === areaId);
        const others = editingId ? areaSchedules.filter((r) => r.id !== editingId) : areaSchedules;
        await this._submitAreaSchedules(areaId, [...others, rule], false, statusEl);
        return;
      }

      const schedules = [...((this._backendConfig && this._backendConfig.custom_schedules) || [])];
      const others = editingId ? schedules.filter((r) => r.id !== editingId) : schedules;
      const newList = [...others, rule];

      await this._submitSchedules(newList, false, statusEl);
    }

    async _saveAreas(areas, navigate = true) {
      try {
        const result = await this._hass.callWS({ type: "smart_shutter/save_custom_areas", areas });
        if (result.success) {
          await this._loadBackendConfig();
          if (navigate) {
            this._editingAreaId = null;
            this._view = "settings-areas";
          }
        }
        if (navigate) this._render();
        return !!result.success;
      } catch (err) {
        const status = this.shadowRoot.querySelector("[data-save-status]");
        if (status) status.textContent = this._message("errorPrefix") + (err.message || String(err));
        this._haptic("failure");
        return false;
      }
    }

    async _saveShutterAreas(shutterAreas) {
      await this._hass.callWS({ type: "smart_shutter/save_shutter_areas", shutter_areas: shutterAreas });
      await this._loadBackendConfig();
    }

    async _collectAndSaveArea() {
      const body = this.shadowRoot.querySelector(".body");
      const existingAreas = (this._backendConfig && this._backendConfig.custom_areas) || [];
      const existing = this._editingAreaId ? existingAreas.find((a) => a.id === this._editingAreaId) : null;
      const readNumber = (key) => {
        const el = body.querySelector(`[data-area-field="${key}"]`);
        if (!el) return existing && existing[key] !== undefined ? existing[key] : null;
        const v = el && el.value.trim();
        return v ? parseInt(v, 10) : null;
      };
      const readSelect = (key) => {
        const el = body.querySelector(`[data-area-field="${key}"]`);
        return el && el.value ? el.value : null;
      };

      const readCheckbox = (key) => {
        const el = body.querySelector(`[data-area-field="${key}"]`);
        if (!el) return existing ? !!existing[key] : false;
        return !!(el && el.checked);
      };

      const readText = (key) => {
        const el = body.querySelector(`[data-area-field="${key}"]`);
        if (!el) return existing && existing[key] ? existing[key] : null;
        return el && el.value.trim() ? el.value.trim() : null;
      };

      const readFloat = (key) => {
        const el = body.querySelector(`[data-area-field="${key}"]`);
        if (!el) return existing && existing[key] !== undefined ? existing[key] : null;
        const v = el && el.value.trim();
        return v ? parseFloat(v) : null;
      };

      const readEntityPicker = (key) => {
        const slot = body.querySelector(
          `[data-entity-picker="${key}"][data-picker-attr="data-area-field"]`
        );
        if (!slot) return existing && existing[key] ? existing[key] : null;
        const v = (slot.getAttribute("data-value") || "").trim();
        return v || null;
      };

      // business area settings - for admins AND (v0.18)
      // editable for non-Admin guests in their assigned area
      // (see websocket_api.handle_save_own_area_settings).
      const operationalFields = {
        open_type: readSelect("open_type"),
        close_type: readSelect("close_type"),
        open_sun_offset: readNumber("open_sun_offset"),
        close_sun_offset: readNumber("close_sun_offset"),
        open_position: readNumber("open_position"),
        close_position: readNumber("close_position"),
        sun_position_enabled: readCheckbox("sun_position_enabled"),
        sun_azimuth_from: readNumber("sun_azimuth_from"),
        sun_azimuth_to: readNumber("sun_azimuth_to"),
        sun_elevation_min: readNumber("sun_elevation_min"),
        sun_elevation_hysteresis: readNumber("sun_elevation_hysteresis"),
        sun_position_target: readNumber("sun_position_target"),
        sun_condition_template: readText("sun_condition_template"),
        sun_notify_enabled: readCheckbox("sun_notify_enabled"),
        sun_notify_text: readText("sun_notify_text"),
        sun_prenotify_enabled: readCheckbox("sun_prenotify_enabled"),
        sun_prenotify_lead_minutes: readNumber("sun_prenotify_lead_minutes"),
        sun_prenotify_text: readText("sun_prenotify_text"),
        inside_temp_sensor: readEntityPicker("inside_temp_sensor"),
        frost_threshold_c: readFloat("frost_threshold_c"),
        notification_mode: readSelect("notification_mode") || this._notificationMode(existing || {}),
        notify_service: readText("notify_service"),
      };
      if (operationalFields.notification_mode !== "custom") operationalFields.notify_service = "";
      const recipient = body.querySelector("[data-notification-recipient]");
      if (operationalFields.notification_mode === "custom" && recipient && !recipient.reportValidity()) return;
      if (
        operationalFields.sun_position_enabled &&
        (operationalFields.sun_azimuth_from === null ||
          operationalFields.sun_azimuth_to === null ||
          operationalFields.sun_elevation_min === null ||
          operationalFields.sun_position_target === null)
      ) {
        window.alert(this._message("sunValuesRequired"));
        return;
      }

      if (!this._isAdmin()) {
        // Guest (v0.18): ONLY the business fields of their own
        // of the already assigned area - no name, no members,
        // no user assignment. The server verifies the permission
        // additionally defined by itself (see _allowed_area_ids), this is only
        // the corresponding UI for it.
        if (!existing) return;
        await this._hass.callWS({
          type: "smart_shutter/save_own_area_settings",
          area_id: existing.id,
          fields: operationalFields,
        });
        await this._loadBackendConfig();
        this._editingAreaId = null;
        this._view = "settings-areas";
        this._render();
        return;
      }

      const name = body.querySelector('[data-area-field="name"]').value.trim();
      if (!name) {
        window.alert(this._message("areaNameRequired"));
        return;
      }

      // ID assigned client-side (instead of guessing them after saving
      // must) - this allows the member assignment to be done in the same step
      // with saving, also for a completely new area.
      const areaId = this._editingAreaId || `area_${Math.random().toString(16).slice(2, 10)}`;

      const areas = [...((this._backendConfig && this._backendConfig.custom_areas) || [])];
      const existingIdx = areas.findIndex((a) => a.id === areaId);
      const assignedUserIds = Array.from(body.querySelectorAll("[data-area-user]"))
        .filter((cb) => cb.checked)
        .map((cb) => cb.getAttribute("data-area-user"));
      const area = {
        id: areaId,
        name,
        ...operationalFields,
        assigned_ha_user_ids: assignedUserIds,
      };
      if (existingIdx >= 0) areas[existingIdx] = area;
      else areas.push(area);

      // Collect member assignments: shutter assigned to checked shutters
      // ADD THIS area to their list of areas, unchecked
      // lose ONLY this one area - membership to other
      // Areas remain untouched (a shutter can belong to multiple
      // areas at the same time, z.B. "Behind" AND "Living areas").
      const shutterAreas = { ...((this._backendConfig && this._backendConfig.shutter_areas) || {}) };
      body.querySelectorAll("[data-area-member]").forEach((cb) => {
        const coverEntityId = cb.getAttribute("data-area-member");
        const current = shutterAreas[coverEntityId] || [];
        const withoutThisArea = current.filter((id) => id !== areaId);
        shutterAreas[coverEntityId] = cb.checked
          ? (current.includes(areaId) ? current : [...current, areaId])
          : withoutThisArea;
        if (!shutterAreas[coverEntityId].length) delete shutterAreas[coverEntityId];
      });

      // Validate the area before changing membership; keep the draft on errors.
      if (!await this._saveAreas(areas, false)) return;
      this._editingAreaId = areaId;
      await this._saveShutterAreas(shutterAreas);
      this._editingAreaId = null;
      this._view = "settings-areas";
      this._render();
    }

    async _applyAreaToMembers(areaId) {
      const area = ((this._backendConfig && this._backendConfig.custom_areas) || []).find((a) => a.id === areaId);
      if (!area) return;
      const members = this._areaMembers(areaId);

      // v0.20.1: before overwriting, check if a member is already
      // individual ("Individual") settings exactly for the fields
      // has, which this area would now overwrite (z.B. a
      // Position limit due to a flower pot on the windowsill) -
      // if yes, first ask for confirmation (including any stored
      // Note, see shutter_notes), instead of silently
      // applies. Applies ONLY to fields that the area actually
      // overrides (empty/undefined area fields never override
      // something, see the individual "!== null" checks further below).
      const notes = (this._backendConfig && this._backendConfig.shutter_notes) || {};
      const conflicts = [];
      for (const s of members) {
        const e = this._seasonEntities(s.entities, this._activeSeason());
        const reasons = [];
        const openSourceState = this._state(e.sourceSelect.open && e.sourceSelect.open.entity_id);
        const closeSourceState = this._state(e.sourceSelect.close && e.sourceSelect.close.entity_id);
        const openPosSourceState = this._state(e.positionSourceSelect.open && e.positionSourceSelect.open.entity_id);
        const closePosSourceState = this._state(e.positionSourceSelect.close && e.positionSourceSelect.close.entity_id);
        const wouldOverrideOpenType =
          (area.open_type || (area.open_sun_offset !== null && area.open_sun_offset !== undefined)) &&
          openSourceState && openSourceState.state === SOURCE_OPTION_LOCAL;
        const wouldOverrideCloseType =
          (area.close_type || (area.close_sun_offset !== null && area.close_sun_offset !== undefined)) &&
          closeSourceState && closeSourceState.state === SOURCE_OPTION_LOCAL;
        const wouldOverrideOpenPos =
          area.open_position !== null && area.open_position !== undefined &&
          openPosSourceState && openPosSourceState.state === SOURCE_OPTION_LOCAL;
        const wouldOverrideClosePos =
          area.close_position !== null && area.close_position !== undefined &&
          closePosSourceState && closePosSourceState.state === SOURCE_OPTION_LOCAL;
        if (wouldOverrideOpenType || wouldOverrideCloseType) reasons.push(this._message("conflictReasonTrigger"));
        if (wouldOverrideOpenPos || wouldOverrideClosePos) reasons.push(this._message("conflictReasonPosition"));
        if (reasons.length) {
          conflicts.push({ name: s.name, reasons, note: notes[s.coverEntityId] || "" });
        }
      }
      if (conflicts.length) {
        const details = conflicts
          .map((c) => `- ${c.name} (${c.reasons.join(", ")})${c.note ? `\n  ${this._message("notePrefix")}: "${c.note}"` : ""}`)
          .join("\n");
        const proceed = window.confirm(this._message("confirmApplyOverrides", conflicts.length, area.name, details));
        if (!proceed) {
          this._haptic("selection");
          return;
        }
      }

      this._showToast(this._message("areaApplying", area.name, members.length));
      this._invalidateForecastCache();
      const globalType = this._seasonEntities(this._model.globalEntities, this._activeSeason()).localType;
      for (const s of members) {
        const e = this._seasonEntities(s.entities, this._activeSeason());
        // IMPORTANT: open_source/close_source controls trigger type AND
        // Solar offset SHARED (see scheduler._use_local_source) -
        // must therefore also be switched to "Individual" in this case,
        // if ONLY the solar offset is overwritten, otherwise the
        // locally set value ignored by the scheduler and still uses the
        // global value used (bug: "area still shows despite
        // global sun offset").
        const openOverridesSourceGoverned =
          area.open_type || (area.open_sun_offset !== null && area.open_sun_offset !== undefined);
        const closeOverridesSourceGoverned =
          area.close_type || (area.close_sun_offset !== null && area.close_sun_offset !== undefined);

        if (openOverridesSourceGoverned) {
          await this._selectOption(e.sourceSelect.open, SOURCE_OPTION_LOCAL);
        }
        if (area.open_type) {
          await this._selectOption(e.localType.open, area.open_type);
        } else if (openOverridesSourceGoverned) {
          // Only the solar offset is overwritten, the trigger type
          // ("Do not overwrite") should remain unchanged. The local
          // Typ-Select is set by default to "Time" without
          // set value - if the source is now set to Individual
          // switched, without setting the local type, the
          // complete action unplanned from (same error class as
          // the critical resolve_fixed_time-Bug). Therefore: local type
          // on the currently globally active value reflect.
          const currentGlobalOpenType = this._state(globalType.open && globalType.open.entity_id);
          if (currentGlobalOpenType) await this._selectOption(e.localType.open, currentGlobalOpenType.state);
        }
        if (closeOverridesSourceGoverned) {
          await this._selectOption(e.sourceSelect.close, SOURCE_OPTION_LOCAL);
        }
        if (area.close_type) {
          await this._selectOption(e.localType.close, area.close_type);
        } else if (closeOverridesSourceGoverned) {
          const currentGlobalCloseType = this._state(globalType.close && globalType.close.entity_id);
          if (currentGlobalCloseType) await this._selectOption(e.localType.close, currentGlobalCloseType.state);
        }
        if (area.open_sun_offset !== null && area.open_sun_offset !== undefined && e.sunOffset.open) {
          await this._hass.callService("number", "set_value", {
            entity_id: e.sunOffset.open.entity_id,
            value: area.open_sun_offset,
          });
        }
        if (area.close_sun_offset !== null && area.close_sun_offset !== undefined && e.sunOffset.close) {
          await this._hass.callService("number", "set_value", {
            entity_id: e.sunOffset.close.entity_id,
            value: area.close_sun_offset,
          });
        }
        if (area.open_position !== null && area.open_position !== undefined && e.position.open) {
          await this._selectOption(e.positionSourceSelect.open, SOURCE_OPTION_LOCAL);
          await this._hass.callService("number", "set_value", {
            entity_id: e.position.open.entity_id,
            value: area.open_position,
          });
        }
        if (area.close_position !== null && area.close_position !== undefined && e.position.close) {
          await this._selectOption(e.positionSourceSelect.close, SOURCE_OPTION_LOCAL);
          await this._hass.callService("number", "set_value", {
            entity_id: e.position.close.entity_id,
            value: area.close_position,
          });
        }
      }
    }

    async _submitSchedules(schedules, force, statusEl) {
      try {
        const result = await this._hass.callWS({
          type: "smart_shutter/save_custom_schedules",
          schedules,
          force,
        });
        if (result.success) {
          await this._loadBackendConfig();
          this._haptic("success");
          this._editingScheduleId = null;
          this._exitEditor("settings-schedules");
          this._render();
          return;
        }
        if (result.conflicts && result.conflicts.length) {
          this._haptic("warning");
          const names = result.conflicts
            .flatMap((c) => c.overlapping_with.map((o) => o.name))
            .join(", ");
          if (
            window.confirm(
              this._message("confirmScheduleConflict", names)
            )
          ) {
            await this._submitSchedules(schedules, true, statusEl);
          }
          return;
        }
        if (result.validation_error) {
          this._haptic("failure");
          const messages = {
            no_name: this._message("validationNoName"),
            no_weekdays: this._message("validationNoWeekdays"),
            no_time: this._message("validationNoTime"),
          };
          if (statusEl) statusEl.textContent = messages[result.validation_error] || this._message("invalidInput");
        }
      } catch (err) {
        this._haptic("failure");
        if (statusEl) statusEl.textContent = this._message("errorPrefix") + (err && err.message ? err.message : String(err));
      }
    }

    async _submitAreaSchedules(areaId, schedules, force, statusEl) {
      try {
        const result = await this._hass.callWS({
          type: "smart_shutter/save_own_area_schedules",
          area_id: areaId,
          schedules,
          force,
        });
        if (result.success) {
          await this._loadBackendConfig();
          this._haptic("success");
          this._editingScheduleId = null;
          this._exitEditor("settings-area-edit");
          this._render();
          return;
        }
        if (result.conflicts && result.conflicts.length) {
          this._haptic("warning");
          const names = result.conflicts
            .flatMap((c) => c.overlapping_with.map((o) => o.name))
            .join(", ");
          if (
            window.confirm(
              this._message("confirmScheduleConflict", names)
            )
          ) {
            await this._submitAreaSchedules(areaId, schedules, true, statusEl);
          }
          return;
        }
        if (result.validation_error) {
          this._haptic("failure");
          const messages = {
            no_name: this._message("validationNoName"),
            no_weekdays: this._message("validationNoWeekdays"),
            no_time: this._message("validationNoTime"),
          };
          if (statusEl) statusEl.textContent = messages[result.validation_error] || this._message("invalidInput");
        }
      } catch (err) {
        this._haptic("failure");
        if (statusEl) statusEl.textContent = this._message("errorPrefix") + (err && err.message ? err.message : String(err));
      }
    }

    _renderSettingsTriggers() {
      const triggers = (this._backendConfig && this._backendConfig.external_triggers) || [];
      const areas = (this._backendConfig && this._backendConfig.custom_areas) || [];
      let html = `<button class="back" data-settings-back><ha-icon icon="mdi:arrow-left"></ha-icon> Back to Settings Menu</button>`;
      html += `<h2>External Triggers</h2>`;
      html += `<div class="hint">Named rules whose target time is set via service (smart_shutter.set_external_trigger) from an external automation. Always takes precedence over profiles/custom profiles. Can control a single shutter OR an entire area (all members).</div>`;

      if (!triggers.length) {
        html += `<p class="empty">No external triggers created yet.</p>`;
      } else {
        triggers.forEach((t) => {
          const targetLabel = t.area_id
            ? `Bereich: ${(areas.find((a) => a.id === t.area_id) || {}).name || t.area_id}`
            : t.entity_id;
          html += `
            <div class="list-item">
              <div class="main">
                <div class="name">${t.name}</div>
                <div class="meta">${targetLabel} · ${t.action === "open" ? "Öffnen" : "Schließen"}</div>
              </div>
              <div class="actions">
                <button data-trigger-edit="${t.id}" title="Bearbeiten"><ha-icon icon="mdi:pencil"></ha-icon></button>
                <button data-trigger-delete="${t.id}" title="Löschen"><ha-icon icon="mdi:delete"></ha-icon></button>
              </div>
            </div>
          `;
        });
      }
      html += `<button class="add-btn" data-trigger-edit="__new__"><ha-icon icon="mdi:plus"></ha-icon> Create new external trigger</button>`;
      html += `<span class="save-status" data-save-status></span>`;
      return html;
    }

    _renderTriggerEdit() {
      const triggers = (this._backendConfig && this._backendConfig.external_triggers) || [];
      const editingId = this._editingTriggerId;
      const existing = editingId ? triggers.find((t) => t.id === editingId) : null;
      const covers = (this._backendConfig && this._backendConfig.covers) || [];
      const areas = (this._backendConfig && this._backendConfig.custom_areas) || [];
      const targetMode = this._triggerTargetMode || (existing && existing.area_id ? "area" : "entity");

      let html = `<button class="back" data-settings-back-triggers><ha-icon icon="mdi:arrow-left"></ha-icon> Zurück${
        this._editReturnView === "detail" ? " zum Rollladen" : " zur Liste"
      }</button>`;
      html += `<h2>${existing ? existing.name : "New external trigger"}</h2>`;
      html += `<div class="form-grid">`;
      html += `
        <div class="form-field">
          <label>Name</label>
          <input type="text" data-trigger-field="name" value="${existing ? existing.name : ""}" />
          <div class="meta">Used as a reference in the service smart_shutter.set_external_trigger.</div>
        </div>
        <div class="form-field">
          <label>Target</label>
          <select data-trigger-target-mode>
            <option value="entity" ${targetMode === "entity" ? "selected" : ""}>Single Shutter</option>
            <option value="area" ${targetMode === "area" ? "selected" : ""}>Entire Area (all members)</option>
          </select>
        </div>
      `;
      if (targetMode === "area") {
        html += `
          <div class="form-field">
            <label>Area</label>
            <select data-trigger-field="area_id">
              ${areas
                .map(
                  (a) =>
                    `<option value="${a.id}" ${existing && existing.area_id === a.id ? "selected" : ""}>${a.name}</option>`
                )
                .join("")}
            </select>
          </div>
        `;
      } else {
        html += this._entityPickerField(
          "entity_id",
          "Rollladen",
          existing ? existing.entity_id : this._prefillTriggerCover || "",
          null,
          "data-trigger-field",
          "",
          covers.map((c) => c.entity_id)
        );
      }
      html += `
        <div class="form-field">
          <label>Action</label>
          <select data-trigger-field="action">
            <option value="open" ${existing && existing.action === "open" ? "selected" : ""}>Open</option>
            <option value="close" ${!existing || existing.action === "close" ? "selected" : ""}>Close</option>
          </select>
        </div>
      `;
      html += `</div>`;
      html += `<button class="save-btn" data-save-trigger>Save</button>`;
      html += `<span class="save-status" data-save-status></span>`;
      return html;
    }

    async _submitTriggers(triggers, statusEl) {
      try {
        const result = await this._hass.callWS({
          type: "smart_shutter/save_external_triggers",
          triggers,
        });
        if (result.success) {
          await this._loadBackendConfig();
          this._haptic("success");
          this._editingTriggerId = null;
          this._exitEditor("settings-triggers");
          this._render();
          return;
        }
        if (result.validation_error) {
          this._haptic("failure");
          const messages = {
            no_name: this._message("validationNoName"),
            duplicate_name: this._message("validationDuplicateName"),
            no_entity: this._message("validationNoEntity"),
          };
          if (statusEl) statusEl.textContent = messages[result.validation_error] || this._message("invalidInput");
        }
      } catch (err) {
        this._haptic("failure");
        if (statusEl) statusEl.textContent = this._message("errorPrefix") + (err && err.message ? err.message : String(err));
      }
    }

    async _saveTrigger() {
      const body = this.shadowRoot.querySelector(".body");
      const statusEl = body.querySelector("[data-save-status]");
      const triggers = [...((this._backendConfig && this._backendConfig.external_triggers) || [])];
      const editingId = this._editingTriggerId;
      const field = (key) => {
        const el = body.querySelector(`[data-trigger-field="${key}"]`);
        if (el) return el.value;
        const slot = body.querySelector(`[data-entity-picker="${key}"][data-picker-attr="data-trigger-field"]`);
        return slot ? slot.getAttribute("data-value") || "" : "";
      };
      const targetModeEl = body.querySelector("[data-trigger-target-mode]");
      const targetMode = targetModeEl ? targetModeEl.value : "entity";
      const trigger = {
        id: editingId || "",
        name: field("name").trim(),
        entity_id: targetMode === "entity" ? field("entity_id") : null,
        area_id: targetMode === "area" ? field("area_id") : null,
        action: field("action"),
      };
      const others = editingId ? triggers.filter((t) => t.id !== editingId) : triggers;
      await this._submitTriggers([...others, trigger], statusEl);
    }

    async _deleteTrigger(triggerId) {
      if (!window.confirm(this._message("confirmDeleteTrigger"))) return;
      const triggers = (
        (this._backendConfig && this._backendConfig.external_triggers) || []
      ).filter((t) => t.id !== triggerId);
      this._haptic("light");
      await this._submitTriggers(triggers, null);
    }

    async _loadManagedCovers() {
      if (!this._isAdmin() || this._savingManagedCovers || this._managedCoversSavePending || this._managedCoversSaveError || this._loadingManagedCovers) return;
      this._loadingManagedCovers = true;
      this._managedCovers = null;
      this._managedCoversError = null;
      this._managedCoversStatus = "";
      this._managedCoverNameChanges = {};
      try {
        this._managedCovers = await this._hass.callWS({
          type: "smart_shutter/get_available_covers",
          entry_id: this._backendConfig && this._backendConfig.entry_id,
        });
        this._managedCoverSelection = [...this._managedCovers.selected];
        this._managedCoverNames = { ...this._managedCovers.names };
        // Show HA user-defined names too; only edited names are sent back.
        for (const shutter of (this._model && this._model.shutters) || []) {
          if (shutter.userName) this._managedCoverNames[shutter.coverEntityId] = shutter.userName;
        }
      } catch (err) {
        this._managedCoversError = err && err.message ? err.message : String(err);
      } finally {
        this._loadingManagedCovers = false;
      }
      if (this._view === "settings-shutters") this._render();
    }

    _renderSettingsShutters() {
      const de = this._language() === "de";
      let html = `<button class="back" data-settings-back><ha-icon icon="mdi:arrow-left"></ha-icon> Back to Settings Menu</button>`;
      html += `<h2>${de ? "Rollläden verwalten" : "Manage shutters"}</h2>`;
      if (!this._isAdmin()) return html;
      if (this._managedCoversError) return html + `<div class="hint error">${this._escapeHtml(this._managedCoversError)}</div>`;
      if (!this._managedCovers) return html + `<p>${de ? "Rollläden werden geladen…" : "Loading shutters…"}</p>`;
      html += `<p class="meta">${de
        ? "Rollläden auswählen und Namen bearbeiten. Änderungen werden automatisch gespeichert. Ein leeres Namensfeld verwendet den Standardnamen."
        : "Select shutters and edit their names. Changes are saved automatically. An empty name field uses the default name."}</p>`;
      html += `<p class="hint">${de
        ? "Beim Entfernen werden die Smart-Shutter-Einstellungen dieses Rollladens gelöscht. Die ursprüngliche cover-Entität bleibt erhalten."
        : "Removing a shutter deletes its Smart Shutter settings. The original cover entity remains available."}</p>`;
      const selected = new Set(this._managedCoverSelection);
      for (const cover of this._managedCovers.covers || []) {
        const suffix = ` (${cover.entity_id})`;
        const sourceName = cover.name || cover.entity_id;
        const label = sourceName.endsWith(suffix) ? sourceName.slice(0, -suffix.length) : sourceName;
        const id = this._escapeHtml(cover.entity_id).replace(/"/g, "&quot;");
        const value = this._escapeHtml(this._managedCoverNames[cover.entity_id] || "").replace(/"/g, "&quot;");
        html += `<div class="managed-cover-row" data-managed-cover-row>
          <label class="control-row">
            <input type="checkbox" data-managed-cover="${id}" ${selected.has(cover.entity_id) ? "checked" : ""} />
            <span>${this._escapeHtml(label)}</span>
          </label>
          <div class="form-field">
            <label for="managed-name-${id}">Name</label>
            <input id="managed-name-${id}" type="text" data-managed-cover-name="${id}" value="${value}"
              placeholder="${this._escapeHtml(label).replace(/"/g, "&quot;")}" ${selected.has(cover.entity_id) ? "" : "disabled"} />
            <div class="meta">${id}</div>
          </div>
        </div>`;
      }
      if (!(this._managedCovers.covers || []).length) html += `<p>${de ? "Keine passenden Rollläden gefunden." : "No supported shutters found."}</p>`;
      html += `<span class="save-status" data-managed-covers-status role="status" aria-live="polite">${this._escapeHtml(this._managedCoversStatus || "")}</span>`;
      html += `<button data-retry-covers ${this._managedCoversSaveError ? "" : "hidden"}>${de ? "Erneut versuchen" : "Retry"}</button>`;
      return html;
    }

    _updateManagedCoverStatus() {
      const status = this.shadowRoot.querySelector("[data-managed-covers-status]");
      if (status) status.textContent = this._managedCoversStatus || "";
      const retry = this.shadowRoot.querySelector("[data-retry-covers]");
      if (retry) retry.hidden = !this._managedCoversSaveError;
    }

    _queueManagedCoverSave(delay) {
      clearTimeout(this._managedCoversSaveTimer);
      this._managedCoversSavePending = true;
      this._managedCoversSaveError = false;
      this._managedCoversStatus = this._language() === "de" ? "Änderungen werden gespeichert…" : "Changes will be saved…";
      this._updateManagedCoverStatus();
      this._managedCoversSaveTimer = setTimeout(() => {
        this._managedCoversSaveTimer = null;
        this._saveManagedCovers();
      }, delay);
    }

    async _saveManagedCovers() {
      if (!this._isAdmin() || this._savingManagedCovers || !this._managedCovers) return;
      clearTimeout(this._managedCoversSaveTimer);
      this._managedCoversSaveTimer = null;
      const selected = [...this._managedCoverSelection];
      const names = Object.fromEntries(Object.entries(this._managedCoverNameChanges).filter(([id]) => selected.includes(id)));
      const removed = this._managedCovers.selected.filter((id) => !selected.includes(id));
      const de = this._language() === "de";
      this._managedCoversSavePending = false;
      this._managedCoversSaveError = false;
      this._managedCoversStatus = de ? "Wird gespeichert…" : "Saving…";
      this._savingManagedCovers = true;
      this._updateManagedCoverStatus();
      try {
        await this._hass.callWS({ type: "smart_shutter/save_covers", entry_id: this._managedCovers.entry_id, covers: selected, names });
        this._managedCovers.selected = selected;
        for (const [id, name] of Object.entries(names)) {
          if (this._managedCoverNameChanges[id] === name) delete this._managedCoverNameChanges[id];
        }
        let refreshed = false;
        for (let attempt = 0; attempt < 30; attempt++) {
          await new Promise((resolve) => setTimeout(resolve, 200));
          // Refresh data without replacing name inputs, focus, or newer drafts.
          await this._loadRegistries(false);
          const backendIds = ((this._backendConfig && this._backendConfig.covers) || []).map((cover) => cover.entity_id);
          const modelIds = this._model ? this._model.shutters.map((shutter) => shutter.coverEntityId) : [];
          if (selected.every((id) => backendIds.includes(id) && modelIds.includes(id)) &&
              removed.every((id) => !backendIds.includes(id) && !modelIds.includes(id))) {
            refreshed = true;
            break;
          }
        }
        this._managedCoversStatus = refreshed
          ? (de ? "Automatisch gespeichert." : "Saved automatically.")
          : (de ? "Gespeichert. Die Integration lädt noch neu." : "Saved. The integration is still reloading.");
        this._haptic("success");
      } catch (err) {
        this._managedCoversStatus = this._message("errorPrefix") + (err && err.message ? err.message : String(err));
        this._managedCoversSaveError = true;
        this._haptic("failure");
      } finally {
        this._savingManagedCovers = false;
        if (this._managedCoversSavePending && !this._managedCoversSaveTimer) this._queueManagedCoverSave(0);
        else this._updateManagedCoverStatus();
        if (this.isConnected && ["overview", "list", "detail", "settings"].includes(this._view)) this._render();
      }
    }

    _renderSettingsGlobal() {
      let html = `<button class="back" data-settings-back><ha-icon icon="mdi:arrow-left"></ha-icon> Back to Settings Menu</button>`;
      const e = this._seasonEntities(this._model.globalEntities);
      html += `<h2>Global Entities</h2>`;
      html += this._renderSeasonPicker();
      html += `<h3>Automation (global, for all shutters)</h3>`;
      html += this._renderAutomationToggle(e.automation.open, "Öffnen");
      html += this._renderAutomationToggle(e.automation.close, "Schließen");

      html += `<h3>Global Times per Profile</h3>`;
      html += `<table><tr><th>Profile</th><th>Open</th><th>Close</th></tr>`;
      for (const pid of STATIC_PROFILE_ORDER) {
        const timeOpen = e.profileTime[pid] && e.profileTime[pid].open;
        const timeClose = e.profileTime[pid] && e.profileTime[pid].close;
        html += `<tr>
          <td>${STATIC_PROFILE_LABELS[pid]}</td>
          <td>${timeOpen ? `<input type="time" data-time-entity="${timeOpen.entity_id}" />` : "-"}</td>
          <td>${timeClose ? `<input type="time" data-time-entity="${timeClose.entity_id}" />` : "-"}</td>
        </tr>`;
      }
      html += `</table>`;

      html += `<h3>Global trigger type &amp; sun offset</h3>`;
      html += this._renderSelect(e.localType.open, "Typ Öffnen");
      html += this._renderNumberSlider(e.sunOffset.open, "Sonnenversatz Öffnen", " min");
      html += this._renderSelect(e.localType.close, "Typ Schließen");
      html += this._renderNumberSlider(e.sunOffset.close, "Sonnenversatz Schließen", " min");

      html += `<h3>Global Target Position</h3>`;
      html += this._renderNumberSlider(e.position.open, "Öffnen", "%");
      html += this._renderNumberSlider(e.position.close, "Schließen", "%");

      return html;
    }
  }

  customElements.define("smart-shutter-card", SmartShutterCard);

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "smart-shutter-card",
    name: "Smart Shutter Manager",
    description:
      "Übersicht und Steuerung aller Smart-Shutter-Manager-Rollläden, automatisch gruppiert nach Geschoss/Bereich.",
  });

  /**
   * SmartShutterPanel - thin wrapper around <smart-shutter-card>, which
   * Map displayed as a full-area sidebar entry (via
   * panel_custom, see __init__.py). Deliberately avoids using own
   * Display logic - all technical aspects remain in SmartShutterCard, so that
   * both usage types (normal dashboard card AND sidebar panel)
   * guarantees exactly the same behavior and is only located in one place
   * must be maintained.
   */
  class SmartShutterPanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
    }

    connectedCallback() {
      if (this._built) return;
      this._built = true;
      const panelTitle = String((this._pendingHass && this._pendingHass.language) || "en")
        .toLowerCase()
        .startsWith("de") ? "Rollläden" : "Shutters";

      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; height: 100%; background: var(--primary-background-color, #111); }
          .toolbar {
            display: flex; align-items: center; gap: 8px; padding: 8px 16px;
            background: var(--app-header-background-color, var(--primary-color));
            color: var(--app-header-text-color, #fff);
          }
          .toolbar h1 { font-size: 1.1em; margin: 0; font-weight: 500; }
          .menu-btn {
            display: none; width: 40px; height: 40px; border-radius: 8px; border: none;
            background: transparent; color: inherit; cursor: pointer; align-items: center;
            justify-content: center; flex-shrink: 0;
          }
          .menu-btn ha-icon { --mdc-icon-size: 24px; }
          @media (max-width: 870px) { .menu-btn { display: flex; } }
          .content { height: calc(100% - 48px); overflow: auto; padding: 8px; box-sizing: border-box; }
          /* In the panel, the full ha-card look (shadows/radius) appears out of place -
             in full screen mode, it should appear flat/seamless. */
          smart-shutter-card { --ha-card-box-shadow: none; --ha-card-border-radius: 0; }
        </style>
        <div class="toolbar">
          <button class="menu-btn" id="menu-btn" title="Menü">
            <ha-icon icon="mdi:menu"></ha-icon>
          </button>
          <h1 id="panel-title">${panelTitle}</h1>
        </div>
        <div class="content"><smart-shutter-card></smart-shutter-card></div>
      `;

      this._card = this.shadowRoot.querySelector("smart-shutter-card");
      this._card.setConfig({});

      const menuBtn = this.shadowRoot.querySelector("#menu-btn");
      menuBtn.addEventListener("click", () => {
        this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
      });

      if (this._pendingHass) this._card.hass = this._pendingHass;
    }

    set hass(hass) {
      this._pendingHass = hass;
      if (this._card) this._card.hass = hass;
      const title = this.shadowRoot.querySelector("#panel-title");
      if (title) {
        title.textContent = String((hass && hass.language) || "en").toLowerCase().startsWith("de")
          ? "Rollläden"
          : "Shutters";
      }
    }

    set narrow(narrow) {
      this._narrow = narrow;
    }

    set panel(panel) {
      this._panel = panel;
    }
  }

  customElements.define("smart-shutter-panel", SmartShutterPanel);
})();
