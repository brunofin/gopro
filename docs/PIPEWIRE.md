Awesome—let’s wire Option A up from Python using PyGObject + GStreamer. The script below ingests a UDP stream and **provides** a PipeWire virtual camera node (apps will see it as a normal webcam).

## 1) Install deps (Fedora examples; adapt to your distro)

```bash
sudo dnf install python3-gobject \
  gstreamer1 gstreamer1-plugins-base gstreamer1-plugins-good \
  gstreamer1-plugins-bad-free gstreamer1-libav \
  pipewire gstreamer1-plugin-pipewire
```

(Arch: `sudo pacman -S python-gobject gst-plugins-{base,good,bad,ugly} gst-libav pipewire gst-plugin-pipewire`)

## 2) Save this as `udp_to_pipewire_cam.py`

```python
#!/usr/bin/env python3
import argparse, signal, sys
from gi.repository import Gst, GObject

GObject.threads_init()
Gst.init(None)

def has_element(name: str) -> bool:
    return Gst.ElementFactory.find(name) is not None

def choose_h264_decoder():
    # Prefer HW decoders if available
    for cand in ["vah264dec", "nvh264dec", "v4l2h264dec", "avdec_h264"]:
        if has_element(cand):
            return cand
    raise RuntimeError("No H.264 decoder found (need avdec_h264 or a HW decoder).")

def build_pipeline(args):
    node_name = args.node_name
    client_name = args.client_name
    media_class = "Video/Source"

    jitter = f"rtpjitterbuffer latency={args.jitter_ms} drop-on-late=true do-lost=true"

    if args.kind == "rtp-h264":
        caps = f'application/x-rtp,media=video,encoding-name=H264,payload={args.payload},clock-rate=90000'
        dec = choose_h264_decoder()
        pipe = (
            f'udpsrc port={args.port} caps="{caps}" ! '
            f'{jitter} ! rtph264depay ! h264parse ! {dec} ! '
            f'videoconvert ! {args.scale_caps} '
            f'queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 leaky=downstream ! '
            f'pipewiresink mode=provide client-name="{client_name}" node-name="{node_name}" '
            f'media-class={media_class} sync=false'
        )

    elif args.kind == "rtp-mjpeg":
        caps = f'application/x-rtp,media=video,encoding-name=JPEG,payload={args.payload}'
        pipe = (
            f'udpsrc port={args.port} caps="{caps}" ! '
            f'{jitter} ! rtpjpegdepay ! jpegdec ! '
            f'videoconvert ! {args.scale_caps} '
            f'queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 leaky=downstream ! '
            f'pipewiresink mode=provide client-name="{client_name}" node-name="{node_name}" '
            f'media-class={media_class} sync=false'
        )

    elif args.kind == "mpegts-h264":
        dec = choose_h264_decoder()
        pipe = (
            f'udpsrc port={args.port} ! tsparse ! tsdemux name=demux '
            f'demux. ! queue ! h264parse ! {dec} ! '
            f'videoconvert ! {args.scale_caps} '
            f'queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 leaky=downstream ! '
            f'pipewiresink mode=provide client-name="{client_name}" node-name="{node_name}" '
            f'media-class={media_class} sync=false'
        )

    else:
        raise ValueError("Unsupported --kind")

    return pipe

def main():
    parser = argparse.ArgumentParser(description="UDP → PipeWire virtual camera")
    parser.add_argument("--kind", choices=["rtp-h264","rtp-mjpeg","mpegts-h264"], required=True,
                        help="UDP payload format")
    parser.add_argument("--port", type=int, default=5000, help="UDP port to listen on")
    parser.add_argument("--payload", type=int, default=96, help="RTP payload type (if applicable)")
    parser.add_argument("--width", type=int, default=1920, help="Output width (set 0 to keep source)")
    parser.add_argument("--height", type=int, default=1080, help="Output height (set 0 to keep source)")
    parser.add_argument("--fps", type=int, default=30, help="Output FPS (set 0 to keep source)")
    parser.add_argument("--node-name", default="UDP Cam", help="PipeWire node name")
    parser.add_argument("--client-name", default="UDP Cam", help="PipeWire client name")
    parser.add_argument("--jitter-ms", type=int, default=0, help="rtpjitterbuffer latency (ms)")
    args = parser.parse_args()

    # Constrain caps to reduce renegotiations & keep latency stable
    if args.width > 0 and args.height > 0 and args.fps > 0:
        args.scale_caps = f'video/x-raw,format=NV12,width={args.width},height={args.height},framerate={args.fps}/1 ! '
    else:
        args.scale_caps = ''  # leave as-is

    launch_str = build_pipeline(args)
    print("GST pipeline:\n", launch_str, "\n", flush=True)

    pipeline = Gst.parse_launch(launch_str)

    bus = pipeline.get_bus()
    bus.add_signal_watch()

    def on_bus(msg):
        t = msg.type
        if t == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            print(f"[ERROR] {err}\n{dbg}", file=sys.stderr, flush=True)
            pipeline.set_state(Gst.State.NULL)
            GObject.MainLoop().quit()
        elif t == Gst.MessageType.EOS:
            print("[EOS] End of stream", flush=True)
            pipeline.set_state(Gst.State.NULL)
            GObject.MainLoop().quit()
        return True

    bus.connect("message", on_bus)

    loop = GObject.MainLoop()

    def handle_sigint(sig, frame):
        print("Stopping…", flush=True)
        pipeline.send_event(Gst.Event.new_eos())

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    finally:
        pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    main()
```

## 3) Run it

Typical RTP/H.264 on port 5000:

```bash
python3 udp_to_pipewire_cam.py --kind rtp-h264 --port 5000 --payload 96 --width 1920 --height 1080 --fps 30
```

RTP/MJPEG:

```bash
python3 udp_to_pipewire_cam.py --kind rtp-mjpeg --port 5000 --payload 26
```

MPEG-TS (H.264 inside):

```bash
python3 udp_to_pipewire_cam.py --kind mpegts-h264 --port 5000
```

That will create a PipeWire source named **“UDP Cam”**. Pick it in any webcam-enabled app.

### Notes for lowest latency

- Keep `--jitter-ms 0` for pristine LAN; bump to **10–30** if you see drops.
- Hardware decode is auto-picked when available (`vah264dec`, `nvh264dec`, or `v4l2h264dec`), else it falls back to `avdec_h264`.
- Fixing output size/FPS avoids renegotiations that add jitter; set `--width/--height/--fps` to 0 to pass-through.

### Optional: systemd user unit

Point the service to this script in ExecStart and it’ll auto-provide your camera on login:

```ini
# ~/.config/systemd/user/udp-virtual-cam.service
[Unit]
Description=UDP → PipeWire Virtual Camera (Python)

[Service]
ExecStart=%h/.local/bin/udp_to_pipewire_cam.py --kind rtp-h264 --port 5000 --payload 96 --width 1920 --height 1080 --fps 30
Restart=on-failure

[Install]
WantedBy=default.target
```

Enable it:

```bash
chmod +x ~/.local/bin/udp_to_pipewire_cam.py
systemctl --user daemon-reload
systemctl --user enable --now udp-virtual-cam.service
```

If you share the exact UDP format/caps you’re sending, I can pre-fill the right `--kind`/caps for you.
