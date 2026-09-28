# Historical development

This history was reconstructed from the `manifest.json` version and README
inside the locally retained `old_versions/` snapshots. The snapshots are
research material and are not distributed in the public repository. Entries
describe what those archives report; their historical test counts have not
been rerun for each version. Some intermediate versions are mentioned by later
READMEs but have no separate snapshot in the available collection.

## v0.17–v0.20: areas, access, and reliability

- **0.20.2** — Added external triggers targeting an entire area. The archived
  README also documents area-specific notification recipients, manual controls
  respecting position limits, confirmation before applying area settings, and
  per-shutter notes. It says the 0.20.2 area-trigger changes were reconstructed
  after a workspace reset and did not pass the former full test suite.
- **0.19.4** — Corrected disabled states for the shutter-list group controls
  and the appearance of the area automation toggle.
- **0.19.2** — Made advanced shutter sections collapsible; the archived README
  also records collapsible area settings introduced around 0.19.1.
- **0.19.0–0.19.3** — Later archived READMEs describe private, area-bound
  schedules, guest edits to their own area's settings, and related access
  checks. Separate snapshots are present for 0.19.2 but not every patch
  version, so the individual changes cannot all be assigned more precisely.
- **0.18.7** — Corrected area quick-action styling and toggle spacing.
- **0.18.6** — Extended the card's visual design system to its other views,
  forms, and controls.
- **0.18.3** — Refined dashboard statistics, navigation, and panel width.
- **0.18.2** — Introduced a dashboard redesign preview with bordered cards,
  clearer typography, and theme-aware styling.
- **0.18.1** — Fixed a guest-access leak: the card had built its shutter list
  from the unfiltered Home Assistant registry and exposed global controls to
  restricted users despite server-side area filtering.
- **0.18.0** — Added area assignments for non-admin users and restricted card
  data and settings to assigned areas. Native Home Assistant entity/service
  permissions still govern actual shutter movement.
- **0.17.0** — The later handover describes temperature-based frost
  protection, area sensor overrides and automatic sensor detection, plus
  temperature variables for sun-position conditions. No separate 0.17.0
  snapshot was found in the supplied collection.

## v0.11–v0.16: custom areas and sun-position rules

- **0.16.2** — Fixed sun-position rules that stopped finding area members
  after the multiple-area change; added optional advance notification.
- **0.16.1** — Simplified the dashboard with group controls, an area shortcut,
  and collapsible postpone/skip actions.
- **0.16.0** — Allowed a shutter to belong to multiple custom areas, with
  backward-compatible conversion of older single-area assignments.
- **0.15.10** — Kept today's past appointments visible in the forecast.
- **0.15.8** — Added optional staggered commands for multiple shutters to
  reduce radio collisions.
- **0.15.7** — Removed the separate Basic/Advanced UI mode while keeping
  functional global/individual source controls.
- **0.15.5** — Added diagnostics for missing position-source entities; its
  archived README describes the underlying issue as unresolved at that point.
- **0.15.4** — Fixed a sun-offset-only area override that could leave a
  shutter without a scheduled action.
- **0.15.2** — Reduced duplicate manual-intervention history events during a
  continuous shutter movement.
- **0.15.1** — Replaced an unreliable embedded history card with Home
  Assistant's history API and corrected area application behavior.
- **0.15.0** — Reworked history and upcoming-action views.
- **0.14.4** — Made the weekdays on which a holiday profile applies
  configurable; Monday through Friday became the default.
- **0.14.1** — Added hysteresis to area sun-position rules.
- **0.14.0** — Added detection of manual shutter movement and a timed pause
  of that shutter's automation.
- **0.13.1** — Added an optional Jinja condition and notification to the
  sun-position rule.
- **0.13.0** — Added area sun-position rules using azimuth, elevation, and a
  target position, independently from the regular schedule.
- **0.12.0** — Added a per-user Basic/Advanced display mode, later removed
  in 0.15.7.
- **0.11.0** — Introduced custom areas as reusable presets applied to member
  shutters, without adding another scheduler resolution layer.

## v0.1–v0.10: initial scheduling and dashboard card

- **0.10.2** — Its archived README records fixes for catch-up after a second
  restart and for editing local positions. No separate 0.10.1 snapshot was
  found, though the README refers to that intermediate change.
- **0.10.0** — Fixed card interaction bugs and expanded bulk postpone/skip and
  per-shutter position controls.
- **0.9.1** — Suppressed advance warnings for shutters already at their target
  position and refined touch and quick-action behavior.
- **0.9.0** — Added WebSocket-backed card settings, and made next-action
  display respect automation switches.
- **0.8.0** — Bundled the dashboard card with the integration and added its
  automatic resource-registration attempt.
- **0.7.2** — Allowed templates in the external-trigger time field and
  tightened its input handling.
- **0.7.1** — Kept other shutters scheduled when one execution or catch-up
  check raises an error.
- **0.7.0** — Added named external triggers set by a service action.
- **0.6.2** — Split automation switches into independent open and close
  controls, globally and per shutter.
- **0.6.1** — Fixed next-action calculation across profile/day boundaries.
- **0.6.0** — Added profile-specific global/individual time sources and fixed
  missing notification imports.
- **0.5.0** — Unified postpone/skip overrides between scheduling and the
  next-action sensor; adjusted notification actions and global controls.
- **0.4.1** — Used actual position data when deciding whether a shutter was
  already at its target.
- **0.4.0** — Added execution history storage, restart catch-up, and advance
  close notifications with actions.
- **0.3.2** — Corrected UTC/local conversion for sunrise and sunset, and
  batched movement notifications.
- **0.3.1** — Limited open/close sun choices to sensible combinations and
  added global sun settings.
- **0.3.0** — Started executing real cover actions and added sunrise/sunset
  scheduling with offsets.
- **0.2.1** — Made next-action sensors update promptly after source or time
  changes.
- **0.2.0** — Added global and per-shutter time profiles, local overrides,
  holiday selection, and next-action display.
- **0.1.3** — Replaced a separate Select All control with preselected covers.
- **0.1.2** — Made Select All populate the actual cover selection.
- **0.1.1** — Inherited cover areas and cleaned duplicate words from names.
- **0.1.0** — Introduced integration setup, cover discovery, selection, and
  per-shutter automation switches.

The collection contains no independent snapshots for several intermediate
patch numbers. Their absence here does not establish that those versions were
never created or distributed.
