"""Layer 1 — visual comparison: masked SSIM + pixel diff, region extraction, heatmap."""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.metrics import structural_similarity

MASK_COLOR = (255, 0, 255)
PIXEL_THRESH = 48        # max per-channel difference counted as "changed"
SSIM_THRESH = 0.6        # local SSIM below this counts as "changed"
MIN_REGION_AREA = 120    # ignore specks smaller than this many pixels
SHIFT = 3                # v2: per-region rigid shift search radius (px)


def _load_masked(path, masks, width, height):
    img = Image.open(path).convert("RGB")
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    canvas.paste(img, (0, 0))
    a = np.array(canvas)
    for x, y, w, h in masks:
        a[max(0, y):max(0, y + h), max(0, x):max(0, x + w)] = MASK_COLOR
    return a


def compare_visual(real, clone, out_dir: Path, slug, scoring="v2"):
    """real/clone: {"shot", "masks"}. Returns dict with score, regions, heatmap path.

    v1: masked SSIM + per-pixel diff, pixel-strict.
    v2: same candidate regions, but each region is re-compared under the best rigid shift within
        ±SHIFT px; only pixels that still differ count. Score = 1 - min(1, 4 * residual fraction).
    """
    ri, ci = Image.open(real["shot"]), Image.open(clone["shot"])
    W, H = max(ri.width, ci.width), max(ri.height, ci.height)
    # Mask the union of both sites' dynamic regions in both images so that
    # e.g. a masked price on one side never registers as a diff on the other.
    masks = real["masks"] + clone["masks"]
    a = _load_masked(real["shot"], masks, W, H)
    b = _load_masked(clone["shot"], masks, W, H)

    ga, gb = a.mean(axis=2), b.mean(axis=2)
    ssim_mean, ssim_map = structural_similarity(ga, gb, data_range=255, full=True)
    pix = np.abs(a.astype(int) - b.astype(int)).max(axis=2) > PIXEL_THRESH
    changed = pix | (ssim_map < SSIM_THRESH)
    changed = ndimage.binary_opening(changed, iterations=1)
    grown = ndimage.binary_dilation(changed, iterations=6)

    labels, n = ndimage.label(grown)
    if scoring != "v1":   # v2 and v3
        return _tolerant(a, b, masks, labels, ri, ci, out_dir, slug)
    regions = []
    for i, sl in enumerate(ndimage.find_objects(labels), start=1):
        if sl is None:
            continue
        area = int((changed[sl] & (labels[sl] == i)).sum())
        if area < MIN_REGION_AREA:
            continue
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        regions.append({"box": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)], "changed_px": area})
    regions.sort(key=lambda r: -r["changed_px"])

    changed_frac = float(changed.mean())
    # Score: blend of structural similarity and the share of unchanged pixels.
    # A height mismatch (content added/removed) is penalised via the padding.
    score = float(0.5 * ssim_mean + 0.5 * (1.0 - min(1.0, changed_frac * 4)))

    heat = _heatmap(a, changed, out_dir / f"heat_{slug}.png")
    return {"score": score, "ssim": float(ssim_mean), "changed_frac": changed_frac,
            "regions": regions, "heatmap": heat, "size": (W, H),
            "height_delta": ci.height - ri.height}


def _tolerant(a, b, masks, labels, ri, ci, out_dir, slug):
    H, W = labels.shape
    masked = np.zeros((H, W), bool)
    for x, y, w, h in masks:
        masked[max(0, y):max(0, y + h), max(0, x):max(0, x + w)] = True
    pad = SHIFT
    bp = np.pad(b.astype(int), ((pad, pad), (pad, pad), (0, 0)), constant_values=255)
    mp = np.pad(masked, pad, constant_values=True)
    ai = a.astype(int)
    residual = np.zeros((H, W), bool)
    regions = []
    for i, sl in enumerate(ndimage.find_objects(labels), start=1):
        if sl is None:
            continue
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        ra, ma = ai[y0:y1, x0:x1], masked[y0:y1, x0:x1]
        best = None
        for dy in range(-SHIFT, SHIFT + 1):
            for dx in range(-SHIFT, SHIFT + 1):
                rb = bp[y0 + pad + dy:y1 + pad + dy, x0 + pad + dx:x1 + pad + dx]
                ign = ma | mp[y0 + pad + dy:y1 + pad + dy, x0 + pad + dx:x1 + pad + dx]
                diff = (np.abs(ra - rb).max(axis=2) > PIXEL_THRESH) & ~ign
                n = int(diff.sum())
                if best is None or n < best[0] or (n == best[0] and abs(dx) + abs(dy) < abs(best[1]) + abs(best[2])):
                    best = (n, dx, dy, diff)
                if n == 0:
                    break
            if best[0] == 0:
                break
        diff = ndimage.binary_opening(best[3], iterations=1)
        area = int(diff.sum())
        if area < MIN_REGION_AREA:
            continue
        residual[y0:y1, x0:x1] |= diff
        regions.append({"box": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)], "changed_px": area,
                        "shift": [best[1], best[2]]})
    regions.sort(key=lambda r: -r["changed_px"])
    frac = float(residual.mean())
    heat = _heatmap(a, residual, out_dir / f"heat_{slug}.png")
    return {"score": float(1.0 - min(1.0, frac * 4)), "ssim": None, "changed_frac": frac,
            "regions": regions, "heatmap": heat, "size": (W, H), "height_delta": ci.height - ri.height}


def _heatmap(base, changed, path):
    over = base.copy().astype(float)
    red = np.zeros_like(over); red[..., 0] = 255
    m = changed[..., None]
    over = np.where(m, over * 0.35 + red * 0.65, over * 0.85 + 255 * 0.15)
    Image.fromarray(over.astype(np.uint8)).save(path)
    return path


def crop_pair(real_shot, clone_shot, box, out_real, out_clone, pad=40):
    x, y, w, h = box
    for src, dst in ((real_shot, out_real), (clone_shot, out_clone)):
        im = Image.open(src).convert("RGB")
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(im.width, x + w + pad), min(im.height, y + h + pad)
        if x1 <= x0 or y1 <= y0:  # region lies outside this (shorter) image
            Image.new("RGB", (max(1, w), max(1, h)), (240, 240, 240)).save(dst)
        else:
            im.crop((x0, y0, x1, y1)).save(dst)
