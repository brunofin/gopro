"""
PipeWire stream consumer for creating virtual camera nodes.

Uses GStreamer to create native PipeWire video sources that appear as webcams
in applications. This is the modern replacement for V4L2 on Linux systems.
"""

import asyncio
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import StreamConsumer, StreamConsumerConfig, StreamConsumerType

# GStreamer imports with graceful fallback
try:
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GObject', '2.0')
    from gi.repository import Gst, GObject
    
    # Initialize GStreamer
    GObject.threads_init()
    Gst.init(None)
    GSTREAMER_AVAILABLE = True
except ImportError:
    GSTREAMER_AVAILABLE = False


class PipeWireConsumerConfig(StreamConsumerConfig):
    """Configuration for PipeWire stream consumer."""
    
    consumer_type: StreamConsumerType = StreamConsumerType.PIPEWIRE
    
    # PipeWire specific settings
    node_name: str = Field(default="GoPro Camera", description="PipeWire node name")
    client_name: str = Field(default="GoPro Webcam Controller", description="PipeWire client name")
    media_class: str = Field(default="Video/Source", description="PipeWire media class")
    
    # Video output settings
    width: int = Field(default=0, description="Output width (0 = keep source)")
    height: int = Field(default=0, description="Output height (0 = keep source)")
    fps: int = Field(default=0, description="Output FPS (0 = keep source)")
    
    # Stream processing settings
    jitter_ms: int = Field(default=0, description="RTP jitter buffer latency in ms")
    payload_type: int = Field(default=96, description="RTP payload type")
    format: str = Field(default="mpegts-h264", description="Stream format: mpegts-h264, rtp-h264, rtp-mjpeg")
    
    # Hardware acceleration
    prefer_hardware_decode: bool = Field(default=True, description="Prefer hardware H.264 decoders")
    
    # Low-latency optimizations
    sync_playback: bool = Field(default=False, description="Sync playback (disable for lower latency)")
    drop_on_late: bool = Field(default=True, description="Drop late packets")
    do_lost: bool = Field(default=True, description="Handle lost packets")


