"""Export deck assets (Task 19) to docs/slides/. Pillow + Playwright only; every number is read from run outputs.

    python tools/slides.py

Inputs: runs/validation{,_heldout,_draft}/ (final v3 runs), runs/agents/results.json (Task 10 outcomes),
runs/predict/results.json (frozen predictor output), runs/fixloop/clone_mid/history.json.
All images are >= 1600 px wide on a light background. Local URLs/ports are replaced by labels.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "refapp"))
from agents import TASKS  # noqa: E402

OUT = ROOT / "docs" / "slides"
RUNS = ROOT / "runs"
W = 1920
BG, INK, MUTED, LINE = (250, 251, 253), (27, 42, 58), (95, 107, 123), (214, 224, 234)
BLUE, ORANGE, GREEN, RED, GREY = (31, 105, 164), (222, 112, 20), (46, 139, 87), (196, 52, 52), (150, 158, 168)


def font(size, bold=False):
    for f in ("/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(f, size, index=1 if bold else 0)
        except OSError:
            pass
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans" + ("-Bold" if bold else "") + ".ttf", size)
    except OSError:
        return ImageFont.load_default()


def canvas(h, title=None, subtitle=None):
    im = Image.new("RGB", (W, h), BG); d = ImageDraw.Draw(im)
    y = 40
    if title:
        d.text((60, y), title, font=font(52, True), fill=INK); y += 72
    if subtitle:
        d.text((60, y), subtitle, font=font(30), fill=MUTED); y += 50
    return im, d, y + 20


def tw(d, s, f):
    b = d.textbbox((0, 0), s, font=f); return b[2] - b[0], b[3] - b[1]


def arrow(d, x0, y0, x1, y1, col=MUTED, w=5):
    d.line([x0, y0, x1, y1], fill=col, width=w)
    a = math.atan2(y1 - y0, x1 - x0)
    for s in (0.45, -0.45):
        d.line([x1, y1, x1 - 22 * math.cos(a + s), y1 - 22 * math.sin(a + s)], fill=col, width=w)


def box(d, x, y, w, h, title, lines, col=BLUE):
    d.rounded_rectangle([x, y, x + w, y + h], 18, fill=(255, 255, 255), outline=col, width=4)
    d.text((x + 24, y + 20), title, font=font(36, True), fill=col)
    for i, s in enumerate(lines):
        d.text((x + 24, y + 76 + i * 40), s, font=font(27), fill=INK)


def architecture():
    im, d, y = canvas(980, "How the auditor works", "One config, two sites, four independent checks, one ticket list")
    top = y + 40
    box(d, 50, top + 170, 300, 300, "Config", ["pages", "viewports", "masks", "flows", "scoring"])
    box(d, 420, top + 170, 320, 300, "Capture", ["real site + clone", "Playwright", "screenshots,", "elements, masks"])
    layers = [("Visual", "screenshots, ±3px tolerant"), ("Elements", "role, name, position"),
              ("Behavior", "clicks, selects, dialogs"), ("Flows", "multi-step tasks, no Pay")]
    for i, (t, s) in enumerate(layers):
        yy = top + i * 165
        d.rounded_rectangle([820, yy, 1230, yy + 140], 18, fill=(255, 255, 255), outline=GREEN, width=4)
        d.text((844, yy + 18), t, font=font(36, True), fill=GREEN)
        d.text((844, yy + 74), s, font=font(27), fill=INK)
        arrow(d, 745, top + 320, 812, yy + 70)
        arrow(d, 1235, yy + 70, 1300, top + 320)
    box(d, 1310, top + 120, 290, 400, "Tickets", ["severity", "element / flow step", "screenshots", "gaps.json", "", "+ audit-coverage", "  summary (0–1)"], ORANGE)
    box(d, 1650, top + 170, 230, 300, "Report", ["report.html", "ranked", "tickets,", "side by side"], BLUE)
    arrow(d, 352, top + 320, 412, top + 320); arrow(d, 1602, top + 320, 1642, top + 320)
    im.save(OUT / "01_architecture.png")


def ticket(run, gap_id, title, fname, note):
    g = next(x for x in json.loads((run / "gaps.json").read_text()) if x["id"] == gap_id)
    a, b = Image.open(run / g["real_screenshot"]).convert("RGB"), Image.open(run / g["clone_screenshot"]).convert("RGB")
    slot_w = (W - 180) // 2
    s = min(slot_w / max(a.width, b.width), 520 / max(a.height, b.height), 4.0)
    a = a.resize((int(a.width * s), int(a.height * s)), Image.LANCZOS); b = b.resize((int(b.width * s), int(b.height * s)), Image.LANCZOS)
    im, d, y = canvas(320 + max(a.height, b.height) + 120, title)
    d.rounded_rectangle([60, y, W - 60, y + 110], 14, fill=(255, 255, 255), outline=LINE, width=2)
    chip = {"high": RED, "medium": ORANGE, "low": GREY}[g["severity"]]
    cw = tw(d, g["severity"], font(28, True))[0]
    d.rounded_rectangle([84, y + 30, 84 + cw + 30, y + 78], 20, fill=chip)
    d.text((99, y + 34), g["severity"], font=font(28, True), fill=(255, 255, 255))
    desc = g["description"] if len(g["description"]) < 95 else g["description"][:92] + "…"
    d.text((84 + cw + 60, y + 34), f"{g['page']}   ·   {desc}", font=font(29), fill=INK)
    y += 150
    for i, (img, cap) in enumerate(((a, "Real site"), (b, "Clone"))):
        x = 60 + i * (slot_w + 60) + (slot_w - img.width) // 2
        d.text((60 + i * (slot_w + 60), y), cap, font=font(32, True), fill=MUTED)
        im.paste(img, (x, y + 50)); d.rectangle([x - 1, y + 49, x + img.width, y + 50 + img.height], outline=LINE, width=2)
    d.text((60, y + 80 + max(a.height, b.height)), note, font=font(28), fill=MUTED)
    im.save(OUT / fname)


def moved_ticket(run, gap_id, fname):
    """Moved targets: crop the SAME region from both full-page screenshots so the move is visible, and outline each
    element's real-site position (dashed) on the clone."""
    g = next(x for x in json.loads((run / "gaps.json").read_text()) if x["id"] == gap_id)
    els = g.get("elements") or [g["element"]]
    page = g["page"].strip("/").replace("/", "_") or "home"
    real = Image.open(run / f"shots/real_{page}_1440x900.png").convert("RGB")
    clone = Image.open(run / f"shots/clone_{page}_1440x900.png").convert("RGB")
    boxes = [e["real_box"] for e in els] + [e["clone_box"] for e in els]
    x0 = max(0, min(b[0] for b in boxes) - 30); y0 = max(0, min(b[1] for b in boxes) - 50)
    x1 = min(real.width, max(b[0] + b[2] for b in boxes) + 60); y1 = max(b[1] + b[3] for b in boxes) + 50
    crops = []
    for src, outline in ((real, False), (clone, True)):
        c = Image.new("RGB", (x1 - x0, y1 - y0), (255, 255, 255)); c.paste(src.crop((x0, y0, min(x1, src.width), min(y1, src.height))), (0, 0))
        if outline:
            dd = ImageDraw.Draw(c)
            for e in els:
                bx, by, bw, bh = e["real_box"]
                dd.rectangle([bx - x0 - 4, by - y0 - 4, bx - x0 + bw + 4, by - y0 + bh + 4], outline=RED, width=3)
        crops.append(c)
    slot_w = (W - 180) // 2
    sc = min(slot_w / crops[0].width, 560 / crops[0].height, 3.0)
    crops = [c.resize((int(c.width * sc), int(c.height * sc)), Image.LANCZOS) for c in crops]
    im, d, y = canvas(330 + crops[0].height + 130, "A ticket: click targets moved (held-out defect)")
    d.rounded_rectangle([60, y, W - 60, y + 110], 14, fill=(255, 255, 255), outline=LINE, width=2)
    cw = tw(d, g["severity"], font(28, True))[0]
    d.rounded_rectangle([84, y + 30, 84 + cw + 30, y + 78], 20, fill=ORANGE)
    d.text((99, y + 34), g["severity"], font=font(28, True), fill=(255, 255, 255))
    d.text((84 + cw + 60, y + 34), f"{g['page']}   ·   {len(els)} click targets moved together ~{g['moved_px']}px down (one layout change)",
           font=font(29), fill=INK)
    y += 150
    for i, (c, cap) in enumerate(zip(crops, ("Real site", "Clone (red: where they are on the real site)"))):
        x = 60 + i * (slot_w + 60)
        d.text((x, y), cap, font=font(32, True), fill=MUTED)
        im.paste(c, (x, y + 50)); d.rectangle([x - 1, y + 49, x + c.width, y + 50 + c.height], outline=LINE, width=2)
    d.text((60, y + 80 + crops[0].height), "Same region on both sites: the button and footer links moved ~60px, "
           "so an agent clicking recorded coordinates hits empty space.", font=font(28), fill=MUTED)
    im.save(OUT / fname)


