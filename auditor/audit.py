"""Orchestrates an audit: capture -> compare (4 layers) -> score -> gaps -> report."""
import json
import time
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from playwright.sync_api import sync_playwright

from .capture import NAV, WAIT, capture_site, new_context, slugify
from .compare.behavior import RETRIES as BEHAVIOR_RETRIES, describe, explore_page
from .compare.elements import MOVE_PX, MOVE_PX_V3, compare_elements
from .compare.flows import QUICK as FLOW_QUICK, compare_flow
from .compare.visual import compare_visual, crop_pair
from .report import write_report

DEFAULT_WEIGHTS = {"visual": 0.15, "elements": 0.30, "behavior": 0.25, "flows": 0.30}
SEV_RANK = {"high": 0, "medium": 1, "low": 2}
# v2: multiplicative penalty per gap. High/medium are the agent-relevant severities (SPEC §6: missing element,
# broken flow / relabel, behaviour change); low (cosmetic, visual-only) costs nothing beyond its layer score.
SEV_PENALTY = {"high": 0.05, "medium": 0.02, "low": 0.0}
LAYER_RANK = {"flows": 0, "elements": 1, "behavior": 2, "visual": 3}


def load_config(path_or_dict):
    cfg = path_or_dict if isinstance(path_or_dict, dict) else yaml.safe_load(Path(path_or_dict).read_text())
    cfg.setdefault("viewports", [[1440, 900]])
    cfg.setdefault("mask", [])
    cfg.setdefault("pages", ["/"])
    cfg.setdefault("flows", [])
    cfg.setdefault("weights", DEFAULT_WEIGHTS)
    cfg.setdefault("scoring", "v3")
    return cfg


def aggregate(page_scores, scoring="v2"):
    """Combine per-page scores of one layer.

    v1: plain mean (one broken page among 7 costs 1/7 of its loss).
    v2: 0.5 * mean + 0.5 * worst page, so a defect on one page is not diluted by the pages that are fine
        (an agent task fails if any page on its path is broken).
    """
    mean = sum(page_scores) / len(page_scores)
    return mean if scoring == "v1" else 0.5 * mean + 0.5 * min(page_scores)


def _el(r, c):
    """Structured element reference for a gap: role and name as on the real site (clone's if it only exists there)."""
    e = r or c
    return {"role": e["role"], "name": e["name"], "real_box": r["box"] if r else None, "clone_box": c["box"] if c else None,
            **({"clone_name": c["name"]} if r and c and c["name"] != r["name"] else {})}


def _flow_step(cfg, f):
    """Structured reference to the flow step where a flow diverged: which step, what it acts on, and how it failed."""
    step = next(x for x in cfg["flows"] if x["name"] == f["name"])["steps"][f["diverged_at"] - 1]
    (kind, arg), = step.items()
    tgt = ({"role": arg.get("role", "button"), "name": arg["name"]} if kind == "click" else
           {"role": "field", "name": arg["label"]} if kind in ("fill", "select") else
           {"role": "dialog" if kind == "expect_dialog" else "button", "name": arg} if isinstance(arg, str) else {})
    return {"flow": f["name"], "index": f["diverged_at"], "action": kind, **tgt, "page": f["page"],
            "outcome": "step failed" if f["detail"].startswith("could not") else "state differs"}


def penalised(base, gaps, scoring="v2"):
    """v2: multiply the weighted layer score by (1 - penalty) per high/medium gap; v1: unchanged.
    A grouped ticket (Task 15) carries `weight` = number of affected targets and is penalised per target, so grouping
    changes the ticket count but not the score."""
    if scoring == "v1":
        return base
    for g in gaps:
        base *= (1.0 - SEV_PENALTY[g["severity"]]) ** g.get("weight", 1)
    return base


MOVE_GROUP_PX = 4   # moves whose offsets agree within this many px share one root cause (Task 15)


def _offset(f):
    (rx, ry, rw, rh), (cx, cy, cw, ch) = f["real"]["box"], f["clone"]["box"]
    return round((cx + cw / 2) - (rx + rw / 2)), round((cy + ch / 2) - (ry + rh / 2))


