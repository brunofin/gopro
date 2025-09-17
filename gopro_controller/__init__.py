"""
GoPro Webcam Controller

A Python application for controlling GoPro cameras as webcams with optimized low-latency settings.
"""

__version__ = "0.1.0"
__author__ = "Bruno Fin"
__email__ = "bruno@example.com"

# Import main classes when module is imported
try:
    from .models.gopro_controller import GoProController
    from .models.webcam_config import WebcamConfig
    
    __all__ = ["GoProController", "WebcamConfig"]
except ImportError:
    # Allow module to be imported even if dependencies aren't installed yet
    __all__ = []