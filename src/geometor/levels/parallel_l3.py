"""Parallel out-of-core Level 3 structure generation and line-by-line golden scan."""

from __future__ import annotations

import json
import math
import signal
import time
from datetime import datetime
from itertools import combinations
from multiprocessing import Pool
from pathlib import Path

import sympy as sp
import sympy.geometry as spg
from geometor.divine.golden import (
    find_chains_in_sections,
    find_golden_sections_in_points,
    unpack_chains,
)
from geometor.model import intersect_2d, zero_test
from geometor.model.element import (
    _compute_approx_coords,
    _structs_exact_equal,
    _structs_numerically_close,
)

from .levels import build_level

_GRID_H = 1e-6


class _LineTimeout(Exception):
    pass


def _alarm_handler(_signum: int, _frame: object) -> None:
    raise _LineTimeout()


def _grid_cell_3d(sig: tuple[float, ...], h: float = _GRID_H) -> tuple[int, int, int] | None:
    if len(sig) < 3 or not all(math.isfinite(v) for v in sig[:3]):
        return None
    return (math.floor(sig[0] / h), math.floor(sig[1] / h), math.floor(sig[2] / h))


def generate_l3_structures(
    cache_path: Path | None = None,
) -> tuple[list[spg.Line], list[spg.Circle]]:
    """Generate all unique Level 3 lines (17,562) and circles (32,719) using 3D grid dedup."""
    if cache_path is not None and cache_path.exists():
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        lines = [sp.sympify(s) for s in data["lines"]]
        circles = [sp.sympify(s) for s in data["circles"]]
        sp.core.cache.clear_cache()
        return lines, circles

    m2 = build_level(2)
    pts_l2 = m2.points

    lines: list[spg.Line] = list(m2.lines)
    line_sigs: list[tuple[float, ...]] = []
    line_grid: dict[tuple[int, int, int], list[int]] = {}

    circles: list[spg.Circle] = list(m2.circles)
    circle_sigs: list[tuple[float, ...]] = []
    circle_grid: dict[tuple[int, int, int], list[int]] = {}

    def _register_line(ln: spg.Line) -> None:
        sig = _compute_approx_coords(ln)
        assert sig is not None
        idx = len(line_sigs)
        line_sigs.append(sig)
        cell = _grid_cell_3d(sig)
        if cell is not None:
            line_grid.setdefault(cell, []).append(idx)

    def _register_circle(c: spg.Circle) -> None:
        sig = _compute_approx_coords(c)
        assert sig is not None
        idx = len(circle_sigs)
        circle_sigs.append(sig)
        cell = _grid_cell_3d(sig)
        if cell is not None:
            circle_grid.setdefault(cell, []).append(idx)

    # Seed with Level 2 lines/circles (register indices aligned with lists)
    seed_lines = list(lines)
    lines.clear()
    for ln in seed_lines:
        _register_line(ln)
        lines.append(ln)

    seed_circles = list(circles)
    circles.clear()
    for c in seed_circles:
        _register_circle(c)
        circles.append(c)

    line_seen_exact = set(lines)
    circle_seen_exact = set(circles)

    def _has_line(cand: spg.Line) -> bool:
        if cand in line_seen_exact:
            return True
        sig = _compute_approx_coords(cand)
        if sig is None:
            return False
        probes = [sig]
        if abs(sig[0]) < _GRID_H:
            probes.append((-sig[0], -sig[1], -sig[2]))
        checked: set[int] = set()
        for probe in probes:
            cell = _grid_cell_3d(probe)
            if cell is None:
                continue
            ix, iy, iz = cell
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for j in line_grid.get((ix + dx, iy + dy, iz + dz), ()):
                            if j in checked:
                                continue
                            checked.add(j)
                            if _structs_numerically_close(
                                lines[j], cand, line_sigs[j], sig
                            ) and _structs_exact_equal(lines[j], cand):
                                return True
        return False

    def _has_circle(cand: spg.Circle) -> bool:
        if cand in circle_seen_exact:
            return True
        sig = _compute_approx_coords(cand)
        if sig is None:
            return False
        cell = _grid_cell_3d(sig)
        if cell is None:
            return False
        ix, iy, iz = cell
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in circle_grid.get((ix + dx, iy + dy, iz + dz), ()):
                        if _structs_numerically_close(
                            circles[j], cand, circle_sigs[j], sig
                        ) and _structs_exact_equal(circles[j], cand):
                            return True
        return False

    for p1, p2 in combinations(pts_l2, 2):
        ln = spg.Line(p1, p2)
        if not _has_line(ln):
            _register_line(ln)
            lines.append(ln)
            line_seen_exact.add(ln)

        r2 = (p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2
        r = sp.sqrt(r2)
        for center in (p1, p2):
            c = spg.Circle(center, r)
            if not _has_circle(c):
                _register_circle(c)
                circles.append(c)
                circle_seen_exact.add(c)

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "lines": [sp.srepr(ln) for ln in lines],
            "circles": [sp.srepr(c) for c in circles],
        }
        cache_path.write_text(json.dumps(payload), encoding="utf-8")

    sp.core.cache.clear_cache()
    return lines, circles


