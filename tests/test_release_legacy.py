"""Run the inherited standalone checks as isolated, portable processes."""

from pathlib import Path
import subprocess
import sys

import pytest


HERE = Path(__file__).parent
LEGACY_CHECKS = (
    "test_compute_forecast.py",
    "test_holiday_weekdays.py",
    "test_manual_intervention.py",
    "test_orphan_cleanup_suffixes.py",
    "test_scheduler_bug5.py",
    "test_stagger_delay.py",
    "test_sun_position.py",
)


@pytest.mark.parametrize("script", LEGACY_CHECKS)
def test_legacy_script(script: str) -> None:
    result = subprocess.run(
        [sys.executable, str(HERE / script)],
        cwd=HERE.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
