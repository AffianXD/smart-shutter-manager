# Smart Shutter Manager

Smart Shutter Manager is a custom integration for Home Assistant that schedules
and controls existing `cover` entities. It includes a dashboard card, schedule
profiles, sun position rules, frost protection, notifications, and area based
settings. It does not replace the cover integration for your devices.

> **Release status:** v0.21.0 is being prepared. The inherited v0.20.2 code
> was reconstructed after a workspace reset; its former full test suite was
> lost. Check the test and release status before installing this branch.

## Requirements

- Home Assistant 2026.3.0 or newer (the intended minimum; compatibility is a
  release gate).
- Existing `cover` entities that support **open, close, and stop**. Covers
  without all three capabilities do not appear in the setup selection.
- A backup of your Home Assistant configuration before upgrading from v0.20.x.

## Install

### HACS custom repository

1. In HACS, open the menu and select **Custom repositories**.
2. Add `https://github.com/AffianXD/smart-shutter-manager` as an **Integration**.
3. Install Smart Shutter Manager and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration** and select
   **Smart Shutter Manager**.

This repository is planned for HACS custom repository use. It is not yet listed
in the HACS default catalog.

### Manual install

Copy this repository's `custom_components/smart_shutter` directory to
`<HA config>/custom_components/smart_shutter`, then restart Home Assistant and
add the integration from **Settings → Devices & services**.

## First use

1. During integration setup, select the covers to manage.
2. Open **Shutters** in the Home Assistant sidebar. The integration also
   provides `custom:smart-shutter-card` for a regular dashboard.
3. Review the global weekday, weekend, and holiday times before relying on
   automation. **Open and close automation switches start enabled.** The
   initial times are 07:00/21:30 on weekdays, 08:30/22:30 on weekends, and
   09:00/22:00 on holidays. Turn off the global open/close switches while
   configuring if these times are unsuitable.
4. Adjust per-shutter settings, areas, and notifications in the card. Check
   the next-action preview before leaving automation enabled.

The integration serves its bundled card at
`/smart_shutter_frontend/smart-shutter-card.js` and tries to register it as a
dashboard resource automatically. If the card is unavailable, open Home
Assistant's **Settings → Dashboards → Resources**, add that URL as a
**JavaScript module**, then add a manual dashboard card with:

```yaml
type: custom:smart-shutter-card
```

YAML-managed dashboards also need this resource registered manually. Restart
Home Assistant after installing or replacing the integration.

## What it does

- Schedule opening and closing by weekday, weekend, holiday, or custom profile.
- Use fixed times or sunrise and sunset with offsets.
- Override settings per shutter or area and preview upcoming actions.
- Pause automation after manual movement; apply frost and position limits.
- Set external trigger times from automations and route notifications per area.
- Give a non-admin user access to an assigned area in the bundled card.

Area access controls the integration's card and WebSocket data. Actual shutter
movement uses Home Assistant's native `cover.*` services. Configure Home
Assistant user and entity permissions separately before giving guests access.

## Configure and use

Open the bundled card to edit schedules, areas, triggers, and per-shutter
settings. The standard
Home Assistant entities and service actions remain available for automations.
See the reconstructed [development history](HISTORY.md) for past releases.
The current service action names are `skip_action`,
`postpone_action`, `clear_override`, `clear_manual_pause`, and
`set_external_trigger` under the `smart_shutter` domain.

The card follows the Home Assistant UI language for English and German, with
English as the fallback. Home Assistant configuration flows and entity labels
also have English and German translations.

## Upgrading from v0.20.x

Read the [v0.21.0 migration guide](MIGRATION.md) before upgrading.
Select option states and several data fields now use language neutral keys.
Saved choices and configuration are migrated, but automations that compare old
German states or attributes need updating.

## Development and support

See [CONTRIBUTING.md](CONTRIBUTING.md) for local checks and
[CHANGELOG.md](CHANGELOG.md) for release notes. Report a reproducible issue
through the [issue tracker](https://github.com/AffianXD/smart-shutter-manager/issues).
Local regression checks have passed, while public CI and installation smoke
tests remain pending before the v0.21.0 release.

Smart Shutter Manager is an independent community project and is not an
official Home Assistant integration.
