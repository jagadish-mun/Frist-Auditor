# Progress log

## 2026-11-12 — Step 0: setup + macOS re-baseline — done
- Setup on macOS (Darwin arm64, Python 3.9.6, Playwright 1.60). `python -m pytest -q tests/` → 13 passed.
- `python validate.py` → noise 1.000 ×3, 0 gaps; recall 14/14; sweep 1.000 → 0.584 monotone; tiers 0.995 / 0.800 / 0.584; drift 0.953.
- Differs from the earlier Linux run by ≤0.003 in score (visual layer only). Mac numbers are now the reference (docs/VALIDATION.md regenerated).
- Note: the first validate.py attempt crashed on a 30 s `Page.goto` timeout against a local server; the rerun was clean. Cause not yet known.

## 2026-11-12 — Task 1: report polish — done
- Fixed: "1 element(s) shifted" plural; behavior descriptions now read "has no visible effect" / "cannot be clicked"; flow divergence says `after step N (click button 'X')` (no nested quotes); paths show `/fares?flight=…`; crop padding 24 → 40px.
- `python validate.py` → recall 14/14, noise 1.000 ×3 with 0 gaps, tiers 0.995 / 0.800 / 0.584, sweep monotone. Only change vs. baseline: mask-off ablation 0.9996 → 0.9997 (random prices, 8 gaps both runs).
- `python -m pytest -q tests/test_units.py` → 9 passed.

## 2026-11-12 — Task 2: screenshot-rebuilt clone — done
- `refapp/clone_rebuilt/app.py` (rebuilt from user-visible observations; app.py not read — DECISIONS D2). Observation tool: `python tools/observe.py --url <real> --out runs/observe`.
- `python validate.py` (jobs `rebuilt*`): rebuilt clone **0.984** (visual 0.892, elements/behavior/flows 1.000), gaps 0/0/14 high/med/low. Hand review (docs/rebuilt_review.md): 14/14 low gaps are real cosmetic differences, 0 noise, none would mislead an agent.
- Planted 4 defects in the rebuild: recall **4/4**; 6 high/med gaps across those runs, all true positives (0 high/med false alarms). All four together: 0.843.
- **Contradiction with a hope, not a claim:** the independent rebuild (0.984) again scores *below* clone_high (0.995), confirming the calibration problem is real and not an artifact of the synthetic `subtle_drift` toggle.
- Also: `validate.py` now retries a crashed audit once and reports it (D4); this run needed no retries. Template results unchanged (recall 14/14, noise 0 gaps).

## 2026-11-12 — Task 3: calibration (scoring v2) — done, all criteria pass
- Changes (DECISIONS D6–D10): ±3px per-region shift-tolerant visual (SSIM dropped); layer = 0.5·mean + 0.5·worst page; overall × 0.95 per high gap and × 0.98 per medium; weights unchanged; `scoring: v1` keeps the old behaviour.
- `python validate.py` (v2 + v1, 661 s, no retries). v2: noise 1.000 ×3, 0 gaps; recall 14/14 template, 4/4 rebuilt; sweep monotone 1.000 → 0.342; **drift 0.990 > clone_high 0.972** (v1: 0.953 < 0.995, FAIL). Rebuilt clone 0.984 → 0.997. Tiers v2: 0.972 / 0.669 / 0.342.
- `python -m pytest -q tests/test_units.py` → 13 passed (4 new: shift tolerance, large shift/colour still flagged, aggregation, penalty).
- **Changes earlier claims:** the tier numbers quoted in SPEC §13/§14 (0.996 / 0.798 / 0.583) are v1 numbers. Under the new default they are 0.972 / 0.669 / 0.342. Both are now reported.

