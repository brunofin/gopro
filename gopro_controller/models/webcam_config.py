"""
Webcam configuration model for optimal low-latency streaming.

Based on research findings for minimizing GoPro webcam latency.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Resolution(str, Enum):
    """Supported webcam resolutions."""
    
    RES_480P = "480p"
    RES_720P = "720p"
    RES_1080P = "1080p"


class FieldOfView(str, Enum):
    """Digital lens/field of view options."""
    
    WIDE = "wide"
    NARROW = "narrow"
    SUPERVIEW = "superview"
    LINEAR = "linear"


class BitRate(str, Enum):
    """Video bit rate options."""
    
    STANDARD = "standard"
    HIGH = "high"


class StreamProtocol(str, Enum):
    """Streaming protocol options."""
    
    UDP = "udp"
    RTSP = "rtsp"


class WebcamConfig(BaseModel):
    """
    Configuration for GoPro webcam with optimized low-latency settings.
    
    Default values are optimized for minimum latency based on research:
    - Narrow FOV reduces processing
    - 720p balances quality and performance
    - Standard bitrate reduces encoding time
    - UDP protocol for lowest latency
    """
    
    # Core webcam settings
    resolution: Resolution = Field(
        default=Resolution.RES_720P,
        description="Webcam resolution - 720p recommended for latency balance"
    )
    
    field_of_view: FieldOfView = Field(
        default=FieldOfView.NARROW,
        description="Digital lens setting - narrow reduces processing overhead"
    )
    
    bit_rate: BitRate = Field(
        default=BitRate.STANDARD,
        description="Video bit rate - standard reduces encoding latency"
    )
    
    protocol: StreamProtocol = Field(
        default=StreamProtocol.UDP,
        description="Streaming protocol - UDP for minimum latency"
    )
    
    # Advanced settings for latency optimization
    disable_hypersmooth: bool = Field(
        default=True,
        description="Disable HyperSmooth stabilization to reduce latency by ~1000ms"
    )
    
    disable_horizon_leveling: bool = Field(
        default=True,
        description="Disable horizon leveling for reduced processing"
    )
    
    max_video_performance: bool = Field(
        default=True,
        description="Enable maximum video performance mode"
    )
    
    # Network settings
    udp_port: int = Field(
        default=8554,
        description="UDP port for streaming"
    )
    
    # Optional preview stream settings
    use_preview_stream: bool = Field(
        default=False,
        description="Use preview stream instead of webcam for even lower latency"
    )
    
    preview_resolution: Optional[Resolution] = Field(
        default=Resolution.RES_480P,
        description="Preview stream resolution when use_preview_stream is True"
    )
    
    def to_gopro_settings(self) -> dict:
        """
        Convert configuration to GoPro API settings dictionary.
        
        Returns:
            Dictionary mapping GoPro setting IDs to values
        """
        settings = {}
        
        # Resolution mapping (webcam endpoint parameter)
        resolution_map = {
            Resolution.RES_480P: 4,
            Resolution.RES_720P: 7,
            Resolution.RES_1080P: 12,
        }
        
        # FOV mapping (setting 43)
        fov_map = {
            FieldOfView.WIDE: 0,
            FieldOfView.NARROW: 2,
            FieldOfView.SUPERVIEW: 3,
            FieldOfView.LINEAR: 4,
        }
        
        # Bit rate mapping (setting 182)
        bitrate_map = {
            BitRate.STANDARD: 0,
            BitRate.HIGH: 1,
        }
        
        # Core settings
        settings["resolution"] = resolution_map[self.resolution]
        settings[43] = fov_map[self.field_of_view]  # Digital lens
        settings[182] = bitrate_map[self.bit_rate]  # Video bit rate
        
        # Latency optimization settings
        if self.disable_hypersmooth:
            settings[135] = 0  # HyperSmooth off
            
        if self.disable_horizon_leveling:
            settings[150] = 0  # Horizon level off
            
        if self.max_video_performance:
            settings[173] = 0  # Video performance mode - maximum
            
        return settings
    
    @classmethod
    def low_latency_preset(cls) -> "WebcamConfig":
        """
        Create a preset optimized for absolute minimum latency.
        
        Uses preview stream at 480p with all processing disabled.
        """
        return cls(
            resolution=Resolution.RES_480P,
            field_of_view=FieldOfView.NARROW,
            bit_rate=BitRate.STANDARD,
            protocol=StreamProtocol.UDP,
            disable_hypersmooth=True,
            disable_horizon_leveling=True,
            max_video_performance=True,
            use_preview_stream=True,
            preview_resolution=Resolution.RES_480P,
        )
    
    @classmethod
    def balanced_preset(cls) -> "WebcamConfig":
        """
        Create a preset balancing quality and latency.
        
        Uses 720p webcam mode with optimizations.
        """
        return cls(
            resolution=Resolution.RES_720P,
            field_of_view=FieldOfView.NARROW,
            bit_rate=BitRate.STANDARD,
            protocol=StreamProtocol.UDP,
            disable_hypersmooth=True,
            disable_horizon_leveling=True,
            max_video_performance=True,
            use_preview_stream=False,
        )
    
    @classmethod
    def quality_preset(cls) -> "WebcamConfig":
        """
        Create a preset optimized for quality with acceptable latency.
        
        Uses 1080p with some optimizations but allows higher quality.
        """
        return cls(
            resolution=Resolution.RES_1080P,
            field_of_view=FieldOfView.LINEAR,
            bit_rate=BitRate.STANDARD,  # Still use standard for latency
            protocol=StreamProtocol.UDP,
            disable_hypersmooth=True,  # Keep this disabled for latency
            disable_horizon_leveling=True,  # Keep this disabled for latency
            max_video_performance=True,
            use_preview_stream=False,
        )