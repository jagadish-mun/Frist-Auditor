"""End-to-end checks against live reference-app instances (~1 min).

    python -m pytest -q tests/test_integration.py
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "refapp"))
from serve import serve  # noqa: E402

from auditor.audit import load_config, run_audit  # noqa: E402


def audit(tmp_path, defects=()):
    cfg = load_config(str(ROOT / "configs" / "harbor.yaml"))
    with serve() as real, serve(defects) as clone:
        cfg["real_url"], cfg["clone_url"] = real, clone
        return run_audit(cfg, tmp_path, log=lambda *_: None)


def test_noise_baseline_real_vs_real(tmp_path):
    s, gaps = audit(tmp_path)
    assert s["overall"] > 0.97
    assert gaps == [], gaps


@pytest.mark.parametrize("defect,layer,keyword", [
    ("rename_continue", "flows", "continue"),
    ("broken_baggage_link", "behavior", "baggage info"),
    ("rename_fare_core", "elements", "core"),
])
def test_planted_defect_is_reported(tmp_path, defect, layer, keyword):
    s, gaps = audit(tmp_path, (defect,))
    assert s["overall"] < 1.0
    assert any(g["layer"] == layer and keyword in g["description"].lower() for g in gaps), gaps


def test_stalled_page_load_is_retried_and_counted():
    """Task 11: a load that stalls past the timeout (simulated by freezing the server, as machine sleep does)
    is retried once and counted instead of crashing the audit."""
    import os, signal, sys, threading
    sys.path.insert(0, "refapp")
    from playwright.sync_api import sync_playwright
    from serve import _listener_pid, serve
    from auditor import capture
    old = dict(capture.NAV)
    capture.NAV.update(timeout_ms=1500, retries=0)
    try:
        with serve() as url, sync_playwright() as pw:
            pid = _listener_pid(int(url.rsplit(":", 1)[1]))
            page = pw.chromium.launch().new_page()
            os.kill(pid, signal.SIGSTOP)
            threading.Timer(2.0, os.kill, (pid, signal.SIGCONT)).start()   # "wake" after the first attempt timed out
            capture.load(page, url + "/")
            assert capture.NAV["retries"] == 1 and "Harbor Air" in page.title()
    finally:
        capture.NAV.update(old)