## 2026-11-12 — Task 4: agent correlation (proxy agents) — done
- `python tools/agents.py --workers 3 && python tools/correlate.py` → docs/AGENT_CORRELATION.md, docs/img/correlation.png. Sanity: both agents 6/6 when trained on the real site.
- Spearman ρ (fidelity vs real-site success), 25 non-nested clones: replay +0.60 (v2) / +0.55 (v1); semantic +0.72 / +0.68. All 38: +0.82 / +0.79 and +0.87 / +0.85.
- **v2 is not measurably better than v1 at predicting success** (bootstrap CI of the difference includes 0); on the 3 tasks that are not audit flows, v1 is nominally higher (+0.49/+0.60 vs +0.44/+0.50). v2 does order drift/rebuilt (success 1.00) above clone_high (0.83) correctly, v1 does not.
- Gap found: a 48px layout shift (v2 0.951) halves replay-agent success; the score under-weights click-target movement.

## 2026-11-12 — Task 5: fix-and-re-audit loop — done
- `python tools/fix_loop.py clone_mid rebuilt_all4` → runs/fixloop/<clone>/iter_NN/report.html, history.json, docs/img/fixloop.png.
- clone_mid (v2): 0.669 → 0.816 → 0.925 → 0.949 → **0.997** in 4 fixes (all via catalog; leaves font_change/button_color, which only produce low gaps).
- rebuilt_all4 (v2): 0.674 → 0.806 → 0.889 → 0.949 → **0.997** in 4 fixes (3 catalog, 1 generic text patch: About-us link). Final score equals the unmodified rebuilt clone (0.997).
- Caveat: the fixer is an oracle for 7 of 8 fixes; this demonstrates the loop, not an autonomous fixer.

## 2026-11-12 — Task 6: presentation material — done
- `runs/demo/`: clone_mid, clone_rebuilt (v2 validation runs) and fix-loop before/after for clone_mid and rebuilt_all4 (each has report.html). Gitignored; reproduce steps in the notes.
- docs/PRESENTATION_NOTES.md: problem, one-sentence layer descriptions, validation table (v2 + v1), worked gap example with crops (clone_mid gap-003, 'Core' → 'Main'), correlation and fix-loop plots, what the score does/doesn't tell you, "what this does not show yet", limitations and next steps.
- Clarification added: docs/rebuilt_review.md was produced under scoring v1; under v2 the rebuilt clone has 7 low gaps (subset of the 14 reviewed).
- **Updated earlier claim:** SPEC §13 demo numbers now quote v2 (0.972 / 0.669 / 0.342) alongside v1, and ~15 s per audit (was ~25 s on Linux).

## 2026-11-13 — Task 7: held-out test set — done
- 10 `ho_` defects written by an isolated subagent (2 moved, 2 relabel, missing, wrong link, dead button, broken submit, extra, cosmetic); frozen in `2900434` before any run. v3 committed (`d01edb3`) before the first held-out run.
- `python validate.py --heldout --scoring v2` → recall **9/10 template, 9/10 rebuilt**; noise 1.000 ×3, 0 gaps; 0 false alarms (the 1 unexplained high gap per clone is a real flow break caused by the relabel); 9/10 defects score below baseline on each clone. Details: docs/HELDOUT.md.
- **Misses / weaknesses:** the cosmetic tint is invisible to v2 (score 1.000); the two ≥40px moves score 0.999 and 0.989.
- **Corrections:** (1) evaluator fix D15: the first run's rebuilt 10/10 included a false match on rebuild noise; honest 9/10. (2) The first held-out run overwrote the gitignored `runs/validation/v2/{noise_*,rebuilt}` folders; fixed by passing the output dir to workers; docs unaffected.

## 2026-11-13 — Task 8: scoring v3 (agent-aware severity) — done, all criteria pass
- v3 = v2 + per-element medium gap for interactive elements moved >20px (D16); default now v3 (D18).
- `python validate.py --scoring v3,v2,v1` (original set): v3 passes drift > clone_high (0.990 vs 0.972), noise 1.000/0 gaps, recall 14/14 and 4/4, monotone sweep, and **layout_shift_hero 0.809 < every no-agent-failure clone (min remove_nav_manage 0.863)**. v2 (0.951) and v1 (0.987) fail the last criterion.
- `python validate.py --heldout --scoring v3,v2,v1`: v3 recall 9/10 template, 9/10 rebuilt; 0 noise gaps. v3 adds 20 high/med gaps not in the expect lists; hand-read: all are real knock-on click-target moves (0 false alarms), but they inflate tickets. All versions miss the cosmetic tint.
- Side-by-side tables: docs/VALIDATION.md §7 (original), docs/HELDOUT.md (held-out).

