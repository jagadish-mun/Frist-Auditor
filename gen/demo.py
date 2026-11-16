"""Live demo run (Task 21): generate a site + clone from a seed, serve both, audit, score against the answer key.

    python gen/demo.py --seed 7 --tmp <empty dir> --out runs/demo_live/<stamp>_seed7
    python gen/demo.py --seed 7 --tmp <empty dir> --out <dir> --noise     # real vs real: must give 0 tickets

Called by scripts/demo.sh. Demo mode (Task 22): after a successful run both sites keep running, detached, on
8101/8102 (or free ports) and runs/demo_live/.active_demo.json records them; on any failure or Ctrl-C they are stopped
here and demo.sh deletes the temp dir. `make end-demo` (gen/active.py) stops a kept demo.
Matching uses validate.detects, the matcher validate.py uses, with the generated defects registered under a `gen:`
prefix. Report, screenshots, answer_key.json, audit.yaml and scorecard.json are written to --out and kept.
"""
import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "refapp")); sys.path.insert(0, str(ROOT / "gen"))
import validate  # noqa: E402
from auditor.audit import load_config, run_audit  # noqa: E402
from serve import _free_port, _listener_pid, serve  # noqa: E402
import active  # noqa: E402
from site_gen import generate  # noqa: E402

HM = ("high", "medium")


def score(answer, gaps):
    """found/missed per planted defect (validate.detects on `expect`), and tickets explained by none of them."""
    names = []
    for d in answer["defects"]:
        n = f"gen:{d['name']}"
        validate.ALL_DEFECTS[n] = {"pages": d["pages"], "expect": [tuple(e) for e in d["expect"]]}
        validate.ALL_DEFECTS[n + ":side"] = {"pages": d["pages"], "expect": [tuple(e) for e in d["side_effects"]]}
        names.append(n)
    found = {n: [g["id"] for g in gaps if validate.detects(n, g)] for n in names}
    extra = [g for g in gaps if not any(validate.detects(n, g) or validate.detects(n + ":side", g) for n in names)]
    return {
        "planted": len(names),
        "found": sorted(n[4:] for n, ids in found.items() if ids),
        "missed": sorted(n[4:] for n, ids in found.items() if not ids),
        "tickets": len(gaps),
        "tickets_hm": sum(g["severity"] in HM for g in gaps),
        "extra": [f"{g['id']} [{g['severity']}/{g['layer']}] {g['page']}: {g['description']}" for g in extra],
        "false_alarms": [f"{g['id']} [{g['severity']}/{g['layer']}] {g['page']}: {g['description']}"
                         for g in extra if g["severity"] in HM],
        "found_by": {n[4:]: ids for n, ids in found.items()},
    }


PREFERRED = {"real": 8101, "clone": 8102}


def _port_free(port):
    """Nothing listening on localhost:port (IPv4 or IPv6) and we can bind it on 127.0.0.1."""
    for fam, addr in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.create_connection((addr, port), timeout=0.3):
                return False                       # something answers there
        except OSError:
            pass
    try:
        with socket.socket() as s:
            s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


