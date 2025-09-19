"""
GoPro controller for webcam functionality.

Manages connection, configuration, and streaming control for GoPro cameras.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from open_gopro import WirelessGoPro, WiredGoPro
from open_gopro.domain.exceptions import GoProNotOpened, GoProError
from open_gopro.models.streaming import WebcamResolution, WebcamFOV, WebcamProtocol
from open_gopro.models.constants.settings import (
    VideoResolution, WebcamDigitalLenses, Hypersmooth, Led, AutoPowerDown
)
from pydantic import BaseModel

from .webcam_config import WebcamConfig

import asyncio
import logging
from enum import Enum
from typing import Optional, Union
from pathlib import Path

from open_gopro import WiredGoPro, WirelessGoPro
from open_gopro.gopro_base import GoProBase
from open_gopro.models.streaming import StreamType, WebcamProtocol, WebcamStreamOptions
from returns.pipeline import is_successful

from .webcam_config import WebcamConfig


class ConnectionType(str, Enum):
    """GoPro connection types."""
    
    WIRED = "wired"
    WIRELESS = "wireless"


class GoProController:
    """
    Controller for GoPro camera webcam functionality.
    
    Manages connection, configuration, and streaming for GoPro cameras
    following the patterns from the official Open GoPro SDK.
    """
    
    def __init__(
        self,
        identifier: Optional[str] = None,
        connection_type: ConnectionType = ConnectionType.WIRELESS,
        wifi_interface: Optional[str] = None,
    ):
        """
        Initialize GoPro controller.
        
        Args:
            identifier: Last 4 digits of GoPro serial number (camera SSID suffix)
            connection_type: Whether to use wired (USB) or wireless (BLE/WiFi) connection
            wifi_interface: System WiFi interface to use (auto-detected if None)
        """
        self.identifier = identifier
        self.connection_type = connection_type
        self.wifi_interface = wifi_interface
        self.logger = logging.getLogger(__name__)
        
        self._gopro: Optional[GoProBase] = None
        self._streaming_active = False
        self._current_config: Optional[WebcamConfig] = None
    
    async def __aenter__(self) -> "GoProController":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to GoPro."""
        return self._gopro is not None
    
    @property
    def is_streaming(self) -> bool:
        """Check if webcam streaming is active."""
        return self._streaming_active
    
    @property
    def current_config(self) -> Optional[WebcamConfig]:
        """Get current webcam configuration."""
        return self._current_config
    
    async def connect(self) -> bool:
        """
        Connect to GoPro camera.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.connection_type == ConnectionType.WIRED:
                self._gopro = WiredGoPro(self.identifier)
            else:
                # For wireless, use both BLE and WiFi interfaces
                wireless_interfaces = {
                    WirelessGoPro.Interface.BLE,
                    WirelessGoPro.Interface.WIFI_AP
                }
                self._gopro = WirelessGoPro(
                    identifier=self.identifier,
                    host_wifi_interface=self.wifi_interface,
                    interfaces=wireless_interfaces,
                )
            
            # Open the connection
            await self._gopro.open()
            
            self.logger.info(f"Successfully connected to GoPro via {self.connection_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to GoPro: {e}")
            self._gopro = None
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from GoPro camera."""
        if self._gopro:
            try:
                # Stop streaming if active
                if self._streaming_active:
                    await self.stop_webcam()
                    
                await self._gopro.close()
                self.logger.info("Disconnected from GoPro")
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
            finally:
                self._gopro = None
                self._streaming_active = False
    
    async def _apply_settings(self, config: WebcamConfig) -> bool:
        """
        Apply webcam configuration settings to the GoPro.
        
        Args:
            config: Webcam configuration to apply
            
        Returns:
            True if configuration successful, False otherwise
        """
        if not self._gopro:
            self.logger.error("Not connected to GoPro")
            return False
        
        try:
            self.logger.info("Configuring GoPro for webcam mode...")
            
            # Apply resolution setting
            if config.resolution:
                resolution_mapping = {
                    "480p": VideoResolution.NUM_1080,  # Use 1080p as minimum since some cameras don't support lower
                    "720p": VideoResolution.NUM_1080,  # Use 1080p for consistency
                    "1080p": VideoResolution.NUM_1080,
                }
                if config.resolution in resolution_mapping:
                    try:
                        result = await self._gopro.http_setting.video_resolution.set(
                            resolution_mapping[config.resolution]
                        )
                        if not result.ok:
                            self.logger.warning(f"Failed to set resolution to {config.resolution}")
                    except Exception as e:
                        self.logger.warning(f"Error setting resolution: {e}")
            
            # Apply field of view setting for webcam
            if config.field_of_view:
                fov_mapping = {
                    "wide": WebcamDigitalLenses.WIDE,
                    "narrow": WebcamDigitalLenses.NARROW,
                    "superview": WebcamDigitalLenses.SUPERVIEW,
                    "linear": WebcamDigitalLenses.LINEAR,
                }
                if config.field_of_view in fov_mapping:
                    try:
                        result = await self._gopro.http_setting.webcam_digital_lenses.set(
                            fov_mapping[config.field_of_view]
                        )
                        if not result.ok:
                            self.logger.warning(f"Failed to set FOV to {config.field_of_view}")
                    except Exception as e:
                        self.logger.warning(f"Error setting FOV: {e}")
            
            # Apply Hypersmooth setting
            if config.disable_hypersmooth:
                try:
                    result = await self._gopro.http_setting.hypersmooth.set(Hypersmooth.OFF)
                    if not result.ok:
                        self.logger.warning("Failed to disable Hypersmooth")
                except Exception as e:
                    self.logger.warning(f"Error setting Hypersmooth: {e}")
            else:
                # Set to low for better performance
                try:
                    result = await self._gopro.http_setting.hypersmooth.set(Hypersmooth.LOW)
                    if not result.ok:
                        self.logger.warning("Failed to set Hypersmooth to low")
                except Exception as e:
                    self.logger.warning(f"Error setting Hypersmooth: {e}")
            
            # Optimize for low latency if requested
            if hasattr(config, 'low_latency_mode') and config.low_latency_mode:
                try:
                    # Disable LED indicators for lower latency
                    result = await self._gopro.http_setting.led.set(Led.FRONT_OFF_ONLY)
                    if not result.ok:
                        self.logger.warning("Failed to optimize LED settings")
                except Exception as e:
                    self.logger.warning(f"Error setting LED optimization: {e}")
                    
                try:
                    # Set auto power down to never for streaming
                    result = await self._gopro.http_setting.auto_power_down.set(AutoPowerDown.NEVER)
                    if not result.ok:
                        self.logger.warning("Failed to set auto power down")
                except Exception as e:
                    self.logger.warning(f"Error setting auto power down: {e}")
            
            self._current_config = config
            self.logger.info("GoPro webcam configuration applied successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure webcam: {e}")
            return False
    
    async def start_webcam(self, config: Optional[WebcamConfig] = None) -> bool:
        """
        Start webcam streaming.
        
        Args:
            config: Webcam configuration to use (uses balanced preset if None)
            
        Returns:
            True if streaming started successfully, False otherwise
        """
        if not self._gopro:
            self.logger.error("Not connected to GoPro")
            return False
        
        if self._streaming_active:
            self.logger.warning("Webcam streaming already active")
            return True
        
        try:
            # Use provided config or default to balanced preset
            if config is None:
                config = WebcamConfig.balanced_preset()
            
            # Apply configuration first
            if not await self._apply_settings(config):
                self.logger.warning("Configuration applied with warnings, continuing...")
            
            self.logger.info("Starting webcam stream...")
            
            # Map config to webcam parameters
            resolution_mapping = {
                "480p": WebcamResolution.RES_720,  # Use 720p as minimum - some cameras don't support 480p
                "720p": WebcamResolution.RES_720,
                "1080p": WebcamResolution.RES_1080,
            }
            
            fov_mapping = {
                "wide": WebcamFOV.WIDE,
                "narrow": WebcamFOV.NARROW,
                "superview": WebcamFOV.SUPERVIEW,
                "linear": WebcamFOV.LINEAR,
            }
            
            # Get webcam parameters - use defaults that are most compatible
            resolution = resolution_mapping.get(config.resolution, WebcamResolution.RES_1080)
            fov = fov_mapping.get(config.field_of_view, WebcamFOV.WIDE)  # WIDE is most compatible
            protocol = WebcamProtocol.TS  # Use MPEG-TS for compatibility
            
            # Start with the simplest webcam call - no parameters first to see if it works
            result = await self._gopro.http_command.webcam_start()
            
            if not result.ok:
                self.logger.error(f"Failed to start webcam: {result}")
                return False
            
            self._streaming_active = True
            self._current_config = config
            self.logger.info(f"Webcam stream started successfully on {self.get_stream_url()}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start webcam: {e}")
        except Exception as e:
            self.logger.error(f"Failed to start webcam: {e}")
            return False
    
    async def stop_webcam(self) -> bool:
        """
        Stop webcam streaming.
        
        Returns:
            True if streaming stopped successfully, False otherwise
        """
        if not self._gopro:
            self.logger.error("Not connected to GoPro")
            return False
        
        if not self._streaming_active:
            self.logger.warning("Webcam streaming not active")
            return True
        
        try:
            self.logger.info("Stopping webcam stream...")
            # Use webcam stop command
            result = await self._gopro.http_command.webcam_stop()
            if not result.ok:
                self.logger.warning(f"Webcam stop returned: {result}")
            
            # Also exit webcam mode
            result = await self._gopro.http_command.webcam_exit()
            if not result.ok:
                self.logger.warning(f"Webcam exit returned: {result}")
                
            self._streaming_active = False
            self.logger.info("Webcam stream stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop webcam: {e}")
            return False
    
    def get_stream_url(self) -> Optional[str]:
        """
        Get the current stream URL.
        
        Returns:
            Stream URL if streaming is active, None otherwise
        """
        if not self._streaming_active or not self._gopro:
            return None
        
        # For UDP streams, use the standard port
        if self._current_config and self._current_config.protocol == "udp":
            return f"udp://@:{self._current_config.udp_port}"
        
        # For RTSP or other protocols, use the GoPro's URL
        return getattr(self._gopro.streaming, 'url', None)
    
    async def get_camera_info(self) -> Optional[dict]:
        """
        Get basic camera information.
        
        Returns:
            Dictionary with camera info if connected, None otherwise
        """
        if not self._gopro:
            return None
        
        try:
            # Get camera status and settings info
            camera_state = await self._gopro.http_command.get_camera_state()
            
            if camera_state.ok:
                # Extract basic info from the response
                data = camera_state.data if hasattr(camera_state, 'data') else {}
                
                return {
                    "connected": True,
                    "connection_type": self.connection_type.value,
                    "streaming": self._streaming_active,
                    "status": "Connected",
                }
            else:
                return {"connected": True, "error": "Failed to get camera state"}
                
        except Exception as e:
            self.logger.error(f"Failed to get camera info: {e}")
            return {"connected": True, "error": str(e)}
    
    async def test_connection(self) -> bool:
        """
        Test the GoPro connection.
        
        Returns:
            True if connection is working, False otherwise
        """
        if not self._gopro:
            return False
        
        try:
            # Try to get basic camera state as a connection test
            result = await self._gopro.http_command.get_camera_state()
            return result.ok
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False