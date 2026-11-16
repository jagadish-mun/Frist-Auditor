"""Start/stop reference-app instances (real site or clones) in subprocesses."""
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

APP = Path(__file__).with_name("app.py")
REBUILT = Path(__file__).parent / "clone_rebuilt" / "app.py"
DRAFT = Path(__file__).parent / "clone_draft" / "app.py"   # independent first-draft clone (Task 9)


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def keep_awake():
    """macOS: stop idle sleep while this process lives (sleep mid-run stalls page loads past their timeout).
    No-op where `caffeinate` does not exist."""
    try:
        subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def _listener_pid(port):
    """PID listening on 127.0.0.1:port per lsof (None if lsof is unavailable, so the check degrades gracefully)."""
    try:
        out = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    pids = [int(x) for x in out.split()]
    return pids[0] if len(pids) == 1 else (-1 if pids else None)


@contextmanager
def serve(defects=(), port=None, app=APP):
    """Start an app instance and yield its URL. Ready = our own process is alive AND answers HTTP on the port.

    A free port is picked by binding port 0 and releasing it, so another process can grab it before the child binds
    (port race). If that happens the child exits on bind; we detect it (process dead) and retry on a new port instead
    of silently talking to somebody else's server (Task 11).
    """
    for attempt in range(3):
        p = port or _free_port()
        proc = subprocess.Popen([sys.executable, str(app), "--port", str(p), "--defects", ",".join(defects)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=Path(app).parent)
        url = f"http://127.0.0.1:{p}"
        deadline = time.time() + 15
        while time.time() < deadline and proc.poll() is None:
            try:
                urllib.request.urlopen(url + "/", timeout=2).close()
                break
            except urllib.error.HTTPError:
                break            # any HTTP answer means a server is up
            except OSError:
                time.sleep(0.1)
        if proc.poll() is None and time.time() < deadline and _listener_pid(p) in (proc.pid, None):
            break
        proc.kill(); proc.wait()
        if port:                 # caller fixed the port: nothing to retry
            raise RuntimeError(f"server on fixed port {port} did not start")
    else:
        raise RuntimeError("server did not start after 3 attempts")
    try:
        yield url
    finally:
        proc.terminate(); proc.wait()
