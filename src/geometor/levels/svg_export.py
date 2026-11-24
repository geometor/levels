"""Export title-free, square (1:1) vector SVGs for Levels 1–3 and interactive switchers."""

from __future__ import annotations

import json
import math
from html import escape
from itertools import combinations
from pathlib import Path

import numpy as np
import sympy as sp
from geometor.divine.golden import GoldenFieldTracker, find_golden_sections_in_model
from geometor.model import Model

from .levels import fundamental


def _mul(*args: float) -> float:
    out = 1.0
    for a in args:
        out *= a
    return out


_FLOAT_ENV = {
    "Point2D": lambda x, y: (float(x), float(y)),
    "Add": lambda *args: sum(args),
    "Mul": _mul,
    "Pow": lambda a, b: a**b,
    "Rational": lambda a, b: a / b,
    "Integer": float,
    "Float": float,
    "sqrt": math.sqrt,
    "GoldenRatio": (1.0 + math.sqrt(5.0)) / 2.0,
    "S": type("S", (), {"Half": 0.5, "One": 1.0, "Zero": 0.0, "NegativeOne": -1.0})(),
}


def _eval_point_float(sym_str: str) -> tuple[float, float]:
    res = eval(sym_str, {"__builtins__": {}}, _FLOAT_ENV)  # noqa: S307
    return (float(res[0]), float(res[1]))