def heatmap():
    src = Image.open(RUNS / "validation/v3/clone_mid/shots/heat_home_1440x900.png").convert("RGB")
    s = (W - 120) / src.width
    src = src.resize((W - 120, int(src.height * s)), Image.LANCZOS)
    im, d, y = canvas(src.height + 260, "Visual layer: where the clone differs (clone_mid, home page)",
                      "Red = still different after the ±3px shift search · magenta = masked dynamic content (prices, dates, clock)")
    im.paste(src, (60, y)); d.rectangle([59, y - 1, 60 + src.width, y + src.height], outline=LINE, width=2)
    im.save(OUT / "04_heatmap_clone_mid_home.png")


def report_top():
    from playwright.sync_api import sync_playwright
    rep = RUNS / "validation/v3/clone_mid/report.html"
    out = OUT / "05_report_top_clone_mid.png"
    with sync_playwright() as pw:
        br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1.25)
        pg.goto(rep.as_uri())
        pg.evaluate("""() => { const s = document.querySelector('.sub'); if (s) s.textContent =
            'Scoring v3 · Real: Harbor Air (reference site) · Clone: clone_mid (6 planted defects) · 7 pages, 3 flows';
            document.title = 'Clone fidelity audit — clone_mid'; }""")
        h = pg.evaluate("() => document.querySelector('.top').getBoundingClientRect().bottom + 30")
        pg.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1600, "height": h})
        br.close()