def start_detached(app, want):
    """Start a site in its own session (setsid), so closing the terminal does not stop it. Ready = our process is alive,
    answers HTTP, and is the one listening on the port (same checks as refapp/serve.py). Preferred port first, then a
    free one if it is taken or lost to a race."""
    for attempt in range(3):
        port = want if attempt == 0 and _port_free(want) else _free_port()
        log = open(Path(app).with_name("server.log"), "ab")
        proc = subprocess.Popen([sys.executable, str(app), "--port", str(port)], cwd=Path(app).parent,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        log.close()
        deadline = time.time() + 15
        while time.time() < deadline and proc.poll() is None:
            if active.answers(f"http://127.0.0.1:{port}"):
                break
            time.sleep(0.1)
        if proc.poll() is None and time.time() < deadline and _listener_pid(port) in (proc.pid, None):
            return proc, port
        proc.kill(); proc.wait()
    raise RuntimeError(f"{app} did not start after 3 attempts")


@contextmanager
def sites(tmp, noise):
    """Noise: both sides are the real site, stopped at the end (refapp serve). Demo: real + clone started detached;
    stopped if anything fails or is interrupted, LEFT RUNNING after success (gen/active.py end stops them)."""
    if noise:
        with serve(app=tmp / "real" / "app.py") as r, serve(app=tmp / "real" / "app.py") as c:
            yield {"real": {"url": r}, "clone": {"url": c}}
        return
    procs = []
    try:
        info = {}
        for key in ("real", "clone"):
            proc, port = start_detached(tmp / key / "app.py", PREFERRED[key])
            procs.append(proc)
            info[key] = {"pid": proc.pid, "port": port, "url": f"http://127.0.0.1:{port}"}
        yield info
        procs = []                               # success: keep them
    finally:
        for p in procs:
            p.kill(); p.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--tmp", required=True, help="empty working dir for the generated sites")
    ap.add_argument("--out", required=True)
    ap.add_argument("--noise", action="store_true", help="audit the real site against itself")
    a = ap.parse_args()
    t0 = time.time()
    tmp, out = Path(a.tmp), Path(a.out)
    answer = generate(a.seed, tmp)
    print(f"Generated {answer['theme']} site '{answer['site']}': {len(answer['pages'])} pages, "
          f"flows {', '.join(answer['flows'])}", flush=True)
    if not a.noise:
        print(f"Planted {len(answer['defects'])} defects in the clone (hidden from the auditor)", flush=True)
    cfg = load_config(str(tmp / "audit.yaml"))
    with sites(tmp, a.noise) as srv:
        real, clone = srv["real"]["url"], srv["clone"]["url"]
        print(f"PORTS real={real.rsplit(':', 1)[1]} clone={clone.rsplit(':', 1)[1]}", flush=True)
        cfg["real_url"], cfg["clone_url"] = real, clone
        print("Auditing ...", flush=True)
        summary, gaps = run_audit(cfg, out, log=lambda *_: None)
        shutil.copy(tmp / "answer_key.json", out / "answer_key.json")
        shutil.copy(tmp / "audit.yaml", out / "audit.yaml")
        if a.noise:
            card = {"seed": a.seed, "noise": True, "tickets": len(gaps), "score": summary["overall"],
                    "gaps": [f"{g['id']} [{g['severity']}/{g['layer']}] {g['page']}: {g['description']}" for g in gaps]}
            print(f"NOISE seed {a.seed}: {len(gaps)} tickets, score {summary['overall']:.3f}")
            for g in card["gaps"]:
                print("   ", g)
        else:
            card = {"seed": a.seed, "theme": answer["theme"], "site": answer["site"], "score": summary["overall"],
                    "nav_retries": summary["nav_retries"],
                    "categories": {d["name"]: d["category"] for d in answer["defects"]}, **score(answer, gaps)}
            by = {d["name"]: d for d in answer["defects"]}
            print(f"\nScorecard — seed {a.seed}, {answer['theme']} site '{answer['site']}', score {summary['overall']:.3f}")
            print(f"  planted {card['planted']}   found {len(card['found'])}   missed {len(card['missed'])}   "
                  f"extra tickets {len(card['extra'])} ({len(card['false_alarms'])} high/medium)")
            for n in sorted(by, key=lambda n: by[n]["category"]):
                d, ok = by[n], n in card["found"]
                print(f"  {'FOUND ' if ok else 'MISSED'} {d['category']:<9} {d['summary']}"
                      + (f"   → {', '.join(card['found_by'][n])}" if ok else ""))
            for e in card["extra"]:
                print(f"  EXTRA  {e}")
        card["seconds"] = round(time.time() - t0, 1)
        (out / "scorecard.json").write_text(json.dumps(card, indent=2))
        print(f"\nReport: {out / 'report.html'}  ({card['seconds']} s)")
        if not a.noise:
            active.write({"seed": a.seed, "theme": answer["theme"], "site": answer["site"],
                          "started": datetime.now().isoformat(timespec="seconds"), "tmp": str(tmp.resolve()),
                          "report": str((out / "report.html").resolve()),
                          **{k: {"pid": v["pid"], "port": v["port"], "url": f"http://localhost:{v['port']}"}
                             for k, v in srv.items()}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
