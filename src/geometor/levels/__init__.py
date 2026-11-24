"""Public package interface for ``geometor.levels``."""

from __future__ import annotations

from .app import main, run
from .levels import (
    build_level,
    fundamental,
    order_pairs_round_robin,
    order_pairs_symmetric,
)

__version__ = "0.3.0"

__all__ = [
    "__version__",
    "build_level",
    "fundamental",
    "main",
    "order_pairs_round_robin",
    "order_pairs_symmetric",
    "run",
]
