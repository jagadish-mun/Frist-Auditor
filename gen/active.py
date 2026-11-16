"""The active live demo (Task 22): state file, end, status.  No heavy imports, so `make end-demo` is instant.

    python gen/active.py end       # stop both servers, delete the temp dir, remove the state file (safe to repeat)
    python gen/active.py status    # is a demo running? URLs and report path
    python gen/active.py banner    # the four lines printed at the end of `make demo`

State file: runs/demo_live/.active_demo.json = {seed, theme, site, started, tmp, report,
real: {pid, port, url}, clone: {pid, port, url}}. Written by gen/demo.py after a successful run.
Safety: a PID is only signalled if its command line contains the demo's temp dir (PIDs are reused after a reboot),
and only a directory named ffdemo.* is ever deleted. Reports are never touched.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "runs" / "demo_live" / ".active_demo.json"
SITES = (("real", "Real site"), ("clone", "Clone"))


def load():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return None


def write(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE)          # atomic: a reader never sees half a file


def ours(pid, tmp):
    """True if pid is alive and was started from this demo's temp dir."""
    r = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True)
    return r.returncode == 0 and f"{tmp}/" in r.stdout


def answers(url):
    try:
        urllib.request.urlopen(url + "/", timeout=3).close()
        return True
    except urllib.error.HTTPError:
        return True
    except OSError:
        return False


def _stop(pid):
    os.kill(pid, signal.SIGTERM)
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return "stopped"
        time.sleep(0.1)
    os.kill(pid, signal.SIGKILL)
    return "killed (did not stop on SIGTERM)"


def _rel(p):
    try:
        return str(Path(p).relative_to(ROOT))
    except ValueError:
        return str(p)


def end():
    s = load()
    if s is None:
        if STATE.exists():                     # unreadable state file: remove it, nothing else is known
            STATE.unlink()
            print("Removed an unreadable state file; no servers could be identified from it.")
        else:
            print("No active demo.")
        return 0
    tmp = s.get("tmp", "")
    print(f"Ending demo (seed {s.get('seed')}, {s.get('theme')} site '{s.get('site')}'):")
    for key, label in SITES:
        srv = s.get(key, {})
        pid = srv.get("pid")
        if pid and tmp and ours(pid, tmp):
            print(f"  {label}: {_stop(pid)} (pid {pid}, port {srv.get('port')})")
        else:
            print(f"  {label}: was not running (pid {pid})")
    if tmp and subprocess.run(["pkill", "-f", f"{tmp}/"], capture_output=True).returncode == 0:
        print("  stopped other processes started from the temp dir")
    t = Path(tmp) if tmp else None
    if t and t.name.startswith("ffdemo.") and t.exists():
        shutil.rmtree(t)
        print(f"  deleted temp dir {tmp}")
    elif t and t.exists():
        print(f"  NOT deleting {tmp}: not a demo temp dir (ffdemo.*)")
    else:
        print("  temp dir already gone")
    STATE.unlink(missing_ok=True)
    print(f"  removed {_rel(STATE)}")
    if s.get("report"):
        print(f"  report kept: {_rel(s['report'])}")
    return 0


def banner(s):
    print(f"Real site:  {s['real']['url']}")
    print(f"Clone:      {s['clone']['url']}")
    print(f"Report:     {_rel(s['report'])}")
    print("Run 'make end-demo' when finished.")


def status():
    s = load()
    if s is None:
        print("No active demo.")
        return 0
    print(f"Demo active: seed {s['seed']}, {s['theme']} site '{s['site']}', started {s['started']}")
    down = []
    for key, label in SITES:
        srv = s[key]
        up = ours(srv["pid"], s["tmp"]) and answers(srv["url"])
        print(f"  {label}: {'up' if up else 'NOT RESPONDING'} (pid {srv['pid']})")
        down += [] if up else [label]
    banner(s)
    if down:
        print(f"Warning: {', '.join(down)} not responding (machine restarted?). 'make end-demo' cleans up.")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "end":
        sys.exit(end())
    if cmd == "banner":
        s = load()
        sys.exit(banner(s) if s else 1)
    sys.exit(status())