def group_moves(findings):
    """Group moved click targets on one page by common offset (greedy, in reading order)."""
    groups = []
    for f in sorted(findings, key=lambda f: (f["real"]["box"][1], f["real"]["box"][0])):
        dx, dy = _offset(f)
        for g in groups:
            gx, gy = _offset(g[0])
            if abs(dx - gx) <= MOVE_GROUP_PX and abs(dy - gy) <= MOVE_GROUP_PX:
                g.append(f); break
        else:
            groups.append([f])
    return groups


def _union(boxes):
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes); y1 = max(b[1] + b[3] for b in boxes)
    return [x0, y0, x1 - x0, y1 - y0]


def _direction(dx, dy):
    parts = ([f"{'down' if dy > 0 else 'up'}"] if abs(dy) > 2 else []) + ([f"{'right' if dx > 0 else 'left'}"] if abs(dx) > 2 else [])
    return " and ".join(parts) or "in place"


def a11y_name_only(a, b):
    """True when two behaviour outcomes differ only in the dialog's accessible name, and the clone's dialog is the same
    dialog without its name (its text starts with the real dialog's name) — an accessibility-name mismatch."""
    if "error" in a or "error" in b or not a.get("dialog") or not b.get("dialog"):
        return False
    same = all(a.get(k) == b.get(k) for k in ("path", "status", "navigated", "changed"))
    return same and a["dialog"] != b["dialog"] and b["dialog"].startswith(a["dialog"])


def _a11y_gap(real_name, clone_name, page, p, vp, box_r, box_c, element):
    """Severity medium: decided from agent data (DECISIONS D27) — both proxy agents complete the affected task."""
    g = {"severity": "medium", "layer": "behavior", "page": page, "_p": p, "kind": "a11y_name",
         "description": f"Accessibility-name mismatch: dialog '{real_name}' opens with the same content on the clone, "
                        f"but has no matching accessible name (clone exposes '{clone_name[:40]}…'). Agents that look "
                        f"dialogs up by role and name will not find it.",
         "_key": ("a11y_name", real_name), "_mag": 2}
    if p is not None:
        g.update({"_box_r": box_r, "_box_c": box_c, "_vp": vp, "element": element})
    return g


def page_path(p):
    return urlsplit(p).path or "/"


def _overlapping(elements, box, limit=3):
    x, y, w, h = box
    hits = []
    for e in elements:
        ex, ey, ew, eh = e["box"]
        if ex < x + w and ex + ew > x and ey < y + h and ey + eh > y and e["name"]:
            hits.append(f"{e['role']} '{e['name'][:40]}'")
    return hits[:limit]


