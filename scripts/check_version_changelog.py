"""Require each pushed change to bump the integration version and changelog."""

from __future__ import annotations

import json
import re
import subprocess
import sys


MANIFEST_PATH = "custom_components/smart_shutter/manifest.json"
CHANGELOG_PATH = "CHANGELOG.md"
VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


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


def validate_version_changelog(
    base_manifest: str | None,
    head_manifest: str,
    base_changelog: str | None,
    head_changelog: str,
) -> str:
    """Validate a version bump and its unique, versioned changelog heading."""
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
    matching = [(index, title) for index, title in headings if title == heading]
    heading_count = len(matching)
    if heading_count != 1:
        raise ValueError(
            f"CHANGELOG.md must contain exactly one '{heading}' section; "
            f"found {heading_count}."
        )
    if base_changelog is not None and any(
        line.strip() == heading for line in base_changelog.splitlines()
    ):
        raise ValueError(
            f"CHANGELOG.md must add a new '{heading}' section for this version bump."
        )
    section_index, _ = matching[0]
    if not headings or headings[0][0] != section_index:
        raise ValueError(f"CHANGELOG.md must put '{heading}' at the top.")

    section_end = next(
        (index for index, _ in headings if index > section_index), len(lines)
    )
    if not any(line.strip() for line in lines[section_index + 1 : section_end]):
        raise ValueError(f"CHANGELOG.md section '{heading}' must contain an entry.")

    return current_version


def _git_show(ref: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout


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
        version = validate_version_changelog(
            base_manifest, head_manifest, base_changelog, head_changelog
        )
    except (ValueError, subprocess.CalledProcessError) as err:
        detail = (
            err.stderr.strip()
            if isinstance(err, subprocess.CalledProcessError) and err.stderr
            else str(err)
        )
        print(f"Version/changelog check failed: {detail}", file=sys.stderr)
        return 1

    print(f"Integration version {version} has a matching changelog section.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
