"""
Main CLI interface for GoPro webcam controller.

Provides commands to connect, configure, and control GoPro cameras as webcams.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from ..models.gopro_controller import GoProController, ConnectionType
from ..models.webcam_config import WebcamConfig
from ..stream_consumers import V4L2Consumer, V4L2ConsumerConfig, PipeWireConsumer, PipeWireConsumerConfig


console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Setup logging with rich formatting."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--identifier", "-i", help="Last 4 digits of GoPro serial number")
@click.option("--wired", is_flag=True, help="Use wired (USB) connection instead of wireless")
@click.option("--wifi-interface", help="WiFi interface to use for wireless connection")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, identifier: Optional[str], wired: bool, wifi_interface: Optional[str]) -> None:
    """GoPro Webcam Controller - Control your GoPro as a webcam with optimized settings."""
    setup_logging(verbose)
    
    # Store common options in context
    ctx.ensure_object(dict)
    ctx.obj["identifier"] = identifier
    ctx.obj["connection_type"] = ConnectionType.WIRED if wired else ConnectionType.WIRELESS
    ctx.obj["wifi_interface"] = wifi_interface


@cli.command()
@click.option("--preset", "-p", type=click.Choice(["low-latency", "balanced", "quality"]), 
              default="balanced", help="Configuration preset to use")
@click.option("--resolution", type=click.Choice(["480p", "720p", "1080p"]), 
              help="Override resolution setting")
@click.option("--fov", type=click.Choice(["wide", "narrow", "superview", "linear"]), 
              help="Override field of view setting")
@click.option("--no-optimization", is_flag=True, help="Disable latency optimizations")
@click.option("--output", type=click.Choice(["none", "v4l2", "pipewire"]), default="none",
              help="Stream output type")
@click.option("--v4l2-device", default="/dev/video42", 
              help="V4L2 device path (when using --output v4l2)")
@click.option("--setup-v4l2", is_flag=True, 
              help="Automatically setup v4l2loopback device")
@click.option("--pipewire-node", default="GoPro Camera",
              help="PipeWire node name (when using --output pipewire)")
@click.pass_context
def enable(
    ctx: click.Context, 
    preset: str, 
    resolution: Optional[str], 
    fov: Optional[str], 
    no_optimization: bool,
    output: str,
    v4l2_device: str,
    setup_v4l2: bool,
    pipewire_node: str,
) -> None:
    """Enable webcam mode on the GoPro."""
    asyncio.run(_enable_webcam(ctx, preset, resolution, fov, no_optimization, output, v4l2_device, setup_v4l2, pipewire_node))


async def _enable_webcam(
    ctx: click.Context, 
    preset: str, 
    resolution: Optional[str], 
    fov: Optional[str], 
    no_optimization: bool,
    output: str,
    v4l2_device: str,
    setup_v4l2: bool,
    pipewire_node: str,
) -> None:
    """Async implementation of enable command."""
    
    # Setup v4l2loopback if requested
    if setup_v4l2 and output == "v4l2":
        console.print("[blue]Setting up v4l2loopback device...")
        device_number = int(v4l2_device.split('video')[-1]) if 'video' in v4l2_device else 42
        if V4L2Consumer.setup_v4l2loopback_device(device_number):
            console.print("[green]✓[/green] v4l2loopback device created")
        else:
            console.print("[red]Failed to setup v4l2loopback device")
            sys.exit(1)
    
    # Create configuration based on preset
    if preset == "low-latency":
        config = WebcamConfig.low_latency_preset()
    elif preset == "quality":
        config = WebcamConfig.quality_preset()
    else:  # balanced
        config = WebcamConfig.balanced_preset()
    
    # Apply overrides
    if resolution:
        config.resolution = resolution
    if fov:
        config.field_of_view = fov
    if no_optimization:
        config.disable_hypersmooth = False
        config.disable_horizon_leveling = False
    
    controller = GoProController(
        identifier=ctx.obj["identifier"],
        connection_type=ctx.obj["connection_type"],
        wifi_interface=ctx.obj["wifi_interface"],
    )
    
    stream_consumer = None
    
    try:
        with console.status("[blue]Connecting to GoPro..."):
            async with controller:
                # Test connection
                if not await controller.test_connection():
                    console.print("[red]Failed to establish connection to GoPro")
                    sys.exit(1)
                
                console.print("[green]✓[/green] Connected to GoPro")
                
                # Show camera info
                info = await controller.get_camera_info()
                if info:
                    _display_camera_info(info)
                
                # Start webcam
                with console.status("[blue]Configuring and starting webcam..."):
                    success = await controller.start_webcam(config)
                
                if not success:
                    console.print("[red]Failed to enable webcam mode")
                    sys.exit(1)
                
                console.print("[green]✓[/green] Webcam mode enabled successfully!")
                
                # Show configuration details
                stream_url = controller.get_stream_url()
                _display_webcam_config(config, stream_url)
                
                # Setup stream consumer if requested
                if output == "v4l2" and stream_url:
                    console.print(f"\n[blue]Setting up V4L2 output to {v4l2_device}...")
                    
                    v4l2_config = V4L2ConsumerConfig(
                        stream_url=stream_url,
                        device_path=v4l2_device,
                        device_label="GoPro Webcam",
                    )
                    
                    stream_consumer = V4L2Consumer(v4l2_config)
                    
                    # Validate requirements
                    missing = stream_consumer.validate_requirements()
                    if missing:
                        console.print(f"[red]Missing requirements for V4L2 output: {', '.join(missing)}")
                        console.print("[yellow]Stream will continue without V4L2 output")
                    else:
                        with console.status("[blue]Starting V4L2 stream consumer..."):
                            if await stream_consumer.start():
                                console.print(f"[green]✓[/green] V4L2 output active on {v4l2_device}")
                                console.print(f"[yellow]You can now use {v4l2_device} as a webcam in your applications")
                            else:
                                console.print("[red]Failed to start V4L2 output")

                elif output == "pipewire" and stream_url:
                    console.print(f"\n[blue]Setting up PipeWire output as '{pipewire_node}'...")
                    
                    pipewire_config = PipeWireConsumerConfig(
                        stream_url=stream_url,
                        node_name=pipewire_node,
                        client_name="GoPro Webcam Controller",
                        format="mpegts-h264",  # GoPro uses MPEG-TS
                        jitter_ms=0,  # LAN - no jitter buffer needed
                        prefer_hardware_decode=True,
                    )
                    
                    stream_consumer = PipeWireConsumer(pipewire_config)
                    
                    # Validate requirements
                    missing = stream_consumer.validate_requirements()
                    if missing:
                        console.print(f"[red]Missing requirements for PipeWire output: {', '.join(missing)}")
                        console.print("[yellow]Stream will continue without PipeWire output")
                        console.print("[blue]Install: sudo dnf install python3-gobject gstreamer1 gstreamer1-plugins-*")
                    else:
                        with console.status("[blue]Starting PipeWire stream consumer..."):
                            if await stream_consumer.start():
                                console.print(f"[green]✓[/green] PipeWire node active: '{pipewire_node}'")
                                console.print(f"[yellow]You can now select '{pipewire_node}' as a camera in your applications")
                                
                                # Show hardware decoder info
                                output_info = stream_consumer.get_output_info()
                                if hasattr(stream_consumer, '_choose_h264_decoder'):
                                    decoder = stream_consumer._choose_h264_decoder()
                                    console.print(f"[dim]Using decoder: {decoder}")
                            else:
                                console.print("[red]Failed to start PipeWire output")
                
                # Keep running until user interrupts
                if output == "none":
                    console.print(f"\n[yellow]Webcam stream is active at {stream_url}")
                    console.print("[yellow]Press Ctrl+C to stop.")
                elif output == "v4l2":
                    console.print("\n[yellow]V4L2 virtual webcam is now active. Press Ctrl+C to stop.[/yellow]")
                elif output == "pipewire":
                    console.print("\n[yellow]PipeWire virtual camera is now active. Press Ctrl+C to stop.[/yellow]")
                else:
                    console.print("\n[yellow]Webcam is now active. Press Ctrl+C to stop.[/yellow]")
                
                # Set up signal handler for clean shutdown
                shutdown_event = asyncio.Event()
                
                def signal_handler():
                    shutdown_event.set()
                
                # Register signal handler
                loop = asyncio.get_event_loop()
                for sig in (signal.SIGTERM, signal.SIGINT):
                    loop.add_signal_handler(sig, signal_handler)
                
                try:
                    # Wait for shutdown signal
                    await shutdown_event.wait()
                except KeyboardInterrupt:
                    pass
                finally:
                    console.print("\n[blue]Stopping webcam...")
                    
                    # Stop stream consumer first
                    if stream_consumer:
                        try:
                            await stream_consumer.stop()
                            if output == "v4l2":
                                console.print("[green]✓[/green] V4L2 output stopped")
                            elif output == "pipewire":
                                console.print("[green]✓[/green] PipeWire output stopped")
                        except Exception as e:
                            console.print(f"[yellow]Warning: Error stopping stream consumer: {e}")
                    
                    # Stop webcam
                    try:
                        await controller.stop_webcam()
                        console.print("[green]✓[/green] Webcam stopped")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Error stopping webcam: {e}")
                    
    except KeyboardInterrupt:
        console.print("\n[blue]Operation cancelled")
        if stream_consumer:
            await stream_consumer.stop()
    except Exception as e:
        console.print(f"[red]Error: {e}")
        if stream_consumer:
            await stream_consumer.stop()
        sys.exit(1)


@cli.command()
@click.pass_context
def stop(ctx: click.Context) -> None:
    """Stop webcam mode on the GoPro."""
    asyncio.run(_stop_webcam(ctx))


async def _stop_webcam(ctx: click.Context) -> None:
    """Async implementation of stop command."""
    controller = GoProController(
        identifier=ctx.obj["identifier"],
        connection_type=ctx.obj["connection_type"],
        wifi_interface=ctx.obj["wifi_interface"],
    )
    
    try:
        with console.status("[blue]Connecting to GoPro..."):
            async with controller:
                if not await controller.test_connection():
                    console.print("[red]Failed to connect to GoPro")
                    sys.exit(1)
                
                console.print("[green]✓[/green] Connected to GoPro")
                
                with console.status("[blue]Stopping webcam..."):
                    success = await controller.stop_webcam()
                
                if success:
                    console.print("[green]✓[/green] Webcam stopped successfully")
                else:
                    console.print("[yellow]Webcam was not active or failed to stop")
                    
    except Exception as e:
        console.print(f"[red]Error: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show GoPro connection and webcam status."""
    asyncio.run(_show_status(ctx))


