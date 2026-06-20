#!/usr/bin/env python3
"""Pi sender using hardware H.264 encoding and UDP transport only."""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
CONFIG_FILE = os.environ.get("AI_DEV_CONFIG_FILE", os.path.join(PROJECT_ROOT, "app_config.json"))


def _load_sender_config() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
        return data.get("pi_sender", {})
    except Exception:
        return {}


SENDER_CONFIG = _load_sender_config()


def _extract_host(server_url: str) -> str:
    parsed = urlparse(server_url if "://" in server_url else f"http://{server_url}")
    if not parsed.hostname:
        raise ValueError(f"Could not parse host from server URL: {server_url}")
    return parsed.hostname


def _require_hardware_pipeline_tools() -> None:
    missing = []
    if shutil.which("libcamera-vid") is None and shutil.which("rpicam-vid") is None:
        missing.append("libcamera-vid/rpicam-vid")
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
    if missing:
        raise RuntimeError(
            "Missing required binaries for hardware pipeline: "
            + ", ".join(missing)
            + ". Install them on the Pi and retry."
        )


def _build_pipeline_command(host: str, port: int, width: int, height: int, fps: int, bitrate: int) -> str:
    camera_bin = shutil.which("libcamera-vid") or shutil.which("rpicam-vid")
    if not camera_bin:
        raise RuntimeError("No camera binary found (expected libcamera-vid or rpicam-vid)")
    stream_url = f"udp://{host}:{port}?pkt_size=1316"
    return (
        f"{shlex.quote(camera_bin)} "
        f"-t 0 --codec h264 --inline --width {width} --height {height} "
        f"--framerate {fps} --bitrate {bitrate} -o - | "
        "ffmpeg -loglevel error -fflags nobuffer -flags low_delay "
        "-f h264 -i - -an -c copy -f mpegts "
        f"{shlex.quote(stream_url)}"
    )


def run_forever(
    host: str,
    port: int,
    width: int,
    height: int,
    fps: int,
    bitrate: int,
    retry_delay: float,
) -> None:
    _require_hardware_pipeline_tools()
    command = _build_pipeline_command(host, port, width, height, fps, bitrate)
    print(f"Starting hardware pipeline to {host}:{port} ({width}x{height}@{fps}fps, {bitrate}bps)", flush=True)
    print(f"Pipeline: {command}", flush=True)
    while True:
        process = subprocess.Popen(
            ["bash", "-lc", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        try:
            assert process.stderr is not None
            for line in process.stderr:
                if line.strip():
                    print(line.rstrip(), flush=True)
        except Exception as exc:
            print(f"Pipeline logging error: {exc}", flush=True)
        exit_code = process.wait()
        print(f"Pipeline exited with code {exit_code}. Restarting in {retry_delay:.1f}s...", flush=True)
        time.sleep(retry_delay)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pi hardware-encoded UDP video sender")
    parser.add_argument("--server", help="Receiver URL, e.g. http://192.168.0.189:8080")
    parser.add_argument("--host", help="Destination host/IP override (defaults from --server)")
    parser.add_argument("--port", type=int, default=int(SENDER_CONFIG.get("udp_port", 5600)), help="Destination UDP port")
    parser.add_argument("--width", type=int, default=int(SENDER_CONFIG.get("width", 1280)), help="Capture width")
    parser.add_argument("--height", type=int, default=int(SENDER_CONFIG.get("height", 720)), help="Capture height")
    parser.add_argument("--fps", type=int, default=int(SENDER_CONFIG.get("fps", 30)), help="Capture framerate")
    parser.add_argument("--bitrate", type=int, default=int(SENDER_CONFIG.get("bitrate", 3_000_000)), help="H.264 bitrate")
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=float(SENDER_CONFIG.get("retry_delay", 2.0)),
        help="Seconds between restarts",
    )
    args = parser.parse_args()

    server = args.server or os.environ.get("SIGNALING_SERVER")
    host = args.host
    if not host:
        if not server:
            print("Provide --host or --server, or set SIGNALING_SERVER", flush=True)
            sys.exit(2)
        host = _extract_host(server)
    run_forever(
        host=host,
        port=args.port,
        width=args.width,
        height=args.height,
        fps=args.fps,
        bitrate=args.bitrate,
        retry_delay=args.retry_delay,
    )


if __name__ == "__main__":
    main()
