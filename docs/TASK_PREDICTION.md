# Task-conditioned failure prediction (Task 14)

**Claim tested:** specific gaps predict specific task failures. The single score doesn't predict agent success (Task 10), and the diagnosis says why: most defects are off the path of most tasks (Task 13). So instead of one number per clone, we ask, for each task, whether the audit reports a serious gap on something that task uses.

**Result: yes, and it holds on unseen data.** On the 20 held-out clones, under scoring v3:
- the replay agent's failures are predicted with F1 **0.91** (precision 0.91, recall 0.91);
- the semantic agent's with F1 **1.00**.

The two baselines that use the clone-level score or severity score F1 0.08–0.17.

## Method

Commands: `python tools/predict.py` (development: `--sets original`). Data: `runs/agents/results_traj.json` (agent outcomes plus trajectories), and the gaps from `python validate.py`, `--heldout` and `--draft`. Full tables: `docs/task_prediction_tables.md`; metrics: `docs/task_prediction_results.json`.

- **Unit:** a (clone, task) pair for one agent: 45 non-nested clones × 14 tasks = 630 pairs per agent and scoring version.
- **Outcome:** the agent failed the task on the real site after training on the clone.
- **What a task needs:** the elements it clicks, the fields it fills or selects, and the pages it visits, all taken from the task's run *on the real site*. The prediction never looks at the agent's run on the clone.
- **Predictor `P_aware`:** predict failure if the clone's audit has a high or medium gap on an element the task needs (on a page it visits), or a flow gap whose failing step targets such an element. Each agent's way of finding elements is taken into account:
  - the semantic agent finds elements by role and name, so it ignores "click target moved" gaps;
  - the replay agent clicks coordinates, so it ignores relabels of links and buttons, and flow failures caused by those relabels.
- **`P`:** the same rule with no agent awareness.
- **Baselines:**
  - `B_score`: predict failure for every task of a clone whose overall score is below a threshold. The threshold is the best-F1 value on the original clones, applied unchanged to the others.
  - `B_high`: predict failure for every task of a clone with any high gap.
- **Protocol:** the predictor was drafted before the Task 13 numbers existed, developed on the 25 original clones only, and frozen in its own commit (`6b887a5`) before its first run on held-out or draft clones (DECISIONS D25, D26).

## Results

F1, with 95% intervals from 2,000 bootstrap resamples of clones:

| Clones | Scoring | Agent | P_aware | P | B_score | B_high |
|---|---|---|---|---|---|---|
| **Held-out (20)** | v3 | replay | **0.91** [0.79, 0.98] | 0.92 [0.83, 0.98] | 0.08 [0.00, 0.11] | 0.17 [0.14, 0.21] |
| | v3 | semantic | **1.00** [1.00, 1.00] | 0.70 [0.53, 0.84] | 0.10 [0.00, 0.12] | 0.16 [0.13, 0.19] |
| | v2 | replay | 0.62 [0.37, 0.81] | 0.67 [0.44, 0.85] | 0.06 [0.00, 0.10] | 0.17 [0.14, 0.21] |
| | v2 | semantic | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.07 [0.00, 0.11] | 0.16 [0.13, 0.19] |
| **All 45** | v3 | replay | **0.93** [0.86, 0.97] | 0.89 [0.81, 0.95] | 0.30 [0.05, 0.48] | 0.23 [0.15, 0.32] |
| | v3 | semantic | **0.96** [0.91, 0.99] | 0.84 [0.71, 0.92] | 0.35 [0.06, 0.54] | 0.25 [0.17, 0.34] |
| | v2 | replay | 0.80 [0.64, 0.90] | 0.77 [0.62, 0.88] | 0.32 [0.03, 0.51] | 0.23 [0.15, 0.32] |
| | v2 | semantic | 0.96 [0.91, 0.99] | 0.96 [0.91, 0.99] | 0.38 [0.04, 0.57] | 0.25 [0.16, 0.34] |

v1 gives the same P/P_aware numbers as v2: the two versions produce the same high and medium gaps, and differ only in the score. Precision and recall for every cell, including the no-flow tasks, are in `docs/task_prediction_tables.md`. On the no-flow tasks alone (all clones, v3), P_aware scores F1 0.88 for replay and 1.00 for semantic; B_score scores 0.32 and 0.27.

## Reading

- **The gap list carries the predictive information; the score throws it away.** The same audits predict task failures at F1 0.9–1.0 when read per task, and at 0.1–0.4 when reduced to one number.
- **This is where v3 earns its place.** The replay agent's held-out failures are mostly moved click targets, which only v3 reports. Under v2 the predictor's replay recall on held-out drops from 0.91 to 0.45. v3 did not improve the clone-level correlation (Task 10), but its gaps are the ones that explain the coordinate agent's failures.
- **Agent awareness matters, and depends on the version.** Under v3 the semantic agent needs `P_aware` (1.00 vs 0.70), because v3's moved-target gaps don't affect an agent that finds elements by name. Under v2 there are no such gaps, so P and P_aware coincide.

## Errors, read by hand

**Held-out, v3:**
- 2 replay false positives (`*_ho_extra_baggage_calc` / baggage_info): the Baggage info link moved on `/help/baggage`, the page the task ends on, but the task clicks it on `/`, where it didn't move. The predictor matches any page the task visits, not the page of the click. That is a precision limit to fix next.
- 2 replay false negatives (`*_ho_relabel_modify_search` / modify_search). **Corrected post-freeze (see "Post-freeze correction" below):** I first called these an artefact of my task check. That was wrong. On these clones the link is relabelled "Change search", and neither agent ever trains on the task, because its success condition ("clicked Modify search") cannot be met on the clone. These are real failures. The predictor misses them because its replay-agent rule assumes a relabel cannot hurt a coordinate agent, which is false when the task itself is defined by the label.
- 0 semantic errors.

