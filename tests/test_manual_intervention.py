"""Isolierter Test von manual_intervention.py - ohne echte Home-
Assistant-Installation."""
import sys
from pathlib import Path
import types
import importlib.util
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ha_stub  # noqa: F401

PKG_DIR = str(Path(__file__).resolve().parents[1] / "custom_components/smart_shutter")
PKG_NAME = "smart_shutter_manual_test"

pkg = types.ModuleType(PKG_NAME)
pkg.__path__ = [PKG_DIR]
sys.modules[PKG_NAME] = pkg


def _load_submodule(name):
    spec = importlib.util.spec_from_file_location(f"{PKG_NAME}.{name}", f"{PKG_DIR}/{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{PKG_NAME}.{name}"] = module
    spec.loader.exec_module(module)
    return module


event_helper_mod = types.ModuleType("homeassistant.helpers.event")


def async_track_state_change_event(hass, entity_ids, callback_fn):
    hass._state_change_callback = callback_fn
    return lambda: None


event_helper_mod.async_track_state_change_event = async_track_state_change_event
sys.modules["homeassistant.helpers.event"] = event_helper_mod
sys.modules["homeassistant.helpers"].__path__ = []

fake_coordinator_mod = types.ModuleType(f"{PKG_NAME}.coordinator")


class SmartShutterCoordinator:
    pass


fake_coordinator_mod.SmartShutterCoordinator = SmartShutterCoordinator
sys.modules[f"{PKG_NAME}.coordinator"] = fake_coordinator_mod

fake_storage_mod = types.ModuleType(f"{PKG_NAME}.storage")


class EventHistoryStore:
    def __init__(self, *a, **kw):
        self.events = []

    def add(self, *args):
        self.events.append(args)


class ManualPauseStore:
    def __init__(self):
        self.data = {}

    def get(self, entity_id):
        return self.data.get(entity_id)

    def set(self, entity_id, iso_dt):
        self.data[entity_id] = iso_dt

    def clear(self, entity_id):
        self.data.pop(entity_id, None)


fake_storage_mod.EventHistoryStore = EventHistoryStore
fake_storage_mod.ManualPauseStore = ManualPauseStore
sys.modules[f"{PKG_NAME}.storage"] = fake_storage_mod

manual_intervention = _load_submodule("manual_intervention")

failures = 0


def check(name, cond):
    global failures
    if not cond:
        failures += 1
    print(f"{'OK  ' if cond else 'FAIL'} - {name}")


class FakeState:
    def __init__(self, state, position=None):
        self.state = state
        self.attributes = {} if position is None else {"current_position": position}


class FakeEvent:
    def __init__(self, entity_id, old_state, new_state):
        self.data = {"entity_id": entity_id, "old_state": old_state, "new_state": new_state}


class FakeCoordinator:
    def __init__(self):
        self.shutters = {"cover.testroom": object()}
        self.manual_pause_minutes = 60


class FakeHass:
    def __init__(self):
        self.bus_events = []

        class FakeBus:
            def __init__(self, outer):
                self.outer = outer

            def async_fire(self, event_type, data):
                self.outer.bus_events.append((event_type, data))

        self.bus = FakeBus(self)


hass = FakeHass()
coordinator = FakeCoordinator()
history = EventHistoryStore()
pause_store = ManualPauseStore()

guard = manual_intervention.ManualInterventionGuard(hass, coordinator, pause_store, history)
guard.async_start()

# --- Szenario 1: Eigene Bewegung (mark_self_initiated) wird ignoriert ---
guard.mark_self_initiated("cover.testroom")
hass._state_change_callback(
    FakeEvent("cover.testroom", FakeState("closed", 0), FakeState("open", 100))
)
check("Eigene, markierte Bewegung loest KEINE Pause aus", not guard.is_paused("cover.testroom"))

# --- Szenario 2: Fremde Bewegung (kein mark_self_initiated) loest Pause aus ---
guard._self_initiated_until.clear()  # simuliert Ablauf der Gnadenfrist aus Szenario 1
hass._state_change_callback(
    FakeEvent("cover.testroom", FakeState("open", 100), FakeState("closed", 0))
)
check("Fremde Bewegung loest Pause aus", guard.is_paused("cover.testroom"))
check("Ereignis wurde im Verlauf protokolliert", len(history.events) == 1)
check("HA-Event wurde gefeuert", len(hass.bus_events) == 1 and hass.bus_events[0][0] == manual_intervention.EVENT_MANUAL_OVERRIDE)

# --- Szenario 3: Manuelles Aufheben funktioniert ---
guard.clear_pause("cover.testroom")
check("Pause laesst sich manuell aufheben", not guard.is_paused("cover.testroom"))

# --- Szenario 3b (Regressionstest): mehrere Positions-Ticks EINER
# durchgehenden Fahrt duerfen nur EINEN Log-/Event-Eintrag erzeugen,
# nicht einen pro Tick (Bugreport: 15+ identische Eintraege binnen
# einer Minute bei Shelly 2PM, das waehrend der Fahrt viele einzelne
# Positions-Updates meldet). ---
history.events.clear()
hass.bus_events.clear()
guard.clear_pause("cover.testroom")
positions = [0, 12, 25, 38, 51, 64, 77, 90, 100]
prev_state = FakeState("closed", positions[0])
for pos in positions[1:]:
    new_state = FakeState("open" if pos > 0 else "closed", pos)
    hass._state_change_callback(FakeEvent("cover.testroom", prev_state, new_state))
    prev_state = new_state
check(
    "Mehrere Positions-Ticks einer Fahrt -> genau EIN Verlaufseintrag (kein Spam)",
    len(history.events) == 1,
)
check(
    "Mehrere Positions-Ticks einer Fahrt -> genau EIN HA-Event",
    len(hass.bus_events) == 1,
)
check("Pause ist nach der letzten Bewegung weiterhin aktiv", guard.is_paused("cover.testroom"))
guard.clear_pause("cover.testroom")

# --- Szenario 4: Reines Attribut-Rauschen ohne echte Positionsaenderung loest NICHTS aus ---
hass._state_change_callback(
    FakeEvent("cover.testroom", FakeState("closed", 0), FakeState("closed", 0))
)
check("Reines Rauschen (keine echte Bewegung) loest keine Pause aus", not guard.is_paused("cover.testroom"))

# --- Szenario 5: Feature deaktiviert (0 Minuten) loest nichts aus ---
coordinator.manual_pause_minutes = 0
hass._state_change_callback(
    FakeEvent("cover.testroom", FakeState("open", 100), FakeState("closed", 0))
)
check("manual_pause_minutes=0 deaktiviert die Erkennung", not guard.is_paused("cover.testroom"))

print(f"\n{'ALLE TESTS OK' if failures == 0 else str(failures) + ' FEHLGESCHLAGEN'}")
sys.exit(0 if failures == 0 else 1)
