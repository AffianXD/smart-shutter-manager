"""Config Flow for Smart Shutter Manager.

Process (Version 0.1, see requirements document sections 4 + 17):
  1. Detect existing cover.* entities with the necessary features
  2. User selects the shutters to be managed
  3. Config Entry is created

Global scheduling, rules, etc. follow from version 0.2 as an options flow."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any
import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ACTION_CLOSE,
    ACTION_OPEN,
    CONF_CATCH_UP_WINDOW,
    CONF_COVERS,
    CONF_CUSTOM_SCHEDULES,
    CONF_EXTERNAL_TRIGGERS,
    CONF_FROST_ENTITY,
    CONF_OUTSIDE_TEMP_SENSOR,
    CONF_INSIDE_TEMP_SENSOR,
    CONF_FROST_THRESHOLD_C,
    DEFAULT_FROST_THRESHOLD_C,
    CONF_HOLIDAY_ENTITY,
    CONF_HOLIDAY_WEEKDAYS,
    DEFAULT_HOLIDAY_WEEKDAYS,
    CONF_STAGGER_DELAY_MS,
    DEFAULT_STAGGER_DELAY_MS,
    MAX_STAGGER_DELAY_MS,
    CONF_NAMES,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_TEXT_FROST,
    CONF_NOTIFY_TEXT_MOVED,
    CONF_NOTIFY_TEXT_PRECLOSE,
    CONF_NOTIFICATION_MAX_AGE,
    CONF_POSTPONE_OPTIONS,
    CONF_PRE_NOTIFY_LEAD,
    CUSTOM_SCHEDULE_ID_PREFIX,
    DATA_COORDINATOR,
    DEFAULT_CATCH_UP_WINDOW_MINUTES,
    DEFAULT_CUSTOM_SCHEDULE_INTERVAL_WEEKS,
    DEFAULT_NOTIFY_TEXT_FROST,
    DEFAULT_NOTIFY_TEXT_MOVED,
    DEFAULT_NOTIFY_TEXT_PRECLOSE,
    DEFAULT_NOTIFICATION_MAX_AGE_MINUTES,
    DEFAULT_POSTPONE_OPTIONS_MINUTES,
    DEFAULT_PRE_NOTIFY_LEAD_MINUTES,
    DOMAIN,
    EXTERNAL_TRIGGER_ID_PREFIX,
    SIGNAL_RECOMPUTE,
    WEEKDAY_KEYS,
)
from .coordinator import SmartShutterCoordinator
from .seasons import CONF_SEASONAL_ENABLED, prepare_seasonal_options
from .helpers import clean_base_name, get_area_name
from .scheduler import custom_schedule_matches, find_overlapping_rules
from .localization import notification_template
from .shutter_management import (
    available_covers,
    async_update_covers,
    discover_eligible_covers as _discover_eligible_covers,
)

CONF_COVER_SELECTION = "cover_selection"

_MENU_ADD_NEW = "__add_new__"
_MENU_DONE = "__done__"


class SmartShutterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow Handler."""

    VERSION = 2

    def __init__(self) -> None:
        self._eligible_covers: dict[str, str] = {}
        self._selected_covers: list[str] = []

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SmartShutterOptionsFlow:
        """Enables changing global settings later via Settings → Devices & Services → Smart Shutter → Configure."""
        return SmartShutterOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """First step: detect existing shutters and let the user select them."""
        errors: dict[str, str] = {}

        self._eligible_covers = _discover_eligible_covers(self.hass)

        if not self._eligible_covers:
            return self.async_abort(reason="no_covers_found")

        if user_input is not None:
            self._selected_covers = user_input.get(CONF_COVER_SELECTION, [])
            if not self._selected_covers:
                errors["base"] = "no_selection"
            else:
                return await self.async_step_names()

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_COVER_SELECTION,
                    # All found shutters are by default
                    # checked - the user only checks those that he
                    # does not want to be managed.
                    default=list(self._eligible_covers.keys()),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=eid, label=label)
                            for eid, label in self._eligible_covers.items()
                        ],
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_names(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Second step: optional individual naming per shutter."""
        if user_input is not None:
            names = {
                cover_entity_id: user_input.get(cover_entity_id, "").strip()
                for cover_entity_id in self._selected_covers
            }
            # Filter out empty inputs -> fallback name will be used later
            # determined by the Coordinator.
            names = {k: v for k, v in names.items() if v}

            return self.async_create_entry(
                title="Smart Shutter Manager",
                data={
                    CONF_COVERS: self._selected_covers,
                    CONF_NAMES: names,
                },
            )

        schema_dict: dict[Any, Any] = {}
        for cover_entity_id in self._selected_covers:
            schema_dict[
                vol.Optional(
                    cover_entity_id, default=self._suggest_name(cover_entity_id)
                )
            ] = str

        return self.async_show_form(
            step_id="names", data_schema=vol.Schema(schema_dict)
        )

    def _suggest_name(self, cover_entity_id: str) -> str:
        """Suggests an ad name: preferably the HA area (Area) of the cover, otherwise the cleaned Friendly Name (without "Shutter"/ "Cover" etc., so that no double "Shutter" is created later)."""
        area_name = get_area_name(self.hass, cover_entity_id)
        if area_name:
            return area_name

        friendly_label = self._eligible_covers.get(
            cover_entity_id, cover_entity_id
        ).split(" (")[0]
        return clean_base_name(friendly_label)


class SmartShutterOptionsFlow(config_entries.OptionsFlow):
    """Options that can be changed later (Version 0.2: holiday entity).

    Requirements document section 8: the integration does not need its own
    holiday logic, but reads the state of an externally selected entity by the
    user (binary_sensor/input_boolean/calendar - all three report "on" when
    holidays/an event is currently active).

    Additionally (on user request): frost protection entity (section 14), an
    optional notify service for notifications when actual movements are executed,
    as well as freely adjustable values for the early warning before closing
    (lead time + shift options) and the catch-up window after a HA restart."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        # Working copy of the custom profiles during the duration of this options flow.
        # Session - so the user can create multiple rules one after the other
        # edit/delete and it is only saved once (at the end),
        # would trigger a reload instead of on each individual change.
        self._pending_schedules: list[dict[str, Any]] | None = None
        self._editing_schedule_id: str | None = None
        self._pending_rule_to_insert: dict[str, Any] | None = None
        self._pending_overlap_names: list[str] | None = None
        # Analog copy for external triggers (v0.7)
        self._pending_triggers: list[dict[str, Any]] | None = None
        self._editing_trigger_id: str | None = None

    def _schedules(self) -> list[dict[str, Any]]:
        if self._pending_schedules is None:
            raw = self._config_entry.options.get(CONF_CUSTOM_SCHEDULES, [])
            self._pending_schedules = [dict(rule) for rule in raw]
        return self._pending_schedules

    def _triggers(self) -> list[dict[str, Any]]:
        if self._pending_triggers is None:
            raw = self._config_entry.options.get(CONF_EXTERNAL_TRIGGERS, [])
            self._pending_triggers = [dict(trigger) for trigger in raw]
        return self._pending_triggers

    def _choice_label(self, english: str, german: str) -> str:
        """Label dynamic selector options in the configured Home Assistant language."""
        return german if self.hass.config.language.lower().startswith("de") else english

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Entry point: Menu between basic settings and the
        management of custom profiles (v0.6)."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "basic_settings",
                "manage_shutters",
                "rename_shutters",
                "custom_schedules_menu",
                "external_triggers_menu",
                "finish",
            ],
        )

    async def async_step_manage_shutters(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add or remove managed covers without editing individual entities."""
        errors: dict[str, str] = {}
        if user_input is not None:
            options = dict(self._config_entry.options)
            if self._pending_schedules is not None:
                options[CONF_CUSTOM_SCHEDULES] = self._pending_schedules
            if self._pending_triggers is not None:
                options[CONF_EXTERNAL_TRIGGERS] = self._pending_triggers
            try:
                async_update_covers(self.hass, self._config_entry, user_input.get(CONF_COVER_SELECTION, []), options=options)
            except ValueError:
                errors["base"] = "invalid_selection"
            else:
                return self.async_create_entry(data=dict(self._config_entry.options))
        covers = available_covers(self.hass, self._config_entry)
        return self.async_show_form(
            step_id="manage_shutters",
            data_schema=vol.Schema({
                vol.Optional(CONF_COVER_SELECTION, default=list(self._config_entry.data.get(CONF_COVERS, []))): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[selector.SelectOptionDict(value=entity_id, label=label) for entity_id, label in covers.items()],
                        multiple=True, mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
            errors=errors,
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Saves (possibly modified) custom profiles and closes the flow, without displaying the base settings again."""
        data = dict(self._config_entry.options)
        if self._pending_schedules is not None:
            data[CONF_CUSTOM_SCHEDULES] = self._pending_schedules
        if self._pending_triggers is not None:
            data[CONF_EXTERNAL_TRIGGERS] = self._pending_triggers
        return self.async_create_entry(data=data)

    async def async_step_basic_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            # Take existing options as a base so that custom profiles
            # (and everything else) when saving the base settings
            # not accidentally lost.
            data = dict(self._config_entry.options)
            if self._pending_schedules is not None:
                data[CONF_CUSTOM_SCHEDULES] = self._pending_schedules
            if self._pending_triggers is not None:
                data[CONF_EXTERNAL_TRIGGERS] = self._pending_triggers

            data[CONF_SEASONAL_ENABLED] = user_input.get(CONF_SEASONAL_ENABLED, data.get(CONF_SEASONAL_ENABLED, False))
            coordinator = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id, {}).get(DATA_COORDINATOR)
            prepare_seasonal_options(coordinator, data)

            if user_input.get(CONF_HOLIDAY_ENTITY):
                data[CONF_HOLIDAY_ENTITY] = user_input[CONF_HOLIDAY_ENTITY]
            else:
                data.pop(CONF_HOLIDAY_ENTITY, None)
            if user_input.get(CONF_HOLIDAY_WEEKDAYS) is not None:
                data[CONF_HOLIDAY_WEEKDAYS] = user_input[CONF_HOLIDAY_WEEKDAYS]
            if user_input.get(CONF_STAGGER_DELAY_MS) is not None:
                data[CONF_STAGGER_DELAY_MS] = user_input[CONF_STAGGER_DELAY_MS]
            if user_input.get(CONF_FROST_ENTITY):
                data[CONF_FROST_ENTITY] = user_input[CONF_FROST_ENTITY]
            else:
                data.pop(CONF_FROST_ENTITY, None)
            if user_input.get(CONF_OUTSIDE_TEMP_SENSOR):
                data[CONF_OUTSIDE_TEMP_SENSOR] = user_input[CONF_OUTSIDE_TEMP_SENSOR]
            else:
                data.pop(CONF_OUTSIDE_TEMP_SENSOR, None)
            if user_input.get(CONF_INSIDE_TEMP_SENSOR):
                data[CONF_INSIDE_TEMP_SENSOR] = user_input[CONF_INSIDE_TEMP_SENSOR]
            else:
                data.pop(CONF_INSIDE_TEMP_SENSOR, None)
            if user_input.get(CONF_FROST_THRESHOLD_C) is not None:
                data[CONF_FROST_THRESHOLD_C] = user_input[CONF_FROST_THRESHOLD_C]
            notify_service = (user_input.get(CONF_NOTIFY_SERVICE) or "").strip()
            if notify_service:
                data[CONF_NOTIFY_SERVICE] = notify_service
            else:
                data.pop(CONF_NOTIFY_SERVICE, None)
            if user_input.get(CONF_PRE_NOTIFY_LEAD) is not None:
                data[CONF_PRE_NOTIFY_LEAD] = user_input[CONF_PRE_NOTIFY_LEAD]
            postpone_options = (user_input.get(CONF_POSTPONE_OPTIONS) or "").strip()
            if postpone_options:
                data[CONF_POSTPONE_OPTIONS] = postpone_options
            else:
                data.pop(CONF_POSTPONE_OPTIONS, None)
            if user_input.get(CONF_CATCH_UP_WINDOW) is not None:
                data[CONF_CATCH_UP_WINDOW] = user_input[CONF_CATCH_UP_WINDOW]
            if user_input.get(CONF_NOTIFICATION_MAX_AGE) is not None:
                data[CONF_NOTIFICATION_MAX_AGE] = user_input[CONF_NOTIFICATION_MAX_AGE]
            for key in (CONF_NOTIFY_TEXT_MOVED, CONF_NOTIFY_TEXT_FROST, CONF_NOTIFY_TEXT_PRECLOSE):
                value = (user_input.get(key) or "").strip()
                if value:
                    data[key] = value
                else:
                    data.pop(key, None)
            return self.async_create_entry(data=data)

        options = self._config_entry.options
        current_holiday = options.get(CONF_HOLIDAY_ENTITY)
        current_holiday_weekdays = options.get(
            CONF_HOLIDAY_WEEKDAYS, DEFAULT_HOLIDAY_WEEKDAYS
        )
        current_stagger_delay = options.get(CONF_STAGGER_DELAY_MS, DEFAULT_STAGGER_DELAY_MS)
        current_frost = options.get(CONF_FROST_ENTITY)
        current_outside_temp_sensor = options.get(CONF_OUTSIDE_TEMP_SENSOR)
        current_inside_temp_sensor = options.get(CONF_INSIDE_TEMP_SENSOR)
        current_frost_threshold = options.get(CONF_FROST_THRESHOLD_C, DEFAULT_FROST_THRESHOLD_C)
        current_notify = options.get(CONF_NOTIFY_SERVICE)
        current_lead = options.get(CONF_PRE_NOTIFY_LEAD, DEFAULT_PRE_NOTIFY_LEAD_MINUTES)
        current_postpone = options.get(
            CONF_POSTPONE_OPTIONS,
            ",".join(str(m) for m in DEFAULT_POSTPONE_OPTIONS_MINUTES),
        )
        current_catch_up = options.get(
            CONF_CATCH_UP_WINDOW, DEFAULT_CATCH_UP_WINDOW_MINUTES
        )
        current_notification_max_age = options.get(
            CONF_NOTIFICATION_MAX_AGE, DEFAULT_NOTIFICATION_MAX_AGE_MINUTES
        )
        current_text_moved = notification_template(
            self.hass, CONF_NOTIFY_TEXT_MOVED,
            options.get(CONF_NOTIFY_TEXT_MOVED), DEFAULT_NOTIFY_TEXT_MOVED,
        )
        current_text_frost = notification_template(
            self.hass, CONF_NOTIFY_TEXT_FROST,
            options.get(CONF_NOTIFY_TEXT_FROST), DEFAULT_NOTIFY_TEXT_FROST,
        )
        current_text_preclose = notification_template(
            self.hass, CONF_NOTIFY_TEXT_PRECLOSE,
            options.get(CONF_NOTIFY_TEXT_PRECLOSE), DEFAULT_NOTIFY_TEXT_PRECLOSE,
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_SEASONAL_ENABLED, default=options.get(CONF_SEASONAL_ENABLED, False)): selector.BooleanSelector(),
                vol.Optional(
                    CONF_HOLIDAY_ENTITY,
                    description={"suggested_value": current_holiday},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "input_boolean", "calendar"]
                    )
                ),
                vol.Optional(
                    CONF_HOLIDAY_WEEKDAYS,
                    description={"suggested_value": current_holiday_weekdays},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                        options=[str(day) for day in range(7)],
                        translation_key="weekday",
                    )
                ),
                vol.Optional(
                    CONF_STAGGER_DELAY_MS,
                    description={"suggested_value": current_stagger_delay},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=MAX_STAGGER_DELAY_MS, step=100, mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="ms",
                    )
                ),
                vol.Optional(
                    CONF_FROST_ENTITY,
                    description={"suggested_value": current_frost},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "input_boolean"]
                    )
                ),
                vol.Optional(
                    CONF_OUTSIDE_TEMP_SENSOR,
                    description={"suggested_value": current_outside_temp_sensor},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
                ),
                vol.Optional(
                    CONF_INSIDE_TEMP_SENSOR,
                    description={"suggested_value": current_inside_temp_sensor},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
                ),
                vol.Optional(
                    CONF_FROST_THRESHOLD_C,
                    description={"suggested_value": current_frost_threshold},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-20, max=15, step=0.5, mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C",
                    )
                ),
                vol.Optional(
                    CONF_NOTIFY_SERVICE,
                    description={"suggested_value": current_notify},
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_PRE_NOTIFY_LEAD,
                    description={"suggested_value": current_lead},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=60, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_POSTPONE_OPTIONS,
                    description={"suggested_value": current_postpone},
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_CATCH_UP_WINDOW,
                    description={"suggested_value": current_catch_up},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=720, step=5, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_NOTIFICATION_MAX_AGE,
                    description={"suggested_value": current_notification_max_age},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=120, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_NOTIFY_TEXT_MOVED,
                    description={"suggested_value": current_text_moved},
                ): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
                vol.Optional(
                    CONF_NOTIFY_TEXT_FROST,
                    description={"suggested_value": current_text_frost},
                ): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
                vol.Optional(
                    CONF_NOTIFY_TEXT_PRECLOSE,
                    description={"suggested_value": current_text_preclose},
                ): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
            }
        )

        return self.async_show_form(step_id="basic_settings", data_schema=schema)

    async def async_step_custom_schedules_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Overview of all Custom Profiles: select existing ones to edit, create a new one, or finish (back to main menu)."""
        if user_input is not None:
            choice = user_input["choice"]
            if choice == _MENU_DONE:
                return await self.async_step_init()
            if choice == _MENU_ADD_NEW:
                self._editing_schedule_id = None
                return await self.async_step_custom_schedule_edit()
            self._editing_schedule_id = choice
            return await self.async_step_custom_schedule_actions()

        schedules = self._schedules()
        options = [
            selector.SelectOptionDict(
                value=rule["id"], label=f"{i + 1}. {rule.get('name', rule['id'])}"
            )
            for i, rule in enumerate(schedules)
        ]
        options.append(
            selector.SelectOptionDict(value=_MENU_ADD_NEW, label=self._choice_label("+ Add custom profile", "+ Eigenes Profil anlegen"))
        )
        options.append(selector.SelectOptionDict(value=_MENU_DONE, label=self._choice_label("« Back", "« Zurück")))

        schema = vol.Schema(
            {
                vol.Required("choice", default=_MENU_DONE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, mode=selector.SelectSelectorMode.LIST
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="custom_schedules_menu", data_schema=schema
        )

    async def async_step_custom_schedule_actions(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Actions for an existing rule: Edit, change priority by dragging up/down (replacement for a Drag&Drop list within the Options-Flow-Form system), or Delete."""
        schedules = self._schedules()
        editing_id = self._editing_schedule_id
        idx = next((i for i, r in enumerate(schedules) if r["id"] == editing_id), None)
        if idx is None:
            return await self.async_step_custom_schedules_menu()

        if user_input is not None:
            action = user_input["action"]
            if action == "edit":
                return await self.async_step_custom_schedule_edit()
            if action == "move_up" and idx > 0:
                schedules[idx - 1], schedules[idx] = schedules[idx], schedules[idx - 1]
            elif action == "move_down" and idx < len(schedules) - 1:
                schedules[idx + 1], schedules[idx] = schedules[idx], schedules[idx + 1]
            elif action == "delete":
                schedules.pop(idx)
            return await self.async_step_custom_schedules_menu()

        rule = schedules[idx]
        options = ["edit", "move_up", "move_down", "delete", "back"]
        schema = vol.Schema(
            {
                vol.Required("action", default="edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, mode=selector.SelectSelectorMode.LIST,
                        translation_key="schedule_action",
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="custom_schedule_actions",
            data_schema=schema,
            description_placeholders={
                "name": rule.get("name", rule["id"]),
                "position": str(idx + 1),
                "total": str(len(schedules)),
            },
        )

    async def async_step_custom_schedule_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create, edit or delete a single custom profile."""
        schedules = self._schedules()
        editing_id = self._editing_schedule_id
        existing = next((r for r in schedules if r["id"] == editing_id), None)

        errors: dict[str, str] = {}

        if user_input is not None:
            if existing is not None and user_input.get("delete"):
                schedules[:] = [r for r in schedules if r["id"] != editing_id]
                return await self.async_step_custom_schedules_menu()

            weekday_labels = user_input.get("weekdays") or []
            weekdays = sorted(
                {WEEKDAY_KEYS.index(w) for w in weekday_labels if w in WEEKDAY_KEYS}
            )
            open_time = user_input.get("open_time") or None
            close_time = user_input.get("close_time") or None

            if not weekdays:
                errors["base"] = "custom_schedule_no_weekdays"
            elif not open_time and not close_time:
                errors["base"] = "custom_schedule_no_time"
            else:
                rule = {
                    "id": existing["id"] if existing else (
                        f"{CUSTOM_SCHEDULE_ID_PREFIX}{uuid.uuid4().hex[:8]}"
                    ),
                    "name": (user_input.get("name") or "").strip() or "Custom-Profil",
                    "weekdays": weekdays,
                    "interval_weeks": int(
                        user_input.get("interval_weeks")
                        or DEFAULT_CUSTOM_SCHEDULE_INTERVAL_WEEKS
                    ),
                    "reference_date": user_input.get("reference_date")
                    or date.today().isoformat(),
                    "end_date": user_input.get("end_date") or None,
                    "open_time": open_time,
                    "close_time": close_time,
                }

                other_rules = [r for r in schedules if r["id"] != rule["id"]]
                overlaps = find_overlapping_rules(rule, other_rules)
                if overlaps:
                    # First after confirmation by the user (next
                    # Step) is actually inserted into the list - so can
                    # they decide which rule wins in case of a conflict.
                    self._pending_rule_to_insert = rule
                    self._pending_overlap_names = [
                        r.get("name", r["id"]) for r in overlaps
                    ]
                    return await self.async_step_custom_schedule_conflict()

                if existing is not None:
                    schedules[:] = [
                        rule if r["id"] == editing_id else r for r in schedules
                    ]
                else:
                    schedules.append(rule)
                return await self.async_step_custom_schedules_menu()

        schema_dict: dict[Any, Any] = {
            vol.Optional(
                "name", description={"suggested_value": existing["name"] if existing else None}
            ): selector.TextSelector(),
            vol.Optional(
                "weekdays",
                description={
                    "suggested_value": [
                        WEEKDAY_KEYS[d] for d in existing["weekdays"]
                    ]
                    if existing
                    else []
                },
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=WEEKDAY_KEYS,
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                    translation_key="custom_weekday",
                )
            ),
            vol.Optional(
                "interval_weeks",
                description={
                    "suggested_value": existing.get(
                        "interval_weeks", DEFAULT_CUSTOM_SCHEDULE_INTERVAL_WEEKS
                    )
                    if existing
                    else DEFAULT_CUSTOM_SCHEDULE_INTERVAL_WEEKS
                },
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=52, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                "reference_date",
                description={
                    "suggested_value": existing.get("reference_date")
                    if existing
                    else date.today().isoformat()
                },
            ): selector.DateSelector(),
            vol.Optional(
                "end_date",
                description={"suggested_value": existing.get("end_date") if existing else None},
            ): selector.DateSelector(),
            vol.Optional(
                "open_time",
                description={"suggested_value": existing.get("open_time") if existing else None},
            ): selector.TimeSelector(),
            vol.Optional(
                "close_time",
                description={
                    "suggested_value": existing.get("close_time") if existing else None
                },
            ): selector.TimeSelector(),
        }
        if existing is not None:
            schema_dict[vol.Optional("delete", default=False)] = selector.BooleanSelector()

        return self.async_show_form(
            step_id="custom_schedule_edit",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={"name": existing["name"] if existing else "Neu"},
        )

    async def async_step_custom_schedule_conflict(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Displayed when the newly created/edited rule overlaps with at least one existing rule (same weekday, same interval pattern). The user decides who wins in this case - the final order can be fine-tuned at any time by shifting up or down in the list."""
        schedules = self._schedules()
        rule = self._pending_rule_to_insert
        overlap_names = self._pending_overlap_names or []

        if rule is None:
            return await self.async_step_custom_schedules_menu()

        if user_input is not None:
            choice = user_input["priority_choice"]
            # Previous version of the same rule (edit case)
            # remove first, then insert at the desired position.
            schedules[:] = [r for r in schedules if r["id"] != rule["id"]]
            if choice == "new_wins":
                schedules.insert(0, rule)
            else:
                schedules.append(rule)

            self._pending_rule_to_insert = None
            self._pending_overlap_names = None
            return await self.async_step_custom_schedules_menu()

        schema = vol.Schema(
            {
                vol.Required("priority_choice", default="existing_wins"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["new_wins", "existing_wins"],
                        mode=selector.SelectSelectorMode.LIST,
                        translation_key="schedule_priority",
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="custom_schedule_conflict",
            data_schema=schema,
            description_placeholders={
                "name": rule.get("name", rule["id"]),
                "conflicts": ", ".join(overlap_names),
            },
        )

    async def async_step_external_triggers_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Overview of all External Triggers: select existing ones to edit, create a new one, or go back to main menu. Unlike Custom Profiles, there is no priority list or overlap check here: an External Trigger technically ALWAYS takes precedence (same override mechanism as shifting/skipping), as long as its time has not yet been reached."""
        if user_input is not None:
            choice = user_input["choice"]
            if choice == _MENU_DONE:
                return await self.async_step_init()
            self._editing_trigger_id = None if choice == _MENU_ADD_NEW else choice
            return await self.async_step_external_trigger_edit()

        triggers = self._triggers()
        options = [
            selector.SelectOptionDict(
                value=trigger["id"],
                label=f"{trigger.get('name', trigger['id'])} ({trigger.get('entity_id', '?')})",
            )
            for trigger in triggers
        ]
        options.append(
            selector.SelectOptionDict(value=_MENU_ADD_NEW, label=self._choice_label("+ Add external trigger", "+ Externen Trigger anlegen"))
        )
        options.append(selector.SelectOptionDict(value=_MENU_DONE, label=self._choice_label("« Back", "« Zurück")))

        schema = vol.Schema(
            {
                vol.Required("choice", default=_MENU_DONE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, mode=selector.SelectSelectorMode.LIST
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="external_triggers_menu", data_schema=schema
        )

    def _clear_trigger_override(self, trigger: dict[str, Any]) -> None:
        """Deletes any still active override set via this external trigger (service smart_shutter.set_ external_trigger) - otherwise the last set time would remain, even though the trigger definition was removed and the service is no longer callable under this name."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
        if not entry_data:
            return  # Integration (still) not loaded - nothing to do
        coordinator: SmartShutterCoordinator = entry_data[DATA_COORDINATOR]
        coordinator.clear_action_override(trigger["entity_id"], trigger["action"])
        async_dispatcher_send(
            self.hass, f"{SIGNAL_RECOMPUTE}_{self._config_entry.entry_id}"
        )

    async def async_step_external_trigger_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create, edit, or delete a single External Trigger (Name + Shutter + Action)."""
        triggers = self._triggers()
        editing_id = self._editing_trigger_id
        existing = next((t for t in triggers if t["id"] == editing_id), None)

        errors: dict[str, str] = {}

        if user_input is not None:
            if existing is not None and user_input.get("delete"):
                triggers[:] = [t for t in triggers if t["id"] != editing_id]
                self._clear_trigger_override(existing)
                return await self.async_step_external_triggers_menu()

            name = (user_input.get("name") or "").strip()
            entity_id = user_input.get("entity_id")
            action = user_input.get("action")

            duplicate = any(
                t["id"] != editing_id and t.get("name") == name for t in triggers
            )

            if not name:
                errors["base"] = "external_trigger_no_name"
            elif duplicate:
                errors["base"] = "external_trigger_duplicate_name"
            elif not entity_id:
                errors["base"] = "external_trigger_no_entity"
            else:
                trigger = {
                    "id": existing["id"] if existing else (
                        f"{EXTERNAL_TRIGGER_ID_PREFIX}{uuid.uuid4().hex[:8]}"
                    ),
                    "name": name,
                    "entity_id": entity_id,
                    "action": action or ACTION_CLOSE,
                }
                if existing is not None:
                    triggers[:] = [
                        trigger if t["id"] == editing_id else t for t in triggers
                    ]
                else:
                    triggers.append(trigger)
                return await self.async_step_external_triggers_menu()

        schema_dict: dict[Any, Any] = {
            vol.Optional(
                "name", description={"suggested_value": existing["name"] if existing else None}
            ): selector.TextSelector(),
            vol.Optional(
                "entity_id",
                description={"suggested_value": existing.get("entity_id") if existing else None},
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="cover")),
            vol.Optional(
                "action",
                description={
                    "suggested_value": existing.get("action", ACTION_CLOSE)
                    if existing
                    else ACTION_CLOSE
                },
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[ACTION_OPEN, ACTION_CLOSE],
                    mode=selector.SelectSelectorMode.LIST,
                    translation_key="trigger_action",
                )
            ),
        }
        if existing is not None:
            schema_dict[vol.Optional("delete", default=False)] = selector.BooleanSelector()

        return self.async_show_form(
            step_id="external_trigger_edit",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={"name": existing["name"] if existing else "Neu"},
        )

    async def async_step_rename_shutters(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Allows renaming of already configured shutters after initial setup - previously only possible during initial setup.
        Useful e.g. if the original name suggestion was left as is and continued typing
        (leads to duplicate names like 'Zimmer Test Zimmer Test').

        Writes directly into entry.data (not entry.options), since the
        shutter names are stored there (see coordinator._load_from_entry)."""
        covers: list[str] = self._config_entry.data.get(CONF_COVERS, [])
        current_names: dict[str, str] = self._config_entry.data.get(CONF_NAMES, {})

        if user_input is not None:
            new_names = {
                cover_entity_id: (user_input.get(cover_entity_id) or "").strip()
                for cover_entity_id in covers
            }
            new_names = {k: v for k, v in new_names.items() if v}
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data={**self._config_entry.data, CONF_NAMES: new_names},
            )
            return await self.async_step_init()

        schema_dict: dict[Any, Any] = {}
        for cover_entity_id in covers:
            suggested = current_names.get(cover_entity_id, "")
            schema_dict[
                vol.Optional(
                    cover_entity_id, description={"suggested_value": suggested}
                )
            ] = selector.TextSelector()

        return self.async_show_form(
            step_id="rename_shutters", data_schema=vol.Schema(schema_dict)
        )