async def _show_status(ctx: click.Context) -> None:
    """Async implementation of status command."""
    controller = GoProController(
        identifier=ctx.obj["identifier"],
        connection_type=ctx.obj["connection_type"],
        wifi_interface=ctx.obj["wifi_interface"],
    )
    
    try:
        with console.status("[blue]Connecting to GoPro..."):
            async with controller:
                if not await controller.test_connection():
                    console.print("[red]Failed to connect to GoPro")
                    sys.exit(1)
                
                info = await controller.get_camera_info()
                if info:
                    _display_camera_info(info, detailed=True)
                else:
                    console.print("[red]Failed to get camera information")
                    
    except Exception as e:
        console.print(f"[red]Error: {e}")
        sys.exit(1)


@cli.command()
def list_devices() -> None:
    """List available V4L2 devices."""
    console.print("\n[bold]Available V4L2 Devices:[/bold]\n")
    
    devices = V4L2Consumer.list_v4l2_devices()
    
    if not devices:
        console.print("[yellow]No V4L2 devices found")
        console.print("Make sure v4l2loopback is loaded or you have other video devices")
        return
    
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Device Path", style="cyan")
    table.add_column("Device Name", style="green")
    
    for device in devices:
        table.add_row(device["path"], device["name"])
    
    console.print(table)
    console.print(f"\n[blue]Found {len(devices)} V4L2 device(s)")