# --- Worker state (initialized once per worker process) ---
_W_LINES: list[spg.Line] = []
_W_LINE_SIGS: list[tuple[float, ...]] = []
_W_CIRCLES: list[spg.Circle] = []
_W_CIRCLE_SIGS: list[tuple[float, ...]] = []
_W_LINE_TIMEOUT_S: int = 60


def _worker_init(
    lines_srepr: list[str],
    circles_srepr: list[str],
    line_timeout_s: int,
) -> None:
    global _W_LINES, _W_LINE_SIGS, _W_CIRCLES, _W_CIRCLE_SIGS, _W_LINE_TIMEOUT_S
    _W_LINES = [sp.sympify(s) for s in lines_srepr]
    _W_LINE_SIGS = [_compute_approx_coords(ln) or (0.0, 0.0, 0.0) for ln in _W_LINES]
    _W_CIRCLES = [sp.sympify(s) for s in circles_srepr]
    _W_CIRCLE_SIGS = [_compute_approx_coords(c) or (0.0, 0.0, 0.0) for c in _W_CIRCLES]
    _W_LINE_TIMEOUT_S = line_timeout_s
    sp.core.cache.clear_cache()
    signal.signal(signal.SIGALRM, _alarm_handler)


def _scan_one_line(line_idx: int) -> dict[str, object]:
    t0 = time.perf_counter()
    line_i = _W_LINES[line_idx]
    ua, ub, uc = _W_LINE_SIGS[line_idx]

    p1, p2 = line_i.p1, line_i.p2
    x1, y1 = float(p1.x.evalf()), float(p1.y.evalf())
    x2, y2 = float(p2.x.evalf()), float(p2.y.evalf())
    if (x2, y2) < (x1, y1):
        x1, y1, x2, y2 = x2, y2, x1, y1
    dx, dy = x2 - x1, y2 - y1
    dnorm = math.hypot(dx, dy)
    ux, uy = dx / dnorm, dy / dnorm

    pts_with_xy: list[tuple[spg.Point2D, float, float]] = []
    pt_set: set[spg.Point2D] = set()
    grid_1d: dict[int, list[tuple[spg.Point2D, float, float]]] = {}

    def _add_pt(pt: spg.Point2D) -> None:
        if pt in pt_set:
            return
        fx, fy = float(pt.x.evalf()), float(pt.y.evalf())
        s_val = (fx - x1) * ux + (fy - y1) * uy
        cell = math.floor(s_val / _GRID_H)
        for dc in (-1, 0, 1):
            for prev_pt, pfx, pfy in grid_1d.get(cell + dc, ()):
                if (
                    abs(fx - pfx) < 1e-9
                    and abs(fy - pfy) < 1e-9
                    and zero_test(pt.x - prev_pt.x)
                    and zero_test(pt.y - prev_pt.y)
                ):
                    return
        pt_set.add(pt)
        pts_with_xy.append((pt, fx, fy))
        grid_1d.setdefault(cell, []).append((pt, fx, fy))

    try:
        # Intersect with all other lines
        for j, line_j in enumerate(_W_LINES):
            if j == line_idx:
                continue
            ua2, ub2, _ = _W_LINE_SIGS[j]
            if abs(ua * ub2 - ub * ua2) < 1e-12:
                continue
            for pt in intersect_2d(line_i, line_j):
                _add_pt(pt)

        # Intersect with all circles (numeric distance pre-filter)
        for j, circ_j in enumerate(_W_CIRCLES):
            cx, cy, r = _W_CIRCLE_SIGS[j]
            if abs(ua * cx + ub * cy + uc) > r + 1e-6:
                continue
            for pt in intersect_2d(line_i, circ_j):
                _add_pt(pt)

        pts_with_xy.sort(key=lambda item: (item[1], item[2]))
        sorted_pts = [item[0] for item in pts_with_xy]
        xy_lookup = {item[0]: (round(item[1], 12), round(item[2], 12)) for item in pts_with_xy}

        signal.alarm(_W_LINE_TIMEOUT_S)
        secs = find_golden_sections_in_points(sorted_pts, use_pool=False)
        signal.alarm(0)

        tree = find_chains_in_sections(secs)
        chains = unpack_chains(tree)
        chain_hist: dict[int, int] = {}
        best_chain_pts: list[list[float]] = []
        max_chain = 0
        for ch in chains:
            clen = len(ch.sections)
            chain_hist[clen] = chain_hist.get(clen, 0) + 1
            if clen > max_chain:
                max_chain = clen
                c_pts = [
                    ch.sections[0].points[0],
                    ch.sections[0].points[1],
                    ch.sections[0].points[2],
                ]
                for s in ch.sections[1:]:
                    c_pts.append(s.points[2])
                best_chain_pts = [list(xy_lookup[p]) for p in c_pts if p in xy_lookup]

        res = {
            "line_idx": line_idx,
            "n_pts": len(sorted_pts),
            "n_sections": len(secs),
            "n_chains": len(chains),
            "max_chain": max_chain,
            "chain_hist": chain_hist,
            "best_chain_pts": best_chain_pts,
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "timed_out": False,
        }
    except _LineTimeout:
        signal.alarm(0)
        res = {
            "line_idx": line_idx,
            "n_pts": len(pts_with_xy),
            "n_sections": 0,
            "n_chains": 0,
            "max_chain": 0,
            "chain_hist": {},
            "best_chain_pts": [],
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "timed_out": True,
        }

    sp.core.cache.clear_cache()
    return res