def validation_table():
    from defects import REBUILT_DEFECTS, SWEEP_ORDER
    from heldout_defects import HELDOUT_DEFECTS as HD
    m = json.loads((RUNS / "validation/results.json").read_text())["v3"]
    h = json.loads((RUNS / "validation_heldout/results.json").read_text())["v3"]
    dr = json.loads((RUNS / "validation_draft/results.json").read_text())["v3"]["draft"]
    noise = [m[f"noise_{i}"] for i in (1, 2, 3)]
    rows = [
        ("Real site vs itself (3 runs)", "No noise", f"{min(x['overall'] for x in noise):.3f}, {sum(x['n_gaps'] for x in noise)} tickets"),
        ("14 defects planted in the real app", "Recall, known defects", f"{sum(1 for d in SWEEP_ORDER if m[f'single_{d}']['detected'])}/14 found"),
        ("4 defects in the screenshot-rebuilt clone", "Recall on realistic noise", f"{sum(1 for d in REBUILT_DEFECTS if m[f'rebuilt_{d}']['detected'])}/4 found"),
        ("10 held-out defects (separate agent, frozen first)", "Recall, unseen defects",
         f"{sum(1 for d in HD if h[f'tpl_{d}']['detected'])}/10 template · {sum(1 for d in HD if h[f'rebuilt_{d}']['detected'])}/10 rebuilt"),
        ("High/medium false alarms (held-out + draft)", "Precision of serious tickets", "0 (hand-checked)"),
        ("First-draft clone (separate agent, ~3 min)", "Realistic agent-made clone",
         f"{dr['gap_counts']['high']} high · {dr['gap_counts']['medium']} medium · {dr['gap_counts']['low']} low, all real"),
        ("Not detected", "Known blind spot", "faint colour-only tint"),
    ]
    im, d, y = canvas(260 + 110 * (len(rows) + 1), "Validation summary (scoring v3)",
                      "Harbor Air reference site · python validate.py, --heldout, --draft")
    cols = [60, 900, 1360]
    d.rectangle([60, y, W - 60, y + 90], fill=(234, 240, 246))
    for x, t in zip(cols, ("Test", "What it shows", "Result")):
        d.text((x + 24, y + 26), t, font=font(32, True), fill=INK)
    for i, r in enumerate(rows):
        yy = y + 90 + i * 110
        d.line([60, yy, W - 60, yy], fill=LINE, width=2)
        for j, (x, t) in enumerate(zip(cols, r)):
            d.text((x + 24, yy + 34), t, font=font(31, j == 2), fill=RED if r[0] == "Not detected" and j == 2 else INK)
    d.line([60, y + 90 + len(rows) * 110, W - 60, y + 90 + len(rows) * 110], fill=LINE, width=2)
    im.save(OUT / "06_validation_summary.png")