def _render_square_svg(
    *,
    pts_xy: dict[str, tuple[float, float]],
    lines_xy: dict[str, tuple[tuple[float, float], tuple[float, float]]],
    circles_xy: dict[str, tuple[tuple[float, float], float]],
    anc_keys: set[str],
    highlight_segments: list[tuple[tuple[float, float], tuple[float, float], str]],
    highlight_pts: list[tuple[str, tuple[float, float]]],
    out_path: Path,
    size: int = 1000,
) -> None:
    """Render a pure, title-free square SVG fitting all highlighted points and ancestor circles."""
    xs = [xy[0] for _, xy in highlight_pts]
    ys = [xy[1] for _, xy in highlight_pts]
    for k in anc_keys:
        if k in pts_xy:
            px, py = pts_xy[k]
            xs.append(px)
            ys.append(py)
        if k in circles_xy:
            (ccx, ccy), cr = circles_xy[k]
            xs.extend([ccx - cr, ccx + cr])
            ys.extend([ccy - cr, ccy + cr])

    if not xs or not ys:
        xs, ys = [-1.5, 1.5], [-1.5, 1.5]

    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    half = max(max(xs) - min(xs), max(ys) - min(ys), 1.4) * 0.58
    scale = (size / 2.0) / half

    def tx(x: float) -> float:
        return (x - cx) * scale + size / 2.0

    def ty(y: float) -> float:
        return size / 2.0 - (y - cy) * scale

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="100%" height="100%" class="levels-svg">',
        f'<defs><clipPath id="sq-clip"><rect x="0" y="0" width="{size}" height="{size}"/>'
        "</clipPath></defs>",
        f'<rect x="0" y="0" width="{size}" height="{size}" fill="#0b0e14"/>',
        '<g clip-path="url(#sq-clip)">',
    ]

    span = half * 2.5

    def _line_endpoints(p1: tuple[float, float], p2: tuple[float, float]) -> str | None:
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        norm = math.hypot(dx, dy)
        if norm == 0.0:
            return None
        ux, uy = dx / norm, dy / norm
        mx, my = (p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0
        return (
            f'x1="{tx(mx - ux * span):.2f}" y1="{ty(my - uy * span):.2f}" '
            f'x2="{tx(mx + ux * span):.2f}" y2="{ty(my + uy * span):.2f}"'
        )

    # 1. Dimmed background lines & circles
    for k, (lp1, lp2) in lines_xy.items():
        if k not in anc_keys:
            coords_attr = _line_endpoints(lp1, lp2)
            if coords_attr:
                parts.append(
                    f'<line {coords_attr} stroke="#1a2332" '
                    f'stroke-width="1.0" stroke-opacity="0.45"/>'
                )
    for k, (center, r) in circles_xy.items():
        if k not in anc_keys:
            parts.append(
                f'<circle cx="{tx(center[0]):.2f}" cy="{ty(center[1]):.2f}" '
                f'r="{r * scale:.2f}" fill="none" stroke="#161f2c" '
                'stroke-width="1.0" stroke-opacity="0.45"/>'
            )

    # 2. Solid cyan ancestor lines & solid magenta ancestor circles
    for k, (lp1, lp2) in lines_xy.items():
        if k in anc_keys:
            coords_attr = _line_endpoints(lp1, lp2)
            if coords_attr:
                parts.append(
                    f'<line {coords_attr} stroke="#4cc9f0" stroke-width="2.2" '
                    'stroke-linecap="round"/>'
                )
    for k, (center, r) in circles_xy.items():
        if k in anc_keys:
            parts.append(
                f'<circle cx="{tx(center[0]):.2f}" cy="{ty(center[1]):.2f}" '
                f'r="{r * scale:.2f}" fill="none" stroke="#ff4dff" stroke-width="2.2"/>'
            )

    # 3. Ancestor defining points
    hl_ids = {pid for pid, _ in highlight_pts}
    for k in sorted(anc_keys):
        if k in pts_xy and k not in hl_ids:
            px, py = pts_xy[k]
            sx, sy = tx(px), ty(py)
            if 0 <= sx <= size and 0 <= sy <= size:
                parts.append(
                    f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="5.5" '
                    'fill="#4cc9f0" stroke="#f8f9fa" stroke-width="1.4"/>'
                )
                lbl_y = sy + 20 if sy < size - 28 else sy - 12
                parts.append(
                    f'<text x="{sx:.2f}" y="{lbl_y:.2f}" fill="#4cc9f0" '
                    'font-family="monospace" font-size="16" font-weight="bold" '
                    f'text-anchor="middle">{escape(k)}</text>'
                )

    # 4. Highlighted golden segments & points
    for p1, p2, color in highlight_segments:
        parts.append(
            f'<line x1="{tx(p1[0]):.2f}" y1="{ty(p1[1]):.2f}" '
            f'x2="{tx(p2[0]):.2f}" y2="{ty(p2[1]):.2f}" '
            f'stroke="{color}" stroke-width="5.5" stroke-linecap="round"/>'
        )
    for pid, (px, py) in highlight_pts:
        sx, sy = tx(px), ty(py)
        parts.append(
            f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="8" '
            'fill="#f8f9fa" stroke="#ffd166" stroke-width="3"/>'
        )
        lbl_y = sy - 14 if sy > 36 else sy + 26
        parts.append(
            f'<text x="{sx:.2f}" y="{lbl_y:.2f}" fill="#f8f9fa" '
            'font-family="monospace" font-size="20" font-weight="bold" '
            f'text-anchor="middle">{escape(pid)}</text>'
        )

    parts.append("</g></svg>")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")


def export_level1_svg(out_path: Path) -> Path:
    """Export a clean square SVG for Level 1 (vesica pisces)."""
    m = Model("level-1", use_point_subscript=True, enable_logging=False)
    pt_a = m.set_point(sp.Rational(-1, 2), 0, classes=["given"])
    pt_b = m.set_point(sp.Rational(1, 2), 0, classes=["given"])
    fundamental(m, pt_a, pt_b)

    pts_xy = {m[p].ID: (float(p.x.evalf()), float(p.y.evalf())) for p in m.points}
    lines_xy = {
        m[ln].ID: (
            (float(ln.p1.x.evalf()), float(ln.p1.y.evalf())),
            (float(ln.p2.x.evalf()), float(ln.p2.y.evalf())),
        )
        for ln in m.lines
    }
    circles_xy = {
        m[c].ID: (
            (float(c.center.x.evalf()), float(c.center.y.evalf())),
            float(c.radius.evalf()),
        )
        for c in m.circles
    }
    anc = set(pts_xy.keys()) | set(lines_xy.keys()) | set(circles_xy.keys())
    _render_square_svg(
        pts_xy=pts_xy,
        lines_xy=lines_xy,
        circles_xy=circles_xy,
        anc_keys=anc,
        highlight_segments=[],
        highlight_pts=[(pid, pts_xy[pid]) for pid in ("A", "B")],
        out_path=out_path,
    )
    return out_path


def export_level2_svgs(out_dir: Path) -> list[dict[str, str]]:
    """Export square SVGs for Level 2 overview and each of its 34 explicit-line golden sections."""
    m = Model("level-2", use_point_subscript=True, enable_logging=False)
    tracker = GoldenFieldTracker(tag_model=True).attach(m)
    pt_a = m.set_point(sp.Rational(-1, 2), 0, classes=["given"])
    pt_b = m.set_point(sp.Rational(1, 2), 0, classes=["given"])
    fundamental(m, pt_a, pt_b)
    for p1, p2 in combinations(m.points, 2):
        fundamental(m, p1, p2)
    tracker.sync(m)

    all_secs, _ = find_golden_sections_in_model(m, include_collinear=True)
    pts_xy = {m[p].ID: (float(p.x.evalf()), float(p.y.evalf())) for p in m.points}
    lines_xy = {
        m[ln].ID: (
            (float(ln.p1.x.evalf()), float(ln.p1.y.evalf())),
            (float(ln.p2.x.evalf()), float(ln.p2.y.evalf())),
        )
        for ln in m.lines
    }
    circles_xy = {
        m[c].ID: (
            (float(c.center.x.evalf()), float(c.center.y.evalf())),
            float(c.radius.evalf()),
        )
        for c in m.circles
    }

    # Overview SVG of all 50 golden sections
    ov_segs = [
        (pts_xy[m[s.points[0]].ID], pts_xy[m[s.points[2]].ID], "#ffd166")
        for s in all_secs
    ]
    _render_square_svg(
        pts_xy=pts_xy,
        lines_xy=lines_xy,
        circles_xy=circles_xy,
        anc_keys=set(lines_xy.keys()) | set(circles_xy.keys()),
        highlight_segments=ov_segs,
        highlight_pts=[("A", pts_xy["A"]), ("B", pts_xy["B"])],
        out_path=out_dir / "l2_overview.svg",
    )

    items: list[dict[str, str]] = []
    for idx, sec in enumerate(tracker.sections, 1):
        tri = tuple(m[p].ID for p in sec.points)
        anc: set[str] = set()
        stack = list(sec.points)
        visited = set()
        while stack:
            cur = stack.pop()
            if cur in visited or cur not in m:
                continue
            visited.add(cur)
            anc.add(m[cur].ID)
            if "given" in m[cur].classes:
                continue
            for par in list(m[cur].parents.keys())[:2]:
                if par not in visited:
                    stack.append(par)

        p0, p1, p2 = (pts_xy[k] for k in tri)
        q1 = (p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2
        q2 = (p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2
        c1, c2 = ("#ffd166", "#f77f00") if q1 >= q2 else ("#f77f00", "#ffd166")
        fname = f"l2_{idx:02d}.svg"
        _render_square_svg(
            pts_xy=pts_xy,
            lines_xy=lines_xy,
            circles_xy=circles_xy,
            anc_keys=anc,
            highlight_segments=[(p0, p1, c1), (p1, p2, c2)],
            highlight_pts=[(k, pts_xy[k]) for k in tri],
            out_path=out_dir / fname,
        )
        items.append({"src": fname, "caption": f"Section {idx}/34: {tri[0]} — {tri[1]} — {tri[2]}"})
    return items


def export_level3_ancestor_svgs(
    ckpt_path: Path,
    out_dir: Path,
    *,
    count: int = 24,
) -> list[dict[str, str]]:
    """Export ``count`` square SVGs of Level 3 golden sections with full recursive ancestors."""
    data = json.loads(ckpt_path.read_text(encoding="utf-8"))
    elements = data["elements"]
    del data

    pts_xy: dict[str, tuple[float, float]] = {}
    lines_xy: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {}
    circles_xy: dict[str, tuple[tuple[float, float], float]] = {}
    parents_map: dict[str, list[str]] = {}
    given_keys: set[str] = set()
    golden_triples: list[tuple[str, str, str]] = []

    for k, v in elements.items():
        parents_map[k] = list(v.get("parents", []))
        if "given" in v.get("classes", []):
            given_keys.add(k)
        sym = v.get("sympy_obj", "")
        if sym.startswith("Point2D("):
            pts_xy[k] = _eval_point_float(sym)
        elif sym.startswith("Line2D("):
            ln = sp.sympify(sym)
            lines_xy[k] = (
                (float(ln.p1.x.evalf()), float(ln.p1.y.evalf())),
                (float(ln.p2.x.evalf()), float(ln.p2.y.evalf())),
            )
        elif sym.startswith("Circle("):
            c = sp.sympify(sym)
            circles_xy[k] = (
                (float(c.center.x.evalf()), float(c.center.y.evalf())),
                float(c.radius.evalf()),
            )
        elif "golden" in v.get("classes", []):
            pts_list = v.get("pts", [])
            if len(pts_list) == 3:
                golden_triples.append((pts_list[0], pts_list[1], pts_list[2]))

    del elements
    sp.core.cache.clear_cache()

    def _get_anc(keys: tuple[str, str, str]) -> set[str]:
        visited: set[str] = set()
        stack = list(keys)
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            if cur in given_keys:
                continue
            for p in parents_map.get(cur, ())[:2]:
                if p not in visited:
                    stack.append(p)
        return visited

    annotated: list[tuple[tuple[str, str, str], set[str], int]] = []
    for tri in golden_triples:
        if all(p in pts_xy for p in tri):
            anc = _get_anc(tri)
            n_structs = sum(1 for a in anc if a in lines_xy or a in circles_xy)
            annotated.append((tri, anc, n_structs))
    annotated.sort(key=lambda item: item[2])

    indices = np.linspace(0, len(annotated) - 1, count, dtype=int)
    items: list[dict[str, str]] = []
    for step, idx in enumerate(indices, 1):
        tri, anc, n_structs = annotated[int(idx)]
        p0, p1, p2 = (pts_xy[k] for k in tri)
        q1 = (p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2
        q2 = (p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2
        c1, c2 = ("#ffd166", "#f77f00") if q1 >= q2 else ("#f77f00", "#ffd166")
        fname = f"l3_{step:02d}.svg"
        _render_square_svg(
            pts_xy=pts_xy,
            lines_xy=lines_xy,
            circles_xy=circles_xy,
            anc_keys=anc,
            highlight_segments=[(p0, p1, c1), (p1, p2, c2)],
            highlight_pts=[(k, pts_xy[k]) for k in tri],
            out_path=out_dir / fname,
        )
        items.append(
            {
                "src": fname,
                "caption": (
                    f"{step}/{count}: {tri[0]} — {tri[1]} — {tri[2]} "
                    f"({n_structs} ancestor lines/circles)"
                ),
            }
        )
    return items
