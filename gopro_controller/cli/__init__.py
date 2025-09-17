"""CLI package for GoPro webcam controller."""

try:
    from .main import main
    __all__ = ["main"]
except ImportError:
    # Allow module to be imported even if dependencies aren't installed yet
    __all__ = []