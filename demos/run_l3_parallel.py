"""Run Stage 1 + Parallel Line-by-Line Level 3 Golden Discovery."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from geometor.levels.parallel_l3 import run_parallel_l3_golden

if __name__ == "__main__":
    run_parallel_l3_golden(workers=4, limit_lines=None, line_timeout_s=120)
