"""Visualization helpers for level constructions and ancestor-isolated golden sections."""

from __future__ import annotations

import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl_geometor")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sympy.geometry as spg
from geometor.model import Model
from geometor.model.sections import Section
from matplotlib.patches import Circle as MplCircle
from PIL import Image

BG = "#0b0e14"
DIM_LINE = "#1e2736"
DIM_CIRCLE = "#1a222f"
DIM_PT = "#2b384c"
CYAN = "#4cc9f0"
MAGENTA = "#ff4dff"
GOLD = "#ffd166"
AMBER = "#f77f00"
WHITE = "#f8f9fa"


def _draw_line_clipped(
    ax: plt.Axes,
    p1: tuple[float, float],
    p2: tuple[float, float],
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    **kwargs: object,
) -> None:
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy)
    if norm == 0.0:
        return
    ux, uy = dx / norm, dy / norm
    span = max(xlim[1] - xlim[0], ylim[1] - ylim[0]) * 2.0
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    ax.plot([mx - ux * span, mx + ux * span], [my - uy * span, my + uy * span], **kwargs)


def section_ancestors(model: Model, section: Section) -> set[spg.GeometryEntity]:
    """Return the union of all causal DAG ancestors for the 3 points of ``section``."""
    anc: set[spg.GeometryEntity] = set(section.points)
    for pt in section.points:
        anc.update(model.get_ancestors(pt).keys())
    return anc


def render_ancestor_cycle_gif(
    model: Model,
    sections: list[Section],
    out_gif: Path,
    *,
    xlim: tuple[float, float] = (-3.4, 3.4),
    ylim: tuple[float, float] = (-1.9125, 1.9125),
    duration_ms: int = 550,
    subtitle_fn: object | None = None,
) -> Path:
    """Render an animated GIF graying out non-ancestors for each golden section."""
    pts_xy = {p: (float(p.x.evalf()), float(p.y.evalf())) for p in model.points}
    lines_xy = {
        ln: (
            (float(ln.p1.x.evalf()), float(ln.p1.y.evalf())),
            (float(ln.p2.x.evalf()), float(ln.p2.y.evalf())),
        )
        for ln in model.lines
    }
    circles_xy = {
        c: ((float(c.center.x.evalf()), float(c.center.y.evalf())), float(c.radius.evalf()))
        for c in model.circles
    }

    frames: list[Image.Image] = []
    total = len(sections)

    for idx, sec in enumerate(sections, 1):
        anc = section_ancestors(model, sec)
        fig = plt.figure(figsize=(9.6, 5.4), dpi=120, facecolor=BG)
        ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
        ax.set_facecolor(BG)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.axis("off")

        # 1. Dimmed background field (non-ancestors)
        for ln, (p1, p2) in lines_xy.items():
            if ln not in anc:
                _draw_line_clipped(
                    ax, p1, p2, xlim, ylim, color=DIM_LINE, lw=0.6, alpha=0.35, zorder=1
                )
        for c, (center, r) in circles_xy.items():
            if c not in anc:
                ax.add_patch(
                    MplCircle(
                        center, r, fill=False, edgecolor=DIM_CIRCLE, lw=0.6, alpha=0.35, zorder=1
                    )
                )
        dim_pts = [pts_xy[p] for p in model.points if p not in anc]
        if dim_pts:
            dx_s, dy_s = zip(*dim_pts)
            ax.scatter(dx_s, dy_s, s=7, color=DIM_PT, alpha=0.45, zorder=2)

        # 2. Illuminated causal ancestors
        for ln, (p1, p2) in lines_xy.items():
            if ln in anc:
                _draw_line_clipped(ax, p1, p2, xlim, ylim, color=CYAN, lw=1.5, alpha=1.0, zorder=3)
        for c, (center, r) in circles_xy.items():
            if c in anc:
                ax.add_patch(
                    MplCircle(center, r, fill=False, edgecolor=CYAN, lw=1.5, alpha=1.0, zorder=3)
                )
        anc_pts = [p for p in model.points if p in anc and p not in sec.points]
        if anc_pts:
            ax.scatter(
                [pts_xy[p][0] for p in anc_pts],
                [pts_xy[p][1] for p in anc_pts],
                s=22,
                color=CYAN,
                alpha=0.85,
                zorder=4,
            )

        # 3. Resulting golden section
        p0, p1, p2 = (pts_xy[p] for p in sec.points)
        q1 = (p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2
        q2 = (p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2
        c1, c2 = (GOLD, AMBER) if q1 >= q2 else (AMBER, GOLD)
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=c1, lw=3.2, zorder=5)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=c2, lw=3.2, zorder=5)
        ax.scatter(
            [p0[0], p1[0], p2[0]],
            [p0[1], p1[1], p2[1]],
            s=65,
            color=WHITE,
            edgecolor=GOLD,
            lw=1.8,
            zorder=6,
        )

        ids = [model[p].ID for p in sec.points]
        for pt_xy, lbl in zip((p0, p1, p2), ids):
            y_off = -0.17 if pt_xy[1] > ylim[1] - 0.35 else 0.11
            ax.text(
                pt_xy[0],
                pt_xy[1] + y_off,
                lbl,
                color=WHITE,
                fontsize=10,
                ha="center",
                fontweight="bold",
                fontfamily="monospace",
                clip_on=True,
                zorder=7,
            )

        sub = (
            subtitle_fn(sec, anc)
            if callable(subtitle_fn)
            else f"Section: {ids[0]} — {ids[1]} — {ids[2]}  |  {len(anc)} causal ancestors"
        )
        ax.text(
            0.02,
            0.96,
            f"Golden Section Ancestors {idx}/{total}",
            transform=ax.transAxes,
            color=WHITE,
            fontsize=14,
            fontweight="bold",
            va="top",
            fontfamily="monospace",
            zorder=8,
        )
        ax.text(
            0.02,
            0.91,
            str(sub),
            transform=ax.transAxes,
            color=GOLD,
            fontsize=11,
            va="top",
            fontfamily="monospace",
            zorder=8,
        )

        fig.canvas.draw()
        w, h = fig.canvas.get_width_height()
        buf = np.asarray(fig.canvas.buffer_rgba())
        frames.append(Image.fromarray(buf.reshape(h, w, 4)).convert("RGB"))
        plt.close(fig)

    out_gif.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=duration_ms, loop=0)
    return out_gif
