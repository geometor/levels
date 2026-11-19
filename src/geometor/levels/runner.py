"""Resilient Level 3 runner with timed checkpoints and signal handling."""

from __future__ import annotations

import signal
import sys
import time
from datetime import datetime
from itertools import combinations
from pathlib import Path

import sympy as sp
from geometor.model import Model

from .levels import fundamental, order_pairs_round_robin, order_pairs_symmetric


def run_level3(
    *,
    order: str = "round_robin",
    output_dir: Path | None = None,
    save_interval_s: float = 3600.0,
) -> Path:
    """Run Level 3 construction using the selected pair ordering.

    Args:
        order: Pair ordering strategy (``"round_robin"`` or ``"symmetric"``).
        output_dir: Directory for logs and JSON checkpoints. Defaults to
            ``<repo_root>/runs/<order>_<YYYYMMDD-HHMMSS>``.
        save_interval_s: Seconds between periodic JSON checkpoints.

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
    log_path.write_text("", encoding="utf-8")

    def log_msg(msg: str) -> None:
        print(msg, flush=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(msg + "\n")

    t0 = time.perf_counter()
    model = Model(f"level-3-{order}", use_point_subscript=True, enable_logging=False)
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
    log_msg(
        f"L2 done in {time.perf_counter() - t1:.4f}s | "
        f"pts={len(model.points)}, lines={len(model.lines)}, circles={len(model.circles)}"
    )

    pts_l2 = list(model.points)
    if order == "round_robin":
        pairs = order_pairs_round_robin(pts_l2)
    elif order == "symmetric":
        pairs = order_pairs_symmetric(pts_l2)
    else:
        raise ValueError(f"Unknown order strategy: {order!r}")

    total = len(pairs)
    log_msg(f"Starting Level 3 ({order}, {total} pairs) -> {out_dir}")

    stop_requested = False

    def handle_signal(signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True
        log_msg(f"Signal {signum} received — will save checkpoint after current pair and exit.")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    t2 = time.perf_counter()
    last_save = t2

    for idx, (p1, p2) in enumerate(pairs, 1):
        if stop_requested:
            break
        pair_start = time.perf_counter()
        pts_b, lines_b, circ_b = len(model.points), len(model.lines), len(model.circles)

        fundamental(model, p1, p2)

        dt = time.perf_counter() - pair_start
        elapsed = time.perf_counter() - t2
        new_pts = len(model.points) - pts_b
        new_lines = len(model.lines) - lines_b
        new_circ = len(model.circles) - circ_b

        if new_pts or new_lines or new_circ or idx % 100 == 0 or idx == total:
            log_msg(
                f"  L3 {idx}/{total} ({100 * idx / total:.3f}%) | "
                f"+{dt:.2f}s (tot {elapsed:.1f}s) | "
                f"pts={len(model.points)} (+{new_pts}), "
                f"lines={len(model.lines)} (+{new_lines}), "
                f"circles={len(model.circles)} (+{new_circ})"
            )

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
                sys.exit(0)

    model.save(str(final_path))
    log_msg(f"Level 3 ({order}) COMPLETE in {time.perf_counter() - t2:.1f}s!")
    return final_path
