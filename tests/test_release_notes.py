"""Check release note selection and failures before any publication."""

import subprocess
import sys

import pytest

from scripts.release_notes import release_notes


def test_exact_version_preserves_nested_sections_and_excludes_neighbors():
    changelog = """# Changelog
## v0.30.0
- Newer release.
## v0.29.0
### Features
- Warnings per shutter.
### Fixes
- A fix.
## v0.28.2
- Older release.
"""
    assert release_notes(changelog, "v0.29.0") == (
        "## v0.29.0\n\n### Features\n- Warnings per shutter.\n"
        "### Fixes\n- A fix.\n"
    )


@pytest.mark.parametrize("tag", ["0.29.0", "v0.29.0-beta", "v00.29.0", "v0.29"])
def test_invalid_tag_rejected(tag):
    with pytest.raises(ValueError, match="stable vX.Y.Z"):
        release_notes("## v0.29.0\n- Change.", tag)


@pytest.mark.parametrize("changelog", [
    "## v0.29.00\n- Wrong version.",
    "## v0.29.0\n\n## v0.28.2\n- Older release.",
    "## v0.29.0\n- Change.\n## v0.29.0\n- Duplicate.",
])
def test_missing_empty_or_duplicate_section_rejected(changelog):
    with pytest.raises(ValueError):
        release_notes(changelog, "v0.29.0")


def test_cli_failure_does_not_write_notes(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## v0.28.2\n- Other release.\n")
    output = tmp_path / "notes.md"
    result = subprocess.run(
        [sys.executable, "-m", "scripts.release_notes", "v0.29.0",
         "--changelog", str(changelog), "--output", str(output)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "no non-empty section" in result.stderr
    assert not output.exists()