def run_parallel_l3_golden(
    *,
    workers: int = 4,
    limit_lines: int | None = None,
    line_timeout_s: int = 120,
    output_dir: Path | None = None,
) -> Path:
    """Generate Level 3 structures and scan lines in parallel for golden sections."""
    repo_root = Path(__file__).resolve().parents[3]
    cache_path = repo_root / "runs" / "l3_structures.json"

    t0 = time.perf_counter()
    lines, circles = generate_l3_structures(cache_path=cache_path)
    print(
        f"Stage 1 ready in {time.perf_counter() - t0:.2f}s: "
        f"{len(lines)} unique lines, {len(circles)} unique circles",
        flush=True,
    )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = output_dir or (repo_root / "runs" / f"l3_parallel_{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "line_results.jsonl"

    done_indices: set[int] = set()
    total_secs = 0
    total_timeouts = 0
    best_chain = 0
    if jsonl_path.exists():
        for line_str in jsonl_path.read_text(encoding="utf-8").splitlines():
            if not line_str.strip():
                continue
            rec = json.loads(line_str)
            done_indices.add(int(rec["line_idx"]))
            total_secs += int(rec["n_sections"])
            if rec.get("timed_out"):
                total_timeouts += 1
            best_chain = max(best_chain, int(rec["max_chain"]))

    n_lines = len(lines) if limit_lines is None else min(limit_lines, len(lines))
    pending = [i for i in range(n_lines) if i not in done_indices]
    lines_srepr = [sp.srepr(ln) for ln in lines]
    circles_srepr = [sp.srepr(c) for c in circles]
    del lines, circles
    sp.core.cache.clear_cache()

    print(
        f"Scanning {len(pending)}/{n_lines} lines ({len(done_indices)} already done) "
        f"with {workers} workers -> {jsonl_path}",
        flush=True,
    )

    t1 = time.perf_counter()
    with (
        Pool(
            processes=workers,
            initializer=_worker_init,
            initargs=(lines_srepr, circles_srepr, line_timeout_s),
        ) as pool,
        jsonl_path.open("a", encoding="utf-8") as fh,
    ):
        for done_offset, res in enumerate(pool.imap_unordered(_scan_one_line, pending), 1):
            fh.write(json.dumps(res) + "\n")
            fh.flush()
            total_secs += int(res["n_sections"])
            if res["timed_out"]:
                total_timeouts += 1
            best_chain = max(best_chain, int(res["max_chain"]))
            done_total = len(done_indices) + done_offset
            if done_total <= 10 or done_total % 25 == 0 or done_offset == len(pending):
                print(
                    f"  [{done_total}/{n_lines}] line={res['line_idx']} | "
                    f"pts={res['n_pts']}, secs={res['n_sections']}, "
                    f"max_chain={res['max_chain']} ({res['elapsed_s']}s) | "
                    f"cum_secs={total_secs}, timeouts={total_timeouts}, best_chain={best_chain}",
                    flush=True,
                )

    print(
        f"\nParallel scan complete in {time.perf_counter() - t1:.2f}s: "
        f"lines={n_lines}, total_sections={total_secs}, "
        f"best_chain={best_chain}, timeouts={total_timeouts}",
        flush=True,
    )
    return jsonl_path