**Original clones (development set) and draft:**
- The "Core → Main" heading relabel is on an element the task *reads*, not one it clicks, so it isn't predicted (3 pairs per agent).
- The drift clone's help_centre replay failure has no gap at all.
- On the first-draft clone, fare_rules is predicted to fail for both agents (the dialog lacks its accessible name), but both succeed. Task 15 decides that gap's severity from this.

## Caveats

- Proxy agents again, with 14 short tasks on one site. "Predicts the failures of these two scripted agents" is the claim, not "predicts what an RL agent will learn".
- The replay-agent rule in `P_aware` was refined on the original clones. The held-out numbers are the ones to quote.
- The predictor needs each task's reference path on the real site. For Frist this means recording the tasks once on the real site, which is cheap, but it is an input the clone-level score doesn't need.

## Confidence intervals and the number of failures behind each F1 (post-freeze addition)

Computed from the frozen v1.0-presentation predictor output (`runs/predict/results.json`, v3), with 2,000 bootstrap resamples of clones (seed 0). n = failing (clone, task) pairs, out of 280 pairs per agent on held-out and 630 on all clones.

| Clones | Agent | Tickets on the task's path (P_aware) | Score threshold (B_score) | Any high ticket (B_high) |
|---|---|---|---|---|
| Held-out (20) | replay, n = 22 | **0.91** [0.79, 0.98] | 0.08 [0.00, 0.11] | 0.17 [0.14, 0.21] |
| Held-out (20) | semantic, n = 14 | **1.00** [1.00, 1.00]* | 0.10 [0.00, 0.12] | 0.16 [0.13, 0.19] |
| All (45) | replay, n = 62 | **0.93** [0.87, 0.98] | 0.30 [0.05, 0.48] | 0.23 [0.16, 0.33] |
| All (45) | semantic, n = 54 | **0.97** [0.93, 1.00] | 0.35 [0.06, 0.54] | 0.26 [0.18, 0.36] |

\* The bootstrap interval is degenerate. The predictor got all 14 held-out semantic failures right with no false positives, so every resample scores 1.00. Exact binomial (Clopper–Pearson) 95% intervals are more informative here: recall 14/14 → [0.77, 1.00], precision 14/14 → [0.77, 1.00]. Replay on held-out: recall 20/22 → [0.71, 0.99], precision 20/22 → [0.71, 0.99].

## Post-freeze correction (2026-11-14, branch `post-freeze`, DECISIONS D31)

**What was claimed:** the 2 held-out replay false negatives were an artefact. The modify_search success check judged the replay agent by the element name recorded on the clone, not the name on the real site.

**What I did:** I changed the check so "clicked" means the element actually clicked on the site where the run happens, by its name there. The semantic agent records the name it looked up; the replay agent records the link or button under the click point. Then I re-ran modify_search for both agents on all 59 clone configurations (`python tools/agents.py --tasks modify_search --workers 3 --out results_modify_search_fixed.json`) and the predictor on the merged outcomes (`python tools/predict.py --agents-file results_traj_corrected.json --out runs/predict_corrected`).

**What happened:** 0 of 118 modify_search outcomes changed, so every F1 is unchanged:

| Held-out, v3 | Original (v1.0-presentation) | Post-freeze correction |
|---|---|---|
| replay F1 (n = 22) | 0.91 [0.79, 0.98] | 0.91 [0.79, 0.98] |
| semantic F1 (n = 14) | 1.00 (recall CI 0.77–1.00) | 1.00 (recall CI 0.77–1.00) |
| All clones, replay / semantic | 0.93 / 0.97 | 0.93 / 0.97 |

**Why nothing changed:** my diagnosis was wrong. On the two relabelled clones, neither agent ever *trained*: the task's success condition ("clicked an element named Modify search") cannot be met on a clone where that link reads "Change search". The failures are real. A task whose reward is keyed to a label cannot be learned on a clone that renames it, whichever agent is used. The error is in the predictor's replay-agent rule (D26), which assumes relabels never hurt a coordinate agent. That rule is frozen and has not been changed; this limitation is now stated with it.

## After Task 15 (grouped tickets, accessibility-name label)

Re-run of the same frozen predictor on the regenerated tickets (`python validate.py`, `--heldout`, `--draft`, then `python tools/predict.py`). The tables in `docs/task_prediction_tables.md` are now these numbers.

| Clones | Scoring | Agent | P_aware F1 (precision / recall) | B_score | B_high |
|---|---|---|---|---|---|
| Held-out (20) | v3 | replay | 0.91 (0.91 / 0.91), unchanged | 0.08 | 0.17 |
| Held-out (20) | v3 | semantic | 1.00 (1.00 / 1.00), unchanged | 0.10 | 0.16 |
| All 45 | v3 | replay | 0.93 (0.97 / 0.90) | 0.30 | 0.23 |
| All 45 | v3 | semantic | 0.97 (1.00 / 0.94) | 0.35 | 0.26 |

The only change: the draft clone's fare_rules false positive is gone for both agents. Its dialog-name difference is now an `a11y_name` ticket, which the frozen rule does not treat as a broken element or flow step.
