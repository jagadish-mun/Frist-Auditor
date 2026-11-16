"""SPEC §9.3 agent-correlation experiment with two non-LLM proxy agents.

    python tools/agents.py                 # all clones, writes runs/agents/{results.json,RESULTS.md,*.png}
    python tools/agents.py --only clone_mid,rebuilt

Each agent "trains" on a clone: breadth-first search over visible clickables (filling form fields
from the task's data by label) until the task's success check passes. The found trajectory is
stored in two forms and replayed on the REAL site:
  * replay agent   — page coordinates of each click / field, plus typed values;
  * semantic agent — role + accessible name (+ index among equals) for clicks, label for fields.
Success on the real site is checked programmatically. The experiment then asks whether a clone's
fidelity score (from runs/validation/results.json, v1 and v2) predicts real-site success.
These are proxy agents, not RL-trained policies.
"""
import argparse
import json
import sys
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "refapp"))
from defects import REBUILT_DEFECTS, SWEEP_ORDER, TIERS  # noqa: E402
from heldout_defects import HELDOUT_DEFECTS  # noqa: E402
from serve import APP, DRAFT, REBUILT, keep_awake, serve  # noqa: E402
from auditor.capture import goto  # noqa: E402

OUT = ROOT / "runs" / "agents"
VIEWPORT = {"width": 1440, "height": 900}
SKIP = ("pay", "delete", "purchase", "buy", "remove")   # never click these (no transactions)
MAX_DEPTH, MAX_EXPANSIONS = 5, 60


def q(url):
    u = urlsplit(url)
    return u.path, {k: v[0] for k, v in parse_qs(u.query).items()}


def _has(hist, path, **params):
    return any(p == path and all(qs.get(k, "").lower() == v.lower() for k, v in params.items())
               for p, qs in map(q, hist))


# overlap with audit flows: "flow" = identical to an audit flow; "partial" = passes through a flow's steps/states;
# "none" = shares no flow step. Analysis (b) in correlate.py uses only "none".
TASKS = {
    "book_core": {"overlap": "flow", "start": "/", "data": {"From": "DCA", "To": "SJU", "First name": "Ada", "Last name": "Lovelace",
                                         "Email": "ada@example.com"},
                  "check": lambda st: q(st["url"])[0] == "/review" and _has(st["hist"], "/results", **{"from": "DCA", "to": "SJU"})
                  and _has(st["hist"], "/passenger", fare="core")},
    "fare_rules": {"overlap": "flow", "start": "/fares?flight=HA101", "data": {},
                   "check": lambda st: "fare rules" in (st["dialog"] or "").lower()},
    "check_in": {"overlap": "flow", "start": "/", "data": {"Confirmation code": "ABC123", "Last name": "Lovelace"},
                 "check": lambda st: q(st["url"])[0] == "/checkin/result" and (st["h1"] or "").strip() == "Your trip"},
    "baggage_info": {"overlap": "none", "start": "/", "data": {}, "check": lambda st: q(st["url"])[0] == "/help/baggage"},
    "sign_in_page": {"overlap": "none", "start": "/results?from=DCA&to=SJU", "data": {},
                     "check": lambda st: q(st["url"])[0] == "/signin"},
    "search_bos_mco": {"overlap": "partial", "start": "/", "data": {"From": "BOS", "To": "MCO"},
                       "check": lambda st: q(st["url"])[0] == "/results" and q(st["url"])[1].get("from") == "BOS"
                       and q(st["url"])[1].get("to") == "MCO"},
    # ---- Phase 2 (Task 10): 8 more tasks ----
    "pax_search": {"overlap": "partial", "start": "/", "data": {"From": "DCA", "To": "SJU", "Passengers": "2 adults"},
                   "check": lambda st: q(st["url"])[0] == "/results" and q(st["url"])[1].get("pax", "").startswith("2")},
    "sort_results": {"overlap": "none", "start": "/results?from=DCA&to=SJU", "data": {"Sort by": "Departure"},
                     "check": lambda st: q(st["url"])[0] == "/results" and st["selects"].get("Sort by") == "Departure"},
    "help_centre": {"overlap": "none", "start": "/fares?flight=HA101", "data": {}, "check": lambda st: q(st["url"])[0] == "/help"},
    "modify_search": {"overlap": "none", "start": "/results?from=DCA&to=SJU", "data": {},
                      "check": lambda st: q(st["url"])[0] == "/" and (st["h1"] or "").strip() == "Where to next?"
                      and any(t["name"] == "Modify search" for t in st["clicked"])},
    "manage_trips": {"overlap": "none", "start": "/checkin", "data": {}, "check": lambda st: q(st["url"])[0] == "/manage"},
    "back_from_review": {"overlap": "none", "start": "/review?flight=HA101&first=Ada&last=Lovelace", "data": {},
                         "check": lambda st: q(st["url"])[0] == "/passenger"},
    "pick_extra_fare": {"overlap": "partial", "start": "/fares?flight=HA101", "data": {},
                        "check": lambda st: q(st["url"])[0] == "/passenger" and q(st["url"])[1].get("fare") == "extra"},
    "checkin_then_home": {"overlap": "partial", "start": "/checkin", "data": {"Confirmation code": "ABC123", "Last name": "Lovelace"},
                          "check": lambda st: q(st["url"])[0] == "/" and _has(st["hist"], "/checkin/result")},
}

