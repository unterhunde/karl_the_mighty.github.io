import argparse
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from camera_handler import CameraHandler

BASE_DIR = Path(__file__).resolve().parent
SENDER_SCRIPT = BASE_DIR / "webrtc_sender.py"
PID_FILE = BASE_DIR / "sender.pid"
LOG_FILE = BASE_DIR / "sender.log"
REQUIREMENTS = [
    "aiortc==1.14.0",
    "aiohttp==3.14.1",
    "av==16.1.0",
    "numpy",
    "picamera2",
]


def is_process_alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def check_server(server):
    url = server.rstrip("/") + "/"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status == 200
    except Exception as exc:
        print(f"Server check failed: {exc}")
        return False


def install_deps():
    print("Installing dependencies into current Python environment...")
    subprocess.run([sys.executable, "-m", "pip", "install", *REQUIREMENTS], check=True)
    print("Dependencies installed.")


def capture_image():
    camera_handler = CameraHandler()
    result = camera_handler.capture_image()
    if result:
        print(f"Image saved at: {result}")
    else:
        print("Failed to capture image.")


def sender_status():
    if not PID_FILE.exists():
        print("Sender is not running.")
        return
    try:
        pid = int(PID_FILE.read_text().strip())
    except ValueError:
        print("Invalid PID file. Remove sender.pid and try again.")
        return
    alive = is_process_alive(pid)
    print(f"Sender PID={pid} alive={alive}")


def stop_sender():
    if not PID_FILE.exists():
        print("No sender PID file found.")
        return
    try:
        pid = int(PID_FILE.read_text().strip())
    except ValueError:
        print("Invalid PID file. Remove sender.pid and try again.")
        return
    if not is_process_alive(pid):
        print(f"Process {pid} is not running.")
        PID_FILE.unlink(missing_ok=True)
        return
    try:
        os.kill(pid, 15)
        print(f"Stopped sender process {pid}.")
    except OSError as exc:
        print(f"Failed to stop sender: {exc}")
    finally:
        PID_FILE.unlink(missing_ok=True)


def start_sender(server):
    if not SENDER_SCRIPT.exists():
        print(f"Sender script not found: {SENDER_SCRIPT}")
        return
    if not check_server(server):
        print(f"Cannot reach signaling server at {server}")
        return
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if is_process_alive(pid):
                print(f"Sender already running with PID {pid}.")
                return
        except ValueError:
            pass
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [sys.executable, str(SENDER_SCRIPT), "--server", server],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    PID_FILE.write_text(str(process.pid), encoding="utf-8")
    print(f"Started sender with PID {process.pid}. Logs are in {LOG_FILE}")


def parse_args():
    parser = argparse.ArgumentParser(description="Pi WebRTC helper for capture and sender management")
    subparsers = parser.add_subparsers(dest="command", required=False)

    subparsers.add_parser("capture", help="Capture a single image using Picamera2")
    subparsers.add_parser("status", help="Show sender process status")
    subparsers.add_parser("stop", help="Stop the running sender process")
    subparsers.add_parser("install-deps", help="Install required Python dependencies")

    stream_parser = subparsers.add_parser("stream", help="Start the Pi WebRTC sender")
    stream_parser.add_argument("--server", required=True, help="Signaling server URL, e.g. http://192.168.0.189:8080")

    parser.add_argument("--log", default=str(LOG_FILE), help="Log file for sender output")
    parser.add_argument("--pid", default=str(PID_FILE), help="PID file for sender process")
    return parser.parse_args()


def main():
    args = parse_args()
    global LOG_FILE, PID_FILE
    LOG_FILE = Path(args.log)
    PID_FILE = Path(args.pid)

    if args.command == "install-deps":
        install_deps()
    elif args.command == "status":
        sender_status()
    elif args.command == "stop":
        stop_sender()
    elif args.command == "stream":
        start_sender(args.server)
    else:
        capture_image()


if __name__ == "__main__":
    main()
