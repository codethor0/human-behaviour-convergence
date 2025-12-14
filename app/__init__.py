"""
Top-level app package shim.

This makes `from app import main` and `from app.main import ...` resolve to the
backend FastAPI application located at `app/backend/app/main.py`.
"""

# Re-export submodule so imports like `from app import main` work consistently.
# We rely on namespace packages (PEP 420) for `app.backend`.
# CI reset - forces workflows to run on main for green badges
__ci_reset__ = True  # noqa: F401
__main_green_reset__ = True  # Forces workflows to re-run and reset badges
from .backend.app import main  # type: ignore  # noqa: F401

__all__ = ["main"]