# Visible interactive elements with role, accessible name, index among same role+name, and box.
ELEMENTS_JS = r"""
() => {
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    if (!r.width || !r.height || s.visibility === 'hidden' || s.display === 'none') return false;
    const d = el.closest('dialog'); return !(d && !d.open); };
  const clean = t => (t || '').replace(/\s+/g, ' ').trim();
  const inDialog = document.querySelector('dialog[open]');
  const out = [], seen = {};
  document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea').forEach(el => {
    if (!vis(el)) return;
    if (inDialog && !el.closest('dialog[open]')) return;          // modal: only dialog contents are reachable
    const t = el.tagName;
    const role = t === 'A' ? 'link' : t === 'BUTTON' ? 'button' : t === 'SELECT' ? 'combobox' : 'textbox';
    let name = el.getAttribute('aria-label') || '';
    if (!name && el.labels && el.labels[0]) name = el.labels[0].innerText;
    if (!name) name = el.innerText || el.value || '';
    name = clean(name);
    const key = role + '|' + name; seen[key] = (seen[key] || 0) + 1;
    const r = el.getBoundingClientRect();
    out.push({role, name, nth: seen[key] - 1, x: r.left + scrollX + r.width / 2, y: r.top + scrollY + r.height / 2,
              submit: role === 'button' && !!el.form});
  });
  return out;
}
"""
STATE_JS = """() => ({h1: document.querySelector('h1')?.innerText || null,
  dialog: [...document.querySelectorAll('dialog[open],[role=dialog]')].map(d => d.innerText).join(' ') || null,
  selects: Object.fromEntries([...document.querySelectorAll('select')].filter(s => s.labels && s.labels[0])
             .map(s => [s.labels[0].innerText.trim(), s.options[s.selectedIndex]?.text]))})"""


def state(page, hist, acted=()):
    for attempt in (1, 2):   # a failed step can leave a navigation in flight; wait for it, then read
        try:
            page.wait_for_load_state("load", timeout=5000)
            s = page.evaluate(STATE_JS)
            break
        except Exception:  # noqa: BLE001
            if attempt == 2:
                raise
            page.wait_for_timeout(300)
    # "clicked": what was actually clicked on THIS site, by its name here (post-freeze fix, DECISIONS D31). Before the
    # fix this was the trajectory as recorded on the clone, so a replay agent clicking the right spot on the real site
    # was judged by the clone's (relabelled) name.
    return {"url": page.url, "hist": hist + [page.url], "clicked": list(acted), **s}


# ---------------- training: BFS on the clone ----------------

