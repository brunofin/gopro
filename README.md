# GoPro Webcam Controller

A Python CLI and GUI application for controlling GoPro cameras as webcams with optimized low-latency settings.

## Features

- Connect to GoPro cameras via USB or Wi-Fi
- Enable webcam mode with optimized low-latency settings
- Support for multiple stream consumption modes:
  - V4L2 virtual device (via ffmpeg)
  - PipeWire virtual camera (modern Linux)
  - Future: RTMP streaming support
- CLI interface with plans for GTK GUI
- Follows MVC architecture pattern

## Installation

### Prerequisites

- Python 3.11 or higher
- GoPro camera with Open GoPro API support
- For V4L2 support: `v4l2loopback` kernel module and `ffmpeg`
- For PipeWire support: GStreamer and PipeWire (modern Linux systems)

### Install Dependencies

```bash
# Install poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# For GUI support (future)
poetry install --extras gui

# For PipeWire support (modern Linux)
poetry install --extras pipewire

# For everything
poetry install --extras all
```

### PipeWire Setup (Modern Linux)

```bash
# Install GStreamer and PipeWire support
# Fedora:
sudo dnf install python3-gobject gstreamer1 gstreamer1-plugins-* pipewire

# Ubuntu:
sudo apt install python3-gi gstreamer1.0-* python3-gst-1.0 pipewire

# Arch:
sudo pacman -S python-gobject gst-plugins-base gst-plugins-good pipewire

# Check support
poetry run gopro-webcam check-pipewire
```

### V4L2 Setup (Traditional Linux)

```bash
# Install v4l2loopback
sudo apt install v4l2loopback-utils v4l2loopback-source
# or on Arch Linux:
# sudo pacman -S v4l2loopback-dkms

# Load the module
sudo modprobe v4l2loopback video_nr=42 card_label="GoPro Webcam"
```

## Usage

### CLI

```bash
# Basic webcam mode activation
poetry run gopro-webcam enable

# Specify device identifier
poetry run gopro-webcam enable --identifier ABCD

# Use wired connection
poetry run gopro-webcam enable --wired

# Enable with V4L2 output
poetry run gopro-webcam enable --output v4l2 --device /dev/video42

# Enable with PipeWire output (modern Linux)
poetry run gopro-webcam enable --preset balanced --output pipewire

# Enable with automatic V4L2 setup
poetry run gopro-webcam enable --preset low-latency --output v4l2 --setup-v4l2

# Check what's supported on your system
poetry run gopro-webcam check-pipewire
poetry run gopro-webcam list-devices

# Show help
poetry run gopro-webcam --help
```

## Architecture

The project follows an MVC pattern to prepare for future GTK integration:

- `models/`: Core GoPro controller and webcam management logic
- `views/`: CLI interface (and future GTK views)
- `controllers/`: Business logic coordinating models and views
- `stream_consumers/`: Pluggable stream consumption backends

## Low Latency Optimizations

Based on extensive research, this application automatically configures:

- Disables HyperSmooth stabilization
- Sets narrow digital lens (FOV)
- Uses standard bit rate (not high)
- Configures optimal resolution settings
- Minimizes buffering in stream processing

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run mypy gopro_controller

# Linting
poetry run pylint gopro_controller
```

## License

MIT License - see LICENSE file for details.
