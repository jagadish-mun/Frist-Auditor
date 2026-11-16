# Design decisions

One entry per decision: date, choice, alternatives considered, rationale.

## D1 (2026-11-12) — macOS is the reference platform
- **Choice:** regenerate docs/VALIDATION.md from the macOS run; `validate.py` now writes the platform into the header.
- **Alternatives:** keep Linux numbers with a note; maintain two tables.
- **Why:** the user asked for it; all later runs happen on this machine, so one self-describing table avoids mixing platforms.

## D2 (2026-11-12) — How the rebuilt clone was built (fairness rule)
- **Choice:** `refapp/clone_rebuilt/app.py` was written only from `tools/observe.py` output (full-page screenshots; visible text with boxes; interactive elements with role, visible name, link target; form labels/placeholders/options/required; URLs reached by submitting forms and running the 3 flows) plus pixel colours sampled from screenshots. **I did not open `refapp/app.py`** at any point in this session (the only line of it I saw is `app.run(...)`, from an earlier grep). I read `configs/harbor.yaml` for page URLs, flows and the mask selector class names `.price` / `.dynamic`, which are part of the audit contract.
- **Iteration:** three correction rounds comparing the clone's observed text boxes with the real site's (offsets → CSS tweaks). Never tuned against auditor output.
- **Alternatives:** single-shot rebuild with no iteration (rougher, more like a first agent draft); reading page HTML/CSS via DevTools (not "what a user sees").
- **Why:** closest affordable stand-in for SPEC §10's agent-built clone while keeping a clear fairness boundary. Caveat: three rounds of box-matching make this a careful rebuild, likely better than a typical first draft.

## D3 (2026-11-12) — Rebuilt-clone planted defects target new elements
- **Choice:** `rb_no_modify` (missing 'Modify search'), `rb_relabel_find` ('Find trip' → 'Look up'), `rb_broken_about` (About us → 404), `rb_search_dead` (Search does not submit). Catalogued as `REBUILT_DEFECTS` in `refapp/defects.py`.
- **Alternatives:** reuse the template-defect elements (sort select, baggage link).
- **Why:** avoids measuring recall only on elements we already know the auditor handles.

## D4 (2026-11-12) — One logged retry per validation audit
- **Choice:** `validate.py` retries a crashed audit once, prints it, and records `attempts` in results.json and a "retried" line in RESULTS.md.
- **Alternatives:** no retry (a single flaky 30 s `goto` timeout killed a 5-minute run in Step 0); silent retry.
- **Why:** robustness without hiding anything. A run that needed a retry is visible in the doc.

## D5 (2026-11-12) — Review low gaps when there are no high/medium ones
- **Choice:** the rebuilt clone produced 0 high/medium gaps, so every low gap was hand-labelled instead (docs/rebuilt_review.md).
- **Why:** otherwise the false-alarm rate would be "0 of 0", which says nothing.

## D6 (2026-11-12) — v2 visual: per-region ±3px rigid-shift search, SSIM dropped
- **Choice:** keep v1's candidate regions (pixel diff | low local SSIM, dilated), then for each region find the single (dx, dy) in ±3px that minimises differing pixels (masked pixels ignored on both sides); only the residual counts. Visual score = 1 − min(1, 4 × residual fraction).
- **Alternatives:** per-pixel independent shift (rejected: lets glyphs of *different* text match stroke-by-stroke, could hide relabels); element-level crop comparison (more code, depends on element matching); larger radius (would absorb cumulative reflow, but a 14px shift does move click targets for a coordinate-based agent, so it should still cost something).
- **Why:** sub-pixel/1–3px drift from a rebuild is not a functional difference; colour, font and >3px layout changes still produce residual. SSIM is not shift-tolerant so it is dropped from v2. Effect: drift clone visual 0.683 → 0.932; rebuilt clone 0.892 → 0.977; noise unchanged (1.000, 0 gaps).
- **Known ceiling:** cumulative vertical reflow >3px still counts as changed.