CLICKED_NAME_JS = """([x, y]) => { const el = document.elementFromPoint(x, y);
  const t = el && el.closest('a[href], button, [role=button], [role=link]');
  return t ? (t.getAttribute('aria-label') || t.innerText || '').replace(/\\s+/g, ' ').trim() : null; }"""


def _do(page, step, mode):
    """Execute one recorded step on a page. mode: 'semantic' | 'replay'.
    Returns the name of the element clicked on this page (None for fills/selects)."""
    if step["kind"] == "select":
        if mode == "semantic":
            page.get_by_label(step["label"], exact=True).first.select_option(label=step["value"], timeout=2000)
        else:   # coordinate agent: whatever <select> sits at the recorded point gets the recorded option
            page.evaluate(f"window.scrollTo(0, {max(0, step['y'] - 400)})")
            ok = page.evaluate("""([x, y, v]) => { const el = document.elementFromPoint(x, y - scrollY);
                if (!el || el.tagName !== 'SELECT') return false;
                const o = [...el.options].find(o => o.text === v); if (!o) return false;
                el.value = o.value; el.dispatchEvent(new Event('change', {bubbles: true})); return true; }""",
                               [step["x"], step["y"], step["value"]])
            if not ok:
                raise RuntimeError("no matching select at point")
        return
    name = None
    if mode == "semantic":
        if step["kind"] == "fill":
            page.get_by_label(step["label"], exact=True).first.fill(step["value"], timeout=2000)
        else:
            page.get_by_role(step["role"], name=step["name"], exact=True).nth(step["nth"]).click(timeout=2000)
            name = step["name"]
    else:
        x, y = step["x"], step["y"]
        page.evaluate(f"window.scrollTo(0, {max(0, y - 400)})")
        sy = page.evaluate("scrollY")
        if step["kind"] == "click":
            name = page.evaluate(CLICKED_NAME_JS, [x, y - sy])
        page.mouse.click(x, y - sy)
        if step["kind"] == "fill":
            page.keyboard.press("ControlOrMeta+a"); page.keyboard.type(step["value"])
    if step["kind"] == "click":
        page.wait_for_load_state("load"); page.wait_for_timeout(80)
    return name


def run(page, base, task, traj, mode):
    goto(page, base + task["start"])
    hist, acted = [page.url], []
    for st in traj:
        try:
            name = _do(page, st, mode)
        except Exception:  # noqa: BLE001 — a failed step means the trajectory does not transfer
            return False, state(page, hist, acted)
        if st["kind"] == "click":
            acted.append({"kind": "click", "name": name})
        hist.append(page.url)
    s = state(page, hist[:-1], acted)
    return bool(task["check"](s)), s


def actions(page, data):
    els = page.evaluate(ELEMENTS_JS)
    fills = [{"kind": "fill", "label": e["name"], "value": data[e["name"]], "x": e["x"], "y": e["y"]}
             for e in els if e["role"] == "textbox" and e["name"] in data]
    sels = [{"kind": "select", "label": e["name"], "value": data[e["name"]], "x": e["x"], "y": e["y"]}
            for e in els if e["role"] == "combobox" and e["name"] in data]
    fills += sels
    acts = [[x] for x in sels]          # a select on its own is also an action (e.g. sorting has no submit)
    for e in els:
        if e["role"] not in ("link", "button") or any(w in e["name"].lower().split() for w in SKIP):
            continue
        click = {"kind": "click", "role": e["role"], "name": e["name"], "nth": e["nth"], "x": e["x"], "y": e["y"]}
        acts.append((fills if e["submit"] else []) + [click])
    return acts


def train(page, base, task):
    """BFS over action sequences on `base`. Returns the shortest successful trajectory or None."""
    start = []
    ok, s = run(page, base, task, start, "semantic")
    if ok:
        return start
    frontier, seen, expansions = deque([start]), {(s["url"], s["dialog"])}, 0
    while frontier and expansions < MAX_EXPANSIONS:
        traj = frontier.popleft()
        if len(traj) and sum(1 for x in traj if x["kind"] == "click") >= MAX_DEPTH:
            continue
        run(page, base, task, traj, "semantic"); expansions += 1
        for act in actions(page, task["data"]):
            cand = traj + act
            ok, s = run(page, base, task, cand, "semantic")
            if ok:
                return cand
            key = (s["url"], s["dialog"])
            if key not in seen:
                seen.add(key); frontier.append(cand)
    return None


