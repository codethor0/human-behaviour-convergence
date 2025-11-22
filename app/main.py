"""
Shim module to expose backend FastAPI app at top-level import path while
preserving attribute forwarding in both directions.

The tests mutate globals such as `RESULTS_DIR` on `app.main`. A plain star-import
copies the backend symbols but does not propagate attribute reassignment back to
the actual backend module, which breaks those tests. This shim keeps the two
modules in sync by proxying attribute access and mutation.
"""

import sys
from importlib import import_module
from types import ModuleType
from typing import Any

_backend_module = import_module("app.backend.app.main")

# Populate the shim module namespace with backend attributes so tools like
# `dir()` and static analyzers see the expected symbols.
globals().update(vars(_backend_module))


class _BackendProxyModule(ModuleType):
    """Proxy module that forwards attribute access/mutation to backend module."""

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - simple delegation
        return getattr(_backend_module, name)

    def __setattr__(self, name: str, value: Any) -> None:
        # Update shim's namespace first so backend hooks can read the new value
        ModuleType.__setattr__(self, name, value)
        # Then update backend module (triggers hooks like _on_cache_size_updated)
        setattr(_backend_module, name, value)


_module = sys.modules[__name__]
_module.__class__ = _BackendProxyModule
