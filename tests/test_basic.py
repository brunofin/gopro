"""Basic tests for the GoPro webcam controller."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from gopro_controller.models.webcam_config import WebcamConfig, Resolution, FieldOfView


class TestWebcamConfig:
    """Test webcam configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = WebcamConfig()
        
        assert config.resolution == Resolution.RES_720P
        assert config.field_of_view == FieldOfView.NARROW
        assert config.disable_hypersmooth is True
        assert config.disable_horizon_leveling is True
    
    def test_low_latency_preset(self):
        """Test low latency preset."""
        config = WebcamConfig.low_latency_preset()
        
        assert config.resolution == Resolution.RES_480P
        assert config.field_of_view == FieldOfView.NARROW
        assert config.use_preview_stream is True
        assert config.disable_hypersmooth is True
    
    def test_quality_preset(self):
        """Test quality preset."""
        config = WebcamConfig.quality_preset()
        
        assert config.resolution == Resolution.RES_1080P
        assert config.field_of_view == FieldOfView.LINEAR
        assert config.disable_hypersmooth is True  # Still disabled for latency
    
    def test_to_gopro_settings(self):
        """Test conversion to GoPro settings."""
        config = WebcamConfig.balanced_preset()
        settings = config.to_gopro_settings()
        
        # Check key settings are present
        assert "resolution" in settings
        assert 43 in settings  # Digital lens
        assert 135 in settings  # HyperSmooth
        assert 150 in settings  # Horizon leveling
        assert 173 in settings  # Video performance mode
        assert 182 in settings  # Bit rate


# Additional test stubs for future implementation
class TestGoProController:
    """Test GoPro controller."""
    
    @pytest.mark.asyncio
    async def test_connection_type_initialization(self):
        """Test controller initialization with different connection types."""
        # This would require mocking the actual GoPro connection
        # For now, just test that we can create the controller
        from gopro_controller.models.gopro_controller import GoProController, ConnectionType
        
        controller = GoProController(connection_type=ConnectionType.WIRED)
        assert controller.connection_type == ConnectionType.WIRED
        assert not controller.is_connected


class TestV4L2Consumer:
    """Test V4L2 stream consumer."""
    
    def test_config_creation(self):
        """Test V4L2 consumer configuration."""
        from gopro_controller.stream_consumers.v4l2_consumer import V4L2ConsumerConfig
        
        config = V4L2ConsumerConfig(
            stream_url="udp://@:8554",
            device_path="/dev/video42"
        )
        
        assert config.stream_url == "udp://@:8554"
        assert config.device_path == "/dev/video42"
        assert config.device_label == "GoPro Webcam"