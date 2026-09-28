"""Isolierter Test von scheduler.py: reproduziert exakt Bug 5
('Nächste anstehende Aktion aktualisiert sich nicht bei individueller
Uhrzeit') mit Fake-Objekten, ohne echte Home-Assistant-Installation."""
import sys
from pathlib import Path
import types
import importlib.util
from datetime import date, datetime, time, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ha_stub  # noqa: F401  (registriert die Stub-Module VOR dem Import unten)

PKG_DIR = str(Path(__file__).resolve().parents[1] / "custom_components/smart_shutter")
PKG_NAME = "smart_shutter_under_test"

# Fake-Package OHNE das echte __init__.py auszuführen (das importiert
# panel_custom/http/etc., die hier nicht gestubbt sind) - nur damit die
# relativen Importe ('from .const import ...') in scheduler.py/const.py
# auflösbar sind.
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
        self.shutter_areas = {}
        # Kein Ferien-/Frost-Sonderfall für diesen Test noetig.
        self.holiday_entity_id = None

    def get_action_override(self, cover_entity_id, action):
        return self._overrides.get(cover_entity_id, {}).get(action)

    def get_custom_schedule(self, rule_id):
        return next((r for r in self._custom_schedules if r["id"] == rule_id), None)


shutter = FakeShutter()
coordinator = FakeCoordinator()

# Trigger-Typ global fest auf 'Uhrzeit' (open_type), damit ausschliesslich
# resolve_fixed_time getestet wird (kein Sonnenstand involviert).
coordinator.global_entities["open_type"] = FakeEntity(action_type=scheduler.TYPE_TIME)

SOURCE_GLOBAL = "global"  # entspricht const.SOURCE_GLOBAL, hier nicht importiert

# Globale Werktags-Zeit: 08:00.
coordinator.global_entities["open_weekday"] = FakeEntity(native_value=time(8, 0))

# Lokale (individuelle) Werktags-Zeit fuer DIESEN Rollladen: 10:00,
# aber die Quelle ('open_werktag_time_source') steht noch auf Global -
# das ist der Ausgangszustand, den ein Nutzer typischerweise hat.
coordinator.shutter_entities["cover.testroom"] = {
    "open_source": FakeEntity(source=SOURCE_GLOBAL),
    "open_weekday_time_source": FakeEntity(source=SOURCE_GLOBAL),
    "open_weekday": FakeEntity(native_value=time(10, 0)),
}

# Ein Montag (Werktag), damit determine_active_profile "werktag" liefert.
a_monday = date(2026, 8, 3)
now = datetime.combine(a_monday, time(6, 0))

# --- Schritt 1: Quelle noch 'Global' -> globale 08:00 muss gewinnen ---
result_before = scheduler.resolve_next_datetime(
    None, coordinator, shutter, scheduler.ACTION_OPEN, "weekday", now
)
check(
    "Vor Umstellung: globale Werktags-Zeit (08:00) wird verwendet",
    result_before is not None and result_before.time() == time(8, 0),
)

# --- Schritt 2: Nutzer stellt 'open_werktag_time_source' auf Individuell ---
coordinator.shutter_entities["cover.testroom"]["open_weekday_time_source"].source = scheduler.SOURCE_LOCAL

result_after = scheduler.resolve_next_datetime(
    None, coordinator, shutter, scheduler.ACTION_OPEN, "weekday", now
)
check(
    "BUG 5 REPRO: nach Umstellung auf Individuell wird die LOKALE Zeit (10:00) verwendet",
    result_after is not None and result_after.time() == time(10, 0),
)

# --- Schritt 3: compute_schedule (das, was der Sensor tatsaechlich aufruft) ---
schedule = scheduler.compute_schedule(None, coordinator, shutter, now=now)
check(
    "compute_schedule liefert ebenfalls die individuelle Zeit (10:00)",
    schedule.next_open is not None and schedule.next_open.time() == time(10, 0),
)

print(f"\n{'ALLE TESTS OK' if failures == 0 else str(failures) + ' FEHLGESCHLAGEN'}")

# ---------------------------------------------------------------
coordinator2 = FakeCoordinator()
coordinator2.global_entities["close_type"] = FakeEntity(action_type=scheduler.TYPE_TIME)
coordinator2.global_entities["close_weekday"] = FakeEntity(native_value=time(20, 0))
coordinator2.shutter_entities["cover.testroom"] = {
    "close_source": FakeEntity(source=SOURCE_GLOBAL),
    # Quelle steht auf Individuell, aber es wurde NIE eine eigene
    # Uhrzeit eingetragen (RestoreEntity-Default = None):
    "close_weekday_time_source": FakeEntity(source=scheduler.SOURCE_LOCAL),
    "close_weekday": FakeEntity(native_value=None),
}
result_broken_state = scheduler.resolve_next_datetime(
    None, coordinator2, shutter, scheduler.ACTION_CLOSE, "weekday", now
)
check(
    "KRITISCH: Individuell-Quelle ohne gesetzten Wert faellt auf Global zurueck (kein kompletter Ausfall)",
    result_broken_state is not None and result_broken_state.time() == time(20, 0),
)

print(f"\n{'ALLE TESTS OK' if failures == 0 else str(failures) + ' FEHLGESCHLAGEN'}")
sys.exit(0 if failures == 0 else 1)
