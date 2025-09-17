"""Model package for GoPro webcam controller."""

try:
    from .gopro_controller import GoProController
    from .webcam_config import WebcamConfig
    
    __all__ = ["GoProController", "WebcamConfig"]
except ImportError:
    # Allow module to be imported even if dependencies aren't installed yet
    __all__ = []