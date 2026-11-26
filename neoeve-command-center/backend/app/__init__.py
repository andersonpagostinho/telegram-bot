"""FastAPI application module."""

def __getattr__(name):
    """Lazy import to avoid loading FastAPI app during testing."""
    if name == "app":
        from .main import app
        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["app"]
