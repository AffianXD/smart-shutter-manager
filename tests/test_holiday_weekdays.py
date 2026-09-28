"""Check that holiday profiles apply only on the configured weekdays."""
import sys
from pathlib import Path
import types
import importlib.util
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ha_stub  # noqa: F401 - register Home Assistant stubs before importing the package

PKG_DIR = str(Path(__file__).resolve().parents[1] / "custom_components/smart_shutter")
PKG_NAME = "smart_shutter_under_test_holiday"

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
const = sys.modules[f"{PKG_NAME}.const"]

failures = 0


def check(name, cond):
    global failures
    status = "OK  " if cond else "FAIL"
    if not cond:
        failures += 1
    print(f"{status} - {name}")


class FakeState:
    def __init__(self, state):
        self.state = state


class FakeStates:
    def __init__(self, values):
        self._values = values

    def get(self, entity_id):
        val = self._values.get(entity_id)
        return FakeState(val) if val is not None else None


class FakeHass:
    def __init__(self, holiday_state="on"):
        self.states = FakeStates({"binary_sensor.holiday": holiday_state})


class FakeCoordinator:
    def __init__(self, holiday_weekdays):
        self.custom_schedules = []
        self.holiday_entity_id = "binary_sensor.holiday"
        self.holiday_weekdays = holiday_weekdays


hass = FakeHass(holiday_state="on")

# Default configuration: Monday through Friday (0-4).
default_weekdays = {int(v) for v in const.DEFAULT_HOLIDAY_WEEKDAYS}
coordinator_default = FakeCoordinator(default_weekdays)

a_monday = date(2026, 8, 3)     # weekday()==0
a_saturday = date(2026, 8, 8)   # weekday()==5
a_sunday = date(2026, 8, 9)     # weekday()==6

check(
    "Default weekdays: holiday sensor on Monday selects holiday profile",
    scheduler.determine_active_profile(hass, coordinator_default, a_monday)
    == scheduler.PROFILE_HOLIDAY,
)
check(
    "Default weekdays: holiday sensor on Saturday retains weekend profile",
    scheduler.determine_active_profile(hass, coordinator_default, a_saturday)
    == scheduler.PROFILE_WEEKEND,
)
check(
    "Default weekdays: holiday sensor on Sunday retains weekend profile",
    scheduler.determine_active_profile(hass, coordinator_default, a_sunday)
    == scheduler.PROFILE_WEEKEND,
)

# Explicitly allow the holiday profile on all seven days.
coordinator_all_days = FakeCoordinator({0, 1, 2, 3, 4, 5, 6})
check(
    "All days configured: holiday sensor on Saturday selects holiday profile",
    scheduler.determine_active_profile(hass, coordinator_all_days, a_saturday)
    == scheduler.PROFILE_HOLIDAY,
)

# With the holiday sensor off, the normal weekday profile applies.
hass_off = FakeHass(holiday_state="off")
check(
    "Holiday sensor off on Monday selects weekday profile",
    scheduler.determine_active_profile(hass_off, coordinator_default, a_monday)
    == scheduler.PROFILE_WEEKDAY,
)

print()
print("ALL TESTS PASSED" if failures == 0 else f"{failures} TEST(S) FAILED")
sys.exit(1 if failures else 0)
