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


def validate_release_tag(tag: str, version: str, tags: list[str]) -> None:
    """Validate a stable tag against the manifest and all existing tags."""
    version_tuple = _version_tuple(version)
    expected_tag = f"v{version}" if version_tuple is not None else None
    if expected_tag is None or tag != expected_tag:
        raise ValueError(
            f"Release tag {tag!r} must use vX.Y.Z and match the manifest version; "
            f"expected {expected_tag!r}."
        )

    prior_tags = [
        (candidate, parsed)
        for candidate in tags
        if candidate != tag
        and candidate.startswith("v")
        and (parsed := _version_tuple(candidate[1:])) is not None
    ]
    prior_release = max(prior_tags, key=lambda item: item[1], default=None)
    if prior_release is not None and not _is_newer_version(
        version_tuple, prior_release[1]
    ):
        raise ValueError(
            f"Release version {version} must be higher than the previous "
            f"release tag {prior_release[0]}."
        )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: check_release_tag.py <tag>", file=sys.stderr)
        return 2

    tag = sys.argv[1]
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        version = manifest.get("version") if isinstance(manifest, dict) else None
        if not isinstance(version, str):
            raise ValueError("Integration manifest must contain a string version.")
        result = subprocess.run(
            ["git", "tag", "--list", "v*"],
            capture_output=True,
            check=True,
            text=True,
        )
        validate_release_tag(tag, version, result.stdout.splitlines())
    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as err:
        detail = (
            err.stderr.strip()
            if isinstance(err, subprocess.CalledProcessError) and err.stderr
            else str(err)
        )
        print(f"Release tag check failed: {detail}", file=sys.stderr)
        return 1

    print(f"Release tag {tag} matches manifest version {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
