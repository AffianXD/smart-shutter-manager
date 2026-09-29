"""Check that a release tag matches the integration manifest version."""

from __future__ import annotations

import json
from pathlib import Path
import sys


MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "smart_shutter"
    / "manifest.json"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: check_release_tag.py <tag>", file=sys.stderr)
        return 2

    tag = sys.argv[1]
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    version = manifest.get("version")
    expected_tag = f"v{version}" if isinstance(version, str) else None

    if expected_tag is None or tag != expected_tag:
        print(
            f"Release tag {tag!r} must match the manifest version; "
            f"expected {expected_tag!r}.",
            file=sys.stderr,
        )
        return 1

    print(f"Release tag {tag} matches manifest version {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
