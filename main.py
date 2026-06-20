import argparse
from pathlib import Path

from sender_manager import (
    DEFAULT_LOG_FILE,
    DEFAULT_PID_FILE,
    install_deps,
    sender_status,
    start_sender,
    stop_sender,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Pi WebRTC sender management")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show sender process status")
    subparsers.add_parser("stop", help="Stop the running sender process")
    subparsers.add_parser("install-deps", help="Install required Python dependencies")

    stream_parser = subparsers.add_parser("stream", help="Start the Pi WebRTC sender")
    stream_parser.add_argument("--server", required=True, help="Signaling server URL, e.g. http://192.168.0.189:8080")

    parser.add_argument("--log", default=str(DEFAULT_LOG_FILE), help="Log file for sender output")
    parser.add_argument("--pid", default=str(DEFAULT_PID_FILE), help="PID file for sender process")
    return parser.parse_args()


def main():
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
        start_sender(args.server, pid_file, log_file)


if __name__ == "__main__":
    main()
