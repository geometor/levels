"""Generate Round-Robin pair SVGs, manifests, and Sphinx collection pages."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from geometor.levels.svg_export import export_round_robin_pairs  # noqa: E402


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main() -> None:
    """Export all Round-Robin pair SVGs/manifests and generate docsrc/round-robin/."""
    repo_root = Path(__file__).resolve().parents[1]
    ckpt_path = (
        repo_root
        / "runs"
        / "round_robin_20261120-181437"
        / "level-3-round_robin-checkpoint.json"
    )
    svg_rr_dir = repo_root / "docsrc" / "_static" / "svg" / "rr"
    summaries = export_round_robin_pairs(ckpt_path, svg_rr_dir)
    print(f"Exported {len(summaries)} round-robin pair summaries to {svg_rr_dir}")

    rr_doc_dir = repo_root / "docsrc" / "round-robin"
    rr_doc_dir.mkdir(parents=True, exist_ok=True)

    table_rows: list[str] = []
    for s in summaries:
        idx = s["pair_idx"]
        pt_p = s["pt_p"]
        pt_q = s["pt_q"]
        folder = f"pair-{idx:02d}-{_slug(pt_p)}-{_slug(pt_q)}"
        pair_dir = rr_doc_dir / folder
        pair_dir.mkdir(parents=True, exist_ok=True)

        title = f"Pair {idx:02d}: {pt_p} — {pt_q}"
        underline = "=" * len(title)

        body = [
            ":type: pair",
            f":order: {idx}",
            "",
            underline,
            title,
            underline,
            "",
            ".. container:: lead",
            "",
            (
                f"   Round-robin step **{idx}/20,503** constructing from points "
                f"**{pt_p}** and **{pt_q}**: "
                f"**+{s['new_pts']}** points, **+{s['new_lines']}** lines, "
                f"**+{s['new_circles']}** circles, and **+{s['new_goldens']}** "
                f"new golden sections."
            ),
            "",
            "Pair Metrics",
            "============",
            "",
            ".. list-table::",
            "   :header-rows: 1",
            "   :widths: 34 33 33",
            "",
            "   * - Metric",
            "     - Added by Pair",
            "     - Cumulative Total",
            "   * - Points",
            f"     - +{s['new_pts']:,}",
            f"     - {s['cum_pts']:,}",
            "   * - Lines",
            f"     - +{s['new_lines']:,}",
            f"     - {s['cum_lines']:,}",
            "   * - Circles",
            f"     - +{s['new_circles']:,}",
            f"     - {s['cum_circles']:,}",
            "   * - Golden Sections",
            f"     - +{s['new_goldens']:,}",
            f"     - {s['cum_goldens']:,}",
            "",
        ]

        if s["has_manifest"]:
            body.extend(
                [
                    "Golden Sections & Ancestors",
                    "===========================",
                    "",
                    (
                        "The first frame overlays all "
                        f"**{s['new_goldens']}** new golden sections introduced by "
                        f"**{pt_p} — {pt_q}** and their recursive ancestors (without labels). "
                        "Press **f** (or click **⛶**) for fullscreen to inspect the "
                        "pair summary, **Count by Size (a)** breakdown, and individual "
                        "golden section algebra."
                    ),
                    "",
                    ".. raw:: html",
                    "",
                    '   <div class="geometor-svg-switcher"',
                    f'        data-manifest="../../_static/svg/rr/pair_{idx:02d}/manifest.json"',
                    f'        data-base="../../_static/svg/rr/pair_{idx:02d}/"',
                    '        data-interval="1500">',
                    "   </div>",
                    "",
                ]
            )
        else:
            body.extend(
                [
                    "Golden Sections",
                    "===============",
                    "",
                    (
                        f"Pair **{pt_p} — {pt_q}** adds **{s['new_lines']}** line(s), "
                        f"**{s['new_circles']}** circle(s), and **{s['new_pts']:,}** "
                        "new intersection points, with **0** new golden sections "
                        "formed at this step."
                    ),
                    "",
                ]
            )

        (pair_dir / "index.rst").write_text("\n".join(body), encoding="utf-8")

        table_rows.extend(
            [
                f"   * - :doc:`Pair {idx:02d} <{folder}/index>`",
                f"     - {pt_p} — {pt_q}",
                f"     - +{s['new_pts']:,}",
                f"     - +{s['new_lines']}",
                f"     - +{s['new_circles']}",
                f"     - +{s['new_goldens']:,}",
                f"     - {s['cum_goldens']:,}",
            ]
        )

    index_lines = [
        ":type: book",
        ":navigation: header",
        ":order: 2",
        ":nav_title: Round Robin",
        ":layout: book",
        "",
        "=================",
        "Round Robin Pairs",
        "=================",
        "",
        ".. container:: lead",
        "",
        (
            "   Step-by-step progression through the **65** active Level 3 round-robin "
            "pairs (**Pair 06: F — G** through **Pair 70: R3 — S3**), tracking every "
            "newly introduced golden section, its recursive ancestors, and its scale "
            "distribution."
        ),
        "",
        "Pairs Summary",
        "=============",
        "",
        ".. list-table:: Round-Robin Pairs 06–70",
        "   :header-rows: 1",
        "   :widths: 14 16 14 12 12 16 16",
        "",
        "   * - Pair",
        "     - Points",
        "     - +Points",
        "     - +Lines",
        "     - +Circles",
        "     - +Goldens",
        "     - Total Goldens",
        *table_rows,
        "",
        "Pairs Catalog",
        "=============",
        "",
        ".. collection::",
        "   :type: pair",
        "   :sort: order",
        "",
    ]
    (rr_doc_dir / "index.rst").write_text("\n".join(index_lines), encoding="utf-8")
    print(f"Generated {len(summaries)} pair pages in {rr_doc_dir}")


if __name__ == "__main__":
    main()
