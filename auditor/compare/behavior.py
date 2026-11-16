"""Layer 3 — behaviour: click each interactive element and record the resulting state.

For each clickable element (links, buttons) on a page we load the page fresh,
fill any required fields in the element's form with dummy values (so submit
buttons actually submit), click it, and record:
    path   — where the browser ended up (path + sorted query keys)
    status — HTTP status of the last main-frame document response
    dialog — accessible name of any open <dialog> / [role=dialog]
    h1     — the resulting page's main heading (normalized)
The same is done for the matched clone element and the two outcomes compared.
Destructive actions (Pay, Delete, ...) are skipped and clicks per page capped.

Extended exploration (config `behavior_extended`, default on; Task 11):
    selects — each option (up to MAX_OPTIONS) of every matched <select> is chosen on a fresh load and the
              resulting state recorded, including whether the visible (masked) page text changed;
    dialogs — for every click that opens a dialog, each button inside the dialog (up to MAX_DIALOG_BUTTONS)
              is clicked once (one level deep) and the resulting state recorded.
"""
import re
from urllib.parse import parse_qsl, urlsplit

from ..capture import extract_elements, load, normalize

CLICKABLE = {"link", "button"}
RETRIES = {"count": 0}   # behaviour outcomes re-measured because exactly one side errored (Task 15)


def _compare(page, real_url, clone_url, r_idx, c_idx, regexes, orr=None, oc=None, **kw):
    """Outcomes on both sites. If exactly one side errored (e.g. a 3 s click timeout under load), re-measure that side
    once: a transient glitch must not become a ticket, while a genuinely dead/missing control errors again."""
    orr = orr or click_outcome(page, real_url, r_idx, regexes, **kw)
    oc = oc or click_outcome(page, clone_url, c_idx, regexes, **kw)
    if ("error" in orr) != ("error" in oc):
        RETRIES["count"] += 1
        if "error" in orr:
            orr = click_outcome(page, real_url, r_idx, regexes, **kw)
        else:
            oc = click_outcome(page, clone_url, c_idx, regexes, **kw)
    return orr, oc
MAX_OPTIONS, MAX_DIALOG_BUTTONS = 4, 4
TEXT_JS = "() => document.body.innerText"
DIALOG_BUTTONS_JS = r"""
() => { const d = [...document.querySelectorAll('dialog[open], [role=dialog]')].find(x => x.getBoundingClientRect().width > 0);
  return d ? [...d.querySelectorAll('button, [role=button], a[href]')].map(b => (b.getAttribute('aria-label') || b.innerText).trim())
               .filter(Boolean) : []; }
"""
OPTIONS_JS = "(idx) => { const el = document.querySelector(`[data-fa-idx=\"${idx}\"]`); return el && el.options ? [...el.options].map(o => o.text) : []; }"

FILL_JS = r"""
(idx) => {
  const el = document.querySelector(`[data-fa-idx="${idx}"]`);
  const f = el && el.form;
  if (!f) return;
  f.querySelectorAll('input[required], textarea[required]').forEach(i => {
    if (!i.value) i.value = i.type === 'email' ? 'test@example.com' : 'TEST';
  });
}
"""

STATE_JS = r"""
() => {
  const d = [...document.querySelectorAll('dialog[open], [role=dialog]')]
     .filter(x => x.getBoundingClientRect().width > 0);
  const h = document.querySelector('h1');
  return { dialog: d.length ? (d[0].getAttribute('aria-label') || d[0].innerText.slice(0, 40)) : null,
           h1: h ? h.innerText : null };
}
"""


def _path(url):
    u = urlsplit(url)
    keys = sorted(k for k, _ in parse_qsl(u.query))
    # Query values are random per run (e.g. flight ids), so only keys are compared; "…" marks an elided value.
    return u.path + (("?" + "&".join(k + "=…" for k in keys)) if keys else "")


def click_outcome(page, url, idx, regexes, select=None, then=None):
    """Load url, act on element idx and return the resulting state.
    select: choose this option label instead of clicking. then: after the click, click this button inside the open dialog."""
    status = {"code": None}

    def on_resp(r):
        if r.request.is_navigation_request() and r.frame == page.main_frame:
            status["code"] = r.status

    load(page, url)
    extract_elements(page, regexes)   # (re)tags elements with data-fa-idx
    before = _path(page.url)
    page.on("response", on_resp)
    text0 = normalize(page.evaluate(TEXT_JS), regexes) if select is not None else None
    try:
        el = page.locator(f'[data-fa-idx="{idx}"]')
        if select is not None:
            if select not in page.evaluate(OPTIONS_JS, idx):
                raise LookupError("option missing")
            el.select_option(label=select, timeout=3000)
        else:
            page.evaluate(FILL_JS, idx)
            el.click(timeout=3000)
            if then is not None:
                page.wait_for_timeout(150)
                page.locator("dialog[open], [role=dialog]").get_by_role("button", name=then, exact=True).first.click(timeout=3000)
        page.wait_for_load_state("load", timeout=5000)
        page.wait_for_timeout(150)
    except Exception as e:  # noqa: BLE001 — record failure as an outcome
        page.remove_listener("response", on_resp)
        return {"error": str(e) if isinstance(e, LookupError) else type(e).__name__}
    page.remove_listener("response", on_resp)
    st = page.evaluate(STATE_JS)
    after = _path(page.url)
    return {
        "path": after,
        "navigated": after != before or status["code"] is not None,
        "status": status["code"] if status["code"] is not None else 200,
        "dialog": normalize(st["dialog"] or "", regexes) or None,
        "h1": normalize(st["h1"] or "", regexes),
        "changed": (normalize(page.evaluate(TEXT_JS), regexes) != text0) if select is not None and after == before else None,
        "in_dialog": then is not None,
    }


