# Smart Shutter Manager

Smart Shutter Manager is a custom integration for Home Assistant that schedules
and controls existing `cover` entities. It includes a dashboard card, schedule
profiles, sun position rules, frost protection, notifications, and area based
settings. It does not replace the cover integration for your devices.

> **Release status:** v0.27.0 is being prepared. The inherited v0.20.2 code
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

When this repository is tracked and installed through HACS, HACS provides a
native update entity in Home Assistant and can install the update from there.
Restart Home Assistant after updating the integration. A manually copied
installation that is not tracked by HACS does not get this update entity.

### Manual install

Copy this repository's `custom_components/smart_shutter` directory to
`<HA config>/custom_components/smart_shutter`, then restart Home Assistant and
add the integration from **Settings → Devices & services**.

## First use

1. During integration setup, select the covers to manage.
2. Open **Shutters** in the Home Assistant sidebar. The first-run wizard lets
   you enter weekday, weekend, and holiday times in place, choose fixed times
   or sunrise/sunset triggers, and set target positions. The integration also
   provides `custom:smart-shutter-card` for a regular dashboard.
3. Optionally select a holiday entity and assign shutters to areas. Review the
   seven-day preview before choosing whether to enable opening and closing.
   **Both automations start disabled on a new setup.** Default times are
   07:00/21:30 on weekdays, 08:30/22:30 on weekends, and 09:00/22:00 on holidays.
4. Per-shutter settings, custom profiles, external triggers, and notifications
   remain available in the card's Settings. After setup, the guide stays
   available for reviewing the schedule and preview.

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

## Notifications

Set a global notification service in the card's basic settings, or leave it
empty and configure recipients only for selected areas or shutters. Each area
and each shutter's Basic tab offers **Inherit**, **Off**, and **Custom recipient**.
Custom recipients use a registered `notify.*` service, such as
`notify.mobile_app_phone`.

Individual shutter settings take priority over area settings, followed by the
global recipient. A shutter with its own recipient can still send notifications
when its area is Off. With multiple assigned areas, the first explicit area
setting in assignment order wins for movement, frost, and pre-close messages.
Sun rules use the triggering area's setting and group notifications by recipient;
names and counts include only that recipient's enabled shutters.

These settings apply to existing movement and frost messages, pre-close warnings,
and enabled sun rule messages. The configured warning lead time and the sun rule
notification toggles still apply. Existing area recipients continue to work.

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
settings. Administrators can add or remove managed shutters under **Smart Shutter
→ Settings → Manage shutters**, or through the integration's **Configure →
Manage shutters** dialog. Selected covers are managed; deselect a cover to stop
managing it. The card also lets you rename shutters in the same view. Selection
changes save automatically; name changes save after a short typing pause.
Removing a shutter requires confirmation. The card shows the save status and
offers a retry if saving fails. Changes reload the integration. Removing a
shutter deletes its
Smart Shutter device, generated entities, and cover-specific configuration;
the original cover entity remains available. Retained shutters keep their
settings, and temporarily missing shutters remain selectable. The standard
Home Assistant entities and service actions remain available for automations.
See the reconstructed [development history](HISTORY.md) for past releases.
The current service action names are `skip_action`,
`postpone_action`, `clear_override`, `clear_manual_pause`, and
`set_external_trigger` under the `smart_shutter` domain.

The card follows the Home Assistant UI language for English and German, with
English as the fallback. Home Assistant configuration flows and entity labels
also have English and German translations. Backend notification text and
next-action sensor text follow the configured Home Assistant language. Custom
notification templates are preserved; `action` and `trigger` are display text,
while `action_raw` and `trigger_raw` provide the original values for template
comparisons (`trigger_raw` is available for movement notifications).

### Summer and winter profiles

Enable **Switch automatically with daylight saving time** under the card's
**Settings → Basic Settings**, or in the integration's **Configure → Basic
Settings** dialog. This optional feature starts disabled. First activation copies
your existing times, trigger types, offsets, and global/individual choices into
both profiles.

In **Global Entities** and each shutter's settings, select **Summer time** or
**Winter time** to edit that profile. The active profile is shown separately;
editing the other profile does not activate it. Each season retains weekday,
weekend, and holiday times, plus opening/closing trigger types and sun offsets.
Individual time sources and trigger sources can differ between seasons.
Positions remain shared. Area presets apply to the currently active season.

The automatic choice uses the configured Home Assistant timezone: daylight
saving time selects summer, standard time selects winter. Timezones without
daylight saving time always use winter. No season sensor is required. Custom
profiles retain their priority and remain season-independent; manual pauses
and postponed/skipped actions still apply.

Future actions and previews use the season at their execution time, including
across a clock change. A missing local time during the spring change moves to
the first valid local minute. A repeated autumn time uses its first occurrence,
with at most one regular action of each kind per local day. Disabling the
feature restores the original settings; seasonal entities stay registered to
retain edits for later reactivation. Existing entity IDs are preserved, and
seasonal settings have additional native time/select/number entities.

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
tests remain pending before the v0.27.0 release.

Smart Shutter Manager is an independent community project and is not an
official Home Assistant integration.
