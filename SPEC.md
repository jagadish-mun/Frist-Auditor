# Clone Fidelity Auditor: Spec

> **Status (2026-11-12):** core tool built and validated against a self-hosted reference app. All four layers, scoring, gap tickets, HTML report and §9 tests 1–2 work. Stretch goals (agent correlation, fix-and-re-audit loop) not started. See §14 for what was built, results and open issues.

## 1. Summary

A tool that compares a **real website** with a **cloned copy** of it and reports how faithful the copy is. AI agents train on these clones, and gaps between clone and real site hurt how well they perform on the real thing.

**Input:** a real site URL, a clone URL, and a few scripted user flows.
**Output:** a fidelity score (0–1) and a ranked list of differences written as fix tickets.

## 2. Problem

- Companies like Frist build pixel-perfect clones of real apps (airline, retail, NetSuite, Bill.com) as RL environments for computer-use agents.
- Higher-fidelity clones train better agents. In Frist's JetBlue experiment, the most faithful clone gave 4x improvement on the live site, versus 2x for a low-fidelity one.
- Today, checking fidelity is manual: experts compare each clone against the live site by hand. This doesn't scale.

## 3. Goals

- Score how closely a clone matches its real site, automatically, in minutes.
- Produce an actionable, ranked list of gaps.
- Show that the score tracks real defects (planted-defect test).
- Stretch: show the score predicts agent performance on the real site.
- Stretch: feed gaps to a coding agent and re-audit in a loop.

## 4. Non-goals

- Building clones by hand.
- Completing real transactions (flows always stop before payment).
- Large-scale crawling of live sites.

## 5. What it compares

| Layer | Question | Method |
|---|---|---|
| 1. Visual | Does it look the same? | Screenshots at fixed viewports, dynamic regions masked, SSIM / pixel diff per region, heatmap |
| 2. Elements | Are the same buttons, fields and labels there? | Accessibility tree + interactive elements via Playwright; match by role, label and position; report missing, extra and mismatched elements |
| 3. Behavior | Do the buttons do the same thing? | Click each interactive element, record the resulting state (navigation, modal, field change); compare state maps |
| 4. Flows | Can you finish the same task on both? | Replay scripted flows step by step on both sites; report the first step where they diverge |

## 6. Output

### Score
- Overall fidelity score from 0 (nothing alike) to 1 (identical).
- Sub-scores per layer and per page.
- Weighted combination. Starting weights: Visual 0.15, Elements 0.30, Behavior 0.25, Flows 0.30 (to be calibrated, see §9).

### Gap list
Each gap is a ticket:

```json
{
  "id": "gap-007",
  "severity": "high",
  "layer": "elements",
  "page": "/booking/fares",
  "description": "Fare card label reads 'Main' on clone, 'Core' on real site",
  "real_screenshot": "shots/real/fares_007.png",
  "clone_screenshot": "shots/clone/fares_007.png"
}
```

Severity rules:
- **High:** breaks a flow, or an interactive element is missing.
- **Medium:** label or behavior mismatch.
- **Low:** visual-only difference.

### Report
A static HTML page with the overall score, per-page breakdown, heatmaps, side-by-side screenshots and the gap list.

## 7. Inputs and config

Implemented in `configs/harbor.yaml`. Keys added beyond the original draft: `pages` (URLs to capture, with query strings), `wait` (`load` or `networkidle`), `max_clicks_per_page`, `skip_actions` (regex of destructive button names), `weights`, a per-flow `start` path, and step types `goto`, `select`, `expect_dialog`, plus `nth` on `click`.

```yaml
real_url: http://localhost:8001
clone_url: http://localhost:8002
viewports: [[1440, 900], [390, 844]]
mask:
  - selector: ".price"
  - regex: "\\$\\d+(\\.\\d{2})?"
  - regex: "\\b\\w{3} \\d{1,2}, \\d{4}\\b"
flows:
  - name: book_flight
    steps:
      - fill: { label: "From", value: "DCA" }
      - fill: { label: "To", value: "SJU" }
      - click: { role: button, name: "Search" }
      - click: { role: button, name: "Select fare" }
      - stop_before: "Pay"
```

## 8. Architecture

