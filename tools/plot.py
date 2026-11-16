"""Minimal PNG charts with Pillow (no matplotlib dependency; DECISIONS D11)."""
from PIL import Image, ImageDraw, ImageFont

W, H, M = 560, 420, 60          # panel size and margin
COLORS = [(31, 105, 164), (230, 120, 20), (60, 150, 60), (150, 60, 160)]


def _font(size):
    for f in ("/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _panel(d, ox, title, xlabel, ylabel, xr, yr, series, kind):
    f, fs = _font(15), _font(12)
    x0, y0, x1, y1 = ox + M, M, ox + W - 20, H - M
    sx = lambda v: x0 + (v - xr[0]) / (xr[1] - xr[0]) * (x1 - x0)
    sy = lambda v: y1 - (v - yr[0]) / (yr[1] - yr[0]) * (y1 - y0)
    d.rectangle([x0, y0, x1, y1], outline=(120, 120, 120))
    xticks = range(int(xr[0]), int(xr[1]) + 1) if kind == "line" else [xr[0] + i * (xr[1] - xr[0]) / 5 for i in range(6)]
    for xv in xticks:
        d.line([sx(xv), y1, sx(xv), y1 + 4], fill=(120, 120, 120))
        d.text((sx(xv) - 12, y1 + 8), f"{xv}" if kind == "line" else f"{xv:.2f}", font=fs, fill=(60, 60, 60))
    for i in range(6):
        yv = yr[0] + i * (yr[1] - yr[0]) / 5
        d.line([x0 - 4, sy(yv), x0, sy(yv)], fill=(120, 120, 120)); d.text((x0 - 40, sy(yv) - 7), f"{yv:.2f}", font=fs, fill=(60, 60, 60))
        d.line([x0, sy(yv), x1, sy(yv)], fill=(235, 235, 235))
    d.text((ox + M, 18), title, font=f, fill=(20, 20, 20))
    d.text(((x0 + x1) / 2 - 40, H - 28), xlabel, font=fs, fill=(40, 40, 40))
    d.text((ox + 6, y0 - 22), ylabel, font=fs, fill=(40, 40, 40))
    for k, (label, pts) in enumerate(series):
        c = COLORS[k % len(COLORS)]
        if kind == "line":
            d.line([(sx(x), sy(y)) for x, y in pts], fill=c, width=2)
        for x, y in pts:
            r = 4
            if k % 2:
                d.rectangle([sx(x) - r, sy(y) - r, sx(x) + r, sy(y) + r], outline=c, width=2)
            else:
                d.ellipse([sx(x) - r, sy(y) - r, sx(x) + r, sy(y) + r], outline=c, width=2)
        d.text((x0 + 10, y0 + 8 + 18 * k), ("● " if k % 2 == 0 else "■ ") + label, font=fs, fill=c)


def chart(path, panels, kind="scatter"):
    """panels: list of dicts {title, xlabel, ylabel, xr, yr, series: [(label, [(x, y), ...]), ...]}."""
    img = Image.new("RGB", (W * len(panels), H), "white")
    d = ImageDraw.Draw(img)
    for i, p in enumerate(panels):
        _panel(d, i * W, p["title"], p["xlabel"], p["ylabel"], p["xr"], p["yr"], p["series"], kind)
    img.save(path)
    return path
