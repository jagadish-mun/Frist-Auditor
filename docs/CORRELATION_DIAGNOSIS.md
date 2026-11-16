# Why the single score doesn't predict agent success (Task 13)

Analysis only; no scoring was changed. Command: `python tools/diagnose.py` (data: `runs/agents/results_traj.json`, the Task 10 agent run repeated with trajectories recorded; 1,651 of 1,652 outcomes identical to Task 10, see DECISIONS D24). Scope: the 7 tasks that share no step with an audit flow, on the 45 non-nested clones.

"On the path" of a task is decided from the ground-truth defect catalogs, not from the auditor:
- **page path:** the defect is on a page the task visits on the real site;
- **element path:** additionally, the defect's element (its `expect` keyword) is something the task clicks or fills.

## Verdict

The weak correlation comes mainly from **(b): most defects are irrelevant to most tasks**. **(a)**, a ceiling, makes it worse. It is **not** mainly **(c)**: the audit sees the defects that matter, but the single score averages them together with all the ones that don't.

| Explanation | Key number | Verdict |
|---|---|---|
| (a) Ceiling / range restriction | Agents succeed on 93% (replay) and 95% (semantic) of the 315 (clone, task) pairs; 29/45 and 33/45 clones are at 100% no-flow success; success takes only 4 distinct values across clones | **Contributes.** Little variance to correlate with. |
| (b) Defects irrelevant to the tasks | Only **19 of 315** pairs (6%) have a defect on the task's element path; 135 (43%) have one somewhere on a page the task visits | **Main cause.** A clone's score falls for defects the task never touches. |
| (c) Score misses what matters | **Every** failure has a planted defect on its path: 16/16 semantic failures on the element path; 22/22 replay failures on the page path (16 element, 6 page-only, see below). When a defect is on the element path the agent fails in 16 of 19 pairs. | **Not the main cause.** The information is there, but at the level of individual defects, not in the whole-site score. |

## The numbers behind each explanation

### (a) Ceiling and range

| Agent | (clone, task) pairs | success share | clones at 100% no-flow success | variance of no-flow success across clones | distinct values |
|---|---|---|---|---|---|
| replay | 315 | 0.930 | 29/45 | 0.0133 | 4 |
| semantic | 315 | 0.949 | 33/45 | 0.0110 | 4 |

For comparison, the variance of the v3 score across the same clones is 0.0157. Most clones sit at the ceiling, so the rank correlation is computed mostly over ties.

### (b) Relevance: how many clones have a defect on each task's path

| Task | replay success | semantic success | clones with a defect on the page path | … on the element path |
|---|---|---|---|---|
| baggage_info | 0.87 | 0.93 | 21/45 | 3/45 |
| sign_in_page | 0.96 | 0.96 | 18/45 | 2/45 |
| sort_results | 0.96 | 0.96 | 18/45 | 2/45 |
| help_centre | 0.93 | 0.96 | 17/45 | 2/45 |
| modify_search | 0.91 | 0.91 | 25/45 | 7/45 |
| manage_trips | 0.89 | 0.93 | 18/45 | 3/45 |
| back_from_review | 1.00 | 1.00 | 18/45 | 0/45 |

14 of 45 clones have a defect on the element path of at least one no-flow task.

### Where the failures come from

| Agent | failures | on the element path | on the page path only | no planted defect on the path |
|---|---|---|---|---|
| replay | 22 | 16 | 6 | 0 |
| semantic | 16 | 16 | 0 | 0 |

The 6 replay failures on the page path only are all **knock-on moves**: a defect elsewhere on the page shifts the element the task clicks. Examples: the 48px hero shift moves the footer's Baggage info link; a relabelled nav link changes the nav's width and moves Manage trips; removing Help centre moves Baggage info. The semantic agent finds elements by name and is never affected by these.

In 3 of the 19 on-element-path pairs the agent still succeeds (for both agents).

### (c) Does the score separate failing from succeeding clones?

| Agent | Scoring | ρ, all 45 clones | ρ, the 14 clones with an on-path defect | median score of failing pairs | median score of succeeding pairs | U-test p (one-sided) |
|---|---|---|---|---|---|---|
| replay | v3 | +0.23 | +0.24 | 0.881 | 0.898 | 0.009 |
| replay | v2 | +0.26 | +0.24 | 0.917 | 0.935 | 0.005 |
| replay | v1 | +0.29 | +0.24 | 0.955 | 0.976 | 0.003 |
| semantic | v3 | +0.11 | +0.20 | 0.881 | 0.898 | 0.019 |
| semantic | v2 | +0.21 | +0.20 | 0.899 | 0.928 | 0.005 |
| semantic | v1 | +0.17 | +0.20 | 0.945 | 0.976 | 0.008 |

Clones where a task fails do score lower, and the difference is statistically significant, but it is small: about 0.02 between the medians. A whole-site score can't tell *which* task a defect breaks. A clone with one broken element on a path scores about the same as a clone with one broken element nobody uses.

## What follows

- The useful signal is in **which** gap, not **how many** gaps. That is the hypothesis Task 14 tests: does a high or medium gap on an element or flow step that a task uses predict that the task fails?
- The catalog-based check above is an upper bound on what a gap-based predictor can do: on-element-path defects predict failure in 16 of 19 pairs and cover all 16 semantic failures, but only 16 of 22 replay failures. Catching the replay agent's other 6 needs the knock-on moves, which only v3 reports as tickets.
- The no-flow task set is small and easy. With 93–95% success, any per-clone summary will correlate weakly with it. More varied or harder tasks would be needed for a stronger test.
