# Architecture Documentation - GoPro Webcam Controller

## System Architecture Overview

This document details the architectural decisions, patterns, and structure of the GoPro Webcam Controller project.

## Core Architecture Principles

### 1. **MVC (Model-View-Controller) Pattern**

Designed for future GUI expansion while maintaining clean separation of concerns.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Models      │    │   Controllers   │    │      Views      │
│                 │    │                 │    │                 │
│ • GoPro Control │    │ • Business      │    │ • CLI (current) │
│ • Configuration │    │   Logic         │    │ • GTK (future)  │
│ • Stream State  │◄──►│ • Coordination  │◄──►│ • Web (future)  │
│                 │    │ • Validation    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2. **Plugin Architecture for Stream Consumers**

Extensible system for different output types:

```
┌─────────────────────────────────────────────┐
│            StreamConsumer (ABC)             │
│  ┌─────────────────────────────────────────┐│
│  │  • validate_requirements()             ││
│  │  • start() / stop()                    ││
│  │  • get_output_info()                   ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│ V4L2Consumer │ │PipeWireConsumer│ │ RTMPConsumer│
│              │ │  (future)   │ │   (future)  │
│ • FFmpeg     │ │ • PipeWire  │ │ • RTMP      │
│ • v4l2loop   │ │ • Low-lat   │ │ • Streaming │
└──────────────┘ └─────────────┘ └─────────────┘
```

### 3. **Async/Await Throughout**

All I/O operations are asynchronous for responsive UI and proper resource management.

## Package Structure

```
gopro_controller/
├── __init__.py                 # Package exports
├── models/                     # Core business logic
│   ├── __init__.py
│   ├── gopro_controller.py     # Main GoPro interface
│   └── webcam_config.py        # Configuration models
├── views/                      # User interfaces
│   └── __init__.py
├── controllers/                # Business logic coordination
│   └── __init__.py
├── stream_consumers/           # Output backends
│   ├── __init__.py
│   ├── base.py                # Abstract base classes
│   └── v4l2_consumer.py       # V4L2 implementation
└── cli/                       # Command-line interface
    ├── __init__.py
    └── main.py                # CLI implementation
```

## Core Components Deep Dive

### Models Layer

#### GoProController (`models/gopro_controller.py`)

**Responsibility**: Primary interface for GoPro camera control

**Key Features**:

- Connection management (wired/wireless)
- Webcam mode control
- Stream URL management
- Status monitoring
- Graceful resource cleanup

**Design Patterns**:

- **Async Context Manager**: Automatic resource management
- **State Machine**: Tracks connection and streaming states
- **Observer Pattern**: Status monitoring callbacks

```python
class GoProController:
    async def __aenter__(self) -> "GoProController":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._streaming_active:
            await self.stop_webcam()
        await self.disconnect()
```

#### WebcamConfig (`models/webcam_config.py`)

**Responsibility**: Configuration management with research-based optimizations

**Key Features**:

- Pydantic data validation
- Preset management (low-latency, balanced, quality)
- GoPro API setting mapping
- Research-backed latency optimizations

**Design Patterns**:

- **Configuration Object**: Immutable configuration state
- **Factory Pattern**: Preset creation methods
- **Strategy Pattern**: Different optimization strategies

```python
class WebcamConfig(BaseModel):
    @classmethod
    def low_latency_preset(cls) -> "WebcamConfig":
        return cls(
            resolution=Resolution.RES_480P,
            use_preview_stream=True,
            disable_hypersmooth=True,
            # ... optimized for minimum latency
        )
```

### Stream Consumers Layer

#### Base Classes (`stream_consumers/base.py`)

**Responsibility**: Define plugin interface for stream outputs

**Key Abstractions**:

- `StreamConsumer`: Abstract base for all consumers
- `StreamConsumerConfig`: Base configuration model
- `StreamConsumerType`: Enumeration of consumer types

**Design Patterns**:

- **Template Method**: Common FFmpeg pipeline construction
- **Strategy Pattern**: Interchangeable output strategies
- **Factory Pattern**: Consumer creation and validation

#### V4L2Consumer (`stream_consumers/v4l2_consumer.py`)

**Responsibility**: Virtual webcam device creation via v4l2loopback

**Key Features**:

- FFmpeg pipeline management
- Device validation and setup
- Low-latency parameter optimization
- Automatic cleanup

**FFmpeg Pipeline Design**:

```bash
ffmpeg \
  -fflags nobuffer          # Disable input buffering
  -flags low_delay          # Low delay mode
  -avioflags direct         # Direct I/O
  -fifo_size 5000000        # Input buffer size
  -i udp://@:8554           # GoPro stream input
  -vf format=yuv420p        # Pixel format
  -r 30                     # Frame rate
  -tune zerolatency         # Zero latency tuning
  -preset ultrafast         # Fastest encoding
  -an                       # No audio
  -f v4l2                   # V4L2 output format
  /dev/video42              # Virtual device
```

