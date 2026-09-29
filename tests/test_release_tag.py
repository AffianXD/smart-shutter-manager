"""Tests for the GitHub release tag and integration version check."""

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "custom_components" / "smart_shutter" / "manifest.json"
CHECK_SCRIPT = ROOT / "scripts" / "check_release_tag.py"


def _check_tag(tag: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), tag],
        capture_output=True,
        check=False,
        text=True,
    )


def test_release_tag_matches_manifest_version() -> None:
    version = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["version"]

    result = _check_tag(f"v{version}")

    assert result.returncode == 0
    assert f"matches manifest version {version}" in result.stdout


def test_release_tag_mismatch_is_rejected() -> None:
    version = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["version"]

    result = _check_tag(f"v{version}-mismatch")

    assert result.returncode == 1
    assert "must match the manifest version" in result.stderr
