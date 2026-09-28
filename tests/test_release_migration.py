"""Exercise migration of v0.20.2 options and persisted overrides."""

import ast
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "custom_components/smart_shutter"


def _isolated_definition(path: Path, name: str, context: dict):
    source = ast.parse(path.read_text(encoding="utf-8"))
    definition = next(node for node in source.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name)
    module = ast.Module(body=[definition], type_ignores=[])
    code = compile(ast.fix_missing_locations(module), str(path), "exec")
    exec(code, context)
    return context[name]


async def test_config_entry_migrates_holiday_weekdays_once() -> None:
    updates = []
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_update_entry=lambda entry, **kwargs: updates.append(kwargs)))
    entry = SimpleNamespace(version=1, options={"ferien_wochentage": ["1", "3"], "notify_service": "notify.owner"})
    migrate = _isolated_definition(PACKAGE / "__init__.py", "async_migrate_entry", {"CONF_HOLIDAY_WEEKDAYS": "holiday_weekdays"})
    assert await migrate(hass, entry) is True
    assert updates == [{"options": {"holiday_weekdays": ["1", "3"], "notify_service": "notify.owner"}, "version": 2}]


async def test_override_store_migrates_legacy_fields_without_losing_values() -> None:
    class FakeStore:
        def __init__(self, *args):
            self.saved = None

        async def async_load(self):
            return {"cover.kitchen": {"close": {"bis": "2026-09-27T20:00:00+02:00", "quelle": "guest"}}}

        def async_delay_save(self, callback, delay):
            self.saved = callback()

    context = {"Store": FakeStore, "STORAGE_VERSION": 1, "HomeAssistant": object}
    cls = _isolated_definition(PACKAGE / "storage.py", "ActionOverrideStore", context)
    store = cls(object(), "entry")
    await store.async_load()
    assert list(store.all_items()) == [("cover.kitchen", "close", "2026-09-27T20:00:00+02:00", "guest")]
    assert store._store.saved["cover.kitchen"]["close"] == {"until": "2026-09-27T20:00:00+02:00", "source": "guest"}


def test_old_profile_unique_ids_remain_registered() -> None:
    const = (PACKAGE / "const.py").read_text(encoding="utf-8")
    select = (PACKAGE / "select.py").read_text(encoding="utf-8")
    times = (PACKAGE / "time.py").read_text(encoding="utf-8")
    assert 'PROFILE_WEEKDAY: "werktag"' in const
    assert 'PROFILE_WEEKEND: "wochenende"' in const
    assert 'PROFILE_HOLIDAY: "ferien"' in const
    assert "LEGACY_PROFILE_IDS.get(profile, profile)" in select
    assert "LEGACY_PROFILE_IDS.get(profile, profile)" in times
