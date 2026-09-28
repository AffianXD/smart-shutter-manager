"""Isolierter Test von sun_position.py (Azimuth-Range inkl. Wrap-around,
Edge-Trigger-Verhalten) - ohne echte Home-Assistant-Installation."""
import sys
from pathlib import Path
import types
import importlib.util

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ha_stub  # noqa: F401

PKG_DIR = str(Path(__file__).resolve().parents[1] / "custom_components/smart_shutter")
PKG_NAME = "smart_shutter_sun_test"

pkg = types.ModuleType(PKG_NAME)
pkg.__path__ = [PKG_DIR]
sys.modules[PKG_NAME] = pkg


def _load_submodule(name):
    spec = importlib.util.spec_from_file_location(f"{PKG_NAME}.{name}", f"{PKG_DIR}/{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{PKG_NAME}.{name}"] = module
    spec.loader.exec_module(module)
    return module


# --- weitere Stubs, die sun_position.py zusätzlich braucht ---
cover_mod = types.ModuleType("homeassistant.components.cover")


class CoverEntityFeature:
    SET_POSITION = 4


cover_mod.CoverEntityFeature = CoverEntityFeature
sys.modules["homeassistant.components.cover"] = cover_mod
sys.modules["homeassistant.components"] = types.ModuleType("homeassistant.components")
sys.modules["homeassistant.components"].__path__ = []

event_helper_mod = types.ModuleType("homeassistant.helpers.event")


def async_track_state_change_event(hass, entity_ids, callback_fn):
    return lambda: None


event_helper_mod.async_track_state_change_event = async_track_state_change_event
sys.modules["homeassistant.helpers.event"] = event_helper_mod
sys.modules["homeassistant.helpers"].__path__ = []

# coordinator/storage-Fakes (nur für Typannotationen gebraucht)
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


fake_storage_mod.EventHistoryStore = EventHistoryStore
sys.modules[f"{PKG_NAME}.storage"] = fake_storage_mod

sun_position = _load_submodule("sun_position")

failures = 0


def check(name, cond):
    global failures
    if not cond:
        failures += 1
    print(f"{'OK  ' if cond else 'FAIL'} - {name}")


# --- _azimuth_in_range ---
check("Normaler Bereich (90-180) trifft 135", sun_position._azimuth_in_range(135, 90, 180))
check("Normaler Bereich (90-180) verfehlt 200", not sun_position._azimuth_in_range(200, 90, 180))
check("Wrap-around (350-30) trifft 10", sun_position._azimuth_in_range(10, 350, 30))
check("Wrap-around (350-30) trifft 355", sun_position._azimuth_in_range(355, 350, 30))
check("Wrap-around (350-30) verfehlt 180", not sun_position._azimuth_in_range(180, 350, 30))

# --- Edge-Trigger-Verhalten via SunPositionMonitor ---
class FakeStates:
    def __init__(self):
        self.data = {}

    def get(self, entity_id):
        return self.data.get(entity_id)


class FakeState:
    def __init__(self, attributes):
        self.attributes = attributes


class FakeHass:
    def __init__(self):
        self.states = FakeStates()
        self.service_calls = []

        class FakeServices:
            def __init__(self, outer):
                self.outer = outer

            async def async_call(self, domain, service, data, blocking=False):
                self.outer.service_calls.append((domain, service, data))

        self.services = FakeServices(self)

    def async_create_task(self, coro):
        # Im echten HA wird das im Event-Loop eingeplant; hier reicht
        # es für den Test, die Coroutine synchron "anzustoßen" -
        # eigentliches Warten übernimmt der Test unten selbst.
        import asyncio

        try:
            asyncio.get_event_loop().run_until_complete(coro)
        except RuntimeError:
            asyncio.run(coro)


class FakeCoordinator:
    def __init__(self):
        self.custom_areas = []
        self.shutter_areas = {}
        self.shutters = {}
        self.notify_service = None

    def area_effective_temps(self, area):
        return None, None


hass = FakeHass()
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 10})
hass.states.data["cover.hinten1"] = FakeState({"supported_features": CoverEntityFeature.SET_POSITION})

