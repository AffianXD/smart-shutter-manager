"""Check that a release tag matches the integration manifest version."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "smart_shutter"
    / "manifest.json"
)
VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    """Parse a stable X.Y.Z version without a leading v."""
    match = VERSION_PATTERN.fullmatch(value)
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _is_newer_version(
    candidate: tuple[int, int, int], previous: tuple[int, int, int]
) -> bool:
    """Return whether candidate is strictly newer than previous."""
    return candidate > previous


def _latest_prior_release_tag(
    current_tag: str,
) -> tuple[str, tuple[int, int, int]] | None:
    """Return the highest earlier stable vX.Y.Z tag in the repository."""
    result = subprocess.run(
        ["git", "tag", "--list", "v*"],
        capture_output=True,
        check=True,
        text=True,
    )
    prior_tags = []
    for tag in result.stdout.splitlines():
        if tag == current_tag or not tag.startswith("v"):
            continue
        version = _version_tuple(tag[1:])
        if version is not None:
            prior_tags.append((tag, version))
    return max(prior_tags, key=lambda item: item[1], default=None)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: check_release_tag.py <tag>", file=sys.stderr)
        return 2

    tag = sys.argv[1]
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    version = manifest.get("version")
    version_tuple = _version_tuple(version) if isinstance(version, str) else None
    expected_tag = f"v{version}" if version_tuple is not None else None

    if expected_tag is None or tag != expected_tag:
        print(
            f"Release tag {tag!r} must use vX.Y.Z and match the manifest version; "
            f"expected {expected_tag!r}.",
            file=sys.stderr,
        )
        return 1

    prior_release = _latest_prior_release_tag(tag)
    if prior_release is not None and not _is_newer_version(
        version_tuple, prior_release[1]
    ):
        print(
            f"Release version {version} must be higher than the previous "
            f"release tag {prior_release[0]}.",
            file=sys.stderr,
        )
        return 1

    print(f"Release tag {tag} matches manifest version {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