## 2026-11-13 — Task 9: independent first-draft clone — done
- `refapp/clone_draft/app.py` from an isolated subagent (~3 min, observation data only; D17). `python validate.py --draft --scoring v3,v2,v1` → **v3 0.819, v2 0.819, v1 0.867**; gaps 1/1/14 in all versions.
- Hand review (docs/draft_review.md): high 1 (real: dialog lacks its accessible name; severity overstated), medium 1 (same root cause), low 14/14 real cosmetic. **False alarms: 0 at every severity**, but 1/1 high is over-rated: a missing aria-label is scored like a broken flow.
- New finding: v2/v3 penalise a semantic-only difference heavily (draft 0.819 ≈ clone_mid territory). To be checked against agent success in Task 10.

## 2026-11-13 — Task 10: correlation without the circularity — done; result is negative for v3
- 14 tasks (7 with no audit-flow overlap), 45 non-nested clones incl. 20 held-out and the draft. `python tools/agents.py --workers 3 && python tools/correlate.py` → docs/AGENT_CORRELATION.md (Phase 2), docs/img/correlation_phase2.png.
- (a) all tasks: replay ρ v3 +0.53 / v2 +0.45 / v1 +0.43; semantic +0.56 / +0.70 / +0.61.
- (b) no-flow tasks: replay +0.23 / +0.27 / +0.29; semantic +0.10 / +0.20 / +0.17. All intervals include or touch 0.
- (c) held-out clones: replay +0.19 / +0.24 / +0.30; semantic +0.61 / +0.76 / +0.67.
- **v3 does not beat v2 on (b) or (c); for the semantic agent it is significantly worse on (a) and (b).** v3 was not tuned against this. **This weakens the Phase 1 claim** that fidelity predicts success (ρ ≈ 0.6–0.7): on tasks independent of the audit flows the correlation is weak and not distinguishable from 0.
- Infrastructure: the first full run crashed (state read during navigation; fixed), and the second had 4 tasks hit by timeouts / ERR_NETWORK_CHANGED (machine sleep suspected); those 4 clones were re-run.

## 2026-11-13 — Task 11: robustness and coverage — done (root cause only partly established)
- **Timeout (D20):** the overnight failures are explained by machine sleep / network change (power log + `ERR_NETWORK_CHANGED`). Server start-up and port reuse did not reproduce in 8,000 cycles, though the readiness check had a latent hole. **The very first crash (2026-11-12 21:14) remains unexplained**: no sleep near it, system log no longer available. Fixes: keep-awake during long runs, one counted retry for a stalled page load, and a readiness check that verifies our own process owns the port.
- **Proof:** `python validate.py` ×3 back to back (114 audits each, ~1316 s each): 0 crashes, 0 audit retries, 0 page-load retries, identical scores in all three (logs: runs/proof/). Stress: 1,800 start/load cycles with the new `serve()`, 0 errors.
- **Behaviour coverage (D21):** select options and one level of dialog buttons. New planted defects both detected: `rb_pax_option_missing` (0.965, medium behaviour gap) and `rb_dialog_close_dead` (0.887, high flow + medium behaviour gap). Noise still 1.000 with 0 gaps.
- **`--quick` (D22):** `python -m auditor configs/harbor.yaml --quick …` → 3.7–3.9 s on a clean clone (target < 6 s); 6.7 s on clone_mid because each broken flow step waits out a 3 s timeout.
- **Numbers that moved** because behaviour now has more checks (all docs regenerated): clone_mid v2 0.669 → 0.648, clone_low v2 0.342 → 0.336; v3 tiers 0.972 / 0.623 / 0.264; draft 0.819 → 0.820. Pass criteria unchanged (all pass under v3).
- Tests: `python -m pytest -q tests/` → 21 passed.

