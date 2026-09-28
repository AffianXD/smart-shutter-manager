"""Minimaler Stub für 'homeassistant', NUR um scheduler.py isoliert zu
importieren und resolve_next_datetime/compute_schedule direkt mit
Fake-Objekten zu testen - ohne eine volle Home-Assistant-Installation
im Sandbox-Container (kein Netzwerkzugriff für pip install verfügbar).
"""
import sys
import types
from datetime import datetime, timezone

# --- homeassistant.core ---
core_mod = types.ModuleType("homeassistant.core")


class HomeAssistant:
    pass


class Event:
    pass


def callback(func):
    return func


core_mod.HomeAssistant = HomeAssistant
core_mod.Event = Event
core_mod.callback = callback

# --- homeassistant.helpers.sun ---
helpers_mod = types.ModuleType("homeassistant.helpers")
sun_mod = types.ModuleType("homeassistant.helpers.sun")


def get_astral_event_next(hass, event, hass_only=None, offset=None):
    raise NotImplementedError("Sonnenereignisse werden in diesem Test nicht gebraucht")


sun_mod.get_astral_event_next = get_astral_event_next

# --- homeassistant.helpers.{area,device,entity}_registry + template ---
area_registry_mod = types.ModuleType("homeassistant.helpers.area_registry")
device_registry_mod = types.ModuleType("homeassistant.helpers.device_registry")
entity_registry_mod = types.ModuleType("homeassistant.helpers.entity_registry")
template_mod = types.ModuleType("homeassistant.helpers.template")


class Template:
    def __init__(self, template_str, hass=None):
        self.template_str = template_str

    def async_render(self, variables=None, parse_result=False):
        return self.template_str  # im generischen Stub unverändert zurückgeben


template_mod.Template = Template
helpers_mod.__path__ = []

# --- homeassistant.util.dt ---
util_mod = types.ModuleType("homeassistant.util")
dt_mod = types.ModuleType("homeassistant.util.dt")


def now():
    return datetime.now(timezone.utc).astimezone()


dt_mod.now = now
dt_mod.DEFAULT_TIME_ZONE = timezone.utc


def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


dt_mod.parse_datetime = parse_datetime

ha_mod = types.ModuleType("homeassistant")
ha_mod.__path__ = []  # macht 'homeassistant' zu einem (leeren) Package für Submodul-Importe

const_mod = types.ModuleType("homeassistant.const")


class Platform:
    SWITCH = "switch"
    SELECT = "select"
    TIME = "time"
    NUMBER = "number"
    SENSOR = "sensor"


const_mod.Platform = Platform

util_mod.__path__ = []

sys.modules["homeassistant"] = ha_mod
sys.modules["homeassistant.const"] = const_mod
sys.modules["homeassistant.core"] = core_mod
sys.modules["homeassistant.helpers"] = helpers_mod
sys.modules["homeassistant.helpers.sun"] = sun_mod
sys.modules["homeassistant.helpers.area_registry"] = area_registry_mod
sys.modules["homeassistant.helpers.device_registry"] = device_registry_mod
sys.modules["homeassistant.helpers.entity_registry"] = entity_registry_mod
sys.modules["homeassistant.helpers.template"] = template_mod
sys.modules["homeassistant.util"] = util_mod
sys.modules["homeassistant.util.dt"] = dt_mod
