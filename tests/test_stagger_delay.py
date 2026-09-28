"""Isolierter Test von coordinator.stagger_delay_ms / stagger_index -
gestaffelte Befehlsausgabe (RF-Kollisionsschutz), siehe README Changelog
'Gestaffelte Befehlsausgabe'. Importiert das ECHTE coordinator.py (nicht
nur eine Fake-Nachbildung), um Tippfehler/falsche Bounds-Logik direkt im
Produktivcode zu fangen."""
import sys
from pathlib import Path
import types
import importlib.util

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ha_stub  # noqa: F401  (registriert die Stub-Module VOR dem Import unten)

PKG_DIR = str(Path(__file__).resolve().parents[1] / "custom_components/smart_shutter")
PKG_NAME = "smart_shutter_under_test_stagger"

# Zusaetzliche Stubs, die ha_stub.py (fuer scheduler.py-Tests gedacht)
# noch nicht mitbringt, aber coordinator.py fuers reine Importieren
# braucht (kein echtes __init__ wird hier aufgerufen).
config_entries_mod = types.ModuleType("homeassistant.config_entries")


class ConfigEntry:  # noqa: D101 - Minimal-Stub, nur fuer den Typ-Import
    pass


config_entries_mod.ConfigEntry = ConfigEntry
sys.modules["homeassistant.config_entries"] = config_entries_mod

storage_mod = types.ModuleType("homeassistant.helpers.storage")


class Store:  # noqa: D101
    def __init__(self, *a, **k):
        pass

    async def async_load(self):
        return None

    def async_delay_save(self, *a, **k):
        pass


storage_mod.Store = Store
sys.modules["homeassistant.helpers.storage"] = storage_mod

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
_load_submodule("helpers")
_load_submodule("storage")
coordinator = _load_submodule("coordinator")

failures = 0


def check(name, cond):
    global failures
    status = "OK  " if cond else "FAIL"
    if not cond:
        failures += 1
    print(f"{status} - {name}")


class FakeEntry:
    def __init__(self, options):
        self.options = options


class FakeShutter:
    def __init__(self, entity_id):
        self.entity_id = entity_id


class FakeSelf:
    """Minimal-Objekt mit nur den Attributen, die stagger_delay_ms/
    stagger_index tatsaechlich lesen (entry, shutters) - spart das
    vollstaendige, deutlich aufwendigere __init__ von
    SmartShutterCoordinator (Stores, Registry-Dicts, etc.)."""

    def __init__(self, options, shutter_ids):
        self.entry = FakeEntry(options)
        self.shutters = {eid: FakeShutter(eid) for eid in shutter_ids}


get_delay = coordinator.SmartShutterCoordinator.stagger_delay_ms.fget
stagger_index = coordinator.SmartShutterCoordinator.stagger_index

# --- stagger_delay_ms: Default, Bounds, ungueltige Werte ---
check("Kein Wert gesetzt -> Default 0 (aus)", get_delay(FakeSelf({}, [])) == 0)
check("Normaler Wert wird uebernommen", get_delay(FakeSelf({"stagger_delay_ms": 300}, [])) == 300)
check("Negativer Wert wird auf 0 begrenzt", get_delay(FakeSelf({"stagger_delay_ms": -50}, [])) == 0)
check(
    "Ungueltiger (nicht-numerischer) Wert faellt auf Default zurueck (kein Crash)",
    get_delay(FakeSelf({"stagger_delay_ms": "nicht-numerisch"}, [])) == 0,
)
check(
    "String-Zahl (z.B. aus dem Frontend) wird korrekt als int uebernommen",
    get_delay(FakeSelf({"stagger_delay_ms": "250"}, [])) == 250,
)

# --- stagger_index: stabile, alphabetische Reihenfolge ---
shutters = ["cover.wohnzimmer", "cover.buero", "cover.kueche", "cover.schlafzimmer"]
fake = FakeSelf({}, shutters)
expected_order = sorted(shutters)
indices = {eid: stagger_index(fake, eid) for eid in shutters}
check(
    "stagger_index liefert 0..n-1 in alphabetischer entity_id-Reihenfolge",
    [k for k, _ in sorted(indices.items(), key=lambda kv: kv[1])] == expected_order,
)
check("Erster Rollladen (alphabetisch) bekommt Index 0", indices[expected_order[0]] == 0)
check("Unbekannter Rollladen faellt auf Index 0 zurueck (kein Crash)", stagger_index(fake, "cover.unbekannt") == 0)

# --- Verzoegerungs-Berechnung (wie in executor._apply_stagger_delay) ---
delay_ms = 200
total_delay_for_4th = indices[expected_order[3]] * delay_ms
check(
    "Berechnete Verzoegerung fuer den 4. Rollladen (Index 3) bei 200ms Basis-Delay = 600ms",
    total_delay_for_4th == 600,
)
check(
    "Erster Rollladen (Index 0) bekommt KEINE Verzoegerung (0ms)",
    indices[expected_order[0]] * delay_ms == 0,
)

print(f"\n{'ALLE TESTS OK' if failures == 0 else str(failures) + ' FEHLGESCHLAGEN'}")
sys.exit(0 if failures == 0 else 1)
