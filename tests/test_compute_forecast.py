"""Isolierter Test von scheduler.compute_forecast() - Vorhersage-
Zeitstrahl fuer die native Zeitleiste (Zukunft-Teil, siehe README
Changelog 'Native Zeitleiste'). Prueft mehrtaegige Vorhersage inkl.
Wochenende/Werktag-Wechsel, aufsteigende Sortierung, keine Duplikate/
Endlosschleife."""
import sys
from pathlib import Path
import types
import importlib.util
from datetime import date, datetime, time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ha_stub  # noqa: F401  (registriert die Stub-Module VOR dem Import unten)

PKG_DIR = str(Path(__file__).resolve().parents[1] / "custom_components/smart_shutter")
PKG_NAME = "smart_shutter_under_test_forecast"

pkg = types.ModuleType(PKG_NAME)
pkg.__path__ = [PKG_DIR]
sys.modules[PKG_NAME] = pkg


def _load_submodule(name):
    spec = importlib.util.spec_from_file_location(f"{PKG_NAME}.{name}", f"{PKG_DIR}/{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{PKG_NAME}.{name}"] = module
    spec.loader.exec_module(module)
    return module


_load_submodule("const")

fake_coordinator = types.ModuleType(f"{PKG_NAME}.coordinator")


class ManagedShutter:
    pass


class SmartShutterCoordinator:
    pass


fake_coordinator.ManagedShutter = ManagedShutter
fake_coordinator.SmartShutterCoordinator = SmartShutterCoordinator
sys.modules[f"{PKG_NAME}.coordinator"] = fake_coordinator

scheduler = _load_submodule("scheduler")

failures = 0


def check(name, cond):
    global failures
    status = "OK  " if cond else "FAIL"
    if not cond:
        failures += 1
    print(f"{status} - {name}")


class FakeEntity:
    def __init__(self, source=None, action_type=None, native_value=None):
        self.source = source
        self.action_type = action_type
        self.native_value = native_value


class FakeShutter:
    entity_id = "cover.testroom"


class FakeCoordinator:
    def __init__(self):
        self.shutter_entities = {}
        self.global_entities = {}
        self._overrides = {}
        self._custom_schedules = []
        self.custom_schedules = self._custom_schedules
        self.holiday_entity_id = None
        self.shutter_areas = {}

    def get_action_override(self, cover_entity_id, action):
        return self._overrides.get(cover_entity_id, {}).get(action)

    def get_custom_schedule(self, rule_id):
        return next((r for r in self._custom_schedules if r["id"] == rule_id), None)


SOURCE_GLOBAL = "global"


def build_coordinator():
    shutter = FakeShutter()
    coordinator = FakeCoordinator()
    coordinator.global_entities["open_type"] = FakeEntity(action_type=scheduler.TYPE_TIME)
    coordinator.global_entities["open_weekday"] = FakeEntity(native_value=time(8, 0))
    coordinator.global_entities["open_weekend"] = FakeEntity(native_value=time(9, 0))
    coordinator.shutter_entities["cover.testroom"] = {
        "open_source": FakeEntity(source=SOURCE_GLOBAL),
        "open_weekday_time_source": FakeEntity(source=SOURCE_GLOBAL),
        "open_weekend_time_source": FakeEntity(source=SOURCE_GLOBAL),
    }
    return shutter, coordinator


a_monday = date(2026, 8, 3)
now = datetime.combine(a_monday, time(6, 0))

shutter, coordinator = build_coordinator()
forecast = scheduler.compute_forecast(None, coordinator, shutter, days=7, now=now)

check("7-Tage-Vorhersage liefert genau 7 Termine (1x 'open' pro Tag)", len(forecast) == 7)

by_weekday = {ts.strftime("%A"): (action, ts.time()) for action, ts in forecast}
check(
    "Werktag (Montag) nutzt globale Werktags-Zeit 08:00",
    by_weekday.get("Monday") == ("open", time(8, 0)),
)
check(
    "Wochenende (Samstag) nutzt globale Wochenende-Zeit 09:00",
    by_weekday.get("Saturday") == ("open", time(9, 0)),
)
check(
    "Wochenende (Sonntag) nutzt globale Wochenende-Zeit 09:00",
    by_weekday.get("Sunday") == ("open", time(9, 0)),
)

timestamps = [ts for _, ts in forecast]
check("Ergebnis ist aufsteigend sortiert", timestamps == sorted(timestamps))
check("Keine doppelten Zeitpunkte (Endlosschleifen-Schutz)", len(set(timestamps)) == len(timestamps))

# Automatik deaktiviert -> keine Termine fuer diese Aktion.
shutter2, coordinator2 = build_coordinator()
coordinator2.global_entities["global_automation_open"] = FakeEntity()
coordinator2.global_entities["global_automation_open"].is_on = False
forecast_disabled = scheduler.compute_forecast(None, coordinator2, shutter2, days=7, now=now)
check(
    "Deaktivierte globale Automatik -> compute_forecast liefert keine 'open'-Termine",
    all(action != "open" for action, _ in forecast_disabled),
)
forecast_disabled_preview = scheduler.compute_forecast(
    None, coordinator2, shutter2, days=7, now=now, include_disabled=True
)
check(
    "Setup-Vorschau zeigt den Zeitplan auch bei deaktivierter Automatik",
    len([action for action, _ in forecast_disabled_preview if action == "open"]) == 7,
)

# Regressionstest: heute bereits vergangene Termine duerfen NICHT aus
# der Vorhersage verschwinden (Bugreport - siehe README Changelog).
shutter3, coordinator3 = build_coordinator()
# "Jetzt" ist absichtlich NACH der Werktags-Oeffnen-Zeit (08:00) - ein
# alter Cursor-Start bei "now" statt Tagesbeginn wuerde das heutige
# 08:00-Ereignis komplett verschlucken.
now_after_open = datetime.combine(a_monday, time(10, 0))
forecast_today = scheduler.compute_forecast(None, coordinator3, shutter3, days=7, now=now_after_open)
todays_open_events = [ts for action, ts in forecast_today if action == "open" and ts.date() == a_monday]
check(
    "Heute bereits vergangenes Ereignis (08:00, 'jetzt' ist 10:00) bleibt in der Vorhersage sichtbar",
    len(todays_open_events) == 1 and todays_open_events[0].time() == time(8, 0),
)

print(f"\n{'ALLE TESTS OK' if failures == 0 else str(failures) + ' FEHLGESCHLAGEN'}")
sys.exit(0 if failures == 0 else 1)