```
config.yaml
   │
   ▼
capture/   Playwright: screenshots, accessibility tree, element list (both sites)
   │
   ▼
compare/
   visual.py     SSIM + pixel diff with masks
   elements.py   element matching (role + label + position, Hungarian assignment)
   behavior.py   click-and-record state exploration
   flows.py      step-by-step flow replay
   │
   ▼
score.py   layer + page scores, weighted total
   │
   ▼
report/    gaps.json + report.html
```

**Stack:** Python, Playwright, scikit-image, pixelmatch, rapidfuzz, scipy, Jinja2 for the report.

## 9. Validation

1. **Planted-defect test.** Start from a good clone and introduce known defects: remove a component, rename labels, break a link, shift the layout. Pass criteria:
   - The score drops as more defects are added.
   - At least 80% of planted defects appear in the gap list.
   - False alarms are reported.
2. **Noise baseline.** Audit the real site against itself 3 times. The score should stay above 0.97.
3. **Agent correlation (stretch).** Build clones at 3 fidelity levels, run the same agent tasks on each and on the real app, and check whether the fidelity score predicts the drop in success on the real app.

## 10. Setup to avoid live-site problems

- Use an open-source app you host yourself as the "real site", and generate the clone from its screenshots with a coding agent. This avoids bot detection and terms-of-service issues and allows unlimited reruns.
- Optionally request a real clone from Frist (research@frist.ai).

## 11. Risks

| Risk | Mitigation |
|---|---|
| Dynamic content creates false diffs | Masks, text normalization, repeated runs |
| Element matching errors | Cost threshold; manual spot-check on demo pages |
| Weights are arbitrary | Calibrate with the planted-defect test |
| Behavior exploration blows up | Cap clicks per page; skip destructive actions |

## 12. Milestones (24 hours)

| Hours | Deliverable |
|---|---|
| 0–3 | Real app hosted, clones ready, 2–3 flows written |
| 3–8 | Capture + visual and element comparison |
| 8–13 | Behavior exploration + flow replay |
| 13–17 | Scoring, gap tickets, HTML report |
| 17–21 | Planted-defect validation (+ agent correlation if time allows) |
| 21–24 | Demo polish |

## 13. Demo

Measured numbers (2026-11-13, macOS, default scoring v3): three clones scored **0.972, 0.623 and 0.264** (v2: 0.972, 0.648, 0.336; v1: 0.995, 0.799, 0.586), about 18 s per audit on 7 pages × 2 viewports + 3 flows, about 4 s with `--quick`. Fix loop: clone_mid 0.623 → 0.997 in 4 fixes. Presentation material: docs/PRESENTATION_NOTES.md and docs/TALK_TRACK.md.


"Here are three clones. The tool scored them 0.52, 0.78 and 0.94 in about 90 seconds. Here are the gaps it found in the middle one, and here's what happens when a coding agent fixes them and we re-audit."

## 14. Implementation status and findings

Status as of 2026-11-14 (end of Phase 3; tagged `v1.0-presentation`). Design history: `docs/DECISIONS.md` (D1–D30). Per-task log with commands: `docs/PROGRESS.md`. Presentation: `docs/PRESENTATION_NOTES.md`, `docs/TALK_TRACK.md`, `docs/SUMMARY.md`.

### What exists

| Spec item | Where | Status |
|---|---|---|
| Real site (§10) | `refapp/app.py` | Fictional airline "Harbor Air" (Flask): 7 pages, random prices/dates/clock |
| Template clones | `refapp/defects.py` | 14 planted defects (+ `subtle_drift`), 3 tiers |
| Rebuilt clone | `refapp/clone_rebuilt/app.py` | From screenshots and visible observations only (D2). Defects: `REBUILT_DEFECTS` (4), `REBUILT_COVERAGE_DEFECTS` (2) |
| First-draft clone | `refapp/clone_draft/app.py` | Isolated agent, ~3 min (D17). Not to be polished |
| Held-out defects | `refapp/heldout_defects.py` | 10 `ho_` defects by an isolated agent, frozen before any run (D14) |
| Capture | `auditor/capture.py` | Playwright; page loads retried once on a stall and counted |
| Visual | `auditor/compare/visual.py` | v1 pixel-strict; v2/v3 ±3px shift tolerance per region |
| Elements | `auditor/compare/elements.py` | Hungarian matching, relabels, moves; v3: moved click targets grouped by common offset |
| Behavior | `auditor/compare/behavior.py` | Clicks, select options, dialog buttons one level deep; one-sided errors re-measured once and counted |
| Flows | `auditor/compare/flows.py` | Step replay, first divergence; accessibility-name mismatches labelled separately |
| Tickets + score | `auditor/audit.py` | Severities, structured fields (`kind`, `element(s)`, `flow_step`, `weight`, …), dedupe, audit-coverage summary v1/v2/v3, `--quick` |
| Report | `auditor/report.py` | `report.html`, `gaps.json`, `summary.json` |
| Validation | `validate.py`, `make validate` | Original (114 audits), `--heldout`, `--draft`; pass-criteria table per version |
| Agent experiments | `tools/agents.py`, `correlate.py`, `diagnose.py`, `predict.py` | Proxy agents, 14 tasks; clone-level correlation, diagnosis, task-conditioned prediction |
| Demo | `make demo` (`scripts/demo.sh`) | Audit clone_mid, one fix, re-audit, open reports (~45 s) |
| Tests | `tests/` | 24, all passing |

