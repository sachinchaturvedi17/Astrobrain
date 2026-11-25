"""AstroMuni (formerly AI Pandit) deterministic core. The LLM never calculates; this package does."""
import sys as _sys

__version__ = "1.4.0"

if "unittest" in _sys.modules and "_pytest.main" not in _sys.modules:
    try:
        import chartkit as _ck  # noqa: F401
    except Exception:
        pass
