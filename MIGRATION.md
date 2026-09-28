# Upgrade from v0.20.x to v0.21.0

Back up Home Assistant before upgrading and restart it after replacing the
integration. v0.21.0 changes several automation-visible identifiers to enable
English and German labels over stable underlying values.

| Before | v0.21.0 | Action |
| --- | --- | --- |
| Select states `Global`, `Individuell` | `global`, `local` | Update state comparisons and `select.select_option` calls. Restored choices migrate automatically. |
| Select states `Uhrzeit`, `Sonnenaufgang`, `Sonnenuntergang` | `time`, `sunrise`, `sunset` | Update state comparisons and select action calls. |
| Built-in profile keys `werktag`, `wochenende`, `ferien` | `weekday`, `weekend`, `holiday` | Update templates comparing active profiles. Existing entity IDs and unique IDs are retained. |
| Option `ferien_wochentage` | `holiday_weekdays` | The config entry migrates automatically. |
| Service field `quelle` | `source` | Change service action calls; `quelle` remains accepted as an alias for this release. |
| Override storage fields `bis`, `quelle` | `until`, `source` | Existing stored overrides migrate automatically. |
| Next action attributes `aktion`, `zeitpunkt`, `profil` | `action`, `scheduled_at`, `profile` | Update templates using these attributes. |
| Next action attributes `naechstes_oeffnen`, `naechstes_schliessen` | `next_open`, `next_close` | Update templates using these attributes. |
| Override attributes `override_aktiv`, `override_bis`, `override_quelle` | `override_active`, `override_until`, `override_source` | Update templates using these attributes. |
| Pause attributes `manuelle_pause_aktiv`, `manuelle_pause_bis` | `manual_pause_active`, `manual_pause_until` | Update templates using these attributes. |
| Sun notification template variables `bereich`, `minuten` | `area`, `minutes` | New templates use the English names. Existing saved templates keep working through compatibility aliases. |

Default notification wording is now English. Saved custom notification templates
are preserved without rewriting their text.
The integration's device display name now uses "Shutter" and its global device
model uses "Global settings". Registered entity IDs and unique IDs are kept.

Check automations and dashboards for comparisons against old German labels.
The bundled card uses the new identifiers. Guest access still depends on Home
Assistant permissions for the underlying `cover` entities.
