<img src="assets/icon.svg" alt="Smart Shutter Manager icon" width="80" height="80">

# Smart Shutter Manager

Smart Shutter Manager is a custom Home Assistant integration for scheduling
and managing your existing `cover` entities. Set shared routines, adjust
individual shutters, and preview upcoming movements from one dashboard
without building a separate automation for every shutter.

## Features

- **Flexible schedules:** weekday, weekend, and holiday times, recurring custom
  profiles, opening at sunrise and closing at sunset with offsets, and optional
  summer/winter profiles that switch with daylight saving time.
- **Individual and area settings:** override shared times and target positions,
  group shutters into areas, and apply area presets.
- **Everyday adjustments:** skip or postpone the next action, pause after
  detected manual movement, or set date-based pauses and alternate times.
- **Sun and frost rules:** set area-specific positions based on the sun's
  azimuth and elevation; block scheduled movements when frost is detected.
- **Notifications:** movement and frost messages, configurable pre-close
  warnings, and recipients per shutter or area.
- **Built-in interface:** sidebar panel, dashboard card, guided setup, and a
  seven-day preview, with English and German translations.

## Installation

### Requirements

- Home Assistant **2026.3.0 or newer**, as declared in the HACS metadata.
- Existing `cover` entities that support **open, close, and stop**. Smart Shutter
  Manager uses your existing device integrations.
- For sun-position rules: the Home Assistant Sun integration (`sun.sun`).
  Partial target positions and sun-position rules also need cover position control.

### Install with HACS

With [HACS](https://github.com/hacs/integration) installed:

1. Open **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/AffianXD/smart-shutter-manager` with type
   **Integration**.
3. Find **Smart Shutter Manager** in HACS and download it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**, select
   **Smart Shutter Manager**, and choose the covers to manage.

The dashboard card is included. Restart Home Assistant after HACS updates.

<details>
<summary>Manual installation</summary>

Copy `custom_components/smart_shutter` from this repository into
`<HA config>/custom_components/smart_shutter`. Restart Home Assistant, then add
**Smart Shutter Manager** under **Settings → Devices & services**.

</details>

## Getting started

1. Open **Shutters** in the Home Assistant sidebar.
2. Follow the setup guide to choose fixed times or sunrise/sunset triggers,
   adjust target positions, and optionally configure a holiday entity and areas.
3. Review the **seven-day preview**, then choose whether to enable opening,
   closing, or both and finish setup. **Both global automation switches start
   disabled on a new installation.**

For example, open at **07:00 on weekdays** and **08:30 on weekends**, then close
at **sunset**. Override a bedroom's opening time in its individual settings, or
postpone its next closing from the dashboard.

Use the dashboard to control shutters and adjust their settings. Administrators
can add, remove, or rename shutters under **Settings → Manage shutters**; removal
clears their Smart Shutter configuration while preserving the original covers.
Configure notification recipients and other optional rules in **Settings**.

### Use the card on another dashboard

Add a manual card with:

```yaml
type: custom:smart-shutter-card
```

The integration attempts to register its JavaScript resource automatically for
dashboards managed through the UI.

<details>
<summary>If the card does not load, or you use YAML dashboards</summary>

Under **Settings → Dashboards → Resources** (available in advanced mode), add
`/smart_shutter_frontend/smart-shutter-card.js` as a **JavaScript module**.

For YAML-managed resources, add this entry to your dashboard resource list:

```yaml
- url: /smart_shutter_frontend/smart-shutter-card.js
  type: module
```

The integration serves this file directly; do not copy it into `config/www`.
Refresh your browser after updates; clear its cache if the old card persists.

</details>

<details>
<summary>Area access for non-admin users</summary>

Area assignments restrict the card and its WebSocket data. Actual cover control
uses Home Assistant's native services and permissions, which must be configured
separately.

</details>

## Documentation and support

- [Changelog](CHANGELOG.md) — release notes and feature details.
- [Migration guide](MIGRATION.md) — read before upgrading from v0.20.x; back up
  Home Assistant and update automations using the old states or attributes.
- [Service actions](custom_components/smart_shutter/services.yaml) — fields for
  skipping, postponing, clearing overrides/pauses, and setting external triggers.
- [Development history](HISTORY.md) — earlier versions.
- [Issue tracker](https://github.com/AffianXD/smart-shutter-manager/issues) —
  include your Home Assistant and integration versions and reproduction steps.

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for
Python/JavaScript checks and release rules, and the
[local Home Assistant guide](docs/local-home-assistant.md) for Docker development
with virtual shutters.

## License

[MIT](LICENSE). Smart Shutter Manager is an independent community project.
