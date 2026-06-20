import os
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SENDER_SCRIPT = BASE_DIR / "webrtc_sender.py"
DEFAULT_PID_FILE = BASE_DIR / "sender.pid"
DEFAULT_LOG_FILE = BASE_DIR / "sender.log"
REQUIREMENTS = [
    "aiortc==1.14.0",
    "aiohttp==3.14.1",
    "av==16.1.0",
    "numpy",
    "picamera2",
]


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def check_server(server: str) -> bool:
    url = server.rstrip("/") + "/"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status == 200
    except Exception as exc:
        print(f"Server check failed: {exc}")
        return False


def install_deps() -> None:
    print("Installing dependencies into current Python environment...")
    subprocess.run([sys.executable, "-m", "pip", "install", *REQUIREMENTS], check=True)
    print("Dependencies installed.")


def sender_status(pid_file: Path) -> None:
    if not pid_file.exists():
        print("Sender is not running.")
        return
    try:
        pid = int(pid_file.read_text().strip())
    except ValueError:
        print("Invalid PID file. Remove sender.pid and try again.")
        return
    alive = is_process_alive(pid)
    print(f"Sender PID={pid} alive={alive}")


def stop_sender(pid_file: Path) -> None:
    if not pid_file.exists():
        print("No sender PID file found.")
        return
    try:
        pid = int(pid_file.read_text().strip())
    except ValueError:
        print("Invalid PID file. Remove sender.pid and try again.")
        return
    if not is_process_alive(pid):
        print(f"Process {pid} is not running.")
        pid_file.unlink(missing_ok=True)
        return
    try:
        os.kill(pid, 15)
        print(f"Stopped sender process {pid}.")
    except OSError as exc:
        print(f"Failed to stop sender: {exc}")
    finally:
        pid_file.unlink(missing_ok=True)


def start_sender(server: str, pid_file: Path, log_file: Path) -> None:
    if not SENDER_SCRIPT.exists():
        print(f"Sender script not found: {SENDER_SCRIPT}")
        return
    if not check_server(server):
        print(f"Cannot reach signaling server at {server}")
        return
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            if is_process_alive(pid):
                print(f"Sender already running with PID {pid}.")
                return
        except ValueError:
            pass
    with open(log_file, "a", encoding="utf-8") as stream:
        process = subprocess.Popen(
            [sys.executable, str(SENDER_SCRIPT), "--server", server],
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    pid_file.write_text(str(process.pid), encoding="utf-8")
    print(f"Started sender with PID {process.pid}. Logs are in {log_file}")
