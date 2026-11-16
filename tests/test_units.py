"""Fast unit tests for the comparison primitives (no browser needed)."""
import numpy as np
from PIL import Image

from auditor.compare.elements import compare_elements
from auditor.compare.visual import compare_visual


def el(role, name, x, y, w=80, h=30, interactive=True):
    return {"role": role, "name": name, "norm": name.lower(), "box": [x, y, w, h],
            "interactive": interactive, "href": None, "idx": 0}


PAGE = (1440, 900)


def test_identical_inventory_scores_one():
    a = [el("button", "Search", 100, 100), el("link", "Book", 10, 10)]
    r = compare_elements(a, [dict(e) for e in a], PAGE)
    assert r["score"] == 1.0 and r["findings"] == []


def test_missing_and_extra():
    real = [el("button", "Search", 100, 100), el("link", "Manage trips", 300, 10)]
    clone = [el("button", "Search", 100, 100), el("button", "Chat with us", 1300, 850)]
    r = compare_elements(real, clone, PAGE)
    kinds = sorted(f["type"] for f in r["findings"])
    assert kinds == ["extra", "missing"]
    assert r["score"] == 1 / 3   # 1 match credit / (2 real + 1 extra)


def test_relabel_in_place_is_label_mismatch_not_missing():
    real = [el("heading", "Core", 500, 200, interactive=False)]
    clone = [el("heading", "Main", 500, 200, interactive=False)]
    r = compare_elements(real, clone, PAGE)
    assert [f["type"] for f in r["findings"]] == ["label"]


def test_role_mismatch_never_matches():
    r = compare_elements([el("button", "Go", 10, 10)], [el("link", "Go", 10, 10)], PAGE)
    assert sorted(f["type"] for f in r["findings"]) == ["extra", "missing"]


def test_duplicate_names_matched_by_position():
    real = [el("link", "Select fare", x, 400) for x in (100, 500, 900)]
    clone = [el("link", "Select fare", x, 400) for x in (100, 500, 900)]
    r = compare_elements(real, clone, PAGE)
    assert r["score"] == 1.0
    assert sorted((i, j) for i, j, _ in r["pairs"]) == [(0, 0), (1, 1), (2, 2)]


def test_moved_element_flagged():
    r = compare_elements([el("button", "Search", 100, 100)], [el("button", "Search", 100, 160)], PAGE)
    assert [f["type"] for f in r["findings"]] == ["moved"]


def _img(tmp_path, name, draw=None, size=(400, 300)):
    a = np.full((size[1], size[0], 3), 255, np.uint8)
    a[40:80, 40:200] = (11, 37, 69)
    if draw:
        draw(a)
    p = tmp_path / name
    Image.fromarray(a).save(p)
    return p


def test_visual_identical(tmp_path):
    p = _img(tmp_path, "a.png")
    v = compare_visual({"shot": p, "masks": []}, {"shot": p, "masks": []}, tmp_path, "t")
    assert v["score"] > 0.999 and v["regions"] == []


def test_visual_detects_colour_change(tmp_path):
    a = _img(tmp_path, "a.png")
    b = _img(tmp_path, "b.png", lambda x: x.__setitem__((slice(40, 80), slice(40, 200)), (232, 115, 12)))
    v = compare_visual({"shot": a, "masks": []}, {"shot": b, "masks": []}, tmp_path, "t")
    assert len(v["regions"]) == 1
    x, y, w, h = v["regions"][0]["box"]
    assert x <= 40 and y <= 40 and x + w >= 200 and y + h >= 80


def test_visual_mask_hides_dynamic_region(tmp_path):
    a = _img(tmp_path, "a.png", lambda x: x.__setitem__((slice(200, 220), slice(50, 120)), 0))
    b = _img(tmp_path, "b.png", lambda x: x.__setitem__((slice(200, 220), slice(60, 140)), 0))
    m = [[45, 195, 100, 30]]
    v = compare_visual({"shot": a, "masks": m}, {"shot": b, "masks": m}, tmp_path, "t")
    assert v["regions"] == [] and v["score"] > 0.999


# ---- scoring v2 (alignment-tolerant visual, worst-page aggregation, severity penalty) ----

def _block(y, x):
    return lambda a: a.__setitem__((slice(y, y + 30), slice(x, x + 120)), (20, 40, 90))


def test_visual_v2_tolerates_small_shift(tmp_path):
    a = _img(tmp_path, "a.png", _block(100, 100))
    b = _img(tmp_path, "b.png", _block(102, 98))     # 2px down, 2px left
    v1 = compare_visual({"shot": a, "masks": []}, {"shot": b, "masks": []}, tmp_path, "t1", scoring="v1")
    v2 = compare_visual({"shot": a, "masks": []}, {"shot": b, "masks": []}, tmp_path, "t2", scoring="v2")
    assert v1["regions"] and v2["regions"] == [] and v2["score"] > 0.999