def run_audit(cfg, out_dir, headless=True, log=print):
    cfg = load_config(cfg)
    out = Path(out_dir)
    shots, crops = out / "shots", out / "crops"
    for d in (shots, crops):
        d.mkdir(parents=True, exist_ok=True)
    regexes = [m["regex"] for m in cfg["mask"] if "regex" in m]
    vps = [tuple(v) for v in cfg["viewports"]]
    quick = cfg.get("quick", False)   # fast iteration: first viewport only, no behaviour exploration
    FLOW_QUICK["on"] = quick
    if quick:
        vps = vps[:1]
    primary = vps[0]
    WAIT["mode"] = cfg.get("wait", "networkidle")
    NAV["retries"] = 0
    BEHAVIOR_RETRIES["count"] = 0
    t0 = time.time()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        log("capturing real site ...")
        real = capture_site(browser, cfg["real_url"], cfg["pages"], vps, cfg["mask"], shots, "real")
        log("capturing clone ...")
        clone = capture_site(browser, cfg["clone_url"], cfg["pages"], vps, cfg["mask"], shots, "clone")

        visual, elements, behavior = {}, {}, {}
        for p in cfg["pages"]:
            for vp in vps:
                k = (p, *vp)
                slug = f"{slugify(p)}_{vp[0]}x{vp[1]}"
                visual[k] = compare_visual(real[k], clone[k], shots, slug, cfg["scoring"])
            k = (p, *primary)
            size = visual[k]["size"]
            elements[p] = compare_elements(real[k]["elements"], clone[k]["elements"], size,
                                           MOVE_PX_V3 if cfg["scoring"] == "v3" else MOVE_PX)

        log("exploring behaviour ..." if not quick else "quick mode: behaviour skipped")
        ctx = new_context(browser, primary)
        cache = {}
        for p in cfg["pages"]:
            k = (p, *primary)
            behavior[p] = {"score": 1.0, "results": []} if quick else explore_page(
                ctx, cfg["real_url"] + p, cfg["clone_url"] + p, real[k]["elements"], clone[k]["elements"],
                elements[p]["pairs"], cfg, cache)
        ctx.close()

        log("replaying flows ...")
        flows = []
        cr, cc = new_context(browser, primary), new_context(browser, primary)
        for f in cfg["flows"]:
            flows.append(compare_flow(cr, cc, cfg["real_url"], cfg["clone_url"], f, regexes, shots))
        cr.close(); cc.close()
        browser.close()

    # ---------------- scores ----------------
    pages = cfg["pages"]
    per_page = OrderedDict()
    for p in pages:
        per_page[p] = {
            "path": page_path(p),
            "visual": sum(visual[(p, *vp)]["score"] for vp in vps) / len(vps),
            "elements": elements[p]["score"],
            "behavior": behavior[p]["score"],
        }
    valid_flows = [f for f in flows if not f.get("invalid")]
    layers = {k: aggregate([v[k] for v in per_page.values()], cfg["scoring"])
              for k in ("visual", "elements", "behavior")}
    layers.update({
        "flows": (sum(f["score"] for f in valid_flows) / len(valid_flows)) if valid_flows else 1.0,
    })
    w = dict(cfg["weights"], **({"behavior": 0} if quick else {}))   # quick: behaviour not measured, not counted
    base = sum(layers[k] * w[k] for k in layers) / sum(w.values())

    # ---------------- gaps ----------------
    raw = []

    def crop(tag, real_shot, clone_shot, box_r, box_c=None):
        rp, cp = crops / f"{tag}_real.png", crops / f"{tag}_clone.png"
        crop_pair(real_shot, real_shot, box_r, rp, rp)
        crop_pair(clone_shot, clone_shot, box_c or box_r, cp, cp)
        return str(rp.relative_to(out)), str(cp.relative_to(out))

    for p in pages:
        k = (p, *primary)
        moved, targets = [], []
        for f in elements[p]["findings"]:
            t = f["type"]
            if t == "moved" and cfg["scoring"] == "v3" and f["real"]["interactive"]:
                # v3: a moved click target breaks coordinate-based agents (Phase 1: layout_shift_hero halved
                # replay-agent success at v2 0.951) -> medium; grouped by common offset below (Task 15).
                targets.append(f); continue
            if t == "moved":
                moved.append(f); continue
            r, c = f.get("real"), f.get("clone")
            el = r or c
            if t == "missing":
                sev = "high" if r["interactive"] else "medium"
                desc = f"Missing {r['role']} '{r['name']}' on clone (present on real site)"
            elif t == "extra":
                sev = "medium" if c["interactive"] else "low"
                desc = f"Extra {c['role']} '{c['name']}' on clone (not on real site)"
            else:
                sev = "medium"
                desc = f"{r['role'].capitalize()} label reads '{c['name']}' on clone, '{r['name']}' on real site"
            raw.append({"severity": sev, "layer": "elements", "page": page_path(p), "_p": p,
                        "description": desc, "kind": t, "element": _el(r, c),
                        "_key": ("elements", t, el["role"], el["norm"]),
                        "_box_r": (r or c)["box"], "_box_c": (c or r)["box"], "_vp": primary,
                        "_mag": 1})
        for grp in group_moves(targets):
            r, c = grp[0]["real"], grp[0]["clone"]
            dx, dy = _offset(grp[0])
            common = {"severity": "medium", "layer": "elements", "page": page_path(p), "_p": p, "_vp": primary,
                      "kind": "target_moved", "element": _el(r, c), "moved_px": grp[0]["px"], "weight": len(grp),
                      "_box_r": _union([g["real"]["box"] for g in grp]), "_box_c": _union([g["clone"]["box"] for g in grp]),
                      "_mag": len(grp) * grp[0]["px"] / 100}
            if len(grp) == 1:
                raw.append({**common, "description": f"{r['role'].capitalize()} '{r['name']}': click target moved {grp[0]['px']}px",
                            "_key": ("elements", "target_moved", r["role"], r["norm"])})
            else:
                names = [g["real"]["name"] for g in grp]
                raw.append({**common, "elements": [_el(g["real"], g["clone"]) for g in grp],
                            "description": f"{len(grp)} click targets moved together ~{grp[0]['px']}px {_direction(dx, dy)} "
                                           f"(one layout change): " + ", ".join(f"'{n}'" for n in names[:6])
                                           + (f" and {len(names) - 6} more" if len(names) > 6 else ""),
                            "_key": ("elements", "target_group", tuple(sorted(g["real"]["norm"] for g in grp)))})
        if moved:
            mx = max(m["px"] for m in moved)
            ex = ", ".join(f"'{m['real']['name'][:25]}'" for m in moved[:3])
            raw.append({"severity": "low", "layer": "elements", "page": page_path(p), "_p": p,
                        "description": f"{len(moved)} element{'s' if len(moved) != 1 else ''} shifted position (up to {mx}px), e.g. {ex}",
                        "kind": "moved", "_key": ("elements", "moved", tuple(m["real"]["norm"] for m in moved), mx), "_box_r": moved[0]["real"]["box"],
                        "_box_c": moved[0]["clone"]["box"], "_vp": primary, "_mag": len(moved)})
        for res in behavior[p]["results"]:
            if res["same"]:
                continue
            r = res["real"]
            label = res.get("label") or f"{r['role'].capitalize()} '{r['name']}'"
            if a11y_name_only(res["real_out"], res["clone_out"]):
                raw.append(_a11y_gap(res["real_out"]["dialog"], res["clone_out"]["dialog"], page_path(p), p, primary,
                                     r["box"], res["clone"]["box"], _el(r, res["clone"])))
                continue
            raw.append({"severity": "medium", "layer": "behavior", "page": page_path(p), "_p": p,
                        "description": f"{label}: "
                                       f"on real site it {describe(res['real_out'])}; on clone it {describe(res['clone_out'])}",
                        "kind": "behavior", "element": _el(r, res["clone"]), **({"variant": res["key"]} if res.get("key") else {}),
                        "_key": ("behavior", r["role"], r["norm"], res.get("key"), describe(res["real_out"]), describe(res["clone_out"])),
                        "_box_r": r["box"], "_box_c": res["clone"]["box"], "_vp": primary, "_mag": 1})
        for vp in vps:
            v = visual[(p, *vp)]
            regs = v["regions"]
            if not regs:
                continue
            top = regs[0]
            over = _overlapping(real[(p, *vp)]["elements"], top["box"])
            x, y, ww, hh = top["box"]
            desc = (f"Visual differences at {vp[0]}x{vp[1]}: {len(regs)} region(s), "
                    f"{v['changed_frac'] * 100:.1f}% of page pixels changed"
                    + (f", page height {v['height_delta']:+d}px" if v["height_delta"] else "")
                    + f". Largest region {ww}x{hh} at ({x},{y})"
                    + (f" overlaps {', '.join(over)}" if over else ""))
            raw.append({"severity": "low", "layer": "visual", "page": page_path(p), "_p": p,
                        "description": desc, "kind": "visual", "_key": ("visual", p, vp),
                        "_box_r": top["box"], "_box_c": top["box"], "_vp": vp,
                        "_mag": v["changed_frac"], "regions": [r["box"] for r in regs[:10]]})
    for f in flows:
        if f.get("invalid"):
            raw.append({"severity": "high", "layer": "flows", "page": "-", "_p": None,
                        "description": f"CONFIG: flow '{f['name']}' {f['detail']}", "kind": "flow_config",
                        "_key": ("flowcfg", f["name"]), "_mag": 99})
        elif f["diverged_at"] and f.get("a11y"):
            raw.append({**_a11y_gap(f["a11y"][0], f["a11y"][1], f["page"], None, None, None, None, None),
                        "flow_step": {**_flow_step(cfg, f), "outcome": "accessibility-name mismatch"},
                        "_flow_shots": (f["real_shot"], f["clone_shot"])})
        elif f["diverged_at"]:
            raw.append({"severity": "high", "layer": "flows", "page": f["page"], "_p": None,
                        "description": f"Flow '{f['name']}' diverges at step {f['diverged_at']}: {f['detail']}",
                        "kind": "flow", "flow_step": _flow_step(cfg, f),
                        "_key": ("flows", f["name"]), "_mag": 99,
                        "_flow_shots": (f["real_shot"], f["clone_shot"])})

    # Merge duplicates across pages (e.g. a header link missing on every page).
    merged = OrderedDict()
    for g in raw:
        if g["_key"] in merged:
            merged[g["_key"]]["pages"].append(g["page"])
        else:
            g["pages"] = [g["page"]]
            merged[g["_key"]] = g
    gaps = sorted(merged.values(), key=lambda g: (SEV_RANK[g["severity"]], LAYER_RANK[g["layer"]], -g["_mag"]))

    final = []
    for n, g in enumerate(gaps, start=1):
        gid = f"gap-{n:03d}"
        item = {"id": gid, "severity": g["severity"], "layer": g["layer"], "page": g["page"],
                "description": g["description"]}
        for k in ("kind", "element", "elements", "flow_step", "moved_px", "variant", "weight"):   # structured fields (Task 15); additive
            if g.get(k) is not None:
                item[k] = g[k]
        if g.get("regions"):
            item["regions"] = g["regions"]
        if len(g["pages"]) > 1:
            item["also_on"] = sorted(set(g["pages"]) - {g["page"]})
        if g.get("_flow_shots"):
            rs, cs = g["_flow_shots"]
            item["real_screenshot"] = str(Path(rs).relative_to(out))
            item["clone_screenshot"] = str(Path(cs).relative_to(out))
        elif g.get("_p") is not None:
            k = (g["_p"], *g["_vp"])
            item["real_screenshot"], item["clone_screenshot"] = crop(
                gid, real[k]["shot"], clone[k]["shot"], g["_box_r"], g["_box_c"])
        final.append(item)

    overall = penalised(base, final, cfg["scoring"])
    summary = {
        "real_url": cfg["real_url"], "clone_url": cfg["clone_url"],
        "scoring": cfg["scoring"], "quick": quick, "overall": round(overall, 4), "base": round(base, 4), "nav_retries": NAV["retries"], "behavior_retries": BEHAVIOR_RETRIES["count"],
        "layers": {k: round(v, 4) for k, v in layers.items()},
        "weights": w,
        "pages": [{"page": v["path"], "url": p, **{k: round(v[k], 4) for k in ("visual", "elements", "behavior")},
                   "heatmaps": [str(visual[(p, *vp)]["heatmap"].relative_to(out)) for vp in vps],
                   "real_shot": str(real[(p, *primary)]["shot"].relative_to(out)),
                   "clone_shot": str(clone[(p, *primary)]["shot"].relative_to(out))}
                  for p, v in per_page.items()],
        "flows": [{k: v for k, v in f.items() if not k.endswith("_shot")} for f in flows],
        "gap_counts": {s: sum(1 for g in final if g["severity"] == s) for s in SEV_RANK},
        "seconds": round(time.time() - t0, 1),
    }
    (out / "gaps.json").write_text(json.dumps(final, indent=2))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    write_report(out, summary, final, cfg)
    log(f"overall fidelity {overall:.3f}  ({summary['seconds']}s, {len(final)} gaps)")
    return summary, final
