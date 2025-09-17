"""
V4L2 stream consumer for creating virtual webcam devices.

Uses FFmpeg to consume GoPro streams and output to V4L2 devices.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import StreamConsumer, StreamConsumerConfig, StreamConsumerType


class V4L2ConsumerConfig(StreamConsumerConfig):
    """Configuration for V4L2 stream consumer."""
    
    consumer_type: StreamConsumerType = StreamConsumerType.V4L2
    
    # V4L2 specific settings
    device_path: str = Field(default="/dev/video42", description="V4L2 device path")
    device_label: Optional[str] = Field(default="GoPro Webcam", description="Device label for v4l2loopback")
    video_size: Optional[str] = Field(default=None, description="Video size override (e.g., '1280x720')")
    framerate: Optional[int] = Field(default=30, description="Output framerate")
    
    # Advanced V4L2 options
    exclusive_caps: bool = Field(default=True, description="Use exclusive_caps for v4l2loopback")
    max_buffers: int = Field(default=2, description="Maximum number of buffers")


class V4L2Consumer(StreamConsumer):
    """
    V4L2 stream consumer that creates virtual webcam devices.
    
    This consumer uses FFmpeg to read the GoPro stream and output it to a
    V4L2 virtual device created by v4l2loopback. This allows the GoPro
    to appear as a standard webcam in video conferencing applications.
    """
    
    def __init__(self, config: V4L2ConsumerConfig):
        """
        Initialize V4L2 consumer.
        
        Args:
            config: V4L2 consumer configuration
        """
        super().__init__(config)
        self.v4l2_config = config
    
    async def start(self) -> bool:
        """
        Start the V4L2 stream consumer.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            self.logger.warning("V4L2 consumer is already running")
            return True
        
        # Validate requirements
        missing = self.validate_requirements()
        if missing:
            self.logger.error(f"Missing requirements: {', '.join(missing)}")
            return False
        
        # Check if device exists and is writable
        if not self._check_device_access():
            return False
        
        # Build FFmpeg command
        cmd = self._build_ffmpeg_command()
        
        # Start the process
        return await self._run_process(cmd)
    
    async def stop(self) -> bool:
        """
        Stop the V4L2 stream consumer.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        return await self._stop_process()
    
    def get_output_info(self) -> Dict[str, Any]:
        """
        Get information about the V4L2 output device.
        
        Returns:
            Dictionary containing device information
        """
        return {
            "type": "v4l2",
            "device_path": self.v4l2_config.device_path,
            "device_label": self.v4l2_config.device_label,
            "video_size": self.v4l2_config.video_size,
            "framerate": self.v4l2_config.framerate,
            "running": self.is_running,
        }
    
    def validate_requirements(self) -> List[str]:
        """
        Validate V4L2 requirements.
        
        Returns:
            List of missing requirements
        """
        missing = []
        
        # Check for FFmpeg
        if not self._check_command_available("ffmpeg"):
            missing.append("ffmpeg")
        
        # Check for v4l2loopback kernel module
        if not self._check_v4l2loopback_loaded():
            missing.append("v4l2loopback kernel module")
        
        # Check if device path exists
        if not Path(self.v4l2_config.device_path).exists():
            missing.append(f"V4L2 device {self.v4l2_config.device_path}")
        
        return missing
    
    def _build_ffmpeg_command(self) -> List[str]:
        """
        Build the complete FFmpeg command for V4L2 output.
        
        Returns:
            Complete FFmpeg command
        """
        # Start with base command
        cmd = self._build_base_ffmpeg_command()
        
        # Add video encoding options
        cmd = self._add_video_encoding_options(cmd)
        
        # Add framerate if specified
        if self.v4l2_config.framerate:
            cmd.extend(["-r", str(self.v4l2_config.framerate)])
        
        # Add video size if specified
        if self.v4l2_config.video_size:
            cmd.extend(["-s", self.v4l2_config.video_size])
        
        # V4L2 specific options
        cmd.extend(["-f", "v4l2"])
        
        # Buffer control for low latency
        cmd.extend(["-bufsize", str(self.v4l2_config.max_buffers)])
        
        # Output device
        cmd.append(self.v4l2_config.device_path)
        
        return cmd
    
    def _check_device_access(self) -> bool:
        """
        Check if the V4L2 device exists and is writable.
        
        Returns:
            True if device is accessible, False otherwise
        """
        device_path = Path(self.v4l2_config.device_path)
        
        if not device_path.exists():
            self.logger.error(f"V4L2 device {device_path} does not exist")
            self.logger.info("Make sure v4l2loopback is loaded with the correct video_nr parameter")
            return False
        
        if not device_path.is_char_device():
            self.logger.error(f"{device_path} is not a character device")
            return False
        
        # Check write permissions
        try:
            # Try to open the device for writing (but don't actually write)
            with open(device_path, "wb") as f:
                pass
            return True
        except PermissionError:
            self.logger.error(f"No write permission for {device_path}")
            self.logger.info("You may need to add your user to the 'video' group or run with sudo")
            return False
        except Exception as e:
            self.logger.error(f"Cannot access {device_path}: {e}")
            return False
    
    def _check_v4l2loopback_loaded(self) -> bool:
        """
        Check if the v4l2loopback kernel module is loaded.
        
        Returns:
            True if module is loaded, False otherwise
        """
        try:
            with open("/proc/modules", "r") as f:
                modules = f.read()
                return "v4l2loopback" in modules
        except Exception:
            # Fallback: check if any loopback devices exist
            return any(Path("/dev").glob("video*"))
    
    @classmethod
    def setup_v4l2loopback_device(
        cls,
        device_number: int = 42,
        device_label: str = "GoPro Webcam",
        exclusive_caps: bool = True,
    ) -> bool:
        """
        Set up a v4l2loopback device.
        
        Args:
            device_number: Video device number to create
            device_label: Label for the device
            exclusive_caps: Whether to use exclusive_caps
            
        Returns:
            True if setup successful, False otherwise
        """
        import subprocess
        
        try:
            # Build modprobe command
            cmd = [
                "sudo", "modprobe", "v4l2loopback",
                f"video_nr={device_number}",
                f"card_label={device_label}",
            ]
            
            if exclusive_caps:
                cmd.append("exclusive_caps=1")
            
            # Load the module
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True
            else:
                logging.getLogger(__name__).error(f"Failed to load v4l2loopback: {result.stderr}")
                return False
                
        except Exception as e:
            logging.getLogger(__name__).error(f"Error setting up v4l2loopback: {e}")
            return False
    
    @classmethod
    def remove_v4l2loopback_device(cls) -> bool:
        """
        Remove the v4l2loopback module.
        
        Returns:
            True if removal successful, False otherwise
        """
        import subprocess
        
        try:
            result = subprocess.run(
                ["sudo", "modprobe", "-r", "v4l2loopback"],
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error removing v4l2loopback: {e}")
            return False
    
    @classmethod
    def list_v4l2_devices(cls) -> List[Dict[str, str]]:
        """
        List available V4L2 devices.
        
        Returns:
            List of device information dictionaries
        """
        devices = []
        
        try:
            import subprocess
            
            # Use v4l2-ctl to list devices if available
            if cls._check_command_available_static("v4l2-ctl"):
                result = subprocess.run(
                    ["v4l2-ctl", "--list-devices"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Parse v4l2-ctl output
                    lines = result.stdout.split('\n')
                    current_device = None
                    
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('/dev/'):
                            current_device = line.rstrip(':')
                        elif line.startswith('/dev/video'):
                            if current_device:
                                devices.append({
                                    "path": line,
                                    "name": current_device,
                                })
            else:
                # Fallback: just list /dev/video* devices
                video_devices = list(Path("/dev").glob("video*"))
                for device in sorted(video_devices):
                    devices.append({
                        "path": str(device),
                        "name": f"Video Device {device.name}",
                    })
                    
        except Exception as e:
            logging.getLogger(__name__).error(f"Error listing V4L2 devices: {e}")
        
        return devices
    
    @staticmethod
    def _check_command_available_static(command: str) -> bool:
        """Static version of command availability check."""
        import subprocess
        
        try:
            subprocess.run(
                [command, "--help"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False