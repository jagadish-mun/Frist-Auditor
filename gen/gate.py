"""Reliability gate for the generated-site demo (Tasks 21 §5, 22 §6).   make demo-gate   (~17 min)

For each seed 1..20:
  * noise: the generated real site audited against itself must give 0 tickets;
  * demo:  `SEED=n NO_OPEN=1 make demo` must exit 0 within 60 s, leave the report and screenshots, and leave both
           sites answering on their localhost URLs; then `make end-demo` must leave no temp dir, no listener on either
           port (lsof), no process running from the temp dir and no state file.
Plus: make demo twice in a row (the second ends the first), make end-demo twice, closing the terminal (SIGHUP + kill
of the shell that ran make demo: sites stay up), port fallback (8101 taken), and Ctrl-C mid-audit (all cleaned up).
Writes runs/demo_gate/GATE.md and gate.json; exits 1 if any check fails.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import socket
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from active import STATE, answers  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "demo_gate"
PY = str(ROOT / ".venv" / "bin" / "python")
SEEDS = range(1, 21)
LIMIT_S = 60


def listening(port):
    r = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], capture_output=True, text=True)
    return r.stdout.split()


def leftovers(stdout):
    """Problems left behind by a finished demo run, from the TMP and PORTS lines it printed."""
    probs = []
    tmp = re.search(r"^TMP (.+)$", stdout, re.M)
    ports = re.search(r"^PORTS real=(\d+) clone=(\d+)$", stdout, re.M)
    if not tmp:
        probs.append("no TMP line")
    else:
        if Path(tmp.group(1)).exists():
            probs.append(f"temp dir still exists: {tmp.group(1)}")
        if subprocess.run(["pgrep", "-f", tmp.group(1) + "/"], capture_output=True).returncode == 0:
            probs.append("process still running from temp dir")
    for p in (ports.groups() if ports else []):
        if listening(p):
            probs.append(f"port {p} still listening")
    if STATE.exists():
        probs.append("state file still exists")
    return probs, (ports.groups() if ports else ())


def make(target, seed=None, timeout=300):
    env = {**os.environ, "NO_OPEN": "1", **({"SEED": str(seed)} if seed is not None else {})}
    return subprocess.run(["make", "-s", target], cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)


def up(stdout):
    """Problems if the sites a finished `make demo` printed are not up (both URLs answer, state file matches)."""
    ports = re.search(r"^PORTS real=(\d+) clone=(\d+)$", stdout, re.M)
    if not ports:
        return ["no PORTS line"]
    probs = [f"http://localhost:{p} not answering" for p in ports.groups() if not answers(f"http://localhost:{p}")]
    try:
        st = json.loads(STATE.read_text())
        if (str(st["real"]["port"]), str(st["clone"]["port"])) != ports.groups():
            probs.append("state file ports differ from the run's")
    except (OSError, ValueError, KeyError):
        probs.append("state file missing or unreadable")
    for want in ("Real site:  http://localhost:", "Clone:      http://localhost:", "Report:     runs/demo_live/",
                 "Run 'make end-demo' when finished."):
        if want not in stdout:
            probs.append(f"missing output line: {want}")
    return probs


def noise(seed):
    tmp = tempfile.mkdtemp(prefix="ffgate.")
    try:
        r = subprocess.run([PY, "gen/demo.py", "--seed", str(seed), "--tmp", tmp, "--out", str(OUT / f"noise_seed{seed}"),
                            "--noise"], cwd=ROOT, capture_output=True, text=True, timeout=300)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode:
        return {"ok": False, "error": r.stderr.strip().splitlines()[-1:]}
    card = json.loads((OUT / f"noise_seed{seed}" / "scorecard.json").read_text())
    return {"ok": card["tickets"] == 0, "tickets": card["tickets"], "gaps": card["gaps"]}


def demo(seed):
    t0 = time.time()
    r = make("demo", seed)
    secs = round(time.time() - t0, 1)
    probs = up(r.stdout)
    e = make("end-demo")
    if e.returncode or "deleted temp dir" not in e.stdout:
        probs.append(f"end-demo: exit {e.returncode}, output {e.stdout.strip()[-120:]!r}")
    more, ports = leftovers(r.stdout)
    probs += more
    if r.returncode:
        probs.append(f"exit {r.returncode}: {(r.stderr.strip().splitlines() or [''])[-1]}")
    rep = re.search(r"^Report: (\S+)", r.stdout, re.M)
    card = None
    if rep:
        out = Path(rep.group(1)).parent
        card = json.loads((out / "scorecard.json").read_text())
        if not (out / "report.html").exists() or not any((out / "shots").glob("*.png")):
            probs.append("report or screenshots missing")
    else:
        probs.append("no report line")
    if secs > LIMIT_S:
        probs.append(f"took {secs} s (> {LIMIT_S} s)")
    return {"ok": not probs, "problems": probs, "seconds": secs, "ports": ports, "card": card}


def interrupt(seed=999):
    """Ctrl-C mid-audit: SIGINT to the whole process group, as a terminal does."""
    p = subprocess.Popen(["make", "demo"], cwd=ROOT, env={**os.environ, "SEED": str(seed), "NO_OPEN": "1"},
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    buf = ""
    for line in p.stdout:
        buf += line
        if line.startswith("Auditing"):
            time.sleep(3)
            os.killpg(p.pid, signal.SIGINT)
            break
    buf += p.stdout.read()
    p.wait(timeout=60)
    time.sleep(1)
    probs, ports = leftovers(buf)
    return {"ok": not probs and p.returncode != 0, "problems": probs, "exit": p.returncode, "ports": ports}


def twice():
    a, b = make("demo", 201), make("demo", 202)
    probs = [] if a.returncode == b.returncode == 0 else [f"exit codes {a.returncode}, {b.returncode}"]
    if "ending it first" not in b.stdout or "Real site: stopped" not in b.stdout:
        probs.append("second run did not end the first")
    tmp1 = re.search(r"^TMP (.+)$", a.stdout, re.M).group(1)
    if Path(tmp1).exists() or subprocess.run(["pgrep", "-f", tmp1 + "/"], capture_output=True).returncode == 0:
        probs.append("first run's temp dir or servers survived")
    probs += up(b.stdout)
    make("end-demo")
    probs += leftovers(b.stdout)[0]
    return {"ok": not probs, "problems": probs}


def end_twice():
    first_none = make("end-demo")
    d = make("demo", 203)
    e1, e2 = make("end-demo"), make("end-demo")
    probs = []
    if first_none.returncode or "No active demo" not in first_none.stdout:
        probs.append(f"end-demo with no demo: {first_none.stdout.strip()!r}")
    if d.returncode or e1.returncode or "deleted temp dir" not in e1.stdout:
        probs.append("demo or first end-demo failed")
    if e2.returncode or "No active demo" not in e2.stdout:
        probs.append(f"second end-demo: exit {e2.returncode}, {e2.stdout.strip()!r}")
    probs += leftovers(d.stdout)[0]
    return {"ok": not probs, "problems": probs}


def terminal_close(seed=204):
    """Run make demo from a shell in its own session, then hang up and kill that whole session: the sites must stay."""
    sh = subprocess.Popen(["bash", "-c", "make -s demo; exec sleep 600"], cwd=ROOT,
                          env={**os.environ, "SEED": str(seed), "NO_OPEN": "1"},
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    buf = ""
    for line in sh.stdout:
        buf += line
        if line.startswith("Run 'make end-demo'"):
            break
    os.killpg(sh.pid, signal.SIGHUP); time.sleep(0.5)
    try:
        os.killpg(sh.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):   # macOS: EPERM once only the unreaped (zombie) shell is left
        pass
    sh.wait(timeout=10); time.sleep(1)
    probs = up(buf)
    make("end-demo")
    probs += leftovers(buf)[0]
    return {"ok": not probs, "problems": probs}


def port_fallback(seed=205):
    """8101 already taken: the real site must come up on another port and everything still work."""
    blocker = socket.socket(); blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blocker.bind(("127.0.0.1", 8101)); blocker.listen()
    try:
        d = make("demo", seed)
        ports = re.search(r"^PORTS real=(\d+) clone=(\d+)$", d.stdout, re.M)
        probs = [] if d.returncode == 0 else [f"exit {d.returncode}"]
        if not ports or ports.group(1) == "8101" or ports.group(2) != "8102":
            probs.append(f"unexpected ports {ports.groups() if ports else None}")
        probs += up(d.stdout)
        make("end-demo")
    finally:
        blocker.close()
    probs += leftovers(d.stdout)[0]
    return {"ok": not probs, "problems": probs, "ports": ports.groups() if ports else None}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    make("end-demo")                       # start from a clean slate
    rows = []
    for s in SEEDS:
        n, d = noise(s), demo(s)
        rows.append({"seed": s, "noise": n, "demo": d})
        c = d["card"] or {}
        print(f"seed {s:>2}: noise {'ok' if n['ok'] else 'FAIL ' + str(n)}  demo {'ok' if d['ok'] else 'FAIL'} "
              f"{d['seconds']} s  {c.get('theme', '?')}  found {len(c.get('found', []))}/{c.get('planted', '?')}  "
              f"false alarms {len(c.get('false_alarms', []))}" + (f"  {d['problems']}" if d["problems"] else ""), flush=True)
    ctrl_c = interrupt()
    print(f"Ctrl-C test: {'ok' if ctrl_c['ok'] else 'FAIL'} {ctrl_c}", flush=True)
    special = {"demo twice": twice(), "end-demo twice": end_twice(), "terminal closed": terminal_close(),
               "port 8101 taken": port_fallback(), "Ctrl-C mid-audit": ctrl_c}
    for k, v in special.items():
        print(f"{k}: {'ok' if v['ok'] else 'FAIL'} {v['problems'] or ''}", flush=True)
    cards = [r["demo"]["card"] for r in rows if r["demo"]["card"]]
    tot = {"planted": sum(c["planted"] for c in cards), "found": sum(len(c["found"]) for c in cards),
           "false_alarms": sum(len(c["false_alarms"]) for c in cards), "extra": sum(len(c["extra"]) for c in cards)}
    missed = [(c["seed"], m) for c in cards for m in c["missed"]]
    by_cat = {}
    for c in cards:
        for n, cat in c["categories"].items():
            b = by_cat.setdefault(cat, [0, 0]); b[0] += 1; b[1] += n in c["found"]
    all_ok = all(r["noise"]["ok"] and r["demo"]["ok"] for r in rows) and all(v["ok"] for v in special.values())
    secs = [r["demo"]["seconds"] for r in rows]
    md = [f"# Demo reliability gate — {'PASS' if all_ok else 'FAIL'}", "",
          f"Seeds {SEEDS.start}–{SEEDS.stop - 1}. Demo wall time per run: min {min(secs)} s, max {max(secs)} s "
          f"(limit {LIMIT_S} s). After each run both sites answered; `make end-demo` then left no temp dir, "
          f"process, listener or state file.", "",
          "| lifecycle test | result |", "|---|---|",
          *[f"| {k} | {'ok' if v['ok'] else 'FAIL: ' + '; '.join(v['problems'])} |" for k, v in special.items()], "",
          f"**Detection:** {tot['found']}/{tot['planted']} planted defects found; "
          f"**false alarms** (high/medium tickets explained by no planted defect): {tot['false_alarms']}; "
          f"extra tickets of any severity: {tot['extra']}.", "",
          "| category | planted | found |", "|---|---|---|",
          *[f"| {k} | {v[0]} | {v[1]} |" for k, v in sorted(by_cat.items())], "",
          "| seed | theme | noise tickets | demo s | planted | found | missed | false alarms | problems |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        c = r["demo"]["card"] or {}
        md.append(f"| {r['seed']} | {c.get('theme', '?')} | {r['noise'].get('tickets', 'ERR')} | {r['demo']['seconds']} | "
                  f"{c.get('planted', '?')} | {len(c.get('found', []))} | {', '.join(c.get('missed', [])) or '–'} | "
                  f"{len(c.get('false_alarms', []))} | {'; '.join(r['demo']['problems']) or '–'} |")
    fa = [(c["seed"], f) for c in cards for f in c["false_alarms"]]
    if fa or missed:
        md += ["", "## Misses and false alarms", *[f"- seed {s}: missed `{m}`" for s, m in missed],
               *[f"- seed {s}: false alarm {f}" for s, f in fa]]
    (OUT / "GATE.md").write_text("\n".join(md) + "\n")
    (OUT / "gate.json").write_text(json.dumps({"rows": rows, "special": special, "totals": tot, "pass": all_ok}, indent=2))
    print("\n".join(md[:8]))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
