"""
Base classes for stream consumers.

Defines the interface for different ways to consume GoPro webcam streams.
"""

import asyncio
import logging
import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path

from pydantic import BaseModel, Field


class StreamConsumerType(str, Enum):
    """Types of stream consumers."""
    
    V4L2 = "v4l2"
    PIPEWIRE = "pipewire"
    RTMP = "rtmp"
    FILE = "file"


class StreamConsumerConfig(BaseModel):
    """Base configuration for stream consumers."""
    
    stream_url: str = Field(description="Source stream URL")
    consumer_type: StreamConsumerType = Field(description="Type of stream consumer")
    buffer_size: int = Field(default=5000000, description="Input buffer size in bytes")
    
    # FFmpeg options for processing
    input_format: Optional[str] = Field(default=None, description="Input format override")
    video_codec: Optional[str] = Field(default=None, description="Video codec for output")
    pixel_format: str = Field(default="yuv420p", description="Pixel format for output")
    
    # Low-latency options
    no_buffer: bool = Field(default=True, description="Disable input buffering")
    low_latency: bool = Field(default=True, description="Enable low-latency optimizations")
    tune_zerolatency: bool = Field(default=True, description="Use zero-latency tuning")


class StreamConsumer(ABC):
    """
    Abstract base class for stream consumers.
    
    Stream consumers take a GoPro webcam stream and output it to various destinations
    such as V4L2 devices, PipeWire, RTMP servers, or files.
    """
    
    def __init__(self, config: StreamConsumerConfig):
        """
        Initialize stream consumer.
        
        Args:
            config: Configuration for the stream consumer
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._process: Optional[subprocess.Popen] = None
        self._running = False
    
    @property
    def is_running(self) -> bool:
        """Check if the stream consumer is currently running."""
        return self._running and self._process is not None and self._process.poll() is None
    
    @abstractmethod
    async def start(self) -> bool:
        """
        Start consuming the stream.
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """
        Stop consuming the stream.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_output_info(self) -> Dict[str, Any]:
        """
        Get information about the output destination.
        
        Returns:
            Dictionary containing output information
        """
        pass
    
    @abstractmethod
    def validate_requirements(self) -> List[str]:
        """
        Validate that all requirements for this consumer are met.
        
        Returns:
            List of missing requirements (empty if all requirements met)
        """
        pass
    
    def _build_base_ffmpeg_command(self) -> List[str]:
        """
        Build base FFmpeg command with common low-latency options.
        
        Returns:
            List of FFmpeg command arguments
        """
        cmd = ["ffmpeg"]
        
        # Input options for low latency
        if self.config.no_buffer:
            cmd.extend(["-fflags", "nobuffer"])
        
        if self.config.low_latency:
            cmd.extend(["-flags", "low_delay"])
            cmd.extend(["-avioflags", "direct"])
        
        # Input format and buffer size
        if self.config.input_format:
            cmd.extend(["-f", self.config.input_format])
        
        cmd.extend(["-fifo_size", str(self.config.buffer_size)])
        
        # Input URL
        cmd.extend(["-i", self.config.stream_url])
        
        return cmd
    
    def _add_video_encoding_options(self, cmd: List[str]) -> List[str]:
        """
        Add video encoding options to FFmpeg command.
        
        Args:
            cmd: Existing FFmpeg command
            
        Returns:
            Updated command with video options
        """
        # Pixel format
        cmd.extend(["-vf", f"format={self.config.pixel_format}"])
        
        # Video codec if specified
        if self.config.video_codec:
            cmd.extend(["-c:v", self.config.video_codec])
        
        # Low-latency encoding options
        if self.config.tune_zerolatency and self.config.video_codec in ["libx264", "h264"]:
            cmd.extend(["-tune", "zerolatency"])
            cmd.extend(["-preset", "ultrafast"])
        
        # Disable audio (webcam typically doesn't need it)
        cmd.extend(["-an"])
        
        return cmd
    
    async def _run_process(self, cmd: List[str]) -> bool:
        """
        Run the FFmpeg process asynchronously.
        
        Args:
            cmd: FFmpeg command to run
            
        Returns:
            True if process started successfully, False otherwise
        """
        try:
            self.logger.info(f"Starting stream consumer with command: {' '.join(cmd)}")
            
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            self._running = True
            
            # Wait a moment to check if process started successfully
            await asyncio.sleep(1)
            
            if self._process.poll() is not None:
                # Process already terminated
                stdout, stderr = self._process.communicate()
                self.logger.error(f"Process terminated early. stderr: {stderr}")
                self._running = False
                return False
            
            self.logger.info("Stream consumer started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start process: {e}")
            self._running = False
            return False
    
    async def _stop_process(self) -> bool:
        """
        Stop the running FFmpeg process.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self._process:
            return True
        
        try:
            self.logger.info("Stopping stream consumer...")
            
            # Terminate the process gracefully
            self._process.terminate()
            
            # Wait for termination with timeout
            try:
                await asyncio.wait_for(
                    asyncio.create_task(self._wait_for_process()),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                # Force kill if it doesn't terminate gracefully
                self.logger.warning("Process didn't terminate gracefully, forcing kill")
                self._process.kill()
                await self._wait_for_process()
            
            self._process = None
            self._running = False
            self.logger.info("Stream consumer stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping process: {e}")
            return False
    
    async def _wait_for_process(self) -> None:
        """Wait for the process to terminate."""
        if self._process:
            # Run in thread pool since communicate() is blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._process.wait)
    
    def _check_command_available(self, command: str) -> bool:
        """
        Check if a command is available in the system PATH.
        
        Args:
            command: Command to check
            
        Returns:
            True if command is available, False otherwise
        """
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
    
    def _check_file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        return Path(file_path).exists()