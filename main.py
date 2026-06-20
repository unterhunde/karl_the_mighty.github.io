"""CLI entrypoint for managing the Pi WebRTC sender process.

Major steps:
1. Parse command-line arguments.
2. Route command to sender manager operations.
3. Pass runtime-selected PID/log paths into manager functions.

Config candidates:
- Default PID/log paths (`DEFAULT_PID_FILE`, `DEFAULT_LOG_FILE`).
- CLI default server URL values passed by callers.
"""

import argparse
import json
import os
from pathlib import Path

from sender_manager import (
    DEFAULT_LOG_FILE,
    DEFAULT_PID_FILE,
    install_deps,
    sender_status,
    start_sender,
    stop_sender,
)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
CONFIG_FILE = Path(os.environ.get("AI_DEV_CONFIG_FILE", PROJECT_ROOT / "app_config.json"))


def _default_server_url() -> str | None:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
        return data.get("client", {}).get("server_url")
    except Exception:
        return None


def parse_args():
    """Parse CLI flags and subcommands for sender lifecycle operations."""
    parser = argparse.ArgumentParser(description="Pi WebRTC sender management")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show sender process status")
    subparsers.add_parser("stop", help="Stop the running sender process")
    subparsers.add_parser("install-deps", help="Install required Python dependencies")

    stream_parser = subparsers.add_parser("stream", help="Start the Pi WebRTC sender")
    stream_parser.add_argument(
        "--server",
        default=_default_server_url(),
        help="Signaling server URL, e.g. http://192.168.0.189:8080",
    )

    parser.add_argument("--log", default=str(DEFAULT_LOG_FILE), help="Log file for sender output")
    parser.add_argument("--pid", default=str(DEFAULT_PID_FILE), help="PID file for sender process")
    return parser.parse_args()


def main():
    """Dispatch sender management commands based on parsed arguments."""
    args = parse_args()
    log_file = Path(args.log)
    pid_file = Path(args.pid)

    if args.command == "install-deps":
        install_deps()
    elif args.command == "status":
        sender_status(pid_file)
    elif args.command == "stop":
        stop_sender(pid_file)
    elif args.command == "stream":
        if not args.server:
            raise SystemExit("Missing --server and no default found in app_config.json")
        start_sender(args.server, pid_file, log_file)


if __name__ == "__main__":
    main()