@cli.command()
def check_pipewire() -> None:
    """Check PipeWire support status."""
    console.print("\n[bold]PipeWire Support Status:[/bold]\n")
    
    status = PipeWireConsumer.check_pipewire_support()
    
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    # GStreamer availability
    gst_status = "✅ Available" if status["gstreamer_available"] else "❌ Missing"
    table.add_row("GStreamer Python", gst_status)
    
    # PipeWire service
    pw_status = "✅ Running" if status["pipewire_running"] else "❌ Not running"
    table.add_row("PipeWire Service", pw_status)
    
    # PipeWire sink
    sink_status = "✅ Available" if status["pipewiresink_available"] else "❌ Missing"
    table.add_row("PipeWire GStreamer Sink", sink_status)
    
    # H.264 decoders
    decoders = status["h264_decoders"]
    if decoders:
        decoder_list = ", ".join(decoders)
        table.add_row("H.264 Decoders", f"✅ {decoder_list}")
    else:
        table.add_row("H.264 Decoders", "❌ None found")
    
    console.print(table)
    
    # Installation hints
    if not status["gstreamer_available"]:
        console.print("\n[yellow]To install GStreamer:")
        console.print("  Fedora: sudo dnf install python3-gobject gstreamer1 gstreamer1-plugins-*")
        console.print("  Ubuntu: sudo apt install python3-gi gstreamer1.0-* python3-gst-1.0")
        console.print("  Arch:   sudo pacman -S python-gobject gst-plugins-base gst-plugins-good")
    
    if not status["pipewire_running"]:
        console.print("\n[yellow]To start PipeWire:")
        console.print("  systemctl --user enable --now pipewire")
    
    # Overall recommendation
    all_good = (status["gstreamer_available"] and status["pipewire_running"] and 
                status["pipewiresink_available"] and len(status["h264_decoders"]) > 0)
    
    if all_good:
        console.print("\n[green]✅ PipeWire consumer ready to use!")
    else:
        console.print("\n[red]❌ PipeWire consumer not ready - install missing components")


