"""CLI:  python -m auditor configs/harbor.yaml --out runs/my_audit [--clone-url URL]"""
import argparse

from .audit import load_config, run_audit

ap = argparse.ArgumentParser(description="Clone Fidelity Auditor")
ap.add_argument("config")
ap.add_argument("--out", default="runs/latest")
ap.add_argument("--real-url")
ap.add_argument("--clone-url")
ap.add_argument("--quick", action="store_true", help="desktop viewport only, no behaviour exploration (fast iteration)")
a = ap.parse_args()
cfg = load_config(a.config)
if a.real_url: cfg["real_url"] = a.real_url
if a.clone_url: cfg["clone_url"] = a.clone_url
cfg["quick"] = a.quick
run_audit(cfg, a.out)
