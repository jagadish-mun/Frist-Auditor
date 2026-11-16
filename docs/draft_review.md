# Hand review: independent first-draft clone vs real Harbor Air

Clone: `refapp/clone_draft/app.py`. It was written by an isolated subagent from `tools/observe.py` output only, in about 3 minutes, without rendering it in a browser (DECISIONS D17). Command: `python validate.py --draft --scoring v3,v2,v1` (2026-11-13, macOS). Raw: `runs/validation_draft/`, `docs/draft_results.json`.

| Scoring | Score | Visual | Elements | Behavior | Flows | High/Med/Low |
|---|---|---|---|---|---|---|
| v3 | 0.819 | 0.946 | 1.000 | 0.952 | 0.667 | 1/1/14 |
| v2 | 0.819 | 0.946 | 1.000 | 0.952 | 0.667 | 1/1/14 |
| v1 | 0.867 | 0.799 | 1.000 | 0.988 | 0.667 | 1/1/14 |

Regenerated after Task 11 (selects and dialog buttons now exercised): v3 0.820, v2 0.820, v1 0.867, behavior 0.956 under v2/v3; same 1/1/14 gaps. The table above is the original Task 9 run.

v3 equals v2 here: no interactive element on the draft moved more than 20px. The gap lists are the same in all three versions; only the visual changed-pixel percentages differ.

## High and medium gaps (all labelled)

| Gap | Severity | Text (abridged) | Label | Notes |
|---|---|---|---|---|
| gap-001 | high | Flow 'fare_rules' diverges at step 1: real shows dialog 'fare rules', clone shows dialog 'fare rules changes allowed on core and…' | **real difference, severity overstated** | Verified in the browser: the real dialog has `aria-label="Fare rules"` and the draft's has none (no accessible name). The visible content is identical. A vision agent sees no difference; an agent that looks up `dialog "Fare rules"` by role and name fails. That is real, but "high" (the same as a broken flow) is too strong. |
| gap-002 | medium | Button 'Fare rules': opens dialog 'fare rules' on real, dialog 'fare rules changes allowed…' on clone | **real difference (same root cause as gap-001)** | One root cause produces two tickets. |

## Low gaps

There are only 14 low gaps, so instead of a random sample of 15, all 14 were labelled. I used the real/clone crop pairs (`crops/gap-*_{real,clone}.png`).

| Gap | Page / viewport | What differs | Label |
|---|---|---|---|
| gap-003 | / mobile | hero form fields and Search button ~4px higher | real cosmetic |
| gap-004 | /results mobile | Modify search / price row offset; price font smaller | real cosmetic |
| gap-005 | /review mobile | summary card line spacing and position | real cosmetic |
| gap-006 | / desktop | hero form row a few px higher | real cosmetic |
| gap-007 | /review desktop | summary card line spacing | real cosmetic |
| gap-008 | /help/baggage mobile | footer ~10px higher | real cosmetic |
| gap-009 | /fares mobile | heading / Fare rules row offset | real cosmetic |
| gap-010 | /results desktop | footer offset | real cosmetic |
| gap-011 | /checkin mobile | 'Find trip' button bolder/larger | real cosmetic |
| gap-012 | /passenger mobile | 'Continue' button bolder/larger | real cosmetic |
| gap-013 | /help/baggage desktop | footer offset | real cosmetic |
| gap-014 | /fares desktop | heading / Fare rules row offset | real cosmetic |
| gap-015 | /checkin desktop | 'Find trip' button bolder/larger | real cosmetic |
| gap-016 | /passenger desktop | 'Continue' button bolder/larger | real cosmetic |

## False-alarm rate by severity

| Severity | Gaps | False alarms (no real difference) | Real but severity overstated |
|---|---|---|---|
| high | 1 | 0 | 1 |
| medium | 1 | 0 | 0 |
| low | 14 (all reviewed) | 0 | 0 |

**Reading:** no gap on the draft is noise. The weakness is severity calibration, not detection. A missing accessible name on a dialog costs the draft about 0.12 under v2/v3: one high gap (×0.95), one medium gap (×0.98), and the flows layer drops to 0.667 because one of three flows "diverges". That puts a visually close, functionally complete first draft (0.819) in the range of clone_mid. This is the opposite of the Phase 1 drift problem: a semantic-only difference is now scored like a broken flow. Task 10's agent results test whether that matters to agents.

**Also not seen by the auditor:** the draft's Sort by select does nothing (the real one is not checked either). Behaviour exploration doesn't exercise selects (Task 11).

## After Task 15 (accessibility-name label, DECISIONS D27)

Command: `python validate.py --draft`. The dialog-name difference is now a single ticket, "Accessibility-name mismatch", severity **medium** (was one high flow ticket plus one medium behaviour ticket). Scores: v3 0.863, v2 0.863, v1 0.867; gaps 0 high / 1 medium / 14 low. The flows layer still counts the divergence (0.667).