def axes(d, x0, y0, x1, y1, xr, yr, xt, yt, xl, yl, fmtx="{:.2f}", fmty="{:.2f}"):
    sx = lambda v: x0 + (v - xr[0]) / (xr[1] - xr[0]) * (x1 - x0)
    sy = lambda v: y1 - (v - yr[0]) / (yr[1] - yr[0]) * (y1 - y0)
    for v in yt:
        d.line([x0, sy(v), x1, sy(v)], fill=(232, 236, 241), width=2)
        d.text((x0 - 20 - tw(d, fmty.format(v), font(26))[0], sy(v) - 15), fmty.format(v), font=font(26), fill=MUTED)
    for v in xt:
        d.text((sx(v) - tw(d, fmtx.format(v), font(26))[0] / 2, y1 + 16), fmtx.format(v), font=font(26), fill=MUTED)
    d.line([x0, y1, x1, y1], fill=MUTED, width=3); d.line([x0, y0, x0, y1], fill=MUTED, width=3)
    if xl:
        d.text(((x0 + x1) / 2 - tw(d, xl, font(30))[0] / 2, y1 + 64), xl, font=font(30), fill=INK)
    d.text((x0, y0 - 52), yl, font=font(30), fill=INK)
    return sx, sy


def correlation():
    agents = json.loads((RUNS / "agents/results.json").read_text())
    scores = {}
    for f in ("validation", "validation_heldout", "validation_draft"):
        for k, v in json.loads((RUNS / f / "results.json").read_text())["v3"].items():
            scores.setdefault(k, v["overall"])
    nonflow = [t for t, s in TASKS.items() if s["overlap"] == "none"]
    rows = [a for a in agents if a["clone"] in scores and a["clone"] != "real" and not a["clone"].startswith("sweep_")]
    im, d, y = canvas(1080, "The single number does not predict agent success",
                      f"Score (v3) vs real-site success on the {len(nonflow)} tasks that share no step with the audit's flows · {len(rows)} clones")
    sx, sy = axes(d, 200, y + 90, W - 120, 940, (0.2, 1.0), (0.0, 1.05), [0.2, 0.4, 0.6, 0.8, 1.0], [0, 0.25, 0.5, 0.75, 1.0],
                  "audit-coverage summary (v3)", "real-site success, no-flow tasks")
    for k, (ag, col) in enumerate((("replay", BLUE), ("semantic", ORANGE))):
        xs = [scores[a["clone"]] for a in rows]
        ys = [sum(a["tasks"][t][ag] for t in nonflow) / len(nonflow) for a in rows]
        rho = spearmanr(xs, ys).correlation
        for x, v in zip(xs, ys):
            cx, cy = sx(x) + (k * 2 - 1) * 5, sy(v) - k * 8
            (d.ellipse if k == 0 else d.rectangle)([cx - 11, cy - 11, cx + 11, cy + 11], outline=col, width=4)
        ly = y + 128 + 50 * k
        (d.ellipse if k == 0 else d.rectangle)([240, ly - 11, 262, ly + 11], outline=col, width=4)
        d.text((280, ly - 20), f"{ag} agent   ρ = {rho:+.2f}", font=font(32, True), fill=col)
    d.text((240, y + 220), "every 95% interval includes 0", font=font(28), fill=MUTED)
    im.save(OUT / "07_correlation_noflow.png")


