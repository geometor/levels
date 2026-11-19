"""Run Level 3 with symmetric radial ordering."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from geometor.levels.runner import run_level3

if __name__ == "__main__":
    run_level3(order="symmetric", save_interval_s=1800.0)
