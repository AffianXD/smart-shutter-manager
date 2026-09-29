"""Tests for the GitHub release tag and integration version check."""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from scripts import check_release_tag
from scripts.check_release_tag import _is_newer_version, _version_tuple


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "custom_components" / "smart_shutter" / "manifest.json"
CHECK_SCRIPT = ROOT / "scripts" / "check_release_tag.py"


def _manifest_version() -> str:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["version"]


def _parsed_manifest_version() -> tuple[int, int, int]:
    version = _version_tuple(_manifest_version())
    assert version is not None
    return version


def _format_version(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)


def _check_tag(tag: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), tag],
        capture_output=True,
        check=False,
        text=True,
    )


def test_release_tag_matches_manifest_version() -> None:
    version = _manifest_version()

    result = _check_tag(f"v{version}")

    assert result.returncode == 0
    assert f"matches manifest version {version}" in result.stdout


def test_release_tag_mismatch_is_rejected() -> None:
    version = _manifest_version()

    result = _check_tag(f"v{version}-mismatch")

    assert result.returncode == 1
    assert "match the manifest version" in result.stderr


def test_version_tuple_uses_semantic_numeric_order() -> None:
    current = _parsed_manifest_version()
    next_major = (current[0] + 1, 0, 0)

    assert _version_tuple(_manifest_version()) == current
    assert _version_tuple(_format_version(next_major)) == next_major
    assert current < next_major
    assert _version_tuple(f"{_manifest_version()}-beta") is None


def test_release_version_must_increase() -> None:
    current = _parsed_manifest_version()
    next_major = (current[0] + 1, 0, 0)

    assert _is_newer_version(next_major, current)
    assert not _is_newer_version(current, current)


def test_release_check_rejects_version_behind_latest_tag(monkeypatch, capsys) -> None:
    version = _manifest_version()
    current = _parsed_manifest_version()
    next_patch_tag = f"v{current[0]}.{current[1]}.{current[2] + 1}"
    current_tag = f"v{version}"

    monkeypatch.setattr(
        check_release_tag.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout=f"{current_tag}\n{next_patch_tag}\n"
        ),
    )
    monkeypatch.setattr(sys, "argv", [str(CHECK_SCRIPT), current_tag])

    assert check_release_tag.main() == 1
    assert (
        f"higher than the previous release tag {next_patch_tag}"
        in capsys.readouterr().err
    )
