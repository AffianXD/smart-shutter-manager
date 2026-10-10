"""Language-aware display text; automation identifiers remain unchanged."""
from homeassistant.core import HomeAssistant

_GERMAN_TEXT = {
    "open": "öffnen", "close": "schließen",
    "opened": "geöffnet", "closed": "geschlossen",
    "Sunrise": "Sonnenaufgang", "Sunset": "Sonnenuntergang", "Schedule": "Zeitplan",
    "Today": "Heute", "Tomorrow": "Morgen",
    "Automation disabled": "Automatik deaktiviert", "Unknown": "Unbekannt",
    "was": "wurde", "were": "wurden", "Trigger": "Auslöser",
    "Skip today": "Heute überspringen", "Shutter closing soon": "Rollladen schließt bald",
}
_GERMAN_TEMPLATES = {
    "notify_text_moved": "{{ summary }} {{ motion }}. Auslöser: {{ trigger }}.",
    "notify_text_frost": "Frostschutz aktiv: {{ names }} {{ 'wird' if count == 1 else 'werden' }} nicht bewegt.",
    "notify_text_preclose": "{{ name }} schließt um {{ time }} Uhr.",
    "sun_notify_text": "Sonnenstandsregel '{{ area }}': {{ count }} {{ 'Rollladen' if count == 1 else 'Rollläden' }} auf {{ position }}% gefahren.",
    "sun_prenotify_text": "Sonnenstandsregel '{{ area }}': Rollläden fahren in etwa {{ minutes }} {{ 'Minute' if minutes == 1 else 'Minuten' }} auf {{ position }}%.",
}


def is_german(hass: HomeAssistant) -> bool:
    """Use the configured HA language, with English as the fallback."""
    return str(getattr(getattr(hass, "config", None), "language", "en")).lower().startswith("de")


def display_text(hass: HomeAssistant, text: str) -> str:
    """Translate known display values without rewriting user text."""
    return _GERMAN_TEXT.get(text, text) if is_german(hass) else text


def notification_template(hass: HomeAssistant, key: str, configured: str | None, english_default: str) -> str:
    """Localize built-in defaults, including previously saved default copies.

    User-authored templates are returned verbatim and never rewritten in storage.
    """
    german_default = _GERMAN_TEMPLATES[key]
    defaults = {english_default, german_default}
    if key == "notify_text_moved":
        defaults.update({
            "{{ names }} {{ 'was' if count == 1 else 'were' }} {{ action }}. Trigger: {{ trigger }}.",
            "{{ names }} {{ 'wurde' if count == 1 else 'wurden' }} {{ action }}. Auslöser: {{ trigger }}.",
        })
    if configured and configured not in defaults:
        return configured
    return german_default if is_german(hass) else english_default
