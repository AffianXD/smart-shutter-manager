"""Executed movements alone determine localized recipient-specific summaries."""
from unittest.mock import AsyncMock, Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.components.cover import CoverEntityFeature

from custom_components.smart_shutter.coordinator import ManagedShutter, SmartShutterCoordinator
from custom_components.smart_shutter.executor import NotificationBatcher, ShutterActionExecutor
from custom_components.smart_shutter.movement_summary import movement_summary


def setup(hass, **options):
    hass.config.language = "de"
    entry = MockConfigEntry(domain="smart_shutter", data={"covers": [], "names": {}}, options={
        "notify_service": "notify.owner",
        "custom_areas": [{"id": "east", "name": "Ost"}, {"id": "west", "name": "West"}],
        "shutter_areas": {"cover.a": ["east"], "cover.b": ["east"], "cover.c": ["west"], "cover.d": ["west"]},
        **options,
    })
    coordinator = SmartShutterCoordinator(hass, entry)
    coordinator.shutters = {f"cover.{key.lower()}": ManagedShutter(f"cover.{key.lower()}", key) for key in "ABCDE"}
    return coordinator


def moves(keys, action="closed", trigger="Schedule"):
    return [(key, action, trigger, f"cover.{key.lower()}") for key in keys]


@pytest.mark.parametrize("keys,subject,count", [
    ("ABCDE", "Alle Rollläden", 5),
    ("AB", "Rollläden im Bereich Ost", 2),
    ("A", "A", 1),
    ("ABCD", "Rollläden in den Bereichen Ost und West", 4),
    ("ABC", "Rollläden im Bereich Ost sowie C", 3),
    ("AC", "A, C", 2),
    ("ABBA", "Rollläden im Bereich Ost", 2),
])
def test_summary_uses_unique_instance_coverage(hass, keys, subject, count):
    assert movement_summary(hass, setup(hass), moves(keys)) == (subject, count)


def test_overlapping_complete_areas_and_stale_assignments(hass):
    coordinator = setup(hass, shutter_areas={"cover.a": ["east"], "cover.b": ["east", "west"], "cover.c": ["west"], "cover.deleted": ["east"]})
    assert movement_summary(hass, coordinator, moves("ABBC")) == ("Rollläden in den Bereichen Ost und West", 3)
    assert movement_summary(hass, coordinator, moves("AB")) == ("Rollläden im Bereich Ost", 2)
    assert movement_summary(hass, coordinator, moves("AC")) == ("A, C", 2)


def test_nested_complete_area_labels_and_legacy_string_assignments(hass):
    coordinator = setup(hass, custom_areas=[{"id": "whole", "name": "Etage"}, {"id": "part", "name": "Teil"}],
                        shutter_areas={"cover.a": ["whole", "part"], "cover.b": "whole"})
    assert movement_summary(hass, coordinator, moves("AB")) == ("Rollläden im Bereich Etage", 2)


def test_duplicate_display_names_still_count_distinct_entities(hass):
    coordinator = setup(hass)
    reports = [("Gleich", "closed", "Schedule", key) for key in ("cover.a", "cover.b")]
    assert movement_summary(hass, coordinator, reports) == ("Rollläden im Bereich Ost", 2)
    assert movement_summary(hass, coordinator, [("A", "closed", "Schedule"), ("B", "closed", "Schedule")]) == ("A, B", 2)


@pytest.mark.parametrize("action,phrase", [("closed", "fahren herunter"), ("opened", "fahren hoch")])
async def test_titles_and_default_body_use_command_execution(hass, action, phrase):
    batcher = NotificationBatcher(hass, setup(hass))
    batcher._call_notify = AsyncMock()
    await batcher._send_batch("notify.owner", moves("ABCDE", action), [])
    batcher._call_notify.assert_awaited_once_with("notify.owner", f"Alle Rollläden {phrase}", f"Alle Rollläden {phrase}. Auslöser: Zeitplan.")


