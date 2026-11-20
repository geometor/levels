"""Track Level 2 point-birth golden impact and render ancestor-isolated cycle."""

from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import sympy as sp
from geometor.divine.golden import GoldenFieldTracker
from geometor.model import Model

from geometor.levels import fundamental
from geometor.levels.visualize import render_ancestor_cycle_gif


def main() -> None:
    """Build Level 2 with GoldenFieldTracker, print impact ranking, and render GIF."""
    model = Model("level-2-impact", use_point_subscript=True, enable_logging=False)
    tracker = GoldenFieldTracker(tag_model=True).attach(model)

    pt_a = model.set_point(sp.Rational(-1, 2), 0, classes=["given"])
    pt_b = model.set_point(sp.Rational(1, 2), 0, classes=["given"])
    fundamental(model, pt_a, pt_b)
    for p1, p2 in combinations(model.points, 2):
        fundamental(model, p1, p2)
    tracker.sync(model)

    print(
        f"Level 2: {len(model.points)} pts, {len(model.lines)} lines, "
        f"{len(model.circles)} circles -> {len(tracker.sections)} explicit-line golden sections"
    )
    ranked = sorted(
        tracker.impact_by_point.items(),
        key=lambda kv: len(kv[1]),
        reverse=True,
    )
    print("\nTop point-birth golden impacts:")
    for pt, impacts in ranked[:15]:
        roles = ", ".join(imp.role for imp in impacts)
        print(f"  {model[pt].ID:>4}: +{len(impacts)} sections ({roles})")

    out_gif = Path(__file__).resolve().parents[1] / "runs" / "level2_ancestor_cycle.gif"
    render_ancestor_cycle_gif(model, tracker.sections, out_gif)
    print(f"\nSaved {out_gif}")


if __name__ == "__main__":
    main()
