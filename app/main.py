# Shim module to expose backend FastAPI app at top-level import path.
# This allows `from app.main import ...` to work alongside tests that modify sys.path.
from .backend.app.main import *  # noqa: F401,F403
