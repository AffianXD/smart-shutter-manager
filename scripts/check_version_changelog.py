"""Check release version/changelog policy for a push or pull request."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "custom_components/smart_shutter/manifest.json"
CHANGELOG_PATH = "CHANGELOG.md"
VERSIONED_DOC_PATHS = {"README.md", "MIGRATION.md", "HISTORY.md"}
VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
BACKFILL_SUBJECT_PATTERN = re.compile(
    r"^(?:build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)"
    r"(?:\([^)]+\))?!?: backfill v"
    r"((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))(?:\s.*)?$"
)


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    """Parse a stable semantic version in X.Y.Z form."""
    match = VERSION_PATTERN.fullmatch(value)
    if match is None:
        return None
    return (int(match[1]), int(match[2]), int(match[3]))


def _manifest_version(contents: str, ref: str) -> str:
    """Read and validate the integration version from manifest JSON."""
    try:
        manifest = json.loads(contents)
    except json.JSONDecodeError as err:
        raise ValueError(f"{ref} manifest is not valid JSON: {err}") from err

    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or _version_tuple(version) is None:
        raise ValueError(f"{ref} manifest must contain a stable X.Y.Z version.")
    return version


def requires_versioned_release(paths: set[str]) -> bool:
    """Whether changed files affect the shipped integration or release docs."""
    return any(
        path.startswith("custom_components/smart_shutter/")
        or path == CHANGELOG_PATH
        or path in VERSIONED_DOC_PATHS
        for path in paths
    )


def _section_body(changelog: str, version: str) -> str | None:
    """Return the body for one exact version heading, if it exists."""
    heading = f"## v{version}"
    lines = changelog.splitlines()
    matches = [index for index, line in enumerate(lines) if line.strip() == heading]
    if len(matches) > 1:
        raise ValueError(
            f"CHANGELOG.md must contain exactly one '{heading}' section; "
            f"found {len(matches)}."
        )
    if not matches:
        return None

    start = matches[0]
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end])


def _require_change_bullet(section: str, heading: str) -> None:
    if not any(line.lstrip().startswith("- ") for line in section.splitlines()):
        raise ValueError(
            f"CHANGELOG.md section '{heading}' must contain at least one change bullet."
        )


def validate_version_changelog(
    base_manifest: str | None,
    head_manifest: str,
    base_changelog: str | None,
    head_changelog: str,
) -> str:
    """Validate a higher version and a new, non-empty changelog section."""
    current_version = _manifest_version(head_manifest, "Updated")
    current_tuple = _version_tuple(current_version)
    assert current_tuple is not None

    if base_manifest is not None:
        previous_version = _manifest_version(base_manifest, "Base")
        previous_tuple = _version_tuple(previous_version)
        assert previous_tuple is not None
        if current_tuple <= previous_tuple:
            raise ValueError(
                f"Integration version must increase from {previous_version}; "
                f"found {current_version}."
            )

    heading = f"## v{current_version}"
    lines = head_changelog.splitlines()
    headings = [
        (index, line.strip())
        for index, line in enumerate(lines)
        if line.startswith("## ")
    ]
    section = _section_body(head_changelog, current_version)
    if section is None:
        raise ValueError(
            f"CHANGELOG.md must contain exactly one '{heading}' section; found 0."
        )
    if base_changelog is not None and _section_body(base_changelog, current_version) is not None:
        raise ValueError(
            f"CHANGELOG.md must add a new '{heading}' section for this version bump."
        )
    section_index = next(index for index, title in headings if title == heading)
    if not headings or headings[0][0] != section_index:
        raise ValueError(f"CHANGELOG.md must put '{heading}' at the top.")
    _require_change_bullet(section, heading)

    return current_version


def validate_backfill_changelog(
    *,
    version: str,
    base_manifest: str | None,
    head_manifest: str,
    base_changelog: str | None,
    head_changelog: str,
    changed_paths: set[str],
) -> None:
    """Validate an explicitly named historical changelog-only backfill."""
    target_tuple = _version_tuple(version)
    if target_tuple is None:
        raise ValueError("A backfill version must use stable X.Y.Z format.")
    if base_manifest is None or base_changelog is None:
        raise ValueError("A historical changelog backfill needs an existing base commit.")

    base_version = _manifest_version(base_manifest, "Base")
    current_version = _manifest_version(head_manifest, "Updated")
    if current_version != base_version:
        raise ValueError(
            "A historical backfill must leave the current manifest version "
            f"unchanged; found {current_version} after {base_version}."
        )
    current_tuple = _version_tuple(current_version)
    assert current_tuple is not None
    if target_tuple >= current_tuple:
        raise ValueError(
            f"Backfill v{version} must be older than the current integration "
            f"version v{current_version}."
        )

    release_paths = {path for path in changed_paths if requires_versioned_release({path})}
    if release_paths != {CHANGELOG_PATH}:
        raise ValueError(
            "A historical backfill may change CHANGELOG.md but no other "
            "release-relevant files."
        )

    current_section = _section_body(head_changelog, version)
    if current_section is None:
        raise ValueError(
            f"CHANGELOG.md must contain exactly one '## v{version}' section; found 0."
        )
    base_section = _section_body(base_changelog, version)
    if current_section == base_section:
        raise ValueError(
            f"CHANGELOG.md section v{version} must be added or updated in this backfill."
        )
    _require_change_bullet(current_section, f"v{version}")


def _git_show(ref: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        check=True,
        cwd=ROOT,
        text=True,
    )
    return result.stdout


def _git_changed_paths(base_sha: str, head_sha: str) -> set[str]:
    if not base_sha or set(base_sha) == {"0"}:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", head_sha],
            capture_output=True,
            check=True,
            cwd=ROOT,
            text=True,
        )
    else:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_sha, head_sha, "--"],
            capture_output=True,
            check=True,
            cwd=ROOT,
            text=True,
        )
    return {path for path in result.stdout.splitlines() if path}


def _commit_subjects(base_sha: str, head_sha: str) -> list[str]:
    revision = head_sha if not base_sha or set(base_sha) == {"0"} else f"{base_sha}..{head_sha}"
    result = subprocess.run(
        ["git", "log", "--format=%s", revision],
        capture_output=True,
        check=True,
        cwd=ROOT,
        text=True,
    )
    return result.stdout.splitlines()


def _backfill_versions_from_subjects(subjects: list[str]) -> set[str]:
    """Read explicit historical backfill versions from commit subjects."""
    versions = set()
    for subject in subjects:
        match = BACKFILL_SUBJECT_PATTERN.fullmatch(subject)
        if match is not None:
            versions.add(match.group(1))
    return versions


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: check_version_changelog.py <base-sha> <head-sha>",
            file=sys.stderr,
        )
        return 2

    base_sha, head_sha = sys.argv[1:]
    try:
        head_manifest = _git_show(head_sha, MANIFEST_PATH)
        head_changelog = _git_show(head_sha, CHANGELOG_PATH)
        base_manifest = (
            None
            if not base_sha or set(base_sha) == {"0"}
            else _git_show(base_sha, MANIFEST_PATH)
        )
        base_changelog = (
            None
            if not base_sha or set(base_sha) == {"0"}
            else _git_show(base_sha, CHANGELOG_PATH)
        )
        changed_paths = _git_changed_paths(base_sha, head_sha)
        backfill_versions = _backfill_versions_from_subjects(
            _commit_subjects(base_sha, head_sha)
        )
    except (ValueError, subprocess.CalledProcessError) as err:
        detail = (
            err.stderr.strip()
            if isinstance(err, subprocess.CalledProcessError) and err.stderr
            else str(err)
        )
        print(f"Version/changelog check failed: {detail}", file=sys.stderr)
        return 1

    if len(backfill_versions) > 1:
        print(
            "Version/changelog check failed: one push cannot backfill multiple "
            "release versions.",
            file=sys.stderr,
        )
        return 1

    if backfill_versions:
        backfill_version = next(iter(backfill_versions))
        try:
            validate_backfill_changelog(
                version=backfill_version,
                base_manifest=base_manifest,
                head_manifest=head_manifest,
                base_changelog=base_changelog,
                head_changelog=head_changelog,
                changed_paths=changed_paths,
            )
        except ValueError as err:
            print(f"Version/changelog check failed: {err}", file=sys.stderr)
            return 1
        print(f"Historical changelog backfill v{backfill_version} is valid.")
        return 0

    if not requires_versioned_release(changed_paths):
        print(
            "No integration or release-documentation files changed; "
            "no version bump is required."
        )
        return 0

    try:
        version = validate_version_changelog(
            base_manifest, head_manifest, base_changelog, head_changelog
        )
    except ValueError as err:
        print(f"Version/changelog check failed: {err}", file=sys.stderr)
        return 1

    print(f"Integration version {version} has a matching changelog section.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
