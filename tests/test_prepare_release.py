"""Tests for the local release preparation draft generator."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.prepare_release import _commit_entry, prepare_release


MANIFEST = "custom_components/smart_shutter/manifest.json"
CHANGELOG = "CHANGELOG.md"


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=True, text=True
    )
    return result.stdout.strip()


def _commit(root: Path, subject: str, *, paths: tuple[str, ...]) -> None:
    _git(root, "add", *paths)
    _git(root, "-c", "user.name=Release Tests", "-c", "user.email=release@example.invalid",
         "commit", "-m", subject)


def _repo(tmp_path: Path, version: str = "1.2.3") -> Path:
    root = tmp_path
    _git(root, "init", "-q")
    manifest = root / MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"domain": "smart_shutter", "version": version}) + "\n")
    (root / CHANGELOG).write_text(
        f"# Changelog\n\n## v{version}\n\n- Previous stable release.\n"
    )
    _commit(root, "chore: create release test baseline", paths=(MANIFEST, CHANGELOG))
    _git(root, "tag", f"v{version}")
    feature = root / "custom_components/smart_shutter/example.py"
    feature.write_text("VALUE = True\n")
    _commit(root, "feat(settings): add the setting option", paths=(str(feature.relative_to(root)),))
    return root


@pytest.mark.parametrize(
    ("increment", "expected"),
    [("patch", "1.2.4"), ("minor", "1.3.0"), ("major", "2.0.0")],
)
def test_semver_bump_updates_manifest_and_builds_changelog(
    tmp_path: Path, increment: str, expected: str
) -> None:
    root = _repo(tmp_path)

    result = prepare_release(increment, root=root)

    manifest = json.loads((root / MANIFEST).read_text())
    changelog = (root / CHANGELOG).read_text()
    assert result.version == expected
    assert result.bumped is True
    assert manifest["version"] == expected
    assert changelog.count(f"## v{expected}") == 1
    assert "### Added\n\n- Add the setting option <!-- prepare-release:" in changelog
    assert "## v1.2.3\n\n- Previous stable release." in changelog


def test_rerun_reuses_existing_version_and_deduplicates_commits(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    first = prepare_release("patch", root=root)
    _commit(root, "chore(release): prepare draft", paths=(MANIFEST, CHANGELOG))

    fix = root / "custom_components/smart_shutter/fix.py"
    fix.write_text("FIXED = True\n")
    _commit(root, "fix: correct the shutter option default", paths=(str(fix.relative_to(root)),))
    second = prepare_release("major", root=root)

    changelog = (root / CHANGELOG).read_text()
    assert first.version == second.version == "1.2.4"
    assert first.bumped is True and second.bumped is False
    assert changelog.count("## v1.2.4") == 1
    assert changelog.count("Add the setting option") == 1
    assert "### Fixed\n\n- Correct the shutter option default" in changelog


def test_existing_matching_changelog_entry_is_not_duplicated(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    changelog = root / CHANGELOG
    changelog.write_text(
        "# Changelog\n\n## v1.2.4\n\n### Added\n\n- Add the setting option\n\n"
        "## v1.2.3\n\n- Previous stable release.\n"
    )
    _commit(root, "docs: keep the current release draft", paths=(CHANGELOG,))

    prepare_release("patch", root=root)

    updated = changelog.read_text()
    assert updated.count("- Add the setting option") == 1
    assert updated.count("## v1.2.4") == 1


def test_duplicate_existing_changelog_bullets_are_reported_without_writes(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    changelog = root / CHANGELOG
    changelog.write_text(
        "# Changelog\n\n## v1.2.4\n\n- Same entry\n- Same entry\n\n"
        "## v1.2.3\n\n- Previous stable release.\n"
    )
    _commit(root, "docs: add release draft", paths=(CHANGELOG,))
    before = changelog.read_text()
    manifest_before = (root / MANIFEST).read_text()

    with pytest.raises(ValueError, match="duplicate changelog entries"):
        prepare_release("patch", root=root)

    assert changelog.read_text() == before
    assert (root / MANIFEST).read_text() == manifest_before


def test_duplicate_version_heading_is_reported_without_writes(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    changelog = root / CHANGELOG
    changelog.write_text(
        "# Changelog\n\n## v1.2.4\n\n- First draft entry.\n\n"
        "## v1.2.4\n\n- Duplicate heading.\n\n## v1.2.3\n- Previous.\n"
    )
    _commit(root, "docs: add duplicate draft section", paths=(CHANGELOG,))
    before = changelog.read_text()

    with pytest.raises(ValueError, match="duplicate '## v1.2.4'"):
        prepare_release("patch", root=root)

    assert changelog.read_text() == before


def test_breaking_commits_are_categorized_and_include_breaking_detail() -> None:
    category, entry = _commit_entry(
        "a" * 40,
        "feat(settings)!: remove legacy schedule mode",
        "BREAKING CHANGE: legacy schedule mode is no longer supported.",
    )

    assert category == "Breaking Changes"
    assert "Remove legacy schedule mode: legacy schedule mode is no longer supported." in entry


@pytest.mark.parametrize("manifest_text", ["{", '{"domain":"smart_shutter"}'])
def test_missing_or_invalid_manifest_version_fails_without_mutation(
    tmp_path: Path, manifest_text: str
) -> None:
    root = _repo(tmp_path)
    manifest = root / MANIFEST
    manifest.write_text(manifest_text)
    _commit(root, "chore: invalidate release metadata", paths=(MANIFEST,))
    changelog_before = (root / CHANGELOG).read_text()

    with pytest.raises(ValueError, match="manifest"):
        prepare_release("patch", root=root)

    assert manifest.read_text() == manifest_text
    assert (root / CHANGELOG).read_text() == changelog_before


def test_unrecognized_commit_is_marked_for_manual_review(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    unclear = root / "custom_components/smart_shutter/unclear.py"
    unclear.write_text("PASS = True\n")
    _commit(root, "some small tweaks", paths=(str(unclear.relative_to(root)),))

    result = prepare_release("patch", root=root)

    changelog = (root / CHANGELOG).read_text()
    assert result.reviewed_commits == 1
    assert "### Review Required" in changelog
    assert "[Review required] some small tweaks" in changelog


def test_modified_manifest_is_refused_without_overwriting_changes(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    manifest = root / MANIFEST
    manifest.write_text('{"version":"9.9.9"}\n')
    changelog_before = (root / CHANGELOG).read_text()

    with pytest.raises(ValueError, match="will not overwrite existing changes"):
        prepare_release("patch", root=root)

    assert manifest.read_text() == '{"version":"9.9.9"}\n'
    assert (root / CHANGELOG).read_text() == changelog_before


def test_uncommitted_integration_changes_are_preserved_and_marked_for_review(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    source = root / "custom_components/smart_shutter/example.py"
    source.write_text("VALUE = 'uncommitted feature'\n")

    result = prepare_release("patch", root=root)

    changelog = (root / CHANGELOG).read_text()
    assert result.reviewed_commits == 1
    assert (
        "Uncommitted release-relevant changes in "
        "`custom_components/smart_shutter/example.py`"
    ) in changelog
    assert "[Review required]" in changelog
    assert source.read_text() == "VALUE = 'uncommitted feature'\n"
    assert (root / MANIFEST).read_text().find('"version": "1.2.4"') >= 0


def test_no_release_commits_fails_without_creating_empty_section(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    # Reset only the temporary test repository's feature commit back to the tag.
    _git(root, "reset", "--hard", "v1.2.3")
    before_manifest = (root / MANIFEST).read_text()
    before_changelog = (root / CHANGELOG).read_text()

    with pytest.raises(ValueError, match="No changelog entries"):
        prepare_release("patch", root=root)

    assert (root / MANIFEST).read_text() == before_manifest
    assert (root / CHANGELOG).read_text() == before_changelog
