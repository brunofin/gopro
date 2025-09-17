# API Reference - GoPro Webcam Controller

## Core Classes and Methods

This document provides comprehensive API documentation for the GoPro Webcam Controller components.

## Models

### GoProController

**Location**: `gopro_controller.models.gopro_controller`

Primary interface for GoPro camera control with webcam functionality.

#### Constructor

```python
GoProController(
    identifier: Optional[str] = None,
    connection_type: ConnectionType = ConnectionType.WIRELESS,
    wifi_interface: Optional[str] = None,
)
```

**Parameters**:

- `identifier`: Last 4 digits of GoPro serial number (camera SSID suffix)
- `connection_type`: `ConnectionType.WIRED` or `ConnectionType.WIRELESS`
- `wifi_interface`: System WiFi interface to use (auto-detected if None)

#### Properties

```python
@property
def is_connected(self) -> bool:
    """Check if connected to GoPro."""

@property
def is_streaming(self) -> bool:
    """Check if webcam streaming is active."""

@property
def current_config(self) -> Optional[WebcamConfig]:
    """Get current webcam configuration."""
```

#### Async Context Manager

```python
async def __aenter__(self) -> "GoProController":
    """Async context manager entry - automatically connects."""

async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    """Async context manager exit - automatically disconnects."""
```

#### Connection Methods

```python
async def connect(self) -> bool:
    """
    Connect to GoPro camera.

    Returns:
        True if connection successful, False otherwise
    """

async def disconnect(self) -> None:
    """Disconnect from GoPro camera."""

async def test_connection(self) -> bool:
    """
    Test the GoPro connection.

    Returns:
        True if connection is working, False otherwise
    """
```

#### Webcam Control Methods

```python
async def configure_webcam(self, config: WebcamConfig) -> bool:
    """
    Configure GoPro for webcam mode with optimized settings.

    Args:
        config: Webcam configuration to apply

    Returns:
        True if configuration successful, False otherwise
    """

async def start_webcam(self, config: Optional[WebcamConfig] = None) -> bool:
    """
    Start webcam streaming.

    Args:
        config: Webcam configuration to use (uses balanced preset if None)

    Returns:
        True if streaming started successfully, False otherwise
    """

async def stop_webcam(self) -> bool:
    """
    Stop webcam streaming.

    Returns:
        True if streaming stopped successfully, False otherwise
    """
```

#### Information Methods

```python
def get_stream_url(self) -> Optional[str]:
    """
    Get the current stream URL.

    Returns:
        Stream URL if streaming is active, None otherwise
    """

async def get_camera_info(self) -> Optional[dict]:
    """
    Get basic camera information.

    Returns:
        Dictionary with camera info if connected, None otherwise
    """
```

### WebcamConfig

**Location**: `gopro_controller.models.webcam_config`

Configuration model for GoPro webcam with optimized low-latency settings.

#### Constructor

```python
WebcamConfig(
    resolution: Resolution = Resolution.RES_720P,
    field_of_view: FieldOfView = FieldOfView.NARROW,
    bit_rate: BitRate = BitRate.STANDARD,
    protocol: StreamProtocol = StreamProtocol.UDP,
    disable_hypersmooth: bool = True,
    disable_horizon_leveling: bool = True,
    max_video_performance: bool = True,
    udp_port: int = 8554,
    use_preview_stream: bool = False,
    preview_resolution: Optional[Resolution] = Resolution.RES_480P,
)
```

#### Enums

```python
class Resolution(str, Enum):
    RES_480P = "480p"
    RES_720P = "720p"
    RES_1080P = "1080p"

class FieldOfView(str, Enum):
    WIDE = "wide"
    NARROW = "narrow"
    SUPERVIEW = "superview"
    LINEAR = "linear"

class BitRate(str, Enum):
    STANDARD = "standard"
    HIGH = "high"

class StreamProtocol(str, Enum):
    UDP = "udp"
    RTSP = "rtsp"
```

#### Class Methods (Presets)

```python
@classmethod
def low_latency_preset(cls) -> "WebcamConfig":
    """
    Create a preset optimized for absolute minimum latency.
    Uses preview stream at 480p with all processing disabled.
    """

@classmethod
def balanced_preset(cls) -> "WebcamConfig":
    """
    Create a preset balancing quality and latency.
    Uses 720p webcam mode with optimizations.
    """

@classmethod
def quality_preset(cls) -> "WebcamConfig":
    """
    Create a preset optimized for quality with acceptable latency.
    Uses 1080p with some optimizations.
    """
```

#### Methods

```python
def to_gopro_settings(self) -> dict:
    """
    Convert configuration to GoPro API settings dictionary.

    Returns:
        Dictionary mapping GoPro setting IDs to values
    """
```

## Stream Consumers

### StreamConsumer (Abstract Base)

**Location**: `gopro_controller.stream_consumers.base`

Abstract base class for stream consumers.

#### Abstract Methods

```python
async def start(self) -> bool:
    """
    Start consuming the stream.

    Returns:
        True if started successfully, False otherwise
    """

async def stop(self) -> bool:
    """
    Stop consuming the stream.

    Returns:
        True if stopped successfully, False otherwise
    """

def get_output_info(self) -> Dict[str, Any]:
    """
    Get information about the output destination.

    Returns:
        Dictionary containing output information
    """

def validate_requirements(self) -> List[str]:
    """
    Validate that all requirements for this consumer are met.

    Returns:
        List of missing requirements (empty if all requirements met)
    """
```

