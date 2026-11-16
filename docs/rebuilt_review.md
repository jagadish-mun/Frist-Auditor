# Hand review: screenshot-rebuilt clone vs real Harbor Air

Run: `python validate.py` (job `rebuilt`, output then at `runs/validation/rebuilt/`), 2026-11-12, macOS, **scoring v1** (the default at the time). Under scoring v2 (Task 3) the same clone scores 0.997 with 0/0/7 gaps: the ±3px shift tolerance removes 7 of these 14 low gaps; all 7 that remain are on this list. Rebuilt clone: `refapp/clone_rebuilt/app.py`
(written from screenshots and user-visible observations only, see DECISIONS.md D2).

**Result:** score 0.984 (visual 0.892, elements 1.000, behavior 1.000, flows 1.000); gaps high/med/low = **0/0/14**.

There were no high or medium gaps to label, so every low gap was reviewed instead (by looking at the heatmaps in
`runs/validation/rebuilt/shots/heat_*.png`, the paired crops, and the element/text box offsets measured with `tools/observe.py`).

## Labels

"Real cosmetic difference" = the clone really does render differently there (verified in the heatmap/crops); "false alarm" =
no actual difference (noise). "Would mislead an agent" = my judgment of whether it could change what a computer-use agent does.

| Gap | Page | Viewport | Severity | Size | What actually differs | Label | Would mislead an agent? |
|---|---|---|---|---|---|---|---|
| gap-001 | /results | mobile | low | 6 region(s), 16.2% of page pixels changed | Flight-row text 0–6px offsets; mobile card internal spacing differs (price/Select row) | real cosmetic difference | no |
| gap-002 | / | mobile | low | 12 region(s), 13.9% of page pixels changed | Hero gradient angle differs; form label/field text 0–3px offsets; card text sub-pixel offsets; mobile cards 3–7px higher (card gap) | real cosmetic difference | no |
| gap-003 | /fares | mobile | low | 15 region(s), 10.5% of page pixels changed | 'Flight HA101 ·' text 6px narrower; card paragraph/footer 0–3px offsets | real cosmetic difference | no |
| gap-004 | /review | mobile | low | 8 region(s), 5.8% of page pixels changed | Back/Pay buttons and footer 4–5px lower (summary card height) | real cosmetic difference | no |
| gap-005 | / | desktop | low | 21 region(s), 4.9% of page pixels changed | Hero gradient angle differs; form label/field text 0–3px offsets; card text sub-pixel offsets | real cosmetic difference | no |
| gap-006 | /review | desktop | low | 8 region(s), 2.9% of page pixels changed | Back/Pay buttons and footer 4–5px lower (summary card height) | real cosmetic difference | no |
| gap-007 | /results | desktop | low | 14 region(s), 2.7% of page pixels changed | Flight-row text 0–6px offsets; footer 1px | real cosmetic difference | no |
| gap-008 | /fares | desktop | low | 15 region(s), 2.2% of page pixels changed | 'Flight HA101 ·' text 6px narrower; card paragraph/footer 0–3px offsets | real cosmetic difference | no |
| gap-009 | /checkin | mobile | low | 5 region(s), 0.8% of page pixels changed | Nav link text offset (desktop: link spacing within ±1px; mobile: link row ±1–5px); plus sub-pixel text rendering | real cosmetic difference | no |
| gap-010 | /passenger | mobile | low | 4 region(s), 0.7% of page pixels changed | Nav link text offset (desktop: link spacing within ±1px; mobile: link row ±1–5px); plus sub-pixel text rendering | real cosmetic difference | no |
| gap-011 | /help/baggage | mobile | low | 3 region(s), 0.5% of page pixels changed | Nav link text offset (desktop: link spacing within ±1px; mobile: link row ±1–5px); plus sub-pixel text rendering | real cosmetic difference | no |
| gap-012 | /checkin | desktop | low | 5 region(s), 0.2% of page pixels changed | Nav link text offset (desktop: link spacing within ±1px; mobile: link row ±1–5px); plus sub-pixel text rendering | real cosmetic difference | no |
| gap-013 | /passenger | desktop | low | 4 region(s), 0.2% of page pixels changed | Nav link text offset (desktop: link spacing within ±1px; mobile: link row ±1–5px); plus sub-pixel text rendering | real cosmetic difference | no |
| gap-014 | /help/baggage | desktop | low | 3 region(s), 0.1% of page pixels changed | Nav link text offset (desktop: link spacing within ±1px; mobile: link row ±1–5px); plus sub-pixel text rendering | real cosmetic difference | no |

**Summary:** 14/14 gaps are real (if small) rendering differences; **0 false alarms** in the sense of noise. All 14 are correctly
rated low. None would plausibly change agent behaviour (no label, target or element is different).

## Planted defects on top of this clone

From the same `validate.py` run (jobs `rebuilt_rb_*`, `rebuilt_all4`): 4/4 planted defects detected, and **every one of the 6
high/medium gaps across those runs is a true positive** for the planted defect (see VALIDATION.md §6). High/medium false-alarm
rate measured here: 0/6.

## What the auditor did *not* report (differences I know exist)

Because I wrote the clone, I know of differences the audit could not or did not surface:

1. **The 'Fall sale' banner** is one text node in the clone but split into spans on the real site. The price regex mask then covers
   the whole banner on the clone side, so any difference inside it is invisible. Masking can hide real differences.
2. **Behaviour I could not observe safely is unverified on both sides**: 'Pay' (skipped by design), and whether 'Sort by' reorders
   rows (no URL change; I did not check order). The clone's Pay is an inert button. The auditor reports nothing here, which is
   correct given its rules but means "behavior 1.000" covers only clickables it exercised.
3. **Hero gradient angle** was guessed; it shows up only as part of a low visual gap, not as its own ticket.

## Caveats

- One clone, built by one builder (me) who iterated against observed element boxes for three rounds. A typical agent-built clone
  will likely be rougher; this is closer to a careful rebuild than to a first draft.
- The rebuild was not tuned against auditor output (only against tools/observe.py measurements of the real site).
- This clone scores 0.984, **below clone_high (0.995)**, which contains a real label error. This repeats the calibration problem
  (SPEC §14) on an independent clone rather than the synthetic `subtle_drift` toggle.