coordinator = FakeCoordinator()
coordinator.custom_areas = [
    {
        "id": "area_hinten",
        "name": "Hinten",
        "sun_position_enabled": True,
        "sun_azimuth_from": 150,
        "sun_azimuth_to": 250,
        "sun_elevation_min": 15,
        "sun_position_target": 40,
    }
]
coordinator.shutter_areas = {"cover.hinten1": ["area_hinten"]}

history = EventHistoryStore()
monitor = sun_position.SunPositionMonitor(hass, coordinator, history)

# Elevation (10) < min (15) -> NICHT aktiv, kein Service-Call.
monitor._check_all_areas()
check("Elevation unter Schwelle -> kein Service-Call", len(hass.service_calls) == 0)

# Elevation steigt über die Schwelle UND Azimuth passt -> jetzt aktiv,
# GENAU EIN Service-Call (edge-triggered).
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 20})
monitor._check_all_areas()
check("Bedingung erfüllt -> genau ein Service-Call ausgelöst", len(hass.service_calls) == 1)
check(
    "Service-Call setzt korrekte Zielposition (40%)",
    hass.service_calls[0][2] == {"entity_id": "cover.hinten1", "position": 40},
)

# Bedingung bleibt erfüllt -> KEIN weiterer Service-Call (kein Dauerfeuern).
monitor._check_all_areas()
check("Bedingung bleibt erfüllt -> kein zusätzlicher Service-Call", len(hass.service_calls) == 1)

# Bedingung verlässt den Bereich und kommt zurück -> erneuter Trigger.
hass.states.data["sun.sun"] = FakeState({"azimuth": 0, "elevation": 20})
monitor._check_all_areas()
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 20})
monitor._check_all_areas()
check("Erneutes Eintreten in den Bereich löst erneut aus", len(hass.service_calls) == 2)

# ---------------------------------------------------------------
# Zusätzliche freie Bedingung (Jinja-Template): löst NUR aus, wenn
# Azimuth/Elevation UND die Zusatzbedingung erfüllt sind.
# ---------------------------------------------------------------
def fake_render_notify_template(hass_, template_str, variables, fallback):
    if "aussen_gt_innen" in template_str:
        return str(hass_.states.data.get("__aussen_gt_innen__", False))
    return fallback


sun_position.render_notify_template = fake_render_notify_template

coordinator.custom_areas[0]["sun_condition_template"] = "{{ aussen_gt_innen }}"
hass.states.data["__aussen_gt_innen__"] = False
hass.states.data["sun.sun"] = FakeState({"azimuth": 0, "elevation": 20})
monitor._check_all_areas()
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 20})
monitor._check_all_areas()
check("Zusatzbedingung=false verhindert Auslösen trotz passendem Sonnenstand", len(hass.service_calls) == 2)

hass.states.data["__aussen_gt_innen__"] = True
hass.states.data["sun.sun"] = FakeState({"azimuth": 0, "elevation": 20})
monitor._check_all_areas()
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 20})
monitor._check_all_areas()
check("Zusatzbedingung=true erlaubt Auslösen bei passendem Sonnenstand", len(hass.service_calls) == 3)

# ---------------------------------------------------------------
# Hysterese: verhindert wiederholtes Auslösen, wenn die Elevation nur
# knapp um die Schwelle pendelt.
# ---------------------------------------------------------------
coordinator.custom_areas[0]["sun_condition_template"] = None
coordinator.custom_areas[0]["sun_elevation_hysteresis"] = 5
monitor._area_triggered.clear()
calls_before = len(hass.service_calls)

# Elevation pendelt knapp UM die Schwelle (15), Hysterese-Puffer = 5:
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 20})
monitor._check_all_areas()  # tritt ein -> loest aus
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 16})
monitor._check_all_areas()  # knapp ueber der (ungepufferten) Schwelle -> bleibt "scharf", kein erneutes Ausloesen
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 12})
monitor._check_all_areas()  # unter 15, aber noch NICHT unter (15-5)=10 -> bleibt "scharf"
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 20})
monitor._check_all_areas()  # wieder ueber der Schwelle, aber weiterhin "scharf" -> KEIN erneutes Ausloesen
check(
    "Hysterese: Pendeln um die Schwelle loest NUR einmal aus",
    len(hass.service_calls) == calls_before + 1,
)

hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 9})
monitor._check_all_areas()  # jetzt unter (15-5)=10 -> wird "entschaerft"
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 20})
monitor._check_all_areas()  # erneuter Eintritt -> loest wieder aus
check(
    "Hysterese: nach ausreichendem Abstand unter der Schwelle loest erneuter Eintritt wieder aus",
    len(hass.service_calls) == calls_before + 2,
)

# ---------------------------------------------------------------
# Vorwarnung (Vorwarnung VOR dem eigentlichen Ausloesen, separat
# konfigurierbar/deaktivierbar je Bereich - Feature-Wunsch vom
# 2026-08-10). Nutzt die Aenderungsrate zwischen zwei Messungen, um
# die Zeit bis zum Erreichen der Mindest-Elevation zu schaetzen.
# ---------------------------------------------------------------
from datetime import timedelta  # noqa: E402
import homeassistant.util.dt as dt_util  # noqa: E402

coordinator.custom_areas[0]["sun_elevation_hysteresis"] = 0
coordinator.custom_areas[0]["sun_prenotify_enabled"] = True
coordinator.custom_areas[0]["sun_prenotify_lead_minutes"] = 5
coordinator.notify_service = "notify.mobile_app_test"
monitor._area_triggered.clear()
monitor._area_prenotified.clear()
monitor._area_last_elevation.clear()

# Deaktiviert (Default) -> auch bei passender Rate keine Vorwarnung.
coordinator.custom_areas[0]["sun_prenotify_enabled"] = False
monitor._area_last_elevation["area_hinten"] = (10.0, dt_util.now() - timedelta(minutes=2))
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 13})  # +1.5 Grad/min, ETA ca. 1.3 min
monitor._check_all_areas()
notify_calls_disabled = [c for c in hass.service_calls if c[0] == "notify"]
check("Vorwarnung deaktiviert (Default) -> keine Benachrichtigung trotz passender ETA", len(notify_calls_disabled) == 0)

# Aktiviert, ETA (~1.3 min) klar innerhalb Vorlaufzeit (5 min) -> Vorwarnung.
coordinator.custom_areas[0]["sun_prenotify_enabled"] = True
monitor._area_triggered.clear()
monitor._area_prenotified.clear()
monitor._area_last_elevation["area_hinten"] = (10.0, dt_util.now() - timedelta(minutes=2))
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 13})
monitor._check_all_areas()
notify_calls = [c for c in hass.service_calls if c[0] == "notify"]
check("Vorwarnung aktiviert, ETA innerhalb Vorlaufzeit -> genau eine Benachrichtigung", len(notify_calls) == 1)

# Erneute Pruefung bei (fast) unveraenderter Lage -> KEINE zweite
# Vorwarnung fuer denselben Anflug (Dedup ueber _area_prenotified).
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 13.2})
monitor._check_all_areas()
notify_calls_after_repeat = [c for c in hass.service_calls if c[0] == "notify"]
check("Vorwarnung feuert nur EINMAL pro Anflug (kein Spam)", len(notify_calls_after_repeat) == 1)

# Weit entfernte ETA (Elevation faellt bzw. Rate zu gering) -> keine
# Vorwarnung, noch zu frueh.
monitor._area_triggered.clear()
monitor._area_prenotified.clear()
monitor._area_last_elevation["area_hinten"] = (5.0, dt_util.now() - timedelta(minutes=10))
hass.states.data["sun.sun"] = FakeState({"azimuth": 200, "elevation": 5.5})  # 0.05 Grad/min, ETA riesig
monitor._check_all_areas()
notify_calls_far = [c for c in hass.service_calls if c[0] == "notify"]
check("Vorwarnung: ETA weit ausserhalb Vorlaufzeit -> (noch) keine weitere Benachrichtigung", len(notify_calls_far) == 1)

print(f"\n{'ALLE TESTS OK' if failures == 0 else str(failures) + ' FEHLGESCHLAGEN'}")
sys.exit(0 if failures == 0 else 1)