## 2026-11-13 — Task 12: presentation material — done
- docs/PRESENTATION_NOTES.md rewritten for Phase 2: headline table v1/v2/v3 × (original, held-out, first-draft clone), new correlation numbers, two worked gap examples (relabel; moved click target from the held-out set), fix loop re-run under v3 (`python tools/fix_loop.py clone_mid rebuilt_all4`: 0.623 → 0.997 and 0.681 → 0.997 in 4 fixes each), "what changed and why" timeline from DECISIONS.md.
- docs/TALK_TRACK.md: 10-minute walkthrough, 8 sections, each with what to show and one key number.
- SPEC.md §13/§14 refreshed. Demo reports: runs/demo/phase2/ (gitignored).
- Correlation table recomputed against the scores regenerated in Task 11; a few cells moved by 0.01, conclusions unchanged.
- **Claims revised in Phase 2:** (1) "fidelity predicts agent success, ρ ≈ 0.6–0.7" → not supported on tasks independent of the audit flows; (2) Phase 1 tier numbers (v2 0.972 / 0.669 / 0.342) → v3 0.972 / 0.623 / 0.264 and v2 0.972 / 0.648 / 0.336 after behaviour coverage grew; (3) rebuilt-clone held-out recall 10/10 → 9/10 after the evaluator fix (D15).

> Note (added 2026-11-14, post-freeze): the Phase 3 entry dates below (2026-11-14) are UTC. The dates themselves are left unchanged.

## 2026-11-14 — Task 13: correlation diagnosis — done
- `python tools/diagnose.py` → docs/CORRELATION_DIAGNOSIS.md (data: docs/diagnosis_results.json). Agent data re-run with trajectories (runs/agents/results_traj.json; 1,651/1,652 outcomes identical to Task 10).
- **Main cause: (b) irrelevance.** Only 19 of 315 (clone, no-flow task) pairs have a planted defect on the task's element path. **(a) ceiling contributes**: success 93% (replay) / 95% (semantic), 29/45 and 33/45 clones at 100%. **(c) is not the main cause**: every failure has a defect on its path (16/16 semantic on the element path; 22/22 replay on the page path, 6 of them knock-on moves), and on-element-path defects cause failure in 16/19 pairs. The score separates failing from succeeding pairs only slightly (median 0.881 vs 0.898 under v3).

## 2026-11-14 — Task 14: task-conditioned prediction — done; the claim holds on held-out data
- `python tools/predict.py` → docs/TASK_PREDICTION.md (tables: docs/task_prediction_tables.md). Predictor frozen in `6b887a5` before any held-out run.
- Held-out clones, v3, P_aware F1: **replay 0.91 [0.79, 0.98], semantic 1.00**; baselines: score threshold 0.08 / 0.10, any-high-gap 0.17 / 0.16. All 45 clones: 0.93 / 0.96 vs 0.30–0.35 and 0.23–0.25.
- v2/v1 replay recall on held-out is only 0.45 (no moved-target gaps): v3's gaps are what explain the coordinate agent's failures.
- Errors read by hand: 2 FP from page-level matching; 2 FN are an artefact of my modify_search success check (relabelled name recorded on the clone), reported as is; the draft's dialog-name gap is a false positive for both agents (→ Task 15 severity).

## 2026-11-14 — Task 15: better tickets — done, all criteria still pass
- **Structured fields** in gaps.json: `kind`, `element` (role, name, real/clone boxes), `elements` for groups, `flow_step` (flow, step, action, target, page, outcome), `moved_px`, `variant`, `weight`. Existing fields unchanged (D25).
- **Root-cause grouping** (D28, D29): ticket counts under v3: clone_low 43 → 35 (moved-target tickets 12 → 4); 20 held-out clones 169 → 157 (22 → 10); draft 16 → 15. Grouped tickets are penalised per target, so scores only moved where a duplicate was removed (e.g. clone_mid v3 0.623 → 0.635; "Book" had been counted twice).
- **Accessibility-name mismatch** (D27): own label, severity medium because both agents succeed on the affected task. Draft clone 0.820 → 0.863 (v2/v3).
- **Found and fixed during validation** (D29): flaky 3 s behaviour-click timeouts had produced 2 false-alarm tickets; one-sided errors are now re-measured once (27 re-measurements in the main run, 0 in held-out).
- `python validate.py`, `--heldout`, `--draft` (final run): all pass criteria hold for v3 (v2/v1 fail the same two as before); recall 14/14, 4/4, held-out 9/10 + 9/10, noise 0 gaps; rebuilt clone 0 high/medium gaps. Predictor re-run: held-out F1 unchanged (0.91 / 1.00). Tests: 24 passed.

