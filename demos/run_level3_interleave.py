"""Run Level 3 with round-robin all-points interleaving."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from geometor.levels.runner import run_level3

if __name__ == "__main__":
    run_level3(
        order="round_robin",
        save_interval_s=3600.0,
        max_rss_gb=18.0,
        min_avail_gb=4.0,
        track_goldens=True,
    )
