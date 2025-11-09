"""
Top-level app package shim.

This makes `from app import main` and `from app.main import ...` resolve to the
backend FastAPI application located at `app/backend/app/main.py`.
"""

# Re-export submodule so imports like `from app import main` work consistently.
# We rely on namespace packages (PEP 420) for `app.backend`.
from .backend.app import main  # type: ignore
