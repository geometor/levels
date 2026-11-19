# GEOMETOR • `levels`

Exhaustive compass-and-straightedge level constructions and emergent golden sections.

---

## 1. Repository Identity & Archetype

- **Organization**: `geometor` (`GEOMETOR`)
- **Package**: `geometor.levels` (`src/geometor/levels/`)
- **Archetype**: `code`

---

## 2. Architectural & Editorial Mandates

1. **Python 3.13 & Exact Symbolic Standards**:
   - Every Python module begins with a module docstring followed immediately by `from __future__ import annotations`, built-in generic types (`list`, `dict`, `tuple`, `X | Y`), Google-style docstrings, and an explicit `__all__`.
   - Zero `float` or `sympy.Float` approximations in symbolic geometry constructions.
2. **Clean Module & Documentation Separation (`code`)**:
   - Keep core implementation in `src/geometor/levels/`, automated tests in `tests/`, runnable examples in `demos/`, and Sphinx Foundation documentation in `docsrc/`.

---

## 3. Verification Commands (Offline Sandbox Safe)

```bash
uv run --no-sync pytest
ruff check src tests demos
publish build
```