@pytest.mark.parametrize("keys,title", [("AB", "Rollläden im Bereich Ost fahren herunter"), ("A", "A fährt herunter"), ("ABC", "Rollläden im Bereich Ost sowie C fahren herunter")])
async def test_area_and_single_titles(hass, keys, title):
    batcher = NotificationBatcher(hass, setup(hass))
    batcher._call_notify = AsyncMock()
    await batcher._send_batch("notify.owner", moves(keys), [])
    assert batcher._call_notify.call_args.args[1] == title


async def test_recipients_disabled_notifications_and_directions_remain_separate(hass):
    coordinator = setup(hass, shutter_notifications={
        "cover.b": {"notification_mode": "custom", "notify_service": "notify.guest"},
        "cover.e": {"notification_mode": "off"},
    })
    batcher = NotificationBatcher(hass, coordinator)
    batcher._call_notify = AsyncMock()
    for key in "ABCDE":
        entity_id = f"cover.{key.lower()}"
        batcher.report_movement(key, "opened" if key == "D" else "closed", "Schedule", coordinator.effective_notify_service(entity_id), entity_id=entity_id)
    batcher._flush_unsub()
    batcher._flush()
    await hass.async_block_till_done()
    calls = batcher._call_notify.await_args_list
    assert len(calls) == 3
    assert {(call.args[0], call.args[1]) for call in calls} == {
        ("notify.owner", "A, C fahren herunter"), ("notify.owner", "D fährt hoch"), ("notify.guest", "B fährt herunter"),
    }
    assert all("Alle" not in call.args[1] and "Bereich" not in call.args[1] for call in calls)


async def test_later_window_does_not_complete_an_earlier_partial_group(hass):
    batcher = NotificationBatcher(hass, setup(hass))
    batcher._call_notify = AsyncMock()
    for key in "AB":
        batcher.report_movement(key, "closed", "Schedule", "notify.owner", entity_id=f"cover.{key.lower()}")
        batcher._flush_unsub()
        batcher._flush()
        await hass.async_block_till_done()
    assert [call.args[1] for call in batcher._call_notify.await_args_list] == ["A fährt herunter", "B fährt herunter"]


def test_custom_template_names_counts_and_raw_values_remain_compatible(hass):
    coordinator = setup(hass, notify_text_moved="{{ names }}|{{ count }}|{{ action_raw }}|{{ trigger_raw }}|{{ action }}|{{ trigger }}")
    batcher = NotificationBatcher(hass, coordinator)
    assert batcher._format_moves(moves("ABBA")) == "A, B|2|closed|Schedule|geschlossen|Zeitplan"
    assert batcher._format_moves(moves("A") + moves("A", trigger="Sunset")) == "A|1|closed|Schedule|geschlossen|Zeitplan"


@pytest.mark.parametrize("language,old_default,expected", [
    ("de", "{{ names }} {{ 'was' if count == 1 else 'were' }} {{ action }}. Trigger: {{ trigger }}.", "A fährt herunter. Auslöser: Zeitplan."),
    ("en", "{{ names }} {{ 'wurde' if count == 1 else 'wurden' }} {{ action }}. Auslöser: {{ trigger }}.", "A is closing. Trigger: Schedule."),
])
def test_saved_historical_defaults_use_current_wording_without_storage_changes(hass, language, old_default, expected):
    coordinator = setup(hass, notify_text_moved=old_default)
    hass.config.language = language
    assert NotificationBatcher(hass, coordinator)._format_moves(moves("A")) == expected
    assert coordinator.entry.options["notify_text_moved"] == old_default


def executor(hass):
    coordinator = setup(hass)
    guard = Mock()
    guard.is_paused.return_value = False
    worker = ShutterActionExecutor(hass, coordinator, coordinator.shutters["cover.a"], Mock(), Mock(), Mock(), guard)
    worker._is_frost_active = Mock(return_value=False)
    worker._already_in_target_state = Mock(return_value=False)
    worker._target_position = Mock(return_value=0)
    worker._apply_stagger_delay = AsyncMock()
    return worker


