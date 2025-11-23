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
        # Prevent recursion by checking if we're already setting this attribute
        try:
            setting_flag = object.__getattribute__(self, "_setting_attr")
            if setting_flag:
                # Already in the middle of setting, bypass hooks
                return ModuleType.__setattr__(self, name, value)
        except AttributeError:
            # Flag doesn't exist yet, that's fine
            pass

        # Mark that we're setting an attribute to prevent recursion
        object.__setattr__(self, "_setting_attr", True)
        try:
            # Update shim's namespace first so backend hooks can read the new value
            ModuleType.__setattr__(self, name, value)
            # Then update backend module (triggers hooks like _on_cache_size_updated)
            # Check if backend module has a custom __setattr__ by looking at its class
            backend_class = type(_backend_module)
            if backend_class is not ModuleType and hasattr(backend_class, "__setattr__"):
                # Backend has custom __setattr__ (likely _MainModule), use object methods to avoid recursion
                # Store the value directly in the module's __dict__ to bypass __setattr__
                _backend_module.__dict__[name] = value
                # Manually trigger hooks if needed (for RESULTS_DIR and MAX_CACHE_SIZE)
                if name == "RESULTS_DIR" and hasattr(_backend_module, "_on_results_dir_updated"):
                    _backend_module._on_results_dir_updated(value)
                elif name == "MAX_CACHE_SIZE" and hasattr(_backend_module, "_on_cache_size_updated"):
                    _backend_module._on_cache_size_updated(value)
            else:
                # Backend has no custom __setattr__, safe to use regular setattr
                setattr(_backend_module, name, value)
        finally:
            # Always clear the flag using object.__delattr__ to bypass __setattr__
            try:
                object.__delattr__(self, "_setting_attr")
            except AttributeError:
                pass


_module = sys.modules[__name__]
_module.__class__ = _BackendProxyModule