## 2026-11-14 — Task 16: default and freeze — done (clean-checkout check below)
- Default stays **v3** (D30): the only version that passes every criterion, and its moved-target tickets are what make the per-task prediction work for the coordinate agent (held-out F1 0.91 vs 0.62 with v2 tickets).
- README rewritten: the number is an "audit-coverage summary", not a predictor; the report header says the same.
- `make demo` (scripts/demo.sh): audit clone_mid, one fix, re-audit, open both reports. Measured **45 s** (0.635 → 0.800).
- `tools/fix_loop.py` gained `--iters` and `--out-root` so the demo never overwrites documented runs.

## 2026-11-14 — Task 17: final presentation material — done
- docs/PRESENTATION_NOTES.md and docs/TALK_TRACK.md rewritten around the seven-part storyline; docs/SUMMARY.md (238 words, 5 numbers, 3 caveats). SPEC.md §14 refreshed.
- Final numbers re-derived from the final runs: `python tools/correlate.py` (all-tasks ρ moved slightly, e.g. replay v3 +0.53 → +0.55; no-flow conclusions unchanged); `python tools/fix_loop.py clone_mid rebuilt_all4` (0.635 → 0.997, 0.681 → 0.997 in 4 fixes).

## 2026-11-14 — Task 16 (cont.): clean-checkout check — passed; tagged `v1.0-presentation`
- `git clone . /tmp/ff_check`, then the README's steps exactly: venv, `pip install -r requirements.txt`, `playwright install chromium`, `make test` (24 passed), `make validate` (original, held-out, draft), `make demo` (45 s). Exit 0; log in runs/clean_checkout.log.
- The clean checkout's results are **identical** to the working repo's for every one of the 207 audits (scores and ticket counts; the random mask-off ablation excluded). All pass criteria hold; held-out recall 9/10 + 9/10. No setup gaps found, so no README changes were needed.
- Retries in the clean run: 0 audits, 0 page loads, 9 behaviour checks re-measured.

## 2026-11-14 — Task 18: post-freeze corrections (branch `post-freeze`) — done
- PROGRESS.md: note that the Phase 3 dates are UTC (dates unchanged).
- CIs and failing-pair counts added to TASK_PREDICTION.md, SUMMARY.md, PRESENTATION_NOTES.md (held-out v3: replay F1 0.91 [0.79, 0.98], n = 22; semantic 1.00, bootstrap interval degenerate, recall 14/14 with exact CI [0.77, 1.00], n = 14).
- modify_search check fixed to use the real site's element names; `python tools/agents.py --tasks modify_search --workers 3 --out results_modify_search_fixed.json` → **0 of 118 outcomes changed**; `python tools/predict.py --agents-file results_traj_corrected.json --out runs/predict_corrected` → **F1 identical** (reported side by side as "post-freeze correction").
- **Correction of an earlier claim (D31):** the 2 held-out replay false negatives are real failures (the task cannot be learned on a clone that renames its link), not an artefact of the task check. TASK_PREDICTION, PRESENTATION_NOTES, TALK_TRACK and SPEC §14 corrected.

## 2026-11-14 — Task 19: deck assets — done
- `python tools/slides.py` → docs/slides/: 01_architecture, 02_ticket_relabel_core_main, 03_ticket_moved_click_targets, 04_heatmap_clone_mid_home, 05_report_top_clone_mid, 06_validation_summary, 07_correlation_noflow, 08_f1_vs_baselines, 09_fix_loop_clone_mid (all ≥ 1600px wide, light background, no local paths or ports).
- docs/slides/deck_outline.md: 12 slides following TALK_TRACK, each with title, 2–4 on-slide bullets, asset and speaker notes. Numbers shared with SUMMARY.md were checked to match exactly; the others cite their source document.
- Visual review caught and fixed four layout problems (moved-target slide showed no move; overflowing caption; missing legend glyph; overlapping labels).