### Scoring (the audit-coverage summary)

- **v1:** weighted mean of four layers (0.15 / 0.30 / 0.25 / 0.30), pixel-strict visual, plain mean over pages.
- **v2:** ±3px shift-tolerant visual; each layer = ½ mean + ½ worst page; × 0.95 per high and × 0.98 per medium ticket.
- **v3 (default, D30):** v2 plus moved click targets (>20px) as medium tickets, grouped per layout change and penalised per target.

The number is presented as an audit-coverage summary, not as a predictor of agent performance.

### Results

- **Noise:** real vs real 1.000, 0 tickets ×3, every version.
- **Recall:**
  - original set: 14/14 template, 4/4 rebuilt (plus 2/2 behaviour-coverage defects);
  - held-out: 9/10 template, 9/10 rebuilt, every version. The miss is a faint colour tint.
- **False alarms:** 0 high or medium tickets that were false alarms, across the held-out set and the first-draft clone (hand-checked).
- **Tiers:** v3 0.972 / 0.635 / 0.269; v2 0.972 / 0.648 / 0.336; v1 0.995 / 0.799 / 0.586.
- **Calibration criteria:** all pass under v3. v2 fails the layout-shift check; v1 fails both the drift and the layout-shift checks.
- **Clone-level correlation with proxy-agent success** (no-flow tasks, 45 clones): ρ +0.11 to +0.29, every interval including 0 (Task 10, final scores).
- **Diagnosis:** only 19/315 (clone, task) pairs have a defect on the task's element path; agents succeed on 93–95% of pairs anyway.
- **Task-conditioned prediction** (held-out clones, v3, frozen before its held-out run): F1 0.91 (replay) and 1.00 (semantic), against 0.08–0.17 for score-threshold and any-high baselines.
- **Tickets after grouping** (v3): clone_low 43 → 35, held-out set 169 → 157, draft 16 → 15.

### Known limitations

1. One fictional site; nothing run on a real Frist clone.
2. Scripted proxy agents on 14 short tasks. The supported claim is "tickets on a task's path predict these agents' failures".
3. The audit-coverage summary does not predict agent success.
4. Faint colour-only changes go unreported.
5. The predictor matches tickets on any page a task visits, not the page of the click (2 held-out false positives). Tickets on elements a task only reads are not linked to it.
6. Coverage is limited to configured pages, matched controls and one dialog level. Masks can hide real differences.
7. One validation crash on 2026-11-12 was never explained; later timeouts were traced to sleep and fixed.
8. The fix loop's fixer is mostly the defect catalog (an oracle).
9. The predictor's replay-agent rule assumes relabels cannot hurt a coordinate agent. That is false when the task's own success condition names the element (2 held-out false negatives). An earlier note blamed the task check; a post-freeze re-run showed that was wrong (TASK_PREDICTION.md, D31).

### Next steps

1. Get a real clone + real-site pair from Frist (research@frist.ai); hand-review the tickets for the false-alarm rate.
2. Run the task-conditioned prediction with real agents on Frist's tasks; record each task's path on the real site once.
3. Match tickets to the page where the task acts; link "read" elements (headings, labels) to the actions next to them.
4. Detect flat colour changes; exercise text inputs and deeper dialogs.
5. Plug a real coding agent into the fix loop.