#### Properties

```python
@property
def is_running(self) -> bool:
    """Check if the stream consumer is currently running."""
```

### V4L2Consumer

**Location**: `gopro_controller.stream_consumers.v4l2_consumer`

V4L2 stream consumer for creating virtual webcam devices.

#### Constructor

```python
V4L2Consumer(config: V4L2ConsumerConfig)
```

#### V4L2ConsumerConfig

```python
V4L2ConsumerConfig(
    stream_url: str,
    device_path: str = "/dev/video42",
    device_label: Optional[str] = "GoPro Webcam",
    video_size: Optional[str] = None,
    framerate: Optional[int] = 30,
    exclusive_caps: bool = True,
    max_buffers: int = 2,

    # Base config options
    buffer_size: int = 5000000,
    input_format: Optional[str] = None,
    video_codec: Optional[str] = None,
    pixel_format: str = "yuv420p",
    no_buffer: bool = True,
    low_latency: bool = True,
    tune_zerolatency: bool = True,
)
```

#### Class Methods

```python
@classmethod
def setup_v4l2loopback_device(
    cls,
    device_number: int = 42,
    device_label: str = "GoPro Webcam",
    exclusive_caps: bool = True,
) -> bool:
    """
    Set up a v4l2loopback device.

    Returns:
        True if setup successful, False otherwise
    """

@classmethod
def remove_v4l2loopback_device(cls) -> bool:
    """
    Remove the v4l2loopback module.

    Returns:
        True if removal successful, False otherwise
    """

@classmethod
def list_v4l2_devices(cls) -> List[Dict[str, str]]:
    """
    List available V4L2 devices.

    Returns:
        List of device information dictionaries
    """
```

## CLI Interface

### Main Entry Point

**Location**: `gopro_controller.cli.main`

```python
def main() -> None:
    """Main entry point for the CLI."""
```

### Command Structure

#### Global Options

```bash
gopro-webcam [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose          Enable verbose logging
  -i, --identifier TEXT  Last 4 digits of GoPro serial number
  --wired                Use wired (USB) connection instead of wireless
  --wifi-interface TEXT  WiFi interface to use for wireless connection
  --help                 Show help message
```

#### Commands

##### enable

```bash
gopro-webcam enable [OPTIONS]

Options:
  -p, --preset [low-latency|balanced|quality]  Configuration preset to use
  --resolution [480p|720p|1080p]               Override resolution setting
  --fov [wide|narrow|superview|linear]         Override field of view setting
  --no-optimization                            Disable latency optimizations
  --output [none|v4l2]                         Stream output type
  --v4l2-device TEXT                           V4L2 device path
  --setup-v4l2                                 Automatically setup v4l2loopback device
```

##### status

```bash
gopro-webcam status

Show GoPro connection and webcam status.
```

##### stop

```bash
gopro-webcam stop

Stop webcam mode on the GoPro.
```

##### presets

```bash
gopro-webcam presets

Show available configuration presets.
```

##### list-devices

```bash
gopro-webcam list-devices

List available V4L2 devices.
```

## Error Handling

### Exception Types

#### GoProController Exceptions

- Connection errors return `False` from methods
- All exceptions logged with detailed error messages
- Graceful degradation on non-critical errors

#### StreamConsumer Exceptions

- Requirement validation via `validate_requirements()`
- Start/stop methods return boolean success indicators
- Process management handles subprocess errors

### Error Response Format

```python
{
    "connected": bool,
    "error": str,  # Present if error occurred
    "connection_type": str,
    "streaming": bool,
    # ... additional status fields
}
```

## Usage Examples

### Basic Webcam Control

```python
import asyncio
from gopro_controller import GoProController, WebcamConfig

async def main():
    config = WebcamConfig.balanced_preset()

    async with GoProController(connection_type="wired") as controller:
        success = await controller.start_webcam(config)
        if success:
            print(f"Stream URL: {controller.get_stream_url()}")
            await asyncio.sleep(30)  # Stream for 30 seconds
            await controller.stop_webcam()

asyncio.run(main())
```

### V4L2 Virtual Webcam

```python
import asyncio
from gopro_controller import GoProController, WebcamConfig
from gopro_controller.stream_consumers import V4L2Consumer, V4L2ConsumerConfig

async def main():
    webcam_config = WebcamConfig.low_latency_preset()

    async with GoProController(connection_type="wired") as controller:
        await controller.start_webcam(webcam_config)

        v4l2_config = V4L2ConsumerConfig(
            stream_url=controller.get_stream_url(),
            device_path="/dev/video42"
        )

        consumer = V4L2Consumer(v4l2_config)

        if await consumer.start():
            print("Virtual webcam active at /dev/video42")
            await asyncio.sleep(60)  # Run for 1 minute
            await consumer.stop()

asyncio.run(main())
```

### Custom Configuration

```python
from gopro_controller.models.webcam_config import WebcamConfig, Resolution, FieldOfView

config = WebcamConfig(
    resolution=Resolution.RES_1080P,
    field_of_view=FieldOfView.LINEAR,
    disable_hypersmooth=True,
    use_preview_stream=False,
)

settings = config.to_gopro_settings()
print(f"GoPro API Settings: {settings}")
```

---

**API Version**: 0.1.0  
**Compatibility**: Python 3.11+  
**Dependencies**: open-gopro, pydantic, click, rich
