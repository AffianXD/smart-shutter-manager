# Changelog

## Unreleased: seasonal time profiles

- Add optional summer/winter schedules selected by daylight saving time in
  Home Assistant's timezone, globally and per shutter.
- Keep weekday/weekend/holiday times within each season, with separate trigger
  types, sun offsets, and global/individual sources. Preserve custom-profile
  priority and manual overrides.
- Copy existing settings on first activation and retain native entity IDs and
  seasonal edits across restarts and reactivation.
- Add independent season editors and an active-season indicator in the card.
  Resolve forecasts and execution across clock changes using absolute times;
  use calendar-day buckets in timelines.
- Cover native restoration, DST gaps/folds, individual inheritance, disabled
  behavior, and card interactions with simulated covers.

## Unreleased: v0.22.1

- Show date-based exceptions in collapsible settings and per-shutter Advanced
  lists. Keep up to ten most recently expired entries available to reactivate,
  restarting the original inclusive date range from today.
- Prune older expired entries at Home Assistant local midnight and while
  loading configuration, so the visible history stays in sync after rollover.

## Unreleased: v0.22.0

- Add admin-only "Manage shutters" to the Smart Shutter settings menu and
  integration options flow, with selection of existing supported covers.
- Add or remove shutters after setup while preserving retained names and
  settings. Keep temporarily missing managed covers selectable.
- Remove generated devices/entities, area memberships, notes, cover-specific
  triggers, and active pauses/overrides for removed shutters. Keep the original
  cover entities, global configuration, shared profiles, and area definitions.
- Reload through the existing config-entry listener and refresh the card after
  saving. Add backend and browser coverage for management and access control.

## Unreleased: v0.21.1

- Localize movement actions, triggers, default notification templates, frost
  messages, sun-rule messages, and early-warning buttons in German.
- Show German next-action sensor text for both individual and global previews;
  use an explicit date for actions later than tomorrow.
- Preserve custom templates, entity IDs, and language-neutral event/attribute
  values. Notification templates can use `action_raw` and `trigger_raw` when
  they need the original values for comparisons.
- Add backend regression coverage for German, English fallback, custom and
  invalid templates, notification buttons, and next-action attributes.

## Unreleased: v0.21.0

This is the first public repository release candidate. It packages the
existing Smart Shutter Manager integration and bundled dashboard card from
v0.20.2; it does not introduce new shutter-control features.

### Packaging and documentation

- Place the authoritative integration at `custom_components/smart_shutter/`
  and the test suite at `tests/` in the repository root. Remove duplicate
  integration and card-test copies from the handover bundle.
- Add HACS custom-repository metadata, an integration brand icon, MIT license,
  contributor and issue guidance, and GitHub validation workflows.
- Replace the installation guide with an English README. Reconstruct an
  English development history from the supplied version archives in
  [HISTORY.md](HISTORY.md). Local handover documents and source archives are
  excluded from the public repository.
- Document the bundled card URL and manual resource-registration fallback.

### Localization and identifiers

- Add complete English and German Home Assistant translations and bilingual
  dashboard-card text. English is the fallback for other UI languages.
- Use stable, language-neutral keys for select states and built-in profiles.
  Migrate saved configuration, restored select choices, and stored overrides
  from the old German identifiers while retaining existing entity IDs and
  unique IDs.
- Rename automation-visible option, service, override, and sensor-attribute
  fields to English. The former `quelle` service input and sun-notification
  template variables remain accepted as compatibility aliases in this release.
- Use English for default notification text, service descriptions, logs, and
  source documentation. Existing user-authored notification templates are
  preserved.

### Verification

- Rebuild the seven legacy Python tests with repository-relative paths and
  add Home Assistant fixture tests for setup, migration, permissions,
  schedules, notification routing, frost protection, and area-wide external
  triggers.
- Update the Chromium card suite for the bundled card and check English and
  German views, dynamic notices, and the renamed service payloads.
- Add CI jobs for Python, card, Hassfest, and HACS checks. Locally, 19 Python
  tests pass with Home Assistant 2026.3.0 and 2026.9.4; the Chromium card suite
  and syntax/static checks also pass. Public CI and installation smoke tests
  remain release gates before publishing v0.21.0.

### Breaking changes

Automations or templates that compare the former German select/profile states
or read renamed attributes must be updated. See the
[v0.21.0 migration guide](MIGRATION.md) for the complete field
mapping and compatibility notes.

## Historical releases through v0.20.2

See [HISTORY.md](HISTORY.md) for the English timeline reconstructed from the
supplied version archives. The source snapshots and original handover
documents remain local and are not part of this public repository.
