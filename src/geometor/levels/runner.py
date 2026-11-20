"""Resilient Level 3 runner with memory guards, golden tracking, and telemetry."""

from __future__ import annotations

import gc
import json
import os
import signal
import time
from datetime import datetime
from itertools import combinations
from pathlib import Path

import sympy as sp
from geometor.divine.golden import GoldenFieldTracker
from geometor.model import Model

from .levels import fundamental, order_pairs_round_robin, order_pairs_symmetric


def _process_rss_gb() -> float:
    """Return current process Resident Set Size (RSS) in GiB on Linux."""
    try:
        pages = int(Path("/proc/self/statm").read_text(encoding="utf-8").split()[1])
        return (pages * os.sysconf("SC_PAGE_SIZE")) / (1024**3)
    except (OSError, ValueError, IndexError):
        return 0.0


def _mem_available_gb() -> float:
    """Return system MemAvailable in GiB from ``/proc/meminfo``."""
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                kb = int(line.split()[1])
                return kb / (1024**2)
    except (OSError, ValueError, IndexError):
        pass
    return 999.0


def run_level3(
    *,
    order: str = "round_robin",
    output_dir: Path | None = None,
    save_interval_s: float = 3600.0,
    max_rss_gb: float = 18.0,
    min_avail_gb: float = 4.0,
    track_goldens: bool = True,
) -> Path:
    """Run Level 3 construction safely with memory guards and optional golden tracking.

    Args:
        order: Pair ordering strategy (``"round_robin"`` or ``"symmetric"``).
        output_dir: Directory for logs, JSONL telemetry, and JSON checkpoints.
            Defaults to ``<repo_root>/runs/<order>_<YYYYMMDD-HHMMSS>``.
        save_interval_s: Seconds between periodic JSON checkpoints.
        max_rss_gb: Stop cleanly and save if process RSS exceeds this GiB limit.
        min_avail_gb: Stop cleanly and save if system MemAvailable drops below this GiB.
        track_goldens: Attach ``GoldenFieldTracker`` to record point-birth golden impact.

    Returns:
        Path to the final saved model JSON file.
    """
    repo_root = Path(__file__).resolve().parents[3]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = output_dir or (repo_root / "runs" / f"{order}_{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    ckpt_path = out_dir / f"level-3-{order}-checkpoint.json"
    final_path = out_dir / f"level-3-{order}.json"
    log_path = out_dir / f"level3_{order}.log"
    jsonl_path = out_dir / f"level3_{order}.jsonl"
    log_path.write_text("", encoding="utf-8")

    def log_msg(msg: str) -> None:
        print(msg, flush=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(msg + "\n")

    t0 = time.perf_counter()
    model = Model(f"level-3-{order}", use_point_subscript=True, enable_logging=False)
    tracker = GoldenFieldTracker(tag_model=True).attach(model) if track_goldens else None

    pt_a = model.set_point(sp.Rational(-1, 2), 0, classes=["given"])
    pt_b = model.set_point(sp.Rational(1, 2), 0, classes=["given"])

    fundamental(model, pt_a, pt_b)
    log_msg(
        f"L1 done in {time.perf_counter() - t0:.4f}s | "
        f"pts={len(model.points)}, lines={len(model.lines)}, circles={len(model.circles)}"
    )

    t1 = time.perf_counter()
    for p1, p2 in combinations(model.points, 2):
        fundamental(model, p1, p2)
    if tracker is not None:
        tracker.sync(model)
    l2_goldens = len(tracker.sections) if tracker is not None else 0
    log_msg(
        f"L2 done in {time.perf_counter() - t1:.4f}s | "
        f"pts={len(model.points)}, lines={len(model.lines)}, "
        f"circles={len(model.circles)}, goldens={l2_goldens}"
    )

    pts_l2 = list(model.points)
    if order == "round_robin":
        pairs = order_pairs_round_robin(pts_l2)
    elif order == "symmetric":
        pairs = order_pairs_symmetric(pts_l2)
    else:
        raise ValueError(f"Unknown order strategy: {order!r}")

    total = len(pairs)
    log_msg(
        f"Starting Level 3 ({order}, {total} pairs, "
        f"max_rss={max_rss_gb}GiB, min_avail={min_avail_gb}GiB) -> {out_dir}"
    )

    stop_requested = False

    def handle_signal(signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True
        log_msg(f"Signal {signum} received — will save checkpoint after current pair and exit.")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    t2 = time.perf_counter()
    last_save = t2

    with jsonl_path.open("a", encoding="utf-8") as jfh:
        for idx, (p1, p2) in enumerate(pairs, 1):
            if stop_requested:
                break
            pair_start = time.perf_counter()
            pts_b, lines_b, circ_b = len(model.points), len(model.lines), len(model.circles)
            secs_b = len(tracker.sections) if tracker is not None else 0

            fundamental(model, p1, p2)
            if tracker is not None:
                tracker.sync(model)

            dt = time.perf_counter() - pair_start
            elapsed = time.perf_counter() - t2
            new_pts = len(model.points) - pts_b
            new_lines = len(model.lines) - lines_b
            new_circ = len(model.circles) - circ_b
            secs_tot = len(tracker.sections) if tracker is not None else 0
            new_secs = secs_tot - secs_b

            rss = _process_rss_gb()
            avail = _mem_available_gb()

            if new_pts or new_lines or new_circ or new_secs or idx % 100 == 0 or idx == total:
                log_msg(
                    f"  L3 {idx}/{total} ({100 * idx / total:.3f}%) | "
                    f"+{dt:.2f}s (tot {elapsed:.1f}s) | "
                    f"pts={len(model.points)} (+{new_pts}), "
                    f"lines={len(model.lines)} (+{new_lines}), "
                    f"circles={len(model.circles)} (+{new_circ}), "
                    f"goldens={secs_tot} (+{new_secs}) | "
                    f"rss={rss:.2f}GiB, avail={avail:.2f}GiB"
                )
                jfh.write(
                    json.dumps(
                        {
                            "pair": idx,
                            "pts": len(model.points),
                            "lines": len(model.lines),
                            "circles": len(model.circles),
                            "goldens": secs_tot,
                            "dt_s": round(dt, 3),
                            "rss_gb": round(rss, 3),
                            "avail_gb": round(avail, 3),
                        }
                    )
                    + "\n"
                )
                jfh.flush()

            if idx % 10 == 0:
                sp.core.cache.clear_cache()
                gc.collect()

            mem_trip = rss >= max_rss_gb or avail <= min_avail_gb
            if mem_trip:
                log_msg(
                    f"  [memory guard] rss={rss:.2f}GiB (max {max_rss_gb}), "
                    f"avail={avail:.2f}GiB (min {min_avail_gb}) — saving & exiting."
                )
                stop_requested = True

            now = time.perf_counter()
            if (now - last_save) >= save_interval_s or stop_requested:
                save_t0 = time.perf_counter()
                model.save(str(ckpt_path))
                log_msg(
                    f"  [checkpoint] saved {ckpt_path.name} at pair {idx} "
                    f"in {time.perf_counter() - save_t0:.1f}s"
                )
                last_save = time.perf_counter()
                if stop_requested:
                    return ckpt_path

    model.save(str(final_path))
    log_msg(f"Level 3 ({order}) COMPLETE in {time.perf_counter() - t2:.1f}s!")
    return final_path