@cli.command()
def presets() -> None:
    """Show available configuration presets."""
    console.print("\n[bold]Available Configuration Presets:[/bold]\n")
    
    # Create example configs
    presets = {
        "low-latency": WebcamConfig.low_latency_preset(),
        "balanced": WebcamConfig.balanced_preset(),
        "quality": WebcamConfig.quality_preset(),
    }
    
    for name, config in presets.items():
        table = Table(title=f"{name.title()} Preset", show_header=False)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Resolution", config.resolution.value)
        table.add_row("Field of View", config.field_of_view.value)
        table.add_row("Bit Rate", config.bit_rate.value)
        table.add_row("Protocol", config.protocol.value)
        table.add_row("Use Preview Stream", "Yes" if config.use_preview_stream else "No")
        table.add_row("HyperSmooth Disabled", "Yes" if config.disable_hypersmooth else "No")
        table.add_row("Horizon Leveling Disabled", "Yes" if config.disable_horizon_leveling else "No")
        
        console.print(table)
        console.print()


def _display_camera_info(info: dict, detailed: bool = False) -> None:
    """Display camera information in a formatted table."""
    table = Table(title="GoPro Camera Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Connection", "Connected" if info.get("connected") else "Disconnected")
    table.add_row("Connection Type", info.get("connection_type", "Unknown").title())
    table.add_row("Webcam Streaming", "Active" if info.get("streaming") else "Inactive")
    
    if detailed:
        table.add_row("Battery Level", f"{info.get('battery_level', 'Unknown')}%")
        table.add_row("Camera Encoding", "Yes" if info.get("encoding") else "No")
        table.add_row("Camera Control", str(info.get("camera_control", "Unknown")))
    
    console.print(table)


def _display_webcam_config(config: WebcamConfig, stream_url: Optional[str]) -> None:
    """Display webcam configuration details."""
    panel_content = f"""[bold cyan]Configuration Applied:[/bold cyan]
• Resolution: {config.resolution.value}
• Field of View: {config.field_of_view.value}
• Bit Rate: {config.bit_rate.value}
• Protocol: {config.protocol.value}
• HyperSmooth: {'Disabled' if config.disable_hypersmooth else 'Enabled'}
• Horizon Leveling: {'Disabled' if config.disable_horizon_leveling else 'Enabled'}
• Preview Stream: {'Yes' if config.use_preview_stream else 'No'}

[bold yellow]Stream URL:[/bold yellow] {stream_url or 'Not available'}"""
    
    console.print(Panel(panel_content, title="Webcam Configuration", border_style="green"))


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()