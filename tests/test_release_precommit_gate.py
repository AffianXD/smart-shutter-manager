"""Tests for searchable subjects and explicit historical backfill mode."""

import json

from scripts.check_version_changelog import (
    _backfill_versions_from_subjects,
    validate_backfill_changelog,
)
from scripts.pre_commit_gate import _validate_subject


BASE_MANIFEST = json.dumps({"version": "0.23.0"})
BASE_CHANGELOG = "# Changelog\n\n## v0.23.0\n\n- Existing release.\n"
BACKFILLED_CHANGELOG = (
    BASE_CHANGELOG + "\n## v0.22.0\n\n- Backfill details.\n"
)


def _assert_raises(message: str, check) -> None:
    try:
        check()
    except ValueError as error:
        assert message in str(error)
    else:
        raise AssertionError(f"Expected ValueError containing {message!r}")


def test_backfill_accepts_explicit_historical_version_without_manifest_downgrade() -> None:
    assert validate_backfill_changelog(
        version="0.22.0",
        base_manifest=BASE_MANIFEST,
        base_changelog=BASE_CHANGELOG,
        head_manifest=BASE_MANIFEST,
        head_changelog=BACKFILLED_CHANGELOG,
        changed_paths={"CHANGELOG.md"},
    ) is None


def test_backfill_rejects_an_unrelated_manifest_change() -> None:
    _assert_raises(
        "must leave the current manifest version unchanged",
        lambda: validate_backfill_changelog(
            version="0.22.0",
            base_manifest=BASE_MANIFEST,
            base_changelog=BASE_CHANGELOG,
            head_manifest=json.dumps({"version": "0.24.0"}),
            head_changelog=BACKFILLED_CHANGELOG,
            changed_paths={"CHANGELOG.md", "custom_components/smart_shutter/manifest.json"},
        ),
    )


def test_backfill_rejects_a_manifest_downgrade() -> None:
    _assert_raises(
        "must leave the current manifest version unchanged",
        lambda: validate_backfill_changelog(
            version="0.22.0",
            base_manifest=BASE_MANIFEST,
            base_changelog=BASE_CHANGELOG,
            head_manifest=json.dumps({"version": "0.22.0"}),
            head_changelog=BACKFILLED_CHANGELOG,
            changed_paths={"CHANGELOG.md"},
        ),
    )


def test_backfill_requires_a_changed_nonempty_release_entry() -> None:
    _assert_raises(
        "must be added or updated",
        lambda: validate_backfill_changelog(
            version="0.22.0",
            base_manifest=BASE_MANIFEST,
            base_changelog=BACKFILLED_CHANGELOG,
            head_manifest=BASE_MANIFEST,
            head_changelog=BACKFILLED_CHANGELOG,
            changed_paths={"CHANGELOG.md"},
        ),
    )
    _assert_raises(
        "at least one change bullet",
        lambda: validate_backfill_changelog(
            version="0.22.0",
            base_manifest=BASE_MANIFEST,
            base_changelog="# Changelog\n",
            head_manifest=BASE_MANIFEST,
            head_changelog="# Changelog\n\n## v0.22.0\n\n",
            changed_paths={"CHANGELOG.md"},
        ),
    )


def test_backfill_cannot_hide_a_shipped_package_change() -> None:
    _assert_raises(
        "no other release-relevant files",
        lambda: validate_backfill_changelog(
            version="0.22.0",
            base_manifest=BASE_MANIFEST,
            base_changelog=BASE_CHANGELOG,
            head_manifest=BASE_MANIFEST,
            head_changelog=BACKFILLED_CHANGELOG,
            changed_paths={
                "CHANGELOG.md",
                "custom_components/smart_shutter/config_flow.py",
            },
        ),
    )


def test_commit_subject_requires_clear_conventional_format() -> None:
    assert _validate_subject("feat(card): add shutter management panel", None) == []
    assert _validate_subject("update", None)
    assert _validate_subject("feat: update", None)


def test_backfill_commit_subject_names_the_historical_release() -> None:
    assert _validate_subject(
        "chore(release): backfill v0.22.0 changelog notes", "0.22.0"
    ) == []
    assert _validate_subject("docs: add historical release notes", "0.22.0")
    assert _validate_subject(
        "chore(release): backfill v0.22.0 changelog notes", None
    )


def test_ci_recognizes_only_explicit_backfill_commit_subjects() -> None:
    versions = _backfill_versions_from_subjects(
        [
            "chore(release): backfill v0.22.0 changelog notes",
            "docs: explain backfill v0.21.1 history",
            "feat: add schedule option",
        ]
    )

    assert versions == {"0.22.0"}
