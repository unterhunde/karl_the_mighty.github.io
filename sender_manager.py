"""Process-management helpers for the Pi WebRTC sender.

Major steps:
1. Validate signaling server reachability before streaming.
2. Start/stop/status the sender background process via PID file.
3. Install required Python dependencies for Pi runtime.

Config candidates:
- `REQUIREMENTS` package pins.
- Default script/log/PID paths.
- Server health-check timeout in `check_server`.
"""

import os
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
CONFIG_FILE = Path(os.environ.get("AI_DEV_CONFIG_FILE", PROJECT_ROOT / "app_config.json"))
SENDER_SCRIPT = BASE_DIR / "webrtc_sender.py"


def _load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
        return data.get("pi_manager", {})
    except Exception:
        return {}


_PI_MANAGER_CONFIG = _load_config()
DEFAULT_PID_FILE = PROJECT_ROOT / _PI_MANAGER_CONFIG.get("default_pid_file", "pi/sender.pid")
DEFAULT_LOG_FILE = PROJECT_ROOT / _PI_MANAGER_CONFIG.get("default_log_file", "pi/sender.log")
REQUIREMENTS = _PI_MANAGER_CONFIG.get(
    "requirements",
    [
        "aiortc==1.14.0",
        "aiohttp==3.14.1",
        "av==16.1.0",
        "numpy",
        "picamera2",
    ],
)
SERVER_CHECK_TIMEOUT_SEC = float(_PI_MANAGER_CONFIG.get("server_check_timeout_sec", 5))


def is_process_alive(pid: int) -> bool:
    """Return True when a PID exists and is signalable by the current user."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def check_server(server: str) -> bool:
    """Verify the signaling server root endpoint responds with HTTP 200."""
    url = server.rstrip("/") + "/"
    try:
        with urllib.request.urlopen(url, timeout=SERVER_CHECK_TIMEOUT_SEC) as response:
            return response.status == 200
    except Exception as exc:
        print(f"Server check failed: {exc}")
        return False


def install_deps() -> None:
    """Install sender runtime dependencies into the active Python environment."""
    print("Installing dependencies into current Python environment...")
    subprocess.run([sys.executable, "-m", "pip", "install", *REQUIREMENTS], check=True)
    print("Dependencies installed.")


def sender_status(pid_file: Path) -> None:
    """Print sender liveness using the process ID stored in `pid_file`."""
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
    """Terminate the sender process referenced by `pid_file`."""
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
    """Launch the sender in a new session and persist PID/log output paths."""
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