class PipeWireConsumer(StreamConsumer):
    """
    PipeWire stream consumer using GStreamer.
    
    Creates a native PipeWire video source node that appears as a webcam
    in applications. This provides better integration with modern Linux
    desktop environments compared to V4L2 loopback devices.
    """
    
    def __init__(self, config: PipeWireConsumerConfig):
        """
        Initialize PipeWire consumer.
        
        Args:
            config: PipeWire consumer configuration
        """
        super().__init__(config)
        self.pipewire_config = config
        self.pipeline: Optional[object] = None  # Gst.Pipeline
        self.bus: Optional[object] = None       # Gst.Bus
        self.loop: Optional[object] = None      # GObject.MainLoop
        self.loop_thread: Optional[threading.Thread] = None
        
        if not GSTREAMER_AVAILABLE:
            self.logger.error("GStreamer not available - cannot use PipeWire consumer")
    
    async def start(self) -> bool:
        """
        Start the PipeWire stream consumer.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            self.logger.warning("PipeWire consumer is already running")
            return True
        
        # Validate requirements
        missing = self.validate_requirements()
        if missing:
            self.logger.error(f"Missing requirements: {', '.join(missing)}")
            return False
        
        try:
            # Build GStreamer pipeline
            pipeline_str = self._build_gstreamer_pipeline()
            self.logger.info(f"Creating GStreamer pipeline: {pipeline_str}")
            
            self.pipeline = Gst.parse_launch(pipeline_str)
            if not self.pipeline:
                self.logger.error("Failed to create GStreamer pipeline")
                return False
            
            # Set up message bus
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect("message", self._on_bus_message)
            
            # Create GObject main loop
            self.loop = GObject.MainLoop()
            
            # Start pipeline
            ret = self.pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                self.logger.error("Failed to start GStreamer pipeline")
                return False
            
            # Run GObject loop in separate thread
            self.loop_thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="PipeWire-GObject-Loop"
            )
            self.loop_thread.start()
            
            self._running = True
            self.logger.info(f"PipeWire consumer started - node: '{self.pipewire_config.node_name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start PipeWire consumer: {e}")
            await self._cleanup()
            return False
    async def stop(self) -> bool:
        """
        Stop the PipeWire stream consumer.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_running:
            return True
        
        try:
            self.logger.info("Stopping PipeWire consumer...")
            
            # Send EOS to pipeline
            if self.pipeline:
                self.pipeline.send_event(Gst.Event.new_eos())
                
                # Wait a bit for graceful shutdown
                await asyncio.sleep(0.5)
                
                # Force stop if needed
                self.pipeline.set_state(Gst.State.NULL)
            
            # Stop GObject loop
            if self.loop and self.loop.is_running():
                self.loop.quit()
            
            # Wait for thread to finish
            if self.loop_thread and self.loop_thread.is_alive():
                self.loop_thread.join(timeout=2.0)
            
            await self._cleanup()
            self._running = False
            self.logger.info("PipeWire consumer stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping PipeWire consumer: {e}")
            await self._cleanup()
            return False
    
    def get_output_info(self) -> Dict[str, Any]:
        """
        Get information about the PipeWire output.
        
        Returns:
            Dictionary containing output information
        """
        return {
            "type": "pipewire",
            "node_name": self.pipewire_config.node_name,
            "client_name": self.pipewire_config.client_name,
            "media_class": self.pipewire_config.media_class,
            "width": self.pipewire_config.width,
            "height": self.pipewire_config.height,
            "fps": self.pipewire_config.fps,
            "format": self.pipewire_config.format,
            "running": self.is_running,
        }
    
    def validate_requirements(self) -> List[str]:
        """
        Validate PipeWire requirements.
        
        Returns:
            List of missing requirements
        """
        missing = []
        
        # Check for GStreamer
        if not GSTREAMER_AVAILABLE:
            missing.append("GStreamer Python bindings (python3-gi, gstreamer1)")
        
        # Check for required GStreamer elements
        if GSTREAMER_AVAILABLE:
            required_elements = [
                "udpsrc",
                "pipewiresink",
                "videoconvert",
            ]
            
            # Add format-specific elements
            if self.pipewire_config.format.startswith("rtp"):
                required_elements.extend(["rtpjitterbuffer"])
                
                if "h264" in self.pipewire_config.format:
                    required_elements.extend(["rtph264depay", "h264parse"])
                elif "mjpeg" in self.pipewire_config.format:
                    required_elements.extend(["rtpjpegdepay", "jpegdec"])
                    
            elif self.pipewire_config.format == "mpegts-h264":
                required_elements.extend(["tsparse", "tsdemux", "h264parse"])
            
            for element in required_elements:
                if not self._has_gst_element(element):
                    missing.append(f"GStreamer element: {element}")
            
            # Check for H.264 decoder
            if "h264" in self.pipewire_config.format:
                decoder = self._choose_h264_decoder()
                if not decoder:
                    missing.append("H.264 decoder (avdec_h264 or hardware decoder)")
        
        # Check for PipeWire
        if not self._check_pipewire_available():
            missing.append("PipeWire service")
        
        return missing
    
    def _build_gstreamer_pipeline(self) -> str:
        """
        Build the GStreamer pipeline string.
        
        Returns:
            GStreamer pipeline string
        """
        # Extract configuration
        port = self._extract_port_from_url(self.config.stream_url)
        node_name = self.pipewire_config.node_name
        client_name = self.pipewire_config.client_name
        media_class = self.pipewire_config.media_class
        
        # Build video constraints
        scale_caps = self._build_scale_caps()
        
        # Build pipeline based on format
        if self.pipewire_config.format == "rtp-h264":
            return self._build_rtp_h264_pipeline(port, scale_caps, node_name, client_name, media_class)
        elif self.pipewire_config.format == "rtp-mjpeg":
            return self._build_rtp_mjpeg_pipeline(port, scale_caps, node_name, client_name, media_class)
        elif self.pipewire_config.format == "mpegts-h264":
            return self._build_mpegts_h264_pipeline(port, scale_caps, node_name, client_name, media_class)
        else:
            raise ValueError(f"Unsupported format: {self.pipewire_config.format}")
    
    def _build_mpegts_h264_pipeline(self, port: int, scale_caps: str, 
                                  node_name: str, client_name: str, media_class: str) -> str:
        """Build pipeline for MPEG-TS H.264 (GoPro format)."""
        decoder = self._choose_h264_decoder()
        
        # Match exactly the working manual pipeline - remove specific format constraints
        return (
            f'udpsrc port={port} ! '
            f'tsparse ! tsdemux ! h264parse ! {decoder} ! '
            f'videoconvert ! '
            f'pipewiresink client-name="{client_name}" name="{node_name}" '
            f'stream-properties="p,media.class=Video/Source,media.role=Camera" '
            f'sync=false'
        )
    
    def _build_rtp_h264_pipeline(self, port: int, scale_caps: str,
                                node_name: str, client_name: str, media_class: str) -> str:
        """Build pipeline for RTP H.264."""
        caps = (f'application/x-rtp,media=video,encoding-name=H264,'
                f'payload={self.pipewire_config.payload_type},clock-rate=90000')
        jitter = self._build_jitter_buffer()
        decoder = self._choose_h264_decoder()
        
        return (
            f'udpsrc port={port} caps="{caps}" ! '
            f'{jitter} ! rtph264depay ! h264parse ! {decoder} ! '
            f'videoconvert ! {scale_caps}'
            f'queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 leaky=downstream ! '
            f'pipewiresink mode=provide '
            f'client-name="{client_name}" node-name="{node_name}" '
            f'media-class={media_class} sync={str(self.pipewire_config.sync_playback).lower()}'
        )
    
    def _build_rtp_mjpeg_pipeline(self, port: int, scale_caps: str,
                                 node_name: str, client_name: str, media_class: str) -> str:
        """Build pipeline for RTP MJPEG."""
        caps = (f'application/x-rtp,media=video,encoding-name=JPEG,'
                f'payload={self.pipewire_config.payload_type}')
        jitter = self._build_jitter_buffer()
        
        return (
            f'udpsrc port={port} caps="{caps}" ! '
            f'{jitter} ! rtpjpegdepay ! jpegdec ! '
            f'videoconvert ! {scale_caps}'
            f'queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 leaky=downstream ! '
            f'pipewiresink mode=provide '
            f'client-name="{client_name}" node-name="{node_name}" '
            f'media-class={media_class} sync={str(self.pipewire_config.sync_playback).lower()}'
        )
    
    def _build_jitter_buffer(self) -> str:
        """Build RTP jitter buffer configuration."""
        return (
            f'rtpjitterbuffer latency={self.pipewire_config.jitter_ms} '
            f'drop-on-late={str(self.pipewire_config.drop_on_late).lower()} '
            f'do-lost={str(self.pipewire_config.do_lost).lower()}'
        )
    
    def _build_scale_caps(self) -> str:
        """Build video scaling capabilities string."""
        if (self.pipewire_config.width > 0 and 
            self.pipewire_config.height > 0 and 
            self.pipewire_config.fps > 0):
            return (
                f'video/x-raw,format=NV12,'
                f'width={self.pipewire_config.width},'
                f'height={self.pipewire_config.height},'
                f'framerate={self.pipewire_config.fps}/1 ! '
            )
        return ''  # Keep source format
    
    def _choose_h264_decoder(self) -> Optional[str]:
        """Choose the best available H.264 decoder."""
        if not GSTREAMER_AVAILABLE:
            return None
        
        # Prefer openh264dec for PipeWire compatibility (outputs I420 directly)
        candidates = ["openh264dec", "vah264dec", "nvh264dec", "v4l2h264dec"]
        
        if not self.pipewire_config.prefer_hardware_decode:
            # Put software decoder first if hardware is disabled
            candidates = ["openh264dec", "vah264dec", "nvh264dec", "v4l2h264dec"]
        
        for decoder in candidates:
            if self._has_gst_element(decoder):
                return decoder
        
        return None
    
    def _has_gst_element(self, element_name: str) -> bool:
        """Check if a GStreamer element is available."""
        if not GSTREAMER_AVAILABLE:
            return False
        return Gst.ElementFactory.find(element_name) is not None
    
    def _extract_port_from_url(self, url: str) -> int:
        """Extract port from stream URL."""
        # Handle formats like "udp://@:8554" or "udp://localhost:8554"
        if ":" in url:
            port_part = url.split(":")[-1]
            try:
                return int(port_part)
            except ValueError:
                pass
        
        # Default to standard port
        return 8554
    
    def _check_pipewire_available(self) -> bool:
        """Check if PipeWire is available on the system."""
        try:
            # Check if PipeWire service is running
            import subprocess
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "pipewire"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            # Fallback: check for PipeWire socket
            pipewire_socket = Path("/run/user").glob("*/pipewire-0")
            return any(pipewire_socket)
    
    def _run_loop(self) -> None:
        """Run the GObject main loop in a separate thread."""
        try:
            if self.loop:
                self.loop.run()
        except Exception as e:
            self.logger.error(f"Error in GObject main loop: {e}")
    
    def _on_bus_message(self, bus, message) -> bool:
        """Handle GStreamer bus messages."""
        if not GSTREAMER_AVAILABLE:
            return True
            
        msg_type = message.type
        
        if msg_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.logger.error(f"GStreamer error: {err}")
            self.logger.debug(f"GStreamer debug: {debug}")
            
            # Stop pipeline on error
            if self.pipeline:
                self.pipeline.set_state(Gst.State.NULL)
            if self.loop:
                self.loop.quit()
                
        elif msg_type == Gst.MessageType.EOS:
            self.logger.info("GStreamer end of stream")
            if self.loop:
                self.loop.quit()
                
        elif msg_type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                self.logger.debug(f"Pipeline state changed: {old_state} -> {new_state}")
        
        return True
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.bus:
                self.bus.remove_signal_watch()
                self.bus = None
            
            self.pipeline = None
            self.loop = None
            self.loop_thread = None
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    @classmethod
    def get_available_decoders(cls) -> List[str]:
        """
        Get list of available H.264 decoders.
        
        Returns:
            List of decoder names
        """
        if not GSTREAMER_AVAILABLE:
            return []
        
        decoders = []
        candidates = ["vah264dec", "nvh264dec", "v4l2h264dec", "avdec_h264"]
        
        for decoder in candidates:
            if Gst.ElementFactory.find(decoder):
                decoders.append(decoder)
        
        return decoders
    
    @classmethod
    def check_pipewire_support(cls) -> Dict[str, bool]:
        """
        Check PipeWire support status.
        
        Returns:
            Dictionary with support status
        """
        status = {
            "gstreamer_available": GSTREAMER_AVAILABLE,
            "pipewire_running": False,
            "pipewiresink_available": False,
            "h264_decoders": [],
        }
        
        if GSTREAMER_AVAILABLE:
            status["pipewiresink_available"] = Gst.ElementFactory.find("pipewiresink") is not None
            status["h264_decoders"] = cls.get_available_decoders()
        
        # Check PipeWire service
        try:
            import subprocess
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "pipewire"],
                capture_output=True,
                text=True
            )
            status["pipewire_running"] = result.returncode == 0
        except Exception:
            pass
        
        return status