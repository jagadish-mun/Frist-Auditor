"""Capture layer: screenshots, element inventory and mask rectangles via Playwright."""
import re
from pathlib import Path

# Disable animation / caret blink so screenshots are deterministic.
STABILIZE_CSS = """
*, *::before, *::after { animation: none !important; transition: none !important; caret-color: transparent !important; }
"""

# Extract visible elements with a role, accessible name and bounding box.
EXTRACT_JS = r"""
() => {
  const SEL = 'a[href], button, input:not([type=hidden]), select, textarea, [role=button], [role=link], h1, h2, h3';
  const vis = el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none') return false;
    const d = el.closest('dialog'); if (d && !d.open) return false;
    return true;
  };
  const clean = t => (t || '').replace(/\s+/g, ' ').trim();
  const role = el => {
    const r = el.getAttribute('role'); if (r) return r;
    const t = el.tagName.toLowerCase();
    if (t === 'a') return 'link';
    if (t === 'button') return 'button';
    if (t === 'select') return 'combobox';
    if (t === 'textarea') return 'textbox';
    if (/^h[1-6]$/.test(t)) return 'heading';
    if (t === 'input') {
      const ty = (el.type || 'text').toLowerCase();
      if (['submit', 'button', 'reset'].includes(ty)) return 'button';
      if (ty === 'checkbox') return 'checkbox';
      if (ty === 'radio') return 'radio';
      return 'textbox';
    }
    return t;
  };
  const name = el => {
    if (el.getAttribute('aria-label')) return clean(el.getAttribute('aria-label'));
    const lb = el.getAttribute('aria-labelledby');
    if (lb) { const n = document.getElementById(lb); if (n) return clean(n.textContent); }
    if (el.id) { const l = document.querySelector(`label[for="${el.id}"]`); if (l) return clean(l.textContent); }
    const pl = el.closest('label'); if (pl) return clean(pl.textContent);
    if (['INPUT', 'TEXTAREA'].includes(el.tagName)) return clean(el.placeholder || el.value || el.name);
    return clean(el.innerText || el.textContent);
  };
  const out = [];
  document.querySelectorAll(SEL).forEach(el => {
    if (!vis(el)) return;
    const r = el.getBoundingClientRect();
    const rl = role(el);
    let href = null;
    if (el.tagName === 'A') { try { const u = new URL(el.href); href = u.pathname + u.search; } catch (e) {} }
    out.push({
      idx: out.length, role: rl, name: name(el), tag: el.tagName.toLowerCase(),
      interactive: rl !== 'heading',
      submit: (el.tagName === 'BUTTON' && (el.type || 'submit') === 'submit' && !!el.form),
      href,
      box: [Math.round(r.left + scrollX), Math.round(r.top + scrollY), Math.round(r.width), Math.round(r.height)],
    });
    el.setAttribute('data-fa-idx', String(out.length - 1));
  });
  return out;
}
"""

# Rectangles to mask: elements matching selectors, and the parent element of any
# text node whose text matches one of the regexes.
MASK_JS = r"""
([selectors, regexes]) => {
  const rects = [];
  const add = el => { const r = el.getBoundingClientRect(); if (r.width && r.height)
      rects.push([Math.floor(r.left + scrollX) - 3, Math.floor(r.top + scrollY) - 3, Math.ceil(r.width) + 6, Math.ceil(r.height) + 6]); };
  selectors.forEach(s => document.querySelectorAll(s).forEach(add));
  const res = regexes.map(r => new RegExp(r));
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    if (res.some(r => r.test(n.textContent)) && n.parentElement) add(n.parentElement);
  }
  return rects;
}
"""


def new_context(browser, viewport):
    ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]},
                              reduced_motion="reduce", device_scale_factor=1)
    ctx.add_init_script(f"document.addEventListener('DOMContentLoaded',()=>{{const s=document.createElement('style');s.textContent={STABILIZE_CSS!r};document.head.appendChild(s);}});")
    return ctx


WAIT = {"mode": "networkidle"}   # set from config: "networkidle" (safe default) or "load" (faster)


# Navigation stalls were seen in long runs (machine sleep or a network change aborts in-flight loads, even to
# 127.0.0.1). One stalled load must not kill a whole audit: retry once, and count it so reports can show it.
NAV = {"timeout_ms": 30000, "retries": 0}


def goto(page, url):
    for attempt in (1, 2):
        try:
            return page.goto(url, wait_until="load", timeout=NAV["timeout_ms"])
        except Exception as e:  # noqa: BLE001
            transient = "Timeout" in type(e).__name__ or "ERR_NETWORK_CHANGED" in str(e) or "ERR_ABORTED" in str(e)
            if attempt == 2 or not transient:
                raise
            NAV["retries"] += 1


def load(page, url):
    goto(page, url)
    if WAIT["mode"] == "networkidle":
        page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts && document.fonts.ready")


def extract_elements(page, regexes):
    els = page.evaluate(EXTRACT_JS)
    for e in els:
        e["norm"] = normalize(e["name"], regexes)
    return els


def normalize(text, regexes):
    t = text or ""
    for r in regexes:
        t = re.sub(r, "§", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def capture_site(browser, base_url, pages, viewports, mask_cfg, outdir: Path, tag: str):
    """Returns {(page, vw, vh): {"shot": path, "elements": [...], "masks": [...], "size": (w,h)}}."""
    sels = [m["selector"] for m in mask_cfg if "selector" in m]
    regs = [m["regex"] for m in mask_cfg if "regex" in m]
    outdir.mkdir(parents=True, exist_ok=True)
    data = {}
    for vw, vh in viewports:
        ctx = new_context(browser, (vw, vh))
        page = ctx.new_page()
        for p in pages:
            load(page, base_url + p)
            slug = slugify(p)
            shot = outdir / f"{tag}_{slug}_{vw}x{vh}.png"
            page.screenshot(path=str(shot), full_page=True)
            data[(p, vw, vh)] = {
                "shot": shot,
                "elements": extract_elements(page, regs),
                "masks": page.evaluate(MASK_JS, [sels, regs]),
            }
        ctx.close()
    return data


def slugify(p):
    s = re.sub(r"[^a-zA-Z0-9]+", "_", p).strip("_")
    return s or "home"