async def test_failed_cover_service_does_not_report_a_movement(hass, monkeypatch):
    worker = executor(hass)
    call = AsyncMock(side_effect=RuntimeError("Command failed"))
    monkeypatch.setattr(type(hass.services), "async_call", call)
    with pytest.raises(RuntimeError, match="Command failed"):
        await worker._execute("close")
    worker._notifier.report_movement.assert_not_called()
    worker._last_executed_store.set.assert_not_called()
    assert call.call_args.kwargs["blocking"] is True


@pytest.mark.parametrize("scheduled_action,current_position,target,direction,phrase", [
    ("close", 0, 30, "opened", "A fährt hoch"),
    ("open", 80, 30, "closed", "A fährt herunter"),
    ("close", 80, 30, "closed", "A fährt herunter"),
    ("open", None, 30, "positioned", "A fährt zur Zielposition"),
    ("close", "unknown", 30, "positioned", "A fährt zur Zielposition"),
    ("close", float("nan"), 30, "positioned", "A fährt zur Zielposition"),
])
async def test_position_commands_report_actual_direction_and_keep_template_action(hass, monkeypatch, scheduled_action, current_position, target, direction, phrase):
    worker = executor(hass)
    worker._target_position = Mock(return_value=target)
    worker._trigger_label = Mock(return_value="Schedule")
    hass.states.async_set("cover.a", "open", {"supported_features": CoverEntityFeature.SET_POSITION, "current_position": current_position})
    call = AsyncMock()
    monkeypatch.setattr(type(hass.services), "async_call", call)
    await worker._execute(scheduled_action)
    call.assert_awaited_once_with("cover", "set_cover_position", {"entity_id": "cover.a", "position": target}, blocking=True)
    report = worker._notifier.report_movement.call_args
    assert report.args[1] == ("opened" if scheduled_action == "open" else "closed")
    assert report.kwargs["direction"] == direction
    batcher = NotificationBatcher(hass, worker._coordinator)
    batcher._call_notify = AsyncMock()
    batcher.report_movement(*report.args, **report.kwargs)
    batcher._flush_unsub()
    batcher._flush()
    await hass.async_block_till_done()
    assert batcher._call_notify.call_args.args[1] == phrase
    assert batcher._call_notify.call_args.args[2] == phrase + ". Auslöser: Zeitplan."


async def test_opposite_position_directions_from_one_schedule_action_stay_separate(hass):
    batcher = NotificationBatcher(hass, setup(hass, notify_text_moved="{{ names }}:{{ action_raw }}:{{ motion }}"))
    batcher._call_notify = AsyncMock()
    await batcher._send_batch("notify.owner", [
        ("A", "closed", "Schedule", "cover.a", "opened"),
        ("B", "closed", "Schedule", "cover.b", "closed"),
        ("C", "closed", "Schedule", "cover.c", "positioned"),
    ], [])
    assert [call.args[1:] for call in batcher._call_notify.await_args_list] == [
        ("A fährt hoch", "A:closed:fährt hoch"),
        ("B fährt herunter", "B:closed:fährt herunter"),
        ("C fährt zur Zielposition", "C:closed:fährt zur Zielposition"),
    ]


@pytest.mark.parametrize("reason", ["manual", "frost", "target"])
async def test_guards_changed_during_delay_do_not_report_movements(hass, reason, monkeypatch):
    worker = executor(hass)
    async def delay():
        if reason == "manual":
            worker._manual_intervention_guard.is_paused.return_value = True
        elif reason == "frost":
            worker._is_frost_active.return_value = True
        else:
            worker._already_in_target_state.return_value = True
    worker._apply_stagger_delay = delay
    call = AsyncMock()
    monkeypatch.setattr(type(hass.services), "async_call", call)
    await worker._execute("close")
    call.assert_not_called()
    worker._notifier.report_movement.assert_not_called()
