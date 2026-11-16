"""Task-conditioned failure prediction (Phase 3, Task 14). FROZEN before its first held-out run (DECISIONS D26).

    python tools/predict.py                     # all sets
    python tools/predict.py --sets original     # development: original clones only (held-out untouched)

Claim under test: "specific gaps predict specific task failures". For each (clone, task, agent) we predict
FAIL iff the clone's audit contains a high or medium gap that refers to something the TASK needs:

  needs(task)  = the reference trajectory of the task on the REAL site (agent trained and run on the real site):
                 clicked elements (role, name), filled / selected fields (label, value), pages visited.
                 It does not depend on the clone, so the prediction uses only the audit + the task definition.
  gap matches  = severity in {high, medium} AND one of
     element gap  (kind missing | label | target_moved | behavior): gap.element (role, name) is in needs AND the gap
                  is reported on a page the task visits (gap.page or gap.also_on);
                  behaviour variants: "dialog:<button>" also matches a needed button of that name;
                  "option:<text>" matches only if the task selects exactly that option in that field;
     flow gap     (kind flow): the diverging step's target (role, name / field label) is in needs AND the step's
                  page is one the task visits.
     kind extra never matches (the element does not exist on the real site, so no real-site task needs it).

Variants:  P       the rule above, same for both agents.
           P_aware as P, with each agent's locating mechanism taken into account:
                   semantic agent (finds elements by role + name): "target_moved" gaps are ignored
                       (fixed a priori, before any predictor run);
                   replay agent (clicks recorded coordinates): "label" gaps on links/buttons are ignored, and so is a
                       flow gap whose step target is a link/button relabelled in the same audit (the flow failed only
                       because it looks the name up). Field relabels still count: both agents fill fields by label
                       while training on the clone
                       (added after inspecting errors on the ORIGINAL clones only; DECISIONS D26).
Baselines: B_score predict FAIL for every task of a clone whose overall score < t; t maximises F1 on the ORIGINAL
                   clones (per agent and scoring version) and is then applied unchanged elsewhere.
           B_high  predict FAIL for every task of a clone that has any high gap.

Outcome = the agent failed the task on the real site after training on the clone (runs/agents/results_traj.json).
Units are (clone, task) pairs over non-nested clones. Writes runs/predict/{RESULTS.md,results.json}.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from agents import TASKS  # noqa: E402

RUNS = ROOT / "runs"
OUT = RUNS / "predict"
AGENTS = ("replay", "semantic")
SCORINGS = ("v3", "v2", "v1")
FIELD_ROLES = {"textbox", "combobox", "field"}


def norm(s):
    return " ".join((s or "").lower().split())


def role_of(r):
    return "field" if r in FIELD_ROLES else r


def needs(ref_task):
    """What a task needs on the real site, from its reference trajectory."""
    els, options = set(), set()
    for st in ref_task["traj"]:
        if st["kind"] == "click":
            els.add((st["role"], norm(st["name"])))
        else:
            els.add(("field", norm(st["label"])))
            if st["kind"] == "select":
                options.add((norm(st["label"]), norm(st["value"])))
    return {"elements": els, "options": options, "pages": set(ref_task["semantic_pages"])}


def gap_matches(g, need, agent, aware, relabelled=frozenset()):
    if g["severity"] not in ("high", "medium"):
        return False
    kind = g.get("kind")
    pages = {g["page"], *g.get("also_on", [])}
    if kind == "flow":
        fs = g["flow_step"]
        tgt = (role_of(fs.get("role")), norm(fs.get("name")))
        if aware and agent == "replay" and tgt in relabelled:
            return False
        return tgt in need["elements"] and fs["page"] in need["pages"]
    if kind in ("missing", "label", "target_moved", "behavior"):
        if aware and agent == "semantic" and kind == "target_moved":
            return False
        if aware and agent == "replay" and kind == "label" and g["element"]["role"] in ("link", "button"):
            return False
        if not pages & need["pages"]:
            return False
        if g.get("elements"):   # grouped ticket (Task 15): one ticket, several elements — read each (representation only)
            return any(gap_matches({**g, "element": e, "elements": None}, need, agent, aware, relabelled) for e in g["elements"])
        e, var = g["element"], g.get("variant", "")
        if var.startswith("option:"):
            return (norm(e["name"]), norm(var[7:])) in need["options"]
        if var.startswith("dialog:") and ("button", norm(var[7:])) in need["elements"]:
            return True
        return (role_of(e["role"]), norm(e["name"])) in need["elements"]
    return False


def prf(pairs):
    """pairs: list of (predicted_fail, actual_fail)."""
    tp = sum(p and a for p, a in pairs); fp = sum(p and not a for p, a in pairs)
    fn = sum(a and not p for p, a in pairs); tn = len(pairs) - tp - fp - fn
    pr = tp / (tp + fp) if tp + fp else float("nan"); rc = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * pr * rc / (pr + rc) if tp else 0.0
    return {"n": len(pairs), "fail": tp + fn, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": pr, "recall": rc, "f1": f1}


def load(sets, agents_file="results_traj.json"):
    agents = {a["clone"]: a for a in json.loads((RUNS / "agents" / agents_file).read_text())}
    ref = agents["real"]["tasks"]
    clones = {}
    for d, want in (("validation", "original"), ("validation_heldout", "heldout"), ("validation_draft", "draft")):
        f = RUNS / d / "results.json"
        if not f.exists() or (want not in sets and "all" not in sets):
            continue
        res = json.loads(f.read_text())
        for name in res["v3"]:
            if name.startswith(("_", "noise", "sweep_")) or name not in agents or name in clones:
                continue
            if d == "validation_heldout" and "_ho_" not in name:
                continue
            clones[name] = {"set": want, "score": {sc: res[sc][name]["overall"] for sc in SCORINGS},
                            "gaps": {sc: json.loads((RUNS / d / sc / name / "gaps.json").read_text()) for sc in SCORINGS},
                            "agent": agents[name]}
    return ref, clones


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="all", help="comma list of original,heldout,draft or 'all'")
    ap.add_argument("--agents-file", default="results_traj.json", help="agent outcomes under runs/agents/ (input only)")
    ap.add_argument("--out", default=str(OUT), help="output directory")
    args = ap.parse_args()
    sets = args.sets.split(",")
    ref, clones = load(sets, args.agents_file)
    need = {t: needs(ref[t]) for t in TASKS}
    nonflow = [t for t, s in TASKS.items() if s["overlap"] == "none"]
    rows = []   # one per (clone, task, agent, scoring)
    for cn, c in clones.items():
        for sc in SCORINGS:
            high = any(g["severity"] == "high" for g in c["gaps"][sc])
            relab = frozenset((role_of(g["element"]["role"]), norm(g["element"]["name"]))
                              for g in c["gaps"][sc] if g.get("kind") == "label" and g["element"]["role"] in ("link", "button"))
            for t in TASKS:
                for ag in AGENTS:
                    hits = {aw: [g["id"] for g in c["gaps"][sc] if gap_matches(g, need[t], ag, aw, relab)] for aw in (False, True)}
                    rows.append({"clone": cn, "set": c["set"], "task": t, "agent": ag, "scoring": sc,
                                 "fail": not c["agent"]["tasks"][t][ag], "P": bool(hits[False]), "P_aware": bool(hits[True]),
                                 "B_high": high, "score": c["score"][sc], "hits": hits[False]})
    # threshold for B_score: best F1 on the original set, per agent and scoring
    thr = {}
    for sc in SCORINGS:
        for ag in AGENTS:
            tr = [r for r in rows if r["set"] == "original" and r["agent"] == ag and r["scoring"] == sc]
            cands = sorted({r["score"] for r in tr}) + [1.01]
            thr[(sc, ag)] = max(cands, key=lambda t: (prf([(r["score"] < t, r["fail"]) for r in tr])["f1"], -t)) if tr else None
    for r in rows:
        t = thr[(r["scoring"], r["agent"])]
        r["B_score"] = (r["score"] < t) if t is not None else False
    views = {"all clones": lambda r: True, "original clones": lambda r: r["set"] == "original",
             "held-out clones": lambda r: r["set"] == "heldout", "no-flow tasks (all clones)": lambda r: r["task"] in nonflow}
    res, L = {}, ["# Task-conditioned failure prediction", "",
                  f"Generated by `python tools/predict.py --sets {','.join(sets)} --agents-file {args.agents_file}`. Units: (clone, task) pairs; "
                  f"{len(clones)} non-nested clones × {len(TASKS)} tasks. Definitions: docstring of tools/predict.py.", ""]
    for vname, vf in views.items():
        sub = [r for r in rows if vf(r)]
        if not sub:
            continue
        L += [f"## {vname}", "", "| Scoring | Agent | pairs | failures | Predictor | precision | recall | F1 | TP | FP | FN |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for sc in SCORINGS:
            for ag in AGENTS:
                s2 = [r for r in sub if r["scoring"] == sc and r["agent"] == ag]
                for pred in ("P", "P_aware", "B_score", "B_high"):
                    m = prf([(r[pred], r["fail"]) for r in s2])
                    res[f"{vname}|{sc}|{ag}|{pred}"] = m
                    label = pred + (f" (t={thr[(sc, ag)]:.3f})" if pred == "B_score" and thr[(sc, ag)] is not None else "")
                    L.append(f"| {sc} | {ag} | {m['n']} | {m['fail']} | {label} | {m['precision']:.2f} | {m['recall']:.2f} | "
                             f"{m['f1']:.2f} | {m['tp']} | {m['fp']} | {m['fn']} |")
        L.append("")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "RESULTS.md").write_text("\n".join(L) + "\n")
    (out / "results.json").write_text(json.dumps({"metrics": res, "thresholds": {f"{k[0]}|{k[1]}": v for k, v in thr.items()},
                                                  "rows": rows}, indent=1))
    print("\n".join(L))


if __name__ == "__main__":
    main()
