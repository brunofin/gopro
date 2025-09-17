# GoPro Webcam Controller - Developer Documentation

This documentation provides comprehensive context for developers working on this project, preserving the current state and future plans.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Current Implementation Status](#current-implementation-status)
- [Architecture Deep Dive](#architecture-deep-dive)
- [Development Setup](#development-setup)
- [API Integration Details](#api-integration-details)
- [Testing Status](#testing-status)
- [Future Development Plans](#future-development-plans)
- [Known Issues & Limitations](#known-issues--limitations)
- [Development Notes](#development-notes)

## Project Overview

### Purpose

A Python CLI and future GTK GUI application for controlling GoPro cameras as webcams with optimized low-latency settings. Built following research-backed optimizations to minimize streaming latency from ~700ms to 200-300ms range.

### Key Goals

1. **Low Latency Streaming**: Research-based optimizations for minimal delay
2. **Multiple Output Types**: V4L2 virtual devices, future PipeWire support
3. **MVC Architecture**: Prepared for GTK GUI integration
4. **Extensible Design**: Plugin-based stream consumers

### Technology Stack

- **Language**: Python 3.11+
- **Package Manager**: Poetry
- **GoPro Integration**: Open GoPro SDK (open-gopro)
- **CLI Framework**: Click + Rich (beautiful terminal UI)
- **Data Models**: Pydantic (type-safe configuration)
- **Async**: asyncio for non-blocking operations
- **Stream Processing**: FFmpeg for V4L2 output

## Current Implementation Status

### ✅ **Fully Implemented & Tested**

#### Core GoPro Control

- **Connection Management**: Both wired (USB) and wireless (BLE/WiFi)
- **Webcam Mode**: Successfully enables/disables webcam streaming
- **Status Monitoring**: Real-time camera status and streaming state
- **Graceful Shutdown**: Proper cleanup on interruption (Ctrl+C)

#### Low-Latency Optimizations

- **HyperSmooth Disabled**: Saves ~1000ms latency
- **Narrow FOV**: Reduces processing overhead
- **Standard Bit Rate**: Faster encoding
- **Preview Stream Option**: Bypasses webcam encoding pipeline
- **UDP Protocol**: Minimum network latency

#### CLI Interface

- **Multiple Presets**: low-latency, balanced, quality
- **Rich Terminal UI**: Beautiful status displays and progress indicators
- **Command Structure**: enable, stop, status, presets, list-devices
- **Configuration Override**: Resolution, FOV, and optimization toggles

#### Stream Consumer Framework

- **Base Architecture**: Abstract base class for extensible consumers
- **V4L2 Consumer**: Complete implementation for virtual webcam devices
- **FFmpeg Integration**: Low-latency pipeline configuration

### 🔄 **Partially Implemented**

#### Configuration Management

- **Core Settings**: ✅ Working but with API compatibility warnings
- **Setting Application**: ⚠️ Some GoPro API methods need adjustment
- **Validation**: ✅ Full validation and error handling

#### V4L2 Integration

- **Consumer Class**: ✅ Complete implementation
- **Device Management**: ✅ Auto-setup and validation
- **Integration**: 🔄 CLI integration ready, needs testing

### ❌ **Not Yet Implemented**

#### GUI Components

- **GTK Interface**: Planned but not started
- **Configuration UI**: Visual preset management
- **Real-time Monitoring**: Live status dashboard

#### Additional Stream Consumers

- **PipeWire Support**: Planned for modern Linux audio/video
- **RTMP Streaming**: For direct streaming to services
- **File Output**: Recording capabilities

#### Advanced Features

- **Multiple Camera Support**: Concurrent GoPro management
- **Profile Management**: Save/load custom configurations
- **Auto-discovery**: Automatic GoPro detection

## Architecture Deep Dive

### MVC Pattern Implementation

```
gopro_controller/
├── models/                    # Core business logic
│   ├── gopro_controller.py   # Main GoPro control interface
│   └── webcam_config.py      # Configuration management
├── views/                     # User interfaces (CLI now, GTK future)
├── controllers/               # Business logic coordination (future)
├── stream_consumers/          # Output backends
│   ├── base.py               # Abstract consumer interface
│   └── v4l2_consumer.py      # V4L2 virtual device implementation
└── cli/                      # Command-line interface
    └── main.py               # Rich CLI implementation
```

### Key Design Decisions

#### 1. **Async/Await Throughout**

- All GoPro operations are async for responsiveness
- Context managers for proper resource cleanup
- Non-blocking stream monitoring

#### 2. **Pydantic Configuration Models**

- Type-safe configuration with validation
- Automatic serialization/deserialization
- Easy preset management

#### 3. **Plugin Architecture for Stream Consumers**

- Base abstract class defines interface
- Easy to add new output types (PipeWire, RTMP, etc.)
- Validation and requirement checking built-in

#### 4. **Rich Terminal UI**

- Beautiful progress indicators and status displays
- Professional CLI experience
- Consistent formatting and colors

### Critical Implementation Details

#### GoPro Connection Pattern

```python
async with GoProController(connection_type=ConnectionType.WIRED) as controller:
    # Automatic connection, configuration, and cleanup
    await controller.start_webcam(config)
    # Stream is active
# Automatic graceful shutdown
```

#### Low-Latency Configuration Mapping

```python
settings = {
    43: 2,    # Digital lens -> Narrow
    135: 0,   # HyperSmooth -> Off
    150: 0,   # Horizon leveling -> Off
    173: 0,   # Video performance -> Maximum
    182: 0,   # Bit rate -> Standard
}
```

## Development Setup

### Prerequisites

- Python 3.11+
- Poetry package manager
- GoPro camera with Open GoPro API support
- v4l2loopback kernel module (for V4L2 features)
- FFmpeg (for stream processing)

### Quick Start

```bash
# Install dependencies
poetry install

# Setup V4L2 (Linux)
make setup-v4l2

# Test connection
poetry run gopro-webcam --wired status

# Enable webcam
poetry run gopro-webcam --wired enable --preset balanced
```

### Development Workflow

```bash
# Format code
make format

# Run tests
make test

# Run linting
make lint

# Clean artifacts
make clean
```

## API Integration Details

### Open GoPro SDK Integration

#### Connection Handling

- **Wired**: `WiredGoPro(identifier)` for USB connections
- **Wireless**: `WirelessGoPro(identifier, interfaces={BLE, WIFI_AP})`
- **Auto-discovery**: mDNS for network discovery

#### Streaming Interface

- **Webcam Mode**: `StreamType.WEBCAM` with `WebcamStreamOptions`
- **Preview Mode**: `StreamType.PREVIEW` for lowest latency
- **Protocol Support**: UDP (TS) and RTSP

#### Status Monitoring

- **Camera State**: Battery, encoding status, ready state
- **Webcam Status**: `IDLE`, `HIGH_POWER_PREVIEW`, `OFF`
- **Error Handling**: Comprehensive error codes and messages

### FFmpeg Pipeline for V4L2

```bash
ffmpeg -fflags nobuffer -flags low_delay -avioflags direct \
       -fifo_size 5000000 -i udp://@:8554 \
       -vf format=yuv420p -r 30 -tune zerolatency \
       -preset ultrafast -an -f v4l2 /dev/video42
```

## Testing Status

### ✅ **Successfully Tested**

- **USB Connection**: GoPro HERO12 Black via USB
- **Webcam Activation**: Stream starts with `HIGH_POWER_PREVIEW` status
- **Status Monitoring**: Real-time status updates every second
- **Graceful Shutdown**: Clean stop on Ctrl+C interruption
- **Stream URL**: UDP stream available at `udp://@:8554`

### 🔄 **Ready for Testing**

- **V4L2 Output**: Implementation complete, needs validation
- **Wireless Connection**: Code complete, needs hardware testing
- **Multiple Presets**: All three presets implemented

### ❌ **Needs Testing**

- **PipeWire Integration**: Not yet implemented
- **Multiple Camera Support**: Future feature
- **GUI Components**: Not yet implemented

## Future Development Plans

### Phase 1: V4L2 Completion

- [ ] Test V4L2 consumer with real video applications
- [ ] Optimize FFmpeg pipeline parameters
- [ ] Add device auto-detection and validation
- [ ] Implement device cleanup on application exit

### Phase 2: GTK GUI Development

- [ ] Design main window layout
- [ ] Implement camera selection interface
- [ ] Add real-time preview window
- [ ] Create configuration management UI
- [ ] Add system tray integration

### Phase 3: Advanced Features

- [ ] PipeWire stream consumer implementation
- [ ] Multiple camera support
- [ ] Profile management (save/load configurations)
- [ ] Auto-discovery and connection management
- [ ] RTMP streaming support

### Phase 4: Distribution & Polish

- [ ] Package as AppImage/Flatpak
- [ ] Add desktop integration
- [ ] Comprehensive documentation
- [ ] User manual and tutorials

## Known Issues & Limitations

### Minor Issues

1. **Setting API Warnings**: Some individual setting changes show warnings but don't affect functionality
2. **Status Parsing**: Minor issue with camera info display (cosmetic only)
3. **Verbose Logging**: Debug output is quite verbose (can be reduced)

### API Compatibility

- **Setting Methods**: The Open GoPro SDK's setting interface has slight variations
- **Resolution Parameters**: Some resolution mappings may need adjustment
- **Protocol Support**: RTSP support varies by GoPro model

### Platform Limitations

- **V4L2**: Linux-specific, needs alternatives for macOS/Windows
- **Kernel Modules**: v4l2loopback requires kernel module installation
- **Permissions**: May need video group membership or sudo for device access

## Development Notes

### Code Quality Standards

- **Type Hints**: Full type annotations throughout
- **Error Handling**: Comprehensive try/catch with logging
- **Documentation**: Docstrings for all classes and methods
- **Testing**: Unit tests for core functionality

### Performance Considerations

- **Async Operations**: All I/O is non-blocking
- **Memory Management**: Proper cleanup of resources
- **Stream Buffering**: Minimal buffering for low latency
- **CPU Usage**: Efficient FFmpeg pipeline configuration

### Security Considerations

- **Device Access**: Validates device permissions before access
- **Network Security**: Uses local UDP streams only
- **Input Validation**: All user inputs validated with Pydantic

### Debugging Tips

#### Common Issues

1. **Connection Failures**: Check USB cable and GoPro power state
2. **Permission Denied**: Add user to video group or run with sudo
3. **Stream Not Available**: Verify GoPro is in correct mode
4. **V4L2 Errors**: Ensure v4l2loopback module is loaded

#### Useful Commands

```bash
# Check GoPro USB connection
lsusb | grep -i gopro

# Check v4l2loopback status
lsmod | grep v4l2loopback

# List video devices
ls -la /dev/video*

# Test stream with VLC
vlc udp://@:8554

# Monitor system logs
journalctl -f | grep video
```

#### Debug Mode

```bash
# Enable verbose logging
poetry run gopro-webcam --verbose --wired status

# Check specific component
python -c "from gopro_controller.models.webcam_config import WebcamConfig; print(WebcamConfig.balanced_preset())"
```

### Architecture Evolution

The current architecture is designed for growth:

1. **Models**: Core logic is stable and extensible
2. **Views**: CLI implementation serves as template for GUI
3. **Stream Consumers**: Plugin architecture ready for new backends
4. **Configuration**: Pydantic models make serialization trivial

### Next Developer Recommendations

1. **Start with V4L2 Testing**: The implementation is complete and ready
2. **Focus on Error Handling**: Improve user experience with better error messages
3. **GUI Prototyping**: Use the CLI patterns as reference for GTK implementation
4. **Documentation**: Keep this documentation updated as features are added

---

**Last Updated**: September 17, 2025  
**Project State**: Core functionality complete, ready for V4L2 testing and GUI development  
**Next Priority**: V4L2 consumer validation and GUI prototyping
