"""Tests for the version and changelog push policy."""

import pytest

from scripts.check_version_changelog import validate_version_changelog


def _manifest(version: str) -> str:
    return f'{{"version": "{version}"}}'


def _changelog(*versions: str) -> str:
    return "\n\n".join(f"## v{version}\n\n- Change" for version in versions)


def test_accepts_higher_version_with_matching_changelog_section() -> None:
    assert (
        validate_version_changelog(
            _manifest("0.22.0"),
            _manifest("0.23.0"),
            _changelog("0.22.0"),
            _changelog("0.23.0", "0.22.0"),
        )
        == "0.23.0"
    )


@pytest.mark.parametrize("current", ["0.22.0", "0.21.9"])
def test_rejects_unchanged_or_lower_version(current: str) -> None:
    with pytest.raises(ValueError, match="must increase"):
        validate_version_changelog(
            _manifest("0.22.0"),
            _manifest(current),
            _changelog("0.22.0"),
            _changelog(current),
        )


@pytest.mark.parametrize("current", ["v0.23.0", "0.23", "0.23.0-beta", "01.2.3"])
def test_rejects_invalid_semantic_version(current: str) -> None:
    with pytest.raises(ValueError, match="stable X.Y.Z"):
        validate_version_changelog(
            _manifest("0.22.0"),
            _manifest(current),
            _changelog("0.22.0"),
            _changelog(current),
        )


def test_rejects_missing_changelog_section() -> None:
    with pytest.raises(ValueError, match="found 0"):
        validate_version_changelog(
            _manifest("0.22.0"),
            _manifest("0.23.0"),
            _changelog("0.22.0"),
            _changelog("0.22.0"),
        )


def test_rejects_duplicate_changelog_section() -> None:
    with pytest.raises(ValueError, match="found 2"):
        validate_version_changelog(
            _manifest("0.22.0"),
            _manifest("0.23.0"),
            _changelog("0.22.0"),
            _changelog("0.23.0", "0.23.0"),
        )


def test_rejects_changelog_section_below_another_version() -> None:
    with pytest.raises(ValueError, match="at the top"):
        validate_version_changelog(
            _manifest("0.22.0"),
            _manifest("0.23.0"),
            _changelog("0.22.0"),
            _changelog("0.22.0", "0.23.0"),
        )


def test_rejects_empty_changelog_section() -> None:
    with pytest.raises(ValueError, match="must contain an entry"):
        validate_version_changelog(
            _manifest("0.22.0"),
            _manifest("0.23.0"),
            _changelog("0.22.0"),
            "## v0.23.0\n\n## v0.22.0\n- Old",
        )


def test_initial_commit_requires_valid_manifest_and_changelog() -> None:
    assert (
        validate_version_changelog(
            None, _manifest("0.1.0"), None, _changelog("0.1.0")
        )
        == "0.1.0"
    )


def test_rejects_changelog_section_already_present_at_base() -> None:
    with pytest.raises(ValueError, match="must add a new"):
        validate_version_changelog(
            _manifest("0.22.0"),
            _manifest("0.23.0"),
            _changelog("0.23.0", "0.22.0"),
            _changelog("0.23.0", "0.22.0"),
        )
