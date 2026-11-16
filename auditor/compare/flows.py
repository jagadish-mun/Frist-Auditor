"""Layer 4 — flows: replay scripted user flows on both sites, find first divergence.

Step types (SPEC §7):
  goto:        { path: "/fares" }
  fill:        { label: "From", value: "DCA" }
  select:      { label: "Passengers", value: "2 adults" }
  click:       { role: button, name: "Search", nth: 0 }
  stop_before: "Pay"      -> asserts a button/link with that name exists, then stops
  expect_dialog: "Fare rules"  -> asserts an open dialog with that name
After every step the state (path, h1, open dialog) is recorded on both sites.
"""
from ..capture import load, normalize
from .behavior import STATE_JS, _path

TIMEOUT = 3000
QUICK = {"on": False}   # --quick: shorter settle wait, no screenshot after a successful fill/select step


def _step_label(step):
    (kind, arg), = step.items()
    if kind == "fill":
        return f"fill '{arg['label']}' with '{arg['value']}'"
    if kind == "select":
        return f"select '{arg['value']}' in '{arg['label']}'"
    if kind == "click":
        return f"click {arg.get('role', 'button')} '{arg['name']}'"
    if kind == "goto":
        return f"go to {arg['path']}"
    if kind == "stop_before":
        return f"reach '{arg}' (stop before it)"
    if kind == "expect_dialog":
        return f"see dialog '{arg}'"
    return kind


def _run_step(page, base, step):
    (kind, arg), = step.items()
    if kind == "goto":
        load(page, base + arg["path"])
    elif kind == "fill":
        page.get_by_label(arg["label"], exact=True).first.fill(str(arg["value"]), timeout=TIMEOUT)
    elif kind == "select":
        page.get_by_label(arg["label"], exact=True).first.select_option(label=str(arg["value"]), timeout=TIMEOUT)
    elif kind == "click":
        loc = page.get_by_role(arg.get("role", "button"), name=arg["name"], exact=True)
        loc.nth(arg.get("nth", 0)).click(timeout=TIMEOUT)
        page.wait_for_load_state("load", timeout=5000)
        page.wait_for_timeout(50 if QUICK["on"] else 150)
    elif kind == "stop_before":
        loc = page.get_by_role("button", name=arg, exact=True).or_(page.get_by_role("link", name=arg, exact=True))
        loc.first.wait_for(state="visible", timeout=TIMEOUT)
    elif kind == "expect_dialog":
        page.get_by_role("dialog", name=arg).first.wait_for(state="visible", timeout=TIMEOUT)
    else:
        raise ValueError(f"unknown step {kind}")


def _state(page, regexes, status):
    st = page.evaluate(STATE_JS)
    return {"path": _path(page.url), "status": status.get("code") or 200,
            "h1": normalize(st["h1"] or "", regexes), "dialog": normalize(st["dialog"] or "", regexes) or None}


def _replay(ctx, base, flow, regexes, shot_prefix):
    page = ctx.new_page()
    page.on("dialog", lambda d: d.dismiss())
    status = {"code": None}
    page.on("response", lambda r: status.__setitem__("code", r.status)
            if r.request.is_navigation_request() and r.frame == page.main_frame else None)
    load(page, base + flow.get("start", "/"))
    trace = []
    for k, step in enumerate(flow["steps"]):
        try:
            _run_step(page, base, step)
            trace.append({"ok": True, "state": _state(page, regexes, status)})
        except Exception as e:  # noqa: BLE001
            msg = str(e).splitlines()[0][:160]
            trace.append({"ok": False, "error": msg, "state": _state(page, regexes, status)})
            page.screenshot(path=f"{shot_prefix}_step{k + 1}.png")
            break
        # A successful fill/select cannot change path, heading or dialog, so the flow cannot diverge at that step.
        if not (QUICK["on"] and next(iter(step)) in ("fill", "select")):
            page.screenshot(path=f"{shot_prefix}_step{k + 1}.png")
    page.close()
    return trace


def compare_flow(ctx_real, ctx_clone, real_url, clone_url, flow, regexes, shots_dir):
    name = flow["name"]
    rt = _replay(ctx_real, real_url, flow, regexes, str(shots_dir / f"flow_{name}_real"))
    ct = _replay(ctx_clone, clone_url, flow, regexes, str(shots_dir / f"flow_{name}_clone"))
    steps = flow["steps"]
    if not all(t["ok"] for t in rt) or len(rt) < len(steps):
        bad = next(i for i, t in enumerate(rt) if not t["ok"])
        return {"name": name, "score": None, "invalid": True,
                "detail": f"flow fails on the REAL site at step {bad + 1} ({_step_label(steps[bad])}): {rt[bad]['error']}"}
    for k, step in enumerate(steps):
        c = ct[k] if k < len(ct) else None
        r = rt[k]
        reason = None
        if c is None:
            break
        if not c["ok"]:
            reason = f"could not {_step_label(step)} on clone ({c['error']})"
        elif (c["state"]["path"], c["state"]["status"], c["state"]["dialog"]) != \
                (r["state"]["path"], r["state"]["status"], r["state"]["dialog"]) or \
                c["state"]["h1"] != r["state"]["h1"]:
            rs, cs = r["state"], c["state"]
            reason = (f"after step {k + 1} ({_step_label(step)}), real is at {rs['path']} "
                      f"(h1 '{rs['h1']}'{', dialog ' + repr(rs['dialog']) if rs['dialog'] else ''}) but clone is at "
                      f"{cs['path']} (HTTP {cs['status']}, h1 '{cs['h1']}'"
                      f"{', dialog ' + repr(cs['dialog']) if cs['dialog'] else ''})")
        a11y = None
        if reason and c["ok"] and (c["state"]["path"], c["state"]["status"], c["state"]["h1"]) == \
                (r["state"]["path"], r["state"]["status"], r["state"]["h1"]) and r["state"]["dialog"] and c["state"]["dialog"] \
                and c["state"]["dialog"] != r["state"]["dialog"] and c["state"]["dialog"].startswith(r["state"]["dialog"]):
            a11y = (r["state"]["dialog"], c["state"]["dialog"])   # same dialog, missing accessible name (Task 15)
        if reason:
            return {"name": name, "score": k / len(steps), "diverged_at": k + 1, "a11y": a11y,
                    "step": _step_label(step), "detail": reason,
                    "page": (rt[k - 1]["state"]["path"] if k else flow.get("start", "/")).split("?")[0],
                    "real_shot": str(shots_dir / f"flow_{name}_real_step{k + 1}.png"),
                    "clone_shot": str(shots_dir / f"flow_{name}_clone_step{k + 1}.png")}
    return {"name": name, "score": 1.0, "diverged_at": None}
