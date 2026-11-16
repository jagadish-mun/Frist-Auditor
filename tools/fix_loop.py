"""Fix-and-re-audit loop (SPEC §13 demo): audit → fix the top high/medium gap → re-audit.

    python tools/fix_loop.py clone_mid          # template clone (defects from TIERS)
    python tools/fix_loop.py rebuilt_all4       # screenshot-rebuilt clone with its 4 planted defects

One fix per iteration, highest-ranked high/medium gap first, until no high/medium gaps remain or
6 iterations. Writes runs/fixloop/<name>/iter_NN/ (full audit incl. report.html), history.json and
score.png.

How fixes are made (recorded per iteration as `method`):
  * template clones   — "catalog": the gap is matched to a planted defect via its `expect` keywords
                        (the same matcher validate.py uses) and that defect is switched off. This is an
                        oracle: it knows the ground truth.
  * rebuilt clone     — "text patch": generic source edits derived only from the gap text, applied to a
                        working copy of refapp/clone_rebuilt/app.py:
                          relabel  "<role> label reads 'X' on clone, 'Y' on real site" → replace 'X' with 'Y'
                          link     "on real site it navigates to /a; on clone it navigates to /b"   → replace '/b' with '/a'
                        Gaps that need new code (missing element, dead button) fall back to "catalog".
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "refapp"))
from auditor.audit import load_config, run_audit  # noqa: E402
from defects import REBUILT_DEFECTS, TIERS  # noqa: E402
from serve import APP, REBUILT, serve  # noqa: E402
from tools.plot import chart  # noqa: E402
from validate import detects  # noqa: E402

MAX_ITERS = 6
RELABEL = re.compile(r"label reads '(.+?)' on clone, '(.+?)' on real site")
RELINK = re.compile(r"on real site it navigates to (/[^\s;?]*)[^;]*; on clone it navigates to (/[^\s;?(]*)")


def text_patch(src: Path, gap):
    """Try a generic source edit for this gap. Returns a description or None."""
    s = src.read_text()
    m = RELABEL.search(gap["description"])
    if m and f'"{m.group(1)}"' in s:
        src.write_text(s.replace(f'"{m.group(1)}"', f'"{m.group(2)}"'))
        return f"replaced label \"{m.group(1)}\" → \"{m.group(2)}\""
    m = RELINK.search(gap["description"])
    if m and m.group(1) != m.group(2) and f"'{m.group(2)}'" in s:
        src.write_text(s.replace(f"'{m.group(2)}'", f"'{m.group(1)}'"))
        return f"replaced link target '{m.group(2)}' → '{m.group(1)}'"
    return None


def main(name, max_iters=MAX_ITERS, root=ROOT / "runs" / "fixloop"):
    rebuilt = name.startswith("rebuilt")
    defects = list(REBUILT_DEFECTS) if name == "rebuilt_all4" else list(TIERS[name])
    out = Path(root) / name
    shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
    app = APP
    if rebuilt:  # work on a copy; never edit the committed clone
        app = out / "work" / "app.py"; app.parent.mkdir(); shutil.copy(REBUILT, app)
    hist = []
    for it in range(max_iters + 1):
        cfg = load_config(str(ROOT / "configs" / "harbor.yaml"))
        with serve() as real, serve(defects, app=app) as clone:
            cfg["real_url"], cfg["clone_url"] = real, clone
            summary, gaps = run_audit(cfg, out / f"iter_{it:02d}", log=lambda *_: None)
        hm = [g for g in gaps if g["severity"] in ("high", "medium")]
        rec = {"iter": it, "score": summary["overall"], "gap_counts": summary["gap_counts"], "active_defects": list(defects)}
        hist.append(rec)
        print(f"{name} iter {it}: score {summary['overall']:.3f} gaps {summary['gap_counts']}", flush=True)
        if not hm or it == max_iters:
            break
        g = hm[0]   # gaps.json is ranked: severity, then magnitude
        how = text_patch(app, g) if rebuilt else None
        if how:
            rec["fix"] = {"gap": g["id"], "gap_text": g["description"], "method": "text patch", "edit": how}
        else:
            d = next((d for d in defects if detects(d, g)), None)
            if d is None:
                rec["fix"] = {"gap": g["id"], "gap_text": g["description"], "method": "none", "edit": "no fix found; stopping"}
                break
            defects.remove(d)
            rec["fix"] = {"gap": g["id"], "gap_text": g["description"], "method": "catalog", "edit": f"switched off {d}"}
        print(f"   fix: {rec['fix']['method']}: {rec['fix']['edit']}", flush=True)
    (out / "history.json").write_text(json.dumps(hist, indent=2))
    return hist


def plot(names, root=ROOT / "runs" / "fixloop"):
    series = []
    for n in names:
        h = json.loads((Path(root) / n / "history.json").read_text())
        series.append((n, [(r["iter"], r["score"]) for r in h]))
    mx = max(len(s[1]) for s in series) - 1
    chart(Path(root) / "score.png", [{
        "title": "Fix-and-re-audit loop: fidelity (v2) per iteration", "xlabel": "iteration (one fix each)",
        "ylabel": "fidelity score", "xr": (0, max(1, mx)), "yr": (0.5, 1.0), "series": series}], kind="line")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=["clone_mid", "rebuilt_all4"])
    ap.add_argument("--iters", type=int, default=MAX_ITERS, help="maximum fix iterations")
    ap.add_argument("--out-root", default=str(ROOT / "runs" / "fixloop"))
    a = ap.parse_args()
    for n in a.names:
        main(n, a.iters, a.out_root)
    plot(a.names, a.out_root)
