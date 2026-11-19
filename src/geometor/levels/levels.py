"""Core level construction and pair-ordering strategies."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations

import sympy as sp
import sympy.geometry as spg
from geometor.model import Model


def fundamental(model: Model, pt_1: spg.Point, pt_2: spg.Point) -> None:
    """Construct the line and both circles determined by ``pt_1`` and ``pt_2``."""
    model.construct_line(pt_1, pt_2)
    model.construct_circle(pt_1, pt_2)
    model.construct_circle(pt_2, pt_1)


def order_pairs_round_robin(
    pts: Sequence[spg.Point],
) -> list[tuple[spg.Point, spg.Point]]:
    """Return all ``C(N, 2)`` pairs in round-robin stride order.

    Stride ``k = 1`` emits ``(P0, P1), (P1, P2), ...``, touching every point
    within the first ``N`` pairs before advancing to stride ``k = 2``.
    """
    n = len(pts)
    pairs: list[tuple[spg.Point, spg.Point]] = []
    for k in range(1, n // 2 + 1):
        limit = n if (n % 2 == 1 or k < n // 2) else n // 2
        for i in range(limit):
            pairs.append((pts[i], pts[(i + k) % n]))
    return pairs


def order_pairs_symmetric(
    pts: Sequence[spg.Point],
) -> list[tuple[spg.Point, spg.Point]]:
    """Return all ``C(N, 2)`` pairs ordered radially outward from the origin."""
    xy = {p: (float(p.x.evalf()), float(p.y.evalf())) for p in pts}
    r2 = {p: round(xy[p][0] ** 2 + xy[p][1] ** 2, 9) for p in pts}

    def _pair_key(pair: tuple[spg.Point, spg.Point]) -> tuple[float, float, float]:
        p1, p2 = pair
        x1, y1 = xy[p1]
        x2, y2 = xy[p2]
        d2 = round((x2 - x1) ** 2 + (y2 - y1) ** 2, 9)
        return (max(r2[p1], r2[p2]), round(r2[p1] + r2[p2], 9), d2)

    return sorted(combinations(pts, 2), key=_pair_key)


def build_level(
    level: int,
    *,
    enable_logging: bool = False,
    use_point_subscript: bool = True,
) -> Model:
    """Build an exact symbolic level model (``level >= 0``)."""
    model = Model(
        f"level-{level}",
        use_point_subscript=use_point_subscript,
        enable_logging=enable_logging,
    )
    model.set_point(sp.Rational(-1, 2), 0, classes=["given"])
    model.set_point(sp.Rational(1, 2), 0, classes=["given"])

    for _ in range(level):
        for p1, p2 in combinations(model.points, 2):
            fundamental(model, p1, p2)

    return model