## D7 (2026-11-12) — v2 page aggregation: 0.5 × mean + 0.5 × worst page
- **Choice:** per layer (visual, elements, behavior).
- **Alternatives:** plain mean (v1; one broken page among 7 costs 1/7 of its loss); pure min (one cosmetic page dominates; noisy); weighting pages by flow traffic (no traffic data).
- **Why:** an agent task fails if any page on its path is broken, so the worst page should matter; keeping half the mean preserves sensitivity to defects on several pages (needed for monotonicity). 0.5/0.5 is a judgment call, not fitted.

## D8 (2026-11-12) — v2 severity penalty: ×0.95 per high gap, ×0.98 per medium, ×1 per low
- **Choice:** overall = weighted layer score × Π(1 − p_severity) over the final (deduplicated) gap list.
- **Alternatives:** lower visual weight only (0.15 → 0.10 gives drift 0.993 vs clone_high 0.993: not a real separation); drop the 0.5 credit for relabels (fixes only relabels, not missing elements or behaviour); severity-capped page scores (similar effect, harder to explain).
- **Why:** SPEC §6 already assigns high/medium to agent-relevant defects (missing element, broken flow, relabel, behaviour change) and low to cosmetic ones. Using that classification directly makes "functional defects hurt more than cosmetic drift" an explicit, explainable rule. Effect: clone_high 0.995 → 0.972, drift 0.953 → 0.990.
- **Risks:** the score now depends on gap deduplication (two defects merged into one gap cost one penalty) and on the severity rules; tier scores spread much wider (clone_low 0.584 → 0.342), so v1 and v2 numbers are not comparable. Sweep is still monotone (VALIDATION.md §3).

## D9 (2026-11-12) — Layer weights unchanged (0.15 / 0.30 / 0.25 / 0.30)
- **Reviewed:** with D6–D8 the criteria pass without touching weights; changing them as well would add an unvalidated degree of freedom. To be revisited with agent-correlation data (Task 4).

## D10 (2026-11-12) — v2 is the default; v1 kept behind `scoring: v1`
- **Why:** the user asked for v1 to stay available; `validate.py` runs both and reports them side by side (VALIDATION.md §7).

## D11 (2026-11-12) — Plots drawn with Pillow, no matplotlib
- **Choice:** small PIL scatter-plot helper for Task 4/5 plots.
- **Alternatives:** add matplotlib (new dependency; the user asked to be consulted before adding dependencies).
- **Why:** Pillow is already a dependency; scatter + line plots need ~40 lines.

## D12 (2026-11-12) — Agent-correlation experiment details (user fixed the design)
- **Choices within the given design:** BFS training (≤5 clicks, ≤60 expansions) with label-matched form filling; state = URL + open-dialog text; skip words pay/delete/purchase/buy/remove; 6 tasks (3 overlap with audit flows, 3 do not, so circularity can be measured); clone set = every validate.py configuration (38) so scores come from the same runs; Spearman reported on all clones and on the 25 non-nested ones, with a 2000-sample bootstrap (seed 0) for ρ and ρ(v2) − ρ(v1).
- **Alternatives:** random-walk training (non-deterministic); only tier clones (n = 3–4, no statistics possible).
- **Why:** deterministic, cheap (~10 min), and honest about the dependence between clones and tasks.

