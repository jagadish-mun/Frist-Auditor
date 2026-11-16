"""Record what a *user* can observe of a site, as source material for a screenshot-based rebuild.

    python tools/observe.py --url http://127.0.0.1:8001 --out runs/observe

Per page and viewport: a full-page screenshot, visible text blocks with their boxes, and the
interactive elements (role, visible name, link target, placeholder, select options, required).
It also replays the audit flows and records the URL / heading reached after each step and a
screenshot of every state (this is what a user learns by clicking around). It does not read
page source, CSS or server code.
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from auditor.audit import load_config  # noqa: E402
from auditor.capture import EXTRACT_JS, new_context  # noqa: E402

TEXT_JS = r"""
() => {
  const out = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const t = n.textContent.replace(/\s+/g, ' ').trim();
    if (!t) continue;
    const el = n.parentElement; const r = document.createRange(); r.selectNodeContents(n);
    const b = r.getBoundingClientRect();
    if (!b.width || !b.height) continue;
    const d = el.closest('dialog'); if (d && !d.open) continue;
    out.push({text: t, box: [Math.round(b.left + scrollX), Math.round(b.top + scrollY), Math.round(b.width), Math.round(b.height)]});
  }
  return out;
}
"""

FIELDS_JS = r"""
() => [...document.querySelectorAll('input:not([type=hidden]), select, textarea')].map(el => ({
  label: (el.labels && el.labels[0] ? el.labels[0].innerText.trim() : null),
  type: el.type, placeholder: el.placeholder || null, required: el.required, value: el.value || null,
  options: el.tagName === 'SELECT' ? [...el.options].map(o => o.text) : null,
}))
"""


def snapshot(page, tag, out):
    page.screenshot(path=str(out / f"{tag}.png"), full_page=True)
    data = {"url": page.url, "title": page.title(), "texts": page.evaluate(TEXT_JS),
            "elements": page.evaluate(EXTRACT_JS), "fields": page.evaluate(FIELDS_JS)}
    (out / f"{tag}.json").write_text(json.dumps(data, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", default="runs/observe")
    ap.add_argument("--config", default=str(ROOT / "configs" / "harbor.yaml"))
    a = ap.parse_args()
    cfg = load_config(a.config)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for vp in cfg["viewports"]:
            ctx = new_context(br, vp)
            page = ctx.new_page()
            for p in cfg["pages"]:
                page.goto(a.url + p, wait_until="load")
                slug = (p.strip("/").split("?")[0].replace("/", "_") or "home")
                snapshot(page, f"{slug}_{vp[0]}", out)
            ctx.close()
        # Flows, desktop only: the URL/heading/dialog after each step.
        ctx = new_context(br, cfg["viewports"][0])
        for f in cfg["flows"]:
            page = ctx.new_page()
            page.goto(a.url + f.get("start", "/"), wait_until="load")
            log = []
            for k, st in enumerate(f["steps"]):
                (kind, arg), = st.items()
                if kind == "fill":
                    page.get_by_label(arg["label"], exact=True).first.fill(str(arg["value"]))
                elif kind == "click":
                    loc = page.get_by_role(arg.get("role", "button"), name=arg["name"], exact=True)
                    loc.nth(arg.get("nth", 0)).click(); page.wait_for_load_state("load")
                page.wait_for_timeout(150)
                snapshot(page, f"flow_{f['name']}_{k + 1}", out)
                log.append({"step": st, "url": page.url,
                            "h1": page.evaluate("document.querySelector('h1')?.innerText"),
                            "dialog": page.evaluate("[...document.querySelectorAll('dialog[open],[role=dialog]')]"
                                                    ".map(d=>d.innerText.slice(0,300))")})
            (out / f"flow_{f['name']}.json").write_text(json.dumps(log, indent=1))
            page.close()
        br.close()


if __name__ == "__main__":
    main()
