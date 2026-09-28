# Changelog

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
