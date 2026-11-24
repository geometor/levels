"""Export square, title-free SVGs and switcher manifests for the Levels website."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from geometor.levels.svg_export import (  # noqa: E402
    export_level1_svg,
    export_level2_svgs,
    export_level3_ancestor_svgs,
)


def main() -> None:
    """Generate Level 1, Level 2, and Level 3 SVGs and manifests in docsrc/_static/svg/."""
    repo_root = Path(__file__).resolve().parents[1]
    svg_root = repo_root / "docsrc" / "_static" / "svg"
    svg_root.mkdir(parents=True, exist_ok=True)

    l1_path = export_level1_svg(svg_root / "l1.svg")
    print(f"Exported Level 1 SVG: {l1_path}")

    l2_dir = svg_root / "l2"
    l2_manifest = export_level2_svgs(l2_dir)
    (l2_dir / "manifest.json").write_text(
        json.dumps(l2_manifest, indent=2),
        encoding="utf-8",
    )
    print(f"Exported {len(l2_manifest)} Level 2 SVGs to {l2_dir}")

    ckpt_path = (
        repo_root
        / "runs"
        / "round_robin_20261120-181437"
        / "level-3-round_robin-checkpoint.json"
    )
    l3_dir = svg_root / "l3"
    l3_manifest = export_level3_ancestor_svgs(ckpt_path, l3_dir, count=24)
    (l3_dir / "manifest.json").write_text(
        json.dumps(l3_manifest, indent=2),
        encoding="utf-8",
    )
    print(f"Exported {len(l3_manifest)} Level 3 SVGs to {l3_dir}")


if __name__ == "__main__":
    main()
