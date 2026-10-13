"""Build GitHub Release notes from the exact version section in CHANGELOG.md."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from scripts.check_version_changelog import (
    ROOT,
    _section_body,
    _version_tuple,
    validate_release_notes_complete,
)


_PREPARE_RELEASE_SOURCE = re.compile(
    r"\s*<!-- prepare-release:[0-9a-z-]{7,40} -->", re.IGNORECASE
)


def release_notes(changelog: str, tag: str) -> str:
    """Preserve the version's prose and nested headings without other releases."""
    if not tag.startswith("v") or _version_tuple(tag[1:]) is None:
        raise ValueError("Release tag must use stable vX.Y.Z format.")
    body = _section_body(changelog, tag[1:])
    if not body or not body.strip():
        raise ValueError(f"CHANGELOG.md has no non-empty section for {tag}.")
    validate_release_notes_complete(body)
    body = _PREPARE_RELEASE_SOURCE.sub("", body)
    body = re.sub(r"[ \t]+\n", "\n", body).strip()
    return f"## {tag}\n\n{body}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--changelog", type=Path, default=ROOT / "CHANGELOG.md")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        notes = release_notes(args.changelog.read_text(encoding="utf-8"), args.tag)
    except (OSError, ValueError) as error:
        print(f"Cannot prepare release notes: {error}", file=sys.stderr)
        return 1
    args.output.write_text(notes, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