def describe(o):
    if "error" in o:
        return f"cannot be used ({o['error']})"
    parts = []
    if o["dialog"]:
        parts.append(f"{'leaves' if o.get('in_dialog') else 'opens'} dialog '{o['dialog']}'" + (" open" if o.get("in_dialog") else ""))
    if o["navigated"]:
        parts.append(f"navigates to {o['path']}" + (f" (HTTP {o['status']})" if o["status"] != 200 else ""))
    if o.get("changed"):
        parts.append("changes the page content")
    return " and ".join(parts) or "has no visible effect"


def diff_outcomes(a, b):
    if "error" in a or "error" in b:
        return ("error" in a) != ("error" in b)
    return any(a[k] != b[k] for k in ("path", "status", "dialog", "navigated", "changed")) or \
        (a["navigated"] and a["h1"] != b["h1"])


def explore_page(browser_ctx, real_url, clone_url, real_els, clone_els, pairs, cfg, cache):
    regexes = [m["regex"] for m in cfg["mask"] if "regex" in m]
    skip = re.compile(cfg.get("skip_actions", r"(?i)\b(pay|delete|purchase|buy|remove)\b"))
    cap = cfg.get("max_clicks_per_page", 25)
    page = browser_ctx.new_page()
    page.on("dialog", lambda d: d.dismiss())
    results, n = [], 0
    for i, j, _ in pairs:
        r, c = real_els[i], clone_els[j]
        if r["role"] not in CLICKABLE or skip.search(r["name"]):
            continue
        if n >= cap:
            break
        n += 1
        # Links with identical (name, href) behave the same on every page; cache them.
        key_r = ("real", r["role"], r["norm"], r["href"]) if r["href"] else None
        key_c = ("clone", c["role"], c["norm"], c["href"]) if c["href"] else None
        orr, oc = _compare(page, real_url, clone_url, r["idx"], c["idx"], regexes,
                           orr=cache.get(key_r) if key_r else None, oc=cache.get(key_c) if key_c else None)
        if key_r: cache[key_r] = orr
        if key_c: cache[key_c] = oc
        results.append({"real": r, "clone": c, "real_out": orr, "clone_out": oc,
                        "same": not diff_outcomes(orr, oc)})
        if cfg.get("behavior_extended", True) and orr.get("dialog") and "error" not in orr:
            # one level inside the dialog the click opened
            try:
                load(page, real_url); extract_elements(page, regexes)
                page.locator(f'[data-fa-idx="{r["idx"]}"]').click(timeout=3000); page.wait_for_timeout(150)
                names = page.evaluate(DIALOG_BUTTONS_JS)[:MAX_DIALOG_BUTTONS]
            except Exception:  # noqa: BLE001 — opener behaved differently on reload; the click result above covers it
                names = []
            for name in names:
                if skip.search(name):
                    continue
                o_r, o_c = _compare(page, real_url, clone_url, r["idx"], c["idx"], regexes, then=name)
                results.append({"real": r, "clone": c, "real_out": o_r, "clone_out": o_c, "same": not diff_outcomes(o_r, o_c),
                                "label": f"Button '{name}' in dialog '{orr['dialog']}'", "key": f"dialog:{name}"})
    if cfg.get("behavior_extended", True):
        for i, j, _ in pairs:
            r, c = real_els[i], clone_els[j]
            if r["role"] != "combobox" or skip.search(r["name"]):
                continue
            load(page, real_url); extract_elements(page, regexes)
            for opt in page.evaluate(OPTIONS_JS, r["idx"])[:MAX_OPTIONS]:
                o_r, o_c = _compare(page, real_url, clone_url, r["idx"], c["idx"], regexes, select=opt)
                results.append({"real": r, "clone": c, "real_out": o_r, "clone_out": o_c, "same": not diff_outcomes(o_r, o_c),
                                "label": f"Select '{r['name']}' option '{opt}'", "key": f"option:{opt}"})
    page.close()
    score = 1.0 if not results else sum(x["same"] for x in results) / len(results)
    return {"score": score, "results": results}