# ---------------- experiment ----------------

def clone_specs():
    specs = [("real", (), APP)]                      # sanity: trained on the real site itself
    specs += [(f"single_{d}", (d,), APP) for d in SWEEP_ORDER]
    specs += [(f"sweep_{k:02d}", tuple(SWEEP_ORDER[:k]), APP) for k in range(2, len(SWEEP_ORDER) + 1)]
    specs += [(t, tuple(ds), APP) for t, ds in TIERS.items()]
    specs += [("drift_rebuild", ("subtle_drift",), APP), ("rebuilt", (), REBUILT)]
    specs += [(f"rebuilt_{d}", (d,), REBUILT) for d in REBUILT_DEFECTS]
    specs += [("rebuilt_all4", tuple(REBUILT_DEFECTS), REBUILT)]
    specs += [(f"tpl_{d}", (d,), APP) for d in HELDOUT_DEFECTS]          # held-out (Task 7)
    specs += [(f"rebuilt_{d}", (d,), REBUILT) for d in HELDOUT_DEFECTS]
    if DRAFT.exists():
        specs += [("draft", (), DRAFT)]                                   # independent first draft (Task 9)
    return specs


def job(spec):
    name, defects, app, *rest = spec
    tasks = {t: TASKS[t] for t in (rest[0] if rest and rest[0] else TASKS)}
    out = {"clone": name, "tasks": {}}
    with serve() as real, serve(defects, app=app) as clone, sync_playwright() as pw:
        br = pw.chromium.launch()
        page = br.new_context(viewport=VIEWPORT, reduced_motion="reduce").new_page()
        for tn, task in tasks.items():
            try:
                traj = train(page, real if name == "real" else clone, task)
                r = {"trained": traj is not None, "steps": len(traj or []),
                     # what the trajectory touches (Task 14): click targets and filled/selected fields
                     "traj": [{k: v for k, v in st.items() if k in ("kind", "role", "name", "nth", "label", "value")}
                              for st in (traj or [])]}
                for mode in ("replay", "semantic"):
                    ok, st = run(page, real, task, traj, mode) if traj is not None else (False, {"hist": []})
                    r[mode] = bool(ok)
                    r[mode + "_pages"] = [urlsplit(u).path for u in st["hist"]]   # pages visited on the REAL site
            except Exception as e:  # noqa: BLE001 — recorded as a failed task with the error, never silently
                r = {"trained": False, "steps": 0, "replay": False, "semantic": False,
                     "error": f"{type(e).__name__}: {str(e).splitlines()[0][:120]}"}
                page = br.new_context(viewport=VIEWPORT, reduced_motion="reduce").new_page()
            out["tasks"][tn] = r
        br.close()
    for mode in ("replay", "semantic"):
        out[mode] = sum(t[mode] for t in out["tasks"].values()) / len(tasks)
    out["trained"] = sum(t["trained"] for t in out["tasks"].values()) / len(tasks)
    print(f"{name:28s} trained={out['trained']:.2f} replay={out['replay']:.2f} semantic={out['semantic']:.2f}", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", default="results.json", help="file name under runs/agents/")
    ap.add_argument("--tasks", default="", help="comma list: run only these tasks (others absent from the output)")
    a = ap.parse_args()
    keep_awake()
    tl = [t for t in a.tasks.split(",") if t]
    specs = [(*s, tl) for s in clone_specs() if not a.only or s[0] in a.only.split(",")]
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(job, specs))
    f = OUT / a.out
    if a.only and f.exists():   # partial rerun: replace those clones in the existing results, keep the rest
        new = {r["clone"]: r for r in res}
        res = [new.pop(r["clone"], r) for r in json.loads(f.read_text())] + list(new.values())
    f.write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
