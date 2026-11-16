"""Layer 2 — element inventory comparison via Hungarian assignment.

Cost of pairing a real element r with a clone element c:
    role mismatch           -> forbidden (BIG)
    0.65 * name distance    (1 - normalized Levenshtein similarity)
    0.35 * position distance (centre distance / page diagonal, x4, capped at 1)
Pairs with cost above MATCH_MAX are rejected. Leftover real/clone elements of the
same role that sit in nearly the same place are then paired as *label
mismatches* (e.g. 'Core' -> 'Main'); everything else is missing / extra.
"""
import math

import numpy as np
from rapidfuzz.distance import Levenshtein
from scipy.optimize import linear_sum_assignment

BIG = 1e6
MATCH_MAX = 0.30
RELABEL_POS_MAX = 0.06   # position distance under which leftovers pair as a relabel
MOVE_PX = 24             # matched element moved more than this -> "moved" (v1/v2)
MOVE_PX_V3 = 20          # v3: interactive elements moved more than this are agent-relevant click-target moves


def _center(e):
    x, y, w, h = e["box"]
    return x + w / 2, y + h / 2


def _pos_dist(a, b, diag):
    (ax, ay), (bx, by) = _center(a), _center(b)
    return min(1.0, 4 * math.hypot(ax - bx, ay - by) / diag)


def _name_dist(a, b):
    return 1.0 - Levenshtein.normalized_similarity(a["norm"], b["norm"])


def match_elements(real, clone, page_size):
    diag = math.hypot(*page_size)
    n, m = len(real), len(clone)
    pairs, relabels = [], []
    if n and m:
        C = np.full((n, m), BIG)
        for i, r in enumerate(real):
            for j, c in enumerate(clone):
                if r["role"] != c["role"]:
                    continue
                C[i, j] = 0.65 * _name_dist(r, c) + 0.35 * _pos_dist(r, c, diag)
        rows, cols = linear_sum_assignment(C)
        for i, j in zip(rows, cols):
            if C[i, j] <= MATCH_MAX:
                pairs.append((i, j, float(C[i, j])))
    used_r = {i for i, _, _ in pairs}
    used_c = {j for _, j, _ in pairs}
    # Second pass: same role, near-identical position, different label.
    left_r = [i for i in range(n) if i not in used_r]
    left_c = [j for j in range(m) if j not in used_c]
    cand = sorted(((
        _pos_dist(real[i], clone[j], diag), i, j) for i in left_r for j in left_c
        if real[i]["role"] == clone[j]["role"] and _pos_dist(real[i], clone[j], diag) <= RELABEL_POS_MAX))
    for _, i, j in cand:
        if i in used_r or j in used_c:
            continue
        relabels.append((i, j))
        used_r.add(i); used_c.add(j)
    missing = [i for i in range(n) if i not in used_r]
    extra = [j for j in range(m) if j not in used_c]
    return pairs, relabels, missing, extra


def compare_elements(real, clone, page_size, move_px=MOVE_PX):
    pairs, relabels, missing, extra = match_elements(real, clone, page_size)
    findings, credit = [], 0.0
    for i, j, cost in pairs:
        r, c = real[i], clone[j]
        (rx, ry), (cx, cy) = _center(r), _center(c)
        moved = math.hypot(rx - cx, ry - cy)
        if r["norm"] != c["norm"]:
            findings.append({"type": "label", "real": r, "clone": c})
            credit += 0.5
        elif moved > move_px:
            findings.append({"type": "moved", "real": r, "clone": c, "px": round(moved)})
            credit += 0.9
        else:
            credit += 1.0
    for i, j in relabels:
        findings.append({"type": "label", "real": real[i], "clone": clone[j]})
        credit += 0.5
    for i in missing:
        findings.append({"type": "missing", "real": real[i]})
    for j in extra:
        findings.append({"type": "extra", "clone": clone[j]})
    denom = len(real) + len(extra)
    score = 1.0 if denom == 0 else credit / denom
    return {"score": score, "findings": findings, "pairs": pairs + [(i, j, None) for i, j in relabels]}
