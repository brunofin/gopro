# GoPro Webcam Controller - Development Makefile

.PHONY: install install-dev test lint format clean setup-v4l2 help

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install project dependencies"
	@echo "  install-dev  - Install project with development dependencies"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting (mypy, pylint)"
	@echo "  format       - Format code (black, isort)"
	@echo "  clean        - Clean build artifacts"
	@echo "  setup-v4l2   - Setup v4l2loopback kernel module"
	@echo "  help         - Show this help message"

# Installation
install:
	poetry install

install-dev:
	poetry install --with dev

# Testing
test:
	poetry run pytest

test-verbose:
	poetry run pytest -v

# Code quality
lint:
	poetry run mypy gopro_controller
	poetry run pylint gopro_controller

format:
	poetry run black gopro_controller tests
	poetry run isort gopro_controller tests

# Development helpers
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

# V4L2 setup (requires sudo)
setup-v4l2:
	@echo "Setting up v4l2loopback kernel module..."
	sudo modprobe v4l2loopback video_nr=42 card_label="GoPro Webcam" exclusive_caps=1
	@echo "V4L2 device created at /dev/video42"
	@echo "Use 'sudo modprobe -r v4l2loopback' to remove"

# List v4l2 devices
list-v4l2:
	@echo "Available V4L2 devices:"
	@ls -la /dev/video* 2>/dev/null || echo "No video devices found"

# Quick development workflow
dev-setup: install-dev setup-v4l2
	@echo "Development environment ready!"

# Run the CLI
run-help:
	poetry run gopro-webcam --help

run-presets:
	poetry run gopro-webcam presets

run-devices:
	poetry run gopro-webcam list-devices

# Example usage
example-enable:
	poetry run gopro-webcam enable --preset balanced --output v4l2

example-enable-lowlat:
	poetry run gopro-webcam enable --preset low-latency --output v4l2 --setup-v4l2

example-enable-pipewire:
	poetry run gopro-webcam enable --preset balanced --output pipewire

check-support:
	poetry run gopro-webcam check-pipewire