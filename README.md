# Clone Fidelity Auditor

Compares a cloned website with the real one and lists every difference as a ranked fix ticket, with screenshots from both sites. Built for Frist's clone-as-RL-environment workflow. Design: `SPEC.md` (§14 is the current status). Presentation: `docs/PRESENTATION_NOTES.md`, `docs/TALK_TRACK.md`, one-page summary `docs/SUMMARY.md`.

It checks four layers on every configured page and viewport:
- **visual:** screenshots, tolerant of small shifts;
- **elements:** links, buttons, fields and headings by role, name and position;
- **behaviour:** clicks, select options and dialog buttons on both sites;
- **flows:** scripted multi-step tasks, never completing a payment.

**How to read the output**
- **The tickets are the result.** Each high or medium ticket names an element or flow step. On the reference app, a ticket on an element a task uses predicts that task's failure for two scripted agents: held-out F1 0.91 (coordinate agent) and 1.00 (name-based agent). See `docs/TASK_PREDICTION.md`.
- **The 0–1 number is an audit-coverage summary:** a severity-weighted summary of how much the audit found. It is **not** a predictor of agent performance; on tasks independent of the audit's own flows it does not correlate with agent success (`docs/AGENT_CORRELATION.md`, `docs/CORRELATION_DIAGNOSIS.md`).

**Validation on the Harbor Air reference app** (macOS, `make validate`):
- Real site vs itself: 1.000, 0 tickets, three runs.
- Planted defects found: 14/14 (template), 4/4 (rebuilt clone), and **9/10 + 9/10 on held-out defects** written by a separate agent and frozen before any run.
- High/medium false alarms: 0, on the held-out set and on an independent first-draft clone.
- Known blind spot: a faint colour-only change is not reported.

## Setup

Needs Python 3.9+ and about 300 MB for Chromium.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

## Use

```bash
make demo         # ~25 s: generates a new site + clone with planted defects, audits, scores against the answer key (see Live demo)
make demo-status  # is a demo running? its URLs and report
make end-demo     # stop the demo's sites and delete the generated files (reports are kept)
make demo-classic # ~1 min: Harbor Air clone_mid, audit, one fix, re-audit, opens both reports (fallback)
make demo-gate    # ~15 min: 20-seed reliability check of make demo
make test         # 25 tests, ~1.5 min
make validate    # full validation: original (~23 min), held-out (~10 min), first-draft clone (~1 min)
```

Audit any pair of URLs:

```bash
.venv/bin/python refapp/app.py --port 8001 &                                            # real site
.venv/bin/python refapp/app.py --port 8002 --defects rename_fare_core,fare_rules_noop &  # a clone
.venv/bin/python -m auditor configs/harbor.yaml --real-url http://127.0.0.1:8001 --clone-url http://127.0.0.1:8002 --out runs/my_audit
open runs/my_audit/report.html      # also: runs/my_audit/gaps.json (tickets), summary.json (scores)
```

Add `--quick` for a ~4 s desktop-only check without behaviour exploration (for iteration; not comparable with full audits). Scoring version: `scoring: v3` (default), `v2` or `v1` in the config.

## Live demo

Each `make demo` run:

1. picks a random seed and prints it (`SEED=1234 make demo` replays that run exactly);
2. generates, into a temp directory, a small Flask site (airline, grocery store or bank, with an invented name) with random colours, nav labels, 5–7 pages, a form, dialogs, random prices and a clock, plus an audit config with 2–3 flows that stop before Pay / Place order / Transfer;
3. generates from the same seed a clone that matches it except for 4–6 planted defects, at least one each of: element (missing or relabelled), behaviour (wrong link or dead button), flow-breaking, and visual-only. The ground truth goes to `answer_key.json`;
4. starts both on free ports, audits the clone, and matches the tickets against the answer key with the same matcher as `validate.py`;
5. prints a scorecard (planted, found, missed, extra tickets) and opens the report from `runs/demo_live/<timestamp>_seed<N>/`, which also keeps the screenshots, `answer_key.json`, `audit.yaml` and `scorecard.json`;
6. **leaves both sites running** so you can click around them, and opens them next to the report:

   ```
   Real site:  http://localhost:8101
   Clone:      http://localhost:8102
   Report:     runs/demo_live/<folder>/report.html
   Run 'make end-demo' when finished.
   ```

   The servers are detached: closing the terminal does not stop them. If 8101 or 8102 is taken, free ports are used and printed. `make demo-status` shows what is running. `make end-demo` stops both, deletes the generated sites and removes the state file `runs/demo_live/.active_demo.json`; it is safe to run twice. Running `make demo` again ends the previous demo first.
7. If the run fails or you press Ctrl-C before it finishes, both servers are stopped and the temp directory deleted, as before. Reports are never deleted.

**Caveat:** the clone comes from the same generator as the real site, with defects planted as exact spec changes. It tests whether the auditor *detects* known differences on a site it has never seen. It does not test realistic clone noise (small rebuild drift, different markup); for that, see the rebuilt and first-draft clones in `docs/VALIDATION.md`. Use `NO_OPEN=1` for headless runs. `make demo-gate` checks 20 seeds plus the start/stop lifecycle (results in `runs/demo_gate/GATE.md`).

## Layout

- `auditor/`: the tool.
- `refapp/`: the reference site, its clones and the defect catalogs.
- `validate.py`: validation.
- `tools/`: experiments (agents, prediction, diagnosis, fix loop).
- `docs/`: results and decisions.
- `runs/`: generated output, gitignored.
