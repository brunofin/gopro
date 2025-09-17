# GoPro Webcam Controller

A Python CLI and GUI application for controlling GoPro cameras as webcams with optimized low-latency settings.

## Features

- Connect to GoPro cameras via USB or Wi-Fi
- Enable webcam mode with optimized low-latency settings
- Support for multiple stream consumption modes:
  - V4L2 virtual device (via ffmpeg)
  - Future: PipeWire device support
- CLI interface with plans for GTK GUI
- Follows MVC architecture pattern

## Installation

### Prerequisites

- Python 3.11 or higher
- GoPro camera with Open GoPro API support
- For V4L2 support: `v4l2loopback` kernel module and `ffmpeg`

### Install Dependencies

```bash
# Install poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# For GUI support (future)
poetry install --extras gui

# For PipeWire support (future)
poetry install --extras pipewire
```

### V4L2 Setup (Linux)

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