def test_visual_v2_still_flags_large_shift_and_colour(tmp_path):
    a = _img(tmp_path, "a.png", _block(100, 100))
    moved = _img(tmp_path, "m.png", _block(110, 100))  # 10px > SHIFT
    recol = _img(tmp_path, "c.png", lambda x: x.__setitem__((slice(100, 130), slice(100, 220)), (232, 115, 12)))
    for b in (moved, recol):
        v = compare_visual({"shot": a, "masks": []}, {"shot": b, "masks": []}, tmp_path, "t", scoring="v2")
        assert v["regions"] and v["score"] < 1.0


def test_aggregate_v1_mean_v2_worst_page():
    from auditor.audit import aggregate
    s = [1.0] * 6 + [0.86]
    assert abs(aggregate(s, "v1") - 0.98) < 1e-9
    assert abs(aggregate(s, "v2") - (0.5 * 0.98 + 0.5 * 0.86)) < 1e-9


def test_severity_penalty():
    from auditor.audit import penalised
    gaps = [{"severity": "high"}, {"severity": "medium"}, {"severity": "low"}]
    assert penalised(0.9, gaps, "v1") == 0.9
    assert abs(penalised(0.9, gaps, "v2") - 0.9 * 0.95 * 0.98) < 1e-12
    assert penalised(0.9, [{"severity": "low"}] * 50, "v2") == 0.9   # cosmetic gaps cost nothing extra


def test_v3_move_threshold_is_20px():
    from auditor.compare.elements import compare_elements
    real = [el("button", "Search", 100, 100)]
    clone = [el("button", "Search", 100, 122)]          # 22px down
    assert compare_elements(real, clone, PAGE)["findings"] == []                       # v1/v2: 24px threshold
    f = compare_elements(real, clone, PAGE, move_px=20)["findings"]
    assert len(f) == 1 and f[0]["type"] == "moved" and f[0]["px"] == 22


def test_behavior_describe_new_outcomes():
    from auditor.compare.behavior import describe, diff_outcomes
    base = {"path": "/", "navigated": False, "status": 200, "dialog": None, "h1": "x", "changed": None}
    assert describe({"error": "option missing"}) == "cannot be used (option missing)"
    assert describe({**base, "changed": True}) == "changes the page content"
    assert describe({**base, "dialog": "fare rules", "in_dialog": True}) == "leaves dialog 'fare rules' open"
    assert diff_outcomes({**base, "changed": True}, {**base, "changed": False})


def test_serve_rejects_foreign_listener():
    """Port race (Task 11): if another server already owns the port, serve() must not hand out its URL."""
    import http.server, sys, threading
    import pytest
    sys.path.insert(0, "refapp")
    from serve import serve
    srv = http.server.HTTPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with pytest.raises(RuntimeError):
            with serve(port=srv.server_port):
                pass
    finally:
        srv.shutdown()


def _mv(name, x, y, dx, dy):
    return {"type": "moved", "px": round((dx * dx + dy * dy) ** 0.5),
            "real": el("link", name, x, y), "clone": el("link", name, x + dx, y + dy)}


def test_group_moves_by_common_offset():
    from auditor.audit import group_moves
    g = group_moves([_mv("About us", 30, 600, 0, 60), _mv("Help centre", 110, 600, 1, 61),
                     _mv("Find trip", 224, 213, 0, -48)])
    assert sorted(len(x) for x in g) == [1, 2]


def test_grouped_ticket_keeps_the_score():
    from auditor.audit import penalised
    assert abs(penalised(0.9, [{"severity": "medium", "weight": 3}], "v3") - penalised(0.9, [{"severity": "medium"}] * 3, "v3")) < 1e-12


def test_a11y_name_only():
    from auditor.audit import a11y_name_only
    o = {"path": "/fares", "status": 200, "navigated": False, "changed": None, "dialog": "fare rules"}
    assert a11y_name_only(o, {**o, "dialog": "fare rules changes allowed on core and"})
    assert not a11y_name_only(o, {**o, "dialog": None})                     # dialog missing: a real behaviour gap
    assert not a11y_name_only(o, {**o, "dialog": "baggage"})


def test_site_generator_is_deterministic_and_plants_every_category(tmp_path):
    """Task 21: same seed → same sites; 5-7 pages; 4-6 defects with one per category; flows stop before the final action."""
    import json
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "gen"))
    import yaml
    from site_gen import generate
    for seed in range(12):
        a, b = generate(seed, tmp_path / f"a{seed}"), generate(seed, tmp_path / f"b{seed}")
        assert a == b
        assert (tmp_path / f"a{seed}/clone/site.json").read_text() == (tmp_path / f"b{seed}/clone/site.json").read_text()
        assert 5 <= len(a["pages"]) <= 7 and 4 <= len(a["defects"]) <= 6
        assert {d["category"] for d in a["defects"]} == {"element", "behaviour", "flow", "visual"}
        real = json.loads((tmp_path / f"a{seed}/real/site.json").read_text())
        cfg = yaml.safe_load((tmp_path / f"a{seed}/audit.yaml").read_text())
        assert 2 <= len(cfg["flows"]) <= 3
        buy = cfg["flows"][0]["steps"]
        assert buy[-1] == {"stop_before": real["final_label"]}
        assert not any(s.get("click", {}).get("name") == real["final_label"] for f in cfg["flows"] for s in f["steps"])