## D13 (2026-11-12) — Fix loop: what counts as a "fix"
- **Choice:** template clones are fixed via the defect catalog (switch off the defect matched to the top high/medium gap; an oracle). The rebuilt clone gets generic text patches derived from the gap description alone (relabel → swap the label string; wrong link → swap the path) on a working copy under runs/fixloop/, falling back to the catalog when a gap needs new code (missing element, dead button). Every iteration records its `method`.
- **Alternatives:** an LLM coding agent (needs an API key: out of bounds per the user's rules); hand-written patches per gap (indistinguishable from the oracle, less honest).
- **Why:** shows the loop mechanics end to end without pretending the fixer is smarter than it is. Result: 1 of 4 rebuilt-clone fixes was a generic text patch; the relabel was fixed via the catalog because its top-ranked gap was the flow failure, which a text patch cannot address.

## D14 (2026-11-13) — Held-out protocol (Task 7)
- **Choice:** a subagent that is given only `refapp/app.py`, `refapp/clone_rebuilt/app.py` and the task instructions writes 10 defects (`ho_*`) into `refapp/heldout_defects.py` plus toggles in both apps. It reports back only defect names and a count per kind. The set is committed on its own before any run. I do not open `heldout_defects.py` or the app diffs, and from held-out runs I read only aggregate numbers (recall, unexplained-gap counts, score ordering), never gap texts, until scoring v3 is designed and committed.
- **Alternatives:** write the defects myself (I would design v3 around them); let the subagent see the auditor (it could write defects tailored to its keyword matcher).
- **Why:** held-out numbers are only honest generalisation numbers if the scoring designer has not seen the defects. Known leak: I know the *kinds* (the user's list) and the names the subagent picks.

## D15 (2026-11-13) — Detection on the rebuilt clone must be new relative to its no-defect baseline
- **Choice:** in `validate.py`, a gap on a `rebuilt_*` run counts as detecting a planted defect only if the same (layer, page, description) is not in the plain `rebuilt` run.
- **Why:** found on the held-out cosmetic defect. A visual-only expectation matched pre-existing rebuild noise and inflated recall (10/10 → honest 9/10). Applies to the Phase 1 rebuilt defects too; their high/medium detections are unaffected.
- **Alternative:** drop visual-only expectations (would make cosmetic defects undetectable by definition).

## D16 (2026-11-13) — Scoring v3 = v2 + per-element "click target moved" medium gaps
- **Choice:** under v3 the element move threshold is 20px (v1/v2: 24px). Every matched *interactive* element moved more than 20px gets its own medium gap ("<Role> '<name>': click target moved Npx"). Non-interactive moves stay in the aggregated low gap. Everything else is as in v2. Coded and committed (`d01edb3`) before any held-out run.
- **Granularity: per element, not per page.** Agents act on individual elements, and a page with 8 moved targets is worse for a coordinate agent than one with 1. Cross-page dedupe still merges the same nav link moving on every page into one gap.
- **Other Phase 1 findings considered and rejected for v3:**
  - weighting nav or flow-relevant elements by agent task usage (no independent usage data; would bake the agent task set into the score);
  - mask-covered regions (a capture issue, not scoring);
  - changing the relabel credit (no evidence it is mis-set).
- **Risk:** any layout change that reflows interactive elements by more than 20px (e.g. removing a nav item shifts the others) now costs a medium gap per moved element.

## D17 (2026-11-13) — Independent first-draft clone (Task 9)
- **Choice:** a fresh subagent got only a copy of `runs/observe/` (screenshots, observation JSON, flow logs, extra-page screenshots) and the audit's mask contract (classes `price`/`dynamic`, regex masks). It had no repo access and a 30-minute budget. It reported ~3 minutes of work and no browser rendering (curl checks only). `refapp/clone_draft/app.py` is committed unmodified apart from a provenance header.
- **Why:** a closer stand-in for "an agent's first draft" than my three-round rebuild (D2). It will not be polished, so it stays a fixed test case.

## D18 (2026-11-13) — v3 becomes the default scoring
- **Evidence:** all Task 3 criteria still hold under v3. layout_shift_hero (0.809) is now below every clone where no Phase 1 agent task fails (lowest: remove_nav_manage 0.863); v2 (0.951) and v1 (0.987) fail this. Held-out recall is 9/10 + 9/10 with 0 noise gaps, the same as v2. Moved targets now cost something on unseen defects (mean of the two ≥40px moves: 0.946 vs 0.994 under v2).
- **Cost accepted:** knock-on moves (D16 risk) produce extra medium tickets (20 on held-out, all real moves). v1/v2 remain selectable.

## D19 (2026-11-13) — Task 10: eight new agent tasks and how "non-flow" is defined
- **Choice:** 8 tasks added (pax_search, sort_results, help_centre, modify_search, manage_trips, back_from_review, pick_extra_fare, checkin_then_home), 14 in total. Each task carries an `overlap` tag: `flow` (identical to an audit flow: book_core, fare_rules, check_in), `partial` (passes through steps or states of a flow: search_bos_mco, pax_search, pick_extra_fare, checkin_then_home) or `none` (shares no flow step: 7 tasks). Analysis (b) uses only `none`. The tags were fixed before the run.
- **Alternatives:** count every task that is not literally a flow as "non-flow" (11 tasks; would leave the Search and Find-trip steps, which flows exercise, inside the "independent" set).
- **Why:** the circularity is about v2/v3 penalising flow breaks; a task that reuses a flow's step still shares that cause. The stricter set is the honest one.
- **Agent changes needed for the new tasks:** `<select>` support (semantic: by label; replay: the select under the recorded point), select values in the state, and the list of clicked names (so "Modify search" cannot be satisfied by clicking the logo). Statistics exclude the real-vs-real point and the nested sweep clones.
- **Robustness fix:** a failed step could leave a navigation in flight and crash the state read (the first 58-clone run died on this). State reads now wait for load and retry once; a task that still errors is recorded as failed with its error text, never dropped.

## D20 (2026-11-13) — The intermittent 30 s `Page.goto` timeout: what was found, what was fixed
- **Evidence gathered:**
  1. *Machine sleep / network change — confirmed cause of the overnight failures.* The 14-task agent run that spanned a system sleep (`pmset -g log`: repeated Sleep/DarkWake from 01:36) recorded three 30 s `Page.goto` timeouts and one `net::ERR_NETWORK_CHANGED` against 127.0.0.1. Playwright's timeout is wall-clock, so a load in flight across a sleep exceeds it; Chrome also aborts in-flight requests when the network configuration changes.
  2. *Server start-up and port reuse — not reproduced.* 8,000 start → load → stop cycles with the old `serve()` (10 parallel workers) gave 0 slow loads and 0 errors (max load 0.03 s). The old readiness check did have a real hole, though: it only tested that *something* accepted a TCP connection on the port, so after a port race it would have handed out another process's server.
  3. *The very first crash (2026-11-12 21:14) is not explained.* The power log shows no sleep near it, and the system log for that minute is no longer available, so a network change can be neither confirmed nor ruled out.
- **Fixes (all three, since one cause is unproven):**
  - `keep_awake()` (macOS `caffeinate -i -w <pid>`) in `validate.py` and `tools/agents.py`: no idle sleep during long runs.
  - `capture.goto()`: one retry of a page load that times out or is aborted by a network change; retries are counted in `summary.json` (`nav_retries`) and totalled in RESULTS.md. Tested by freezing the server with SIGSTOP (`tests/test_integration.py`).
  - `serve()`: ready means our own child process is alive, answers HTTP, and is the process listening on the port (`lsof`); otherwise retry on a new port. Tested with a foreign listener (`tests/test_units.py`).
- **Alternatives:** raise the timeout (hides stalls, slows failure); silent retries (rejected: every retry is reported).
- **Honest status:** cause 1 is established and fixed; cause 2 was a latent bug, fixed but never observed; the first crash remains unexplained. The 3 clean runs show the suite is stable now, not that the first crash's cause was found.

## D21 (2026-11-13) — Behaviour layer: select options and one level inside dialogs
- **Choice:** with `behavior_extended` (default on), each matched `<select>` has up to 4 options chosen on a fresh load, and the outcome records navigation, dialog and whether the masked page text changed ("changes the page content"). For each click that opens a dialog, up to 4 buttons inside it are clicked once and the outcome recorded ("leaves dialog … open"). Results count toward the behaviour score like any other clickable. Skip words (pay, delete, …) apply inside dialogs too.
- **Alternatives:** compare the full DOM after a select change (too noisy); recurse into dialogs (unbounded).
- **Why:** Phase 1 limitation 4 and the draft review (a Sort select that does nothing was invisible). Note: Harbor Air's own Sort select does nothing either, so the capability is tested with planted defects, not on real behaviour.
- **Planted defects for the new capabilities** (`REBUILT_COVERAGE_DEFECTS`, kept apart from the Phase 1 four): `rb_pax_option_missing`, `rb_dialog_close_dead`.
- **Effect on existing numbers:** more behaviour results per page, so behaviour-layer scores (and totals) shift slightly; all validation tables were regenerated.

## D22 (2026-11-13) — `--quick` mode
- **Choice:** `python -m auditor … --quick`: first (desktop) viewport only, no behaviour exploration, behaviour weight set to 0 so the score is the weighted mean of the three layers that ran; flows keep running but with a 50 ms settle wait and no screenshot after a successful fill/select (which cannot change the compared state). Measured 3.7–3.9 s on a clean clone, 6.7 s on clone_mid (each broken flow step waits out a 3 s timeout).
- **Why:** fast iteration while fixing a clone. Quick scores are not comparable with full scores and must not be quoted as fidelity numbers.

## D23 (2026-11-13) — v3 stays the default after the Task 10 result, and is not tuned
- **Result:** v3 does not predict proxy-agent success better than v2 on the no-flow-overlap tasks or the held-out clones, and is significantly worse for the semantic agent (docs/AGENT_CORRELATION.md).
- **Choice:** leave v3 unchanged and as the default; state the result plainly everywhere the default is mentioned; v2 remains one config line away.
- **Alternatives:** revert the default to v2 (defensible: better fit for name-based agents, fewer duplicate tickets); soften v3's move penalty until its correlation recovers (rejected: that is tuning on the evaluation data, which the user ruled out).
- **Why:** v3 meets the criteria it was specified against (Task 8) and surfaces moved click targets as tickets, which v2 hides at 0.95+. Which agent type matters more is Frist's call and needs real agents; the proxies cannot settle it.

## D24 (2026-11-14) — Phase 3 data: trajectories recorded by re-running the agents
- **Choice:** `tools/agents.py` now records each task's trajectory (click targets, filled/selected fields) and the pages visited on the real site. Re-run into `runs/agents/results_traj.json`; the Task 10 file is untouched.
- **Check:** 1,651 of 1,652 (clone, task, agent) outcomes match Task 10. The one flip (`single_signin_goes_home`, back_from_review, semantic: fail → success) shows the agents are not perfectly deterministic. Phase 3 uses the new file throughout.

## D25 (2026-11-14) — Structured ticket fields, and the predictor written before the diagnosis
- **Ticket fields (additive):** `kind` (missing, extra, label, target_moved, moved, behavior, visual, flow, flow_config), `element` {role, name, real_box, clone_box, clone_name}, `flow_step` {flow, index, action, role, name, page, outcome}, plus `moved_px` and `variant` (`option:<text>`, `dialog:<button>`) where relevant. Existing fields unchanged; scores unchanged.
- **Predictor:** `tools/predict.py` was drafted before any Task 13 numbers were computed and is committed now, before any predictor run. It will be developed on the original clones only and frozen in its own commit before its first held-out run.

## D26 (2026-11-14) — Task-conditioned predictor: frozen definition
- **What it predicts:** for each (clone, task, agent), FAIL iff the clone's audit has a high or medium gap that refers to an element the task clicks or fills on the real site (on a page the task visits), or a flow gap whose diverging step targets such an element. "What the task needs" comes from the task's reference trajectory on the real site, so the prediction uses only the audit and the task, never the agent's run on the clone. Full definition: `tools/predict.py` docstring.
- **Variants:** `P` (same rule for both agents) and `P_aware` (accounts for how each agent finds elements):
  - semantic agent ignores "click target moved" gaps. Fixed a priori.
  - replay agent ignores relabels of links/buttons, and flow failures caused by such a relabel. Added after inspecting errors on the **original clones only**. A first version also ignored field relabels; that lowered recall (0.90 → 0.80) because both agents fill fields by label while training, so it was narrowed to clickables.
- **Baselines:** `B_score` (overall score below a threshold chosen for best F1 on the original clones, then applied unchanged) and `B_high` (any high gap in the clone).
- **Development numbers (original clones, 25 × 14 tasks, v3):** P_aware F1 0.94 (replay) and 0.95 (semantic); B_score 0.44 / 0.49; B_high 0.26 / 0.31.
- **Frozen** in its own commit before the first held-out or draft predictor run. Known blind spots: a defect on an element the task only *reads* (the "Core → Main" heading next to the clicked link) and failures with no gap at all (drift clone / help_centre, replay).

## D27 (2026-11-14) — Accessibility-name mismatch: its own label, severity medium
- **Rule:** a dialog that opens with the same visible content on the clone but without the real site's accessible name (the clone's exposed name starts with the real one; path, status and heading identical) becomes one ticket of kind `a11y_name`, "Accessibility-name mismatch", whether the behaviour layer or a flow saw it. The flows layer still counts the divergence in its own score.
- **Severity from the agent data (as the user specified):** the only clone with this difference is the first draft. On its affected task (fare_rules), both proxy agents succeed, in Task 10 and in the Task 14 rerun: semantic 1/1, replay 1/1, and 14/14 tasks overall for both. The semantic agent does not fail, so the severity is **medium** (it was high).
- **Caveat stated with it:** our semantic agent finds the dialog's *button* by role and name, but checks the dialog by its text. An agent that looks dialogs up by role *and accessible name* would fail. The evidence is one clone and one task.
- **Effect:** draft clone 0.820 → 0.863 (v2/v3); its high/medium tickets go from 1 high + 1 medium to 1 medium.

## D28 (2026-11-14) — Root-cause grouping of moved click targets (v3)
- **Rule:** on each page, matched interactive elements that moved more than 20px are grouped greedily by offset; offsets within 4px of a group's first member join it. A group of 2 or more becomes one ticket: "N click targets moved together ~Npx down (one layout change): 'A', 'B', …". It keeps `elements` (all members) and `weight` = N. A group of one keeps the old per-element wording.
- **Score:** a grouped ticket is penalised per target, `(1 − p)^weight`, so grouping changes ticket counts but not scores. This was deliberate. With a flat penalty per ticket, layout_shift_hero would rise to about 0.93 and fail the Task 8 criterion. The score is about how many click targets are broken; the ticket list is about how many fixes are needed.
- **Container naming:** the user's wording was "N click targets in <container>". The capture has no landmark information, so the ticket names the elements and the direction instead of a container.
- **Predictor:** `tools/predict.py` now reads every element of a grouped ticket. This is a representation change only; the rule frozen in D26 is the same.

## D29 (2026-11-14) — Two fixes found by the first Task 15 validation run
- **Flaky behaviour clicks were producing false alarms.** Two medium tickets in that run read "cannot be used (TimeoutError)": one on the *real* site's Find trip button (on the plain rebuilt clone, which had 0 high/medium gaps in every earlier run), one on the clone's Manage trips link. Both are 3 s click timeouts, not differences. **Fix:** when exactly one side of a behaviour comparison errors, that side is re-measured once; the count is recorded (`behavior_retries` in summary.json, totalled in RESULTS.md). A genuinely dead or missing control errors again and still becomes a ticket.
- **The same move on several pages was split into tickets.** "Baggage info moved 94px" appeared three times because per-page offsets fell into different 4px buckets of the ticket key. **Fix:** moved-target tickets are keyed by their element names only, so one element (or one group) moving on several pages is one ticket with `also_on`. The same rule removed a double-count of the nav link "Book" (moved 112px on some pages, 114px on others) and nudges v3 scores of clones with that defect up by about 0.01 (clone_mid 0.623 → 0.635).
- **Not changed:** the per-target penalty (D28), severities, the predictor.

## D30 (2026-11-14) — Final default: scoring v3, presented as an audit-coverage summary
v3 stays the default. On its own terms it passes every validation criterion, including the two v2 and v1 fail: the drift clone above clone_high (v1 fails), and layout_shift_hero below every clone where no agent task fails (v2 and v1 fail). Its distinctive output, moved click targets, now arrives as one grouped ticket per layout change. The decisive evidence is Task 14. Read per task, v3's tickets predict the coordinate-based agent's held-out failures with F1 0.91, against 0.62 under v2 (recall 0.91 vs 0.45), and they lose nothing for the name-based agent (1.00 under both). What v3 does *not* do is make the single number a better predictor of agent success; Task 10 showed it is slightly worse than v2 there. The single number is therefore presented everywhere (README, report header, presentation) as an "audit-coverage summary", a severity-weighted count of what the audit found, and not as a predictor of agent performance. The claim that is supported is the narrower one: specific high or medium tickets on elements a task uses predict that task's failure. v1 and v2 remain selectable with `scoring:`.

## D31 (2026-11-14, post-freeze) — modify_search check corrected; the earlier diagnosis was wrong
- **Change:** in `tools/agents.py`, a task's "clicked" list now holds the elements actually clicked on the site where the run happens, by their names there (semantic: the looked-up name; replay: the link or button under the click point), instead of the trajectory as recorded on the clone. `--tasks` and `tools/predict.py --agents-file/--out` were added so only modify_search could be re-run and re-scored. Scoring, the predictor rule and all validation results are unchanged; the `v1.0-presentation` tag still points at the original.
- **Result:** 0 of 118 modify_search outcomes changed (59 clone configurations × 2 agents), so every F1 is identical.
- **Correction of a published claim:** Task 14 called the 2 held-out replay false negatives an artefact of the task check. They are not. On the two relabelled clones, neither agent trains: the success condition names "Modify search", and the clone says "Change search". They are real failures that the predictor's replay-agent rule (D26) misses, because it assumes relabels cannot affect a coordinate agent. The docs now say so; the rule is frozen and not changed.
- **Also added post-freeze:** bootstrap 95% intervals and failing-pair counts for every F1 in TASK_PREDICTION, SUMMARY and PRESENTATION_NOTES. The semantic held-out interval is degenerate ([1.00, 1.00]), so exact binomial intervals for its recall and precision (14/14 → [0.77, 1.00]) are given beside it.

## D32 (2026-11-14) — Deck assets generated from run outputs, not hand-made
- **Choice:** `tools/slides.py` builds all nine PNGs in `docs/slides/` directly from the final run outputs. It uses Pillow, plus Playwright for the report screenshot; no new dependency. Images are 1920px wide (the report screenshot 2000px) on a light background, with type sized for a projector.
- **Choices inside it:**
  - The moved-target slide crops the *same* page region from both full screenshots and outlines the real-site positions on the clone. The report's own crops are centred on each element and would hide the move.
  - In the report screenshot, the local server URLs are replaced with "Real: Harbor Air (reference site) · Clone: clone_mid".
  - The correlation slide uses the Task 10 agent outcomes and the final v3 scores, i.e. the same data as the ρ in SUMMARY.md.
- **Why:** every number on a slide is traceable to a command, and the assets regenerate with one command if a run is repeated.

## D33 (2026-11-13) — Generated-site live demo (Task 21)
- **One engine, two specs.** `gen/site_gen.py` writes a `site.json` spec plus a copy of a fixed Flask engine (`gen/site_app.py`) for the real site, and the same engine with a mutated spec for the clone. Each planted defect is a spec change (a relabelled string, a dropped field, a changed href, a disabled dialog, a CSS override), so the clone can differ from the real site only where a defect was planted. This was chosen for robustness the night before a live demo. The cost is that the clone has no rebuild noise; the demo tests detection only (stated in README and TALK_TRACK).
- **4–6 defects, not 3–6.** The task asks for at least one per category (element, behaviour, flow-breaking, visual-only), which needs at least 4. Each run plants one per category plus 0–2 more from the non-visual pools.
- **Visual-only defects are honest.** A colour-only change (heading background or button colour) goes on one page that no other planted defect changes visually. Its expectation is "any visual ticket on that page", which nothing else can produce. Colour changes never move elements, so they cause no element or behaviour tickets.
- **Matching** uses `validate.detects`, unchanged: the generated defects are registered in `validate.ALL_DEFECTS` under a `gen:` prefix for that process only. Each defect has `expect` triples (count as found) and `side_effects` triples (other tickets it legitimately causes, e.g. a removed form field re-flows the form grid, so every element ticket on the form page counts as a side effect).
- **Scorecard terms.** *Extra tickets* = tickets matched by no planted defect's `expect` or `side_effects`. *False alarms* = extra tickets of high or medium severity. This is stricter than validate.py's `explained()`, which accepts any flow ticket and any ticket on a `*` defect's pages.
- **Masks:** `.price` and `.dynamic` selectors plus money and clock regexes. Prices sit in fixed-size blocks so random widths never move neighbours. Real-vs-real gives 0 tickets for every gate seed.
- **Safety:** the final action (Pay / Place order / Transfer) is a `type=button` with no handler, flows end in `stop_before`, and `skip_actions` also covers "place order" and "transfer".
- **Cleanup** is owned by `scripts/demo.sh`: `trap cleanup EXIT` (plus INT/TERM → exit 130) kills any process whose command line contains the canonical temp path (`pkill -f`) and removes the temp dir. Reports go straight to `runs/demo_live/<timestamp>_seed<N>/`; the report uses relative paths to `shots/` and `crops/` there, so nothing has to be copied.
- **Gate:** `make demo-gate` (`gen/gate.py`) runs seeds 1–20: real-vs-real noise (0 tickets required), then `SEED=n NO_OPEN=1 make demo`, checking exit 0, < 60 s, report and screenshots present, temp dir gone, both ports free (`lsof`) and no process running from the temp dir. It also runs one Ctrl-C test (SIGINT to the process group mid-audit). Not changed: scoring, Harbor Air, validate.py.

## D34 (2026-11-13) — Live demo sites stay up until `make end-demo` (Task 22)
- **Detached servers.** `gen/demo.py` starts both sites with `start_new_session=True` (the child calls `setsid`), stdin from /dev/null and output to `server.log` in the temp dir. They are in their own session, so a terminal hangup (SIGHUP) or Ctrl-C (SIGINT to the terminal's process group) never reaches them. That is why the Python side and `demo.sh`'s trap stop them explicitly when a run fails. `nohup` is not used: a new session already covers what it does.
- **Kept only on success.** The servers are killed in a `finally` unless the audit, scorecard and state file all completed. `demo.sh` sets `KEEP=1` only after `gen/demo.py` exits 0; before that its EXIT trap still kills anything running from the temp dir, deletes it, and removes a state file that names that temp dir (covering a Ctrl-C in the instant between the two).
- **Ports.** 8101 (real) and 8102 (clone). A port counts as taken if anything answers on 127.0.0.1 or ::1, or it cannot be bound; then a free port is used. After start, the same readiness check as `refapp/serve.py`: our process alive, HTTP answers, and lsof shows our PID listening. A lost race falls back to a free port (3 attempts). The audit itself uses 127.0.0.1 URLs; the printed URLs use `localhost`, as asked.
- **State file** `runs/demo_live/.active_demo.json` (seed, theme, site, started, tmp, report, real/clone pid, port, url), written atomically after success.
- **`make end-demo`** (`gen/active.py end`) signals a PID only if its command line contains the demo's temp dir, because PIDs are reused after a reboot. It sends SIGTERM, then SIGKILL after 5 s, and runs `pkill -f <tmp>/` as a backstop. It deletes the temp dir only if it is named `ffdemo.*`, removes the state file, and never touches reports. With no state file it prints "No active demo." and exits 0, so it is idempotent. `make demo` calls it first if a state file exists.
- **`make demo-status`** checks each server is ours and answers before calling it "up", so a stale state file after a reboot shows "NOT RESPONDING" and points to `make end-demo`.
- **Not changed:** scoring, the generator's defects, Harbor Air, `make demo-classic`. The noise check in the gate still uses `refapp/serve.py` (servers scoped to the audit).
