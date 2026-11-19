"""Tests for ``geometor.levels``."""

from __future__ import annotations

from geometor.levels import (
    build_level,
    order_pairs_round_robin,
    order_pairs_symmetric,
)


def test_level_1_and_2_counts() -> None:
    """Level 1 and Level 2 produce exact canonical point/line/circle counts."""
    m1 = build_level(1)
    assert len(m1.points) == 6
    assert len(m1.lines) == 1
    assert len(m1.circles) == 2

    m2 = build_level(2)
    assert len(m2.points) == 203
    assert len(m2.lines) == 10
    assert len(m2.circles) == 16


def test_level_3_pair_orderings_complete_and_unique() -> None:
    """Both round-robin and symmetric orderings cover all 20,503 unique pairs."""
    m2 = build_level(2)
    pts = m2.points
    expected = len(pts) * (len(pts) - 1) // 2

    rr = order_pairs_round_robin(pts)
    assert len(rr) == expected
    assert len({frozenset(p) for p in rr}) == expected
    assert rr[0] == (pts[0], pts[1])
    assert rr[1] == (pts[1], pts[2])

    sym = order_pairs_symmetric(pts)
    assert len(sym) == expected
    assert len({frozenset(p) for p in sym}) == expected