def f1_bars():
    rows = json.loads((RUNS / "predict/results.json").read_text())["rows"]
    rng = np.random.default_rng(0)

    def f1(rr, p):
        tp = sum(x[p] and x["fail"] for x in rr); fp = sum(x[p] and not x["fail"] for x in rr); fn = sum(x["fail"] and not x[p] for x in rr)
        return 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    data = {}
    for ag in ("replay", "semantic"):
        rr = [x for x in rows if x["set"] == "heldout" and x["scoring"] == "v3" and x["agent"] == ag]
        by = {}
        for x in rr:
            by.setdefault(x["clone"], []).append(x)
        cl = sorted(by)
        for p in ("P_aware", "B_score", "B_high"):
            bs = [f1([yy for c in rng.choice(cl, len(cl)) for yy in by[c]], p) for _ in range(2000)]
            data[(ag, p)] = (f1(rr, p), np.percentile(bs, 2.5), np.percentile(bs, 97.5), sum(x["fail"] for x in rr))
    im, d, y = canvas(1080, "Tickets on a task's path predict which tasks fail",
                      "Held-out clones (20), scoring v3 · F1 with bootstrap 95% intervals · predictor frozen before its held-out run")
    for bi, (lab, col) in enumerate((("Tickets on the task's path", GREEN), ("Score below threshold", GREY), ("Clone has any high ticket", (110, 120, 132)))):
        lx = 200 + bi * 520
        d.rectangle([lx, y + 6, lx + 30, y + 36], fill=col); d.text((lx + 44, y + 4), lab, font=font(28), fill=INK)
    y += 50
    sx, sy = axes(d, 200, y + 90, W - 120, 900, (0, 1), (0, 1.05), [], [0, 0.25, 0.5, 0.75, 1.0], "", "F1")
    labels = (("P_aware", "Tickets on the task's path", GREEN), ("B_score", "Score below threshold", GREY),
              ("B_high", "Clone has any high ticket", (110, 120, 132)))
    gx = [560, 1340]
    for gi, ag in enumerate(("replay", "semantic")):
        n = data[(ag, "P_aware")][3]
        cap = f"{ag} agent (n = {n} failures)"
        d.text((gx[gi] - tw(d, cap, font(32, True))[0] / 2, 912), cap, font=font(32, True), fill=INK)
        for bi, (p, lab, col) in enumerate(labels):
            v, lo, hi, _ = data[(ag, p)]
            x = gx[gi] + (bi - 1) * 190
            d.rectangle([x - 70, sy(v), x + 70, sy(0)], fill=col)
            for yy in (lo, hi):
                d.line([x - 18, sy(yy), x + 18, sy(yy)], fill=INK, width=4)
            d.line([x, sy(lo), x, sy(hi)], fill=INK, width=4)
            d.text((x - tw(d, f"{v:.2f}", font(32, True))[0] / 2, sy(max(v, hi)) - 48), f"{v:.2f}", font=font(32, True), fill=INK)
    d.text((200, 1010), "Semantic agent: all 14 failures predicted, no false positives, so the bootstrap interval is degenerate; "
           "exact 95% CI for recall 0.77–1.00.", font=font(26), fill=MUTED)
    im.save(OUT / "08_f1_vs_baselines.png")


def fixloop():
    h = json.loads((RUNS / "fixloop/clone_mid/history.json").read_text())
    pts = [(r["iter"], r["score"]) for r in h]
    im, d, y = canvas(1000, "Fix the top ticket, re-audit, repeat (clone_mid)",
                      "Each step switches off the planted defect behind the top high/medium ticket · scoring v3")
    sx, sy = axes(d, 200, y + 90, W - 160, 860, (-0.3, len(pts) - 0.7), (0.5, 1.05), list(range(len(pts))),
                  [0.5, 0.6, 0.7, 0.8, 0.9, 1.0], "fix iteration", "audit-coverage summary", fmtx="{}")
    d.line([(sx(x), sy(v)) for x, v in pts], fill=BLUE, width=6)
    for (x, v), r in zip(pts, h):
        d.ellipse([sx(x) - 14, sy(v) - 14, sx(x) + 14, sy(v) + 14], fill=BLUE)
        gc = r["gap_counts"]
        d.text((sx(x) - 40, sy(v) - 62), f"{v:.3f}", font=font(32, True), fill=INK)
        d.text((sx(x) - 60, sy(v) + 24), f"{gc['high']} high · {gc['medium']} med", font=font(26), fill=MUTED)
    im.save(OUT / "09_fix_loop_clone_mid.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    architecture()
    ticket(RUNS / "validation/v3/clone_mid", "gap-004", "A ticket: relabelled fare card (clone_mid)", "02_ticket_relabel_core_main.png",
           "An agent told to 'choose the Core fare' cannot find it on this clone.")
    moved_ticket(RUNS / "validation_heldout/v3/tpl_ho_move_find_trip", "gap-001", "03_ticket_moved_click_targets.png")
    heatmap(); report_top(); validation_table(); correlation(); f1_bars(); fixloop()
    for p in sorted(OUT.glob("*.png")):
        im = Image.open(p)
        print(f"{p.name:40s} {im.size}")
        assert im.width >= 1600, p


if __name__ == "__main__":
    main()