## 2026-11-13 — Task 21: generated-site live demo (branch `demo-gen`) — done
- `make demo` now generates a new site (airline / grocery / bank) and a clone with 4–6 planted defects from a random seed (`SEED=` replays), audits the clone, scores the tickets against `answer_key.json` with `validate.detects`, prints a scorecard and keeps the report in `runs/demo_live/<timestamp>_seed<N>/`. A `trap` always stops the servers and deletes the temp dir. Old demo kept unchanged as `make demo-classic` (re-checked: 0.635 → 0.800, 44 s). Design: DECISIONS D33. New: `gen/site_gen.py`, `gen/site_app.py`, `gen/demo.py`, `gen/gate.py`; one unit test (25 tests pass).
- **Gate (`make demo-gate`, seeds 1–20) — PASS.** Real vs real: 0 tickets on all 20 seeds. Every demo run exited 0 in 15.7–27.8 s, with no temp dir, no listener on either port (lsof) and no process from the temp dir left behind. Ctrl-C mid-audit also cleaned up.
- **Detection:** 97/97 planted defects found (element 21/21, behaviour 23/23, flow 33/33, visual 20/20); 0 false alarms; 0 extra tickets.
- **First gate run** (same seeds, same detection): 4 medium "false alarms", all "Button 'Continue' … navigates to /review?<one key fewer>" on clones with a removed form field. The auditor was right: the clone submits one parameter fewer. The answer key had not declared that side effect. Fixed in the generator (side effect added to both field-removal defects), then all 20 seeds were re-run; the numbers above are from the re-run.
- Caveat (README, TALK_TRACK): the clone comes from the same generator, so this tests detection of known differences on an unseen site, not realistic clone noise. 97/97 should not be read as the auditor's recall on real clones.

## 2026-11-14 — Task 22: persistent demo sites (branch `demo-persist`) — done
- `make demo` now leaves both generated sites running after a successful run: detached (own session via setsid), on http://localhost:8101 (real) and :8102 (clone), or free ports if those are taken. It opens the report and both sites, prints the four-line banner and records the demo in `runs/demo_live/.active_demo.json`. New `make end-demo` (stops both, deletes the temp dir, removes the state file, prints each step; "No active demo." when there is none) and `make demo-status`. A new `make demo` ends an active one first. A failure or Ctrl-C before success still removes everything. Design: DECISIONS D34; new `gen/active.py`.
- **Gate (`make demo-gate`) — PASS.** Seeds 1–20: real vs real 0 tickets on every seed; every `make demo` exited 0 in 15.8–27.8 s with both sites answering on their localhost URLs afterwards; every `make end-demo` then left both ports free (lsof), no process from the temp dir, no temp dir and no state file. Detection unchanged: 97/97 found, 0 false alarms, 0 extra tickets.
- **Lifecycle tests, all ok:** `make demo` twice in a row (the second ended the first: its servers and temp dir gone); `make end-demo` twice (and with no demo: "No active demo.", exit 0); terminal closed (demo run from a shell in its own session, then SIGHUP + SIGKILL to that session: both sites still up, then end-demo cleaned up); port 8101 taken (real site came up on a free port, clone on 8102, everything worked); Ctrl-C mid-audit (exit by SIGINT, nothing left, no state file).
- One gate-script bug was found and fixed before the full run: on macOS `killpg` returns EPERM once only the unreaped shell is left; the terminal-close test now tolerates that. The demo itself needed no fix.
- `make test` 25 passed; `make demo-classic` unchanged (0.635 → 0.800, 44 s). Not changed: scoring, the generator's defects (`gen/site_gen.py`, `gen/site_app.py`), Harbor Air, validate.py.
