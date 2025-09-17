# GoPro Webcam Controller - Quick Start Guide

## Overview

This project provides a Python CLI application for controlling GoPro cameras as webcams with optimized low-latency settings. It's built following MVC patterns to prepare for future GTK GUI integration.

## Features Implemented

✅ **Core GoPro Control**

- Connect via USB (wired) or WiFi/BLE (wireless)
- Enable webcam mode with optimized settings
- Automatic low-latency configuration

✅ **Low-Latency Optimizations**

- Disables HyperSmooth stabilization (~1000ms latency reduction)
- Uses narrow field of view for reduced processing
- Configures standard bit rate for faster encoding
- Supports preview stream mode for absolute minimum latency

✅ **Stream Consumer Framework**

- Extensible architecture for multiple output types
- V4L2 virtual device support via FFmpeg
- Ready for future PipeWire integration

✅ **CLI Interface**

- Multiple configuration presets (low-latency, balanced, quality)
- V4L2 device management and auto-setup
- Real-time status monitoring

## Quick Start

### 1. Install Dependencies

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
make install

# Install development dependencies (optional)
make install-dev
```

### 2. Setup V4L2 (Linux)

```bash
# Install v4l2loopback
sudo apt install v4l2loopback-utils v4l2loopback-source

# Setup virtual webcam device
make setup-v4l2
```

### 3. Basic Usage

```bash
# Show available commands
poetry run gopro-webcam --help

# Show configuration presets
poetry run gopro-webcam presets

# Enable webcam with balanced settings
poetry run gopro-webcam enable --preset balanced

# Enable with V4L2 output (creates virtual webcam)
poetry run gopro-webcam enable --preset balanced --output v4l2

# Enable with automatic V4L2 setup
poetry run gopro-webcam enable --preset low-latency --output v4l2 --setup-v4l2

# Use wired connection
poetry run gopro-webcam enable --wired --preset balanced

# Override specific settings
poetry run gopro-webcam enable --preset balanced --resolution 1080p --fov linear
```

### 4. List Available Devices

```bash
# List V4L2 devices
poetry run gopro-webcam list-devices

# Check GoPro status
poetry run gopro-webcam status
```

## Configuration Presets

### Low-Latency Preset

- **Resolution**: 480p
- **Field of View**: Narrow
- **Stream Type**: Preview stream
- **Optimizations**: All enabled
- **Best for**: Real-time applications, video calls

### Balanced Preset (Default)

- **Resolution**: 720p
- **Field of View**: Narrow
- **Stream Type**: Webcam
- **Optimizations**: All enabled
- **Best for**: General webcam use

### Quality Preset

- **Resolution**: 1080p
- **Field of View**: Linear
- **Stream Type**: Webcam
- **Optimizations**: Latency optimizations enabled
- **Best for**: Recording, high-quality streaming

## Architecture

```
gopro_controller/
├── models/                 # Core business logic
│   ├── gopro_controller.py # GoPro connection and control
│   └── webcam_config.py    # Configuration management
├── views/                  # User interfaces
├── controllers/            # Application controllers
├── stream_consumers/       # Output backends
│   ├── base.py            # Base consumer interface
│   └── v4l2_consumer.py   # V4L2 virtual device support
└── cli/                   # Command-line interface
    └── main.py
```

## Development

```bash
# Run tests
make test

# Format code
make format

# Run linting
make lint

# Clean build artifacts
make clean

# Setup complete development environment
make dev-setup
```

## Low-Latency Research Implementation

The application implements research-based optimizations:

1. **HyperSmooth Disabled**: Removes ~1000ms of processing latency
2. **Narrow FOV**: Reduces pixel processing overhead
3. **Standard Bit Rate**: Faster encoding vs high bit rate
4. **Preview Stream Option**: Bypasses webcam encoding pipeline
5. **FFmpeg Optimizations**: No-buffer flags and low-latency tuning

## Future Enhancements

🔄 **Planned Features**:

- GTK GUI interface
- PipeWire output support
- RTMP streaming support
- Multiple camera support
- Configuration profiles

## Troubleshooting

### V4L2 Issues

```bash
# Check if v4l2loopback is loaded
lsmod | grep v4l2loopback

# List video devices
ls -la /dev/video*

# Check permissions
groups # Should include 'video' group
```

### GoPro Connection Issues

```bash
# Check wireless interface
ip link show

# Test with specific identifier (last 4 digits of serial)
poetry run gopro-webcam enable --identifier 1234

# Use wired connection if WiFi fails
poetry run gopro-webcam enable --wired
```

This implementation provides a solid foundation for GoPro webcam control with the architecture ready for future GUI and additional stream consumer implementations.