### Views Layer

#### CLI Interface (`cli/main.py`)

**Responsibility**: Command-line user interface with Rich formatting

**Key Features**:

- Click command framework
- Rich terminal UI (tables, progress bars, panels)
- Async command handling
- Comprehensive help and validation

**Command Structure**:

```
gopro-webcam [global-options] command [command-options]

Global Options:
  --verbose, --wired, --identifier, --wifi-interface

Commands:
  enable     # Start webcam with configuration
  stop       # Stop webcam streaming
  status     # Show camera status
  presets    # List configuration presets
  list-devices # Show V4L2 devices
```

## Data Flow Architecture

### Webcam Activation Flow

```
CLI Command
    │
    ▼
Parse Args & Create Config
    │
    ▼
Initialize GoProController
    │
    ▼
Connect to GoPro (USB/WiFi)
    │
    ▼
Apply Configuration Settings
    │
    ▼
Start Webcam Stream
    │
    ▼
Create Stream Consumer (V4L2)
    │
    ▼
Start FFmpeg Pipeline
    │
    ▼
Monitor Status Loop
    │
    ▼ (Ctrl+C)
Stop Consumer → Stop Webcam → Disconnect
```

### Configuration Flow

```
User Input (CLI)
    │
    ▼
Preset Selection
    │
    ▼
Override Application
    │
    ▼
Pydantic Validation
    │
    ▼
GoPro API Settings Map
    │
    ▼
Apply via SDK
```

## Error Handling Strategy

### Layered Error Handling

1. **SDK Level**: Open GoPro SDK error codes
2. **Model Level**: Business logic validation
3. **Consumer Level**: FFmpeg and device validation
4. **CLI Level**: User-friendly error messages

### Error Categories

- **Connection Errors**: GoPro not found, permission denied
- **Configuration Errors**: Invalid settings, unsupported options
- **Stream Errors**: Network issues, encoding problems
- **Device Errors**: V4L2 setup, permission issues

## Performance Considerations

### Memory Management

- **Async Context Managers**: Automatic resource cleanup
- **Stream Buffering**: Minimal buffering for low latency
- **Process Management**: Proper FFmpeg process lifecycle

### CPU Optimization

- **Async I/O**: Non-blocking operations
- **FFmpeg Tuning**: Ultra-fast presets and zero-latency tuning
- **Efficient Polling**: Smart status update intervals

### Network Efficiency

- **UDP Streaming**: Minimal protocol overhead
- **Local Processing**: No unnecessary network hops
- **Buffer Management**: Optimal buffer sizes for latency

## Security Architecture

### Access Control

- **Device Permissions**: Validate access to video devices
- **Network Security**: Local UDP streams only
- **Input Validation**: All user inputs validated via Pydantic

### Process Security

- **Subprocess Management**: Secure FFmpeg process execution
- **Resource Limits**: Prevent resource exhaustion
- **Clean Termination**: Proper cleanup on all exit paths

## Extension Points

### Adding New Stream Consumers

1. Inherit from `StreamConsumer`
2. Implement abstract methods
3. Add to `StreamConsumerType` enum
4. Register in CLI command options

```python
class NewConsumer(StreamConsumer):
    def validate_requirements(self) -> List[str]:
        # Check dependencies

    async def start(self) -> bool:
        # Start consumption

    async def stop(self) -> bool:
        # Stop and cleanup
```

### Adding New Configuration Presets

1. Create new preset method in `WebcamConfig`
2. Add to CLI preset choices
3. Document performance characteristics

### Adding New Views (GUI)

1. Create new view package
2. Import and use existing models
3. Implement async event handling
4. Follow MVC separation

## Testing Architecture

### Unit Testing Strategy

- **Model Testing**: Configuration validation, preset generation
- **Consumer Testing**: Mock FFmpeg, device validation
- **CLI Testing**: Command parsing, error handling

### Integration Testing

- **GoPro Hardware**: Real device testing
- **Stream Validation**: End-to-end stream testing
- **Performance Testing**: Latency measurement

### Mocking Strategy

- **GoPro SDK**: Mock for unit tests
- **FFmpeg Processes**: Mock subprocess calls
- **Device Files**: Mock V4L2 devices

## Future Architecture Evolution

### Planned Extensions

1. **GUI Layer**: GTK4 interface with async support
2. **Multi-Camera**: Support for multiple simultaneous GoPros
3. **Plugin System**: Dynamic consumer loading
4. **Configuration Persistence**: Save/load user profiles

### Scalability Considerations

- **Resource Pooling**: Shared FFmpeg processes
- **Event System**: Pub/sub for status updates
- **Configuration Management**: Database for complex setups

---

**Architecture Status**: Core foundation complete and validated  
**Design Principles**: MVC, Plugin Architecture, Async/Await  
**Extension Ready**: New consumers, views, and features can be added cleanly
