# Held-out validation

The defects in `refapp/heldout_defects.py` were written by an isolated subagent that saw only the two app files (DECISIONS D14). They were frozen in commit `2900434` before any audit ran on them. Scoring v3 was coded and committed (`d01edb3`) before the first held-out run.

## Task 7: scoring v2 on the held-out set (the generalisation numbers)

Command: `python validate.py --heldout --scoring v2` (184 s). Raw output: `runs/validation_heldout/RESULTS.md`.


| Defect | Kind | Template: score | detected | unexpl. high/med | Rebuilt: score | detected | unexpl. high/med |
|---|---|---|---|---|---|---|---|
| ho_move_fare_rules | moved | 0.999 | yes | 0 | 0.996 | yes | 0 |
| ho_move_find_trip | moved | 0.989 | yes | 0 | 0.989 | yes | 0 |
| ho_relabel_checkin_nav | relabel | 0.789 | yes | 1 | 0.816 | yes | 1 |
| ho_relabel_modify_search | relabel | 0.974 | yes | 0 | 0.971 | yes | 0 |
| ho_missing_help_footer | missing | 0.920 | yes | 0 | 0.917 | yes | 0 |
| ho_select_skips_fares | wrong link | 0.833 | yes | 0 | 0.829 | yes | 0 |
| ho_continue_dead | dead button | 0.898 | yes | 0 | 0.894 | yes | 0 |
| ho_checkin_wrong_action | broken submit | 0.893 | yes | 0 | 0.890 | yes | 0 |
| ho_extra_baggage_calc | extra | 0.953 | yes | 0 | 0.953 | yes | 0 |
| ho_promo_tint | cosmetic | 1.000 | **no** | 0 | 0.997 | **no** | 0 |

- Recall: template **9/10**, rebuilt **9/10** (pass ≥ 80%).
- Noise (real vs real ×3): scores 1.000, 1.000, 1.000; gaps 0.
- High/medium gaps not explained by the planted defect: template 1, rebuilt 1.
- Ordering: defect clone scores below its no-defect baseline: template 9/10, rebuilt 9/10 (rebuilt baseline 0.997).
- Ordering: functional defect scores below the cosmetic-only defect: template 9/9, rebuilt 9/9 pairs.

Wall time 184.0 s.

### Hand reading of the anomalies

- **The 1 "unexplained" high gap per clone is a true positive.** Relabelling the nav "Check in" link breaks the `check_in` flow at step 1 ("could not click link 'Check in'"). The subagent's `expect` list didn't include that flow consequence. **False alarms: 0** on both clones.
- **The cosmetic tint is missed by v2.** The template clone scores 1.000 with no gaps.
  - The first run reported the rebuilt-clone version as "detected". That was an evaluator artefact: its 7 gaps are identical to the no-defect rebuilt run, and the visual-only expectation ("any visual gap on /") matched pre-existing rebuild noise.
  - The evaluator now requires a detection to be a gap absent from the no-defect baseline (DECISIONS D15). With that, rebuilt recall is 9/10.
- **The moved click targets are detected but barely scored.** The two ≥40px moves score 0.999 and 0.989 (template), almost the same as no defect. This is the Phase 1 layout-shift weakness again, on unseen defects.
- **The "functional below cosmetic 9/9" ordering is hollow,** because the cosmetic defect wasn't detected at all (score 1.000).

### Process note
The first held-out run wrote its audit folders into `runs/validation/v2/`, because worker processes didn't see the reassigned output directory. This overwrote the gitignored `noise_*` and `rebuilt` run folders there. It is fixed: the output dir is passed explicitly. The committed copies in `docs/` were unaffected, and the numbers above come from the clean rerun.

## Task 8: v3 vs v2 vs v1 on the held-out set

Command: `python validate.py --heldout --scoring v3,v2,v1`. v3 was committed (`d01edb3`) before any held-out run and was not changed after.

| Defect | Kind | v3 template | v2 template | v1 template | v3 rebuilt | v2 rebuilt | v1 rebuilt |
|---|---|---|---|---|---|---|---|
| ho_move_fare_rules | moved | 0.979 | 0.999 | 0.999 | 0.976 | 0.996 | 0.983 |
| ho_move_find_trip | moved | 0.912 | 0.989 | 0.996 | 0.912 | 0.989 | 0.980 |
| ho_relabel_checkin_nav | relabel | 0.758 | 0.789 | 0.843 | 0.783 | 0.816 | 0.866 |
| ho_relabel_modify_search | relabel | 0.974 | 0.974 | 0.998 | 0.971 | 0.971 | 0.982 |
| ho_missing_help_footer | missing | 0.902 | 0.920 | 0.973 | 0.898 | 0.917 | 0.957 |
| ho_select_skips_fares | wrong link | 0.833 | 0.833 | 0.921 | 0.829 | 0.829 | 0.905 |
| ho_continue_dead | dead button | 0.898 | 0.898 | 0.976 | 0.894 | 0.894 | 0.960 |
| ho_checkin_wrong_action | broken submit | 0.893 | 0.893 | 0.971 | 0.890 | 0.890 | 0.955 |
| ho_extra_baggage_calc | extra | 0.897 | 0.953 | 0.992 | 0.897 | 0.953 | 0.976 |
| ho_promo_tint | cosmetic | 1.000 (missed) | 1.000 (missed) | 1.000 (missed) | 0.997 (missed) | 0.997 (missed) | 0.984 (missed) |

| Aggregate | v3 | v2 | v1 |
|---|---|---|---|
| Recall template / rebuilt | 9/10 / 9/10 | 9/10 / 9/10 | 9/10 / 9/10 |
| Noise gaps (3 runs) | 0 | 0 | 0 |
| High/med gaps not in the defect's expect list (template / rebuilt) | 10 / 10 | 1 / 1 | 1 / 1 |
| Mean score of the two ≥40px moves (template) | 0.946 | 0.994 | 0.998 |

**Hand reading of v3's extra unexplained gaps (20 in total):** every one is a "click target moved" medium gap on an element *displaced by* the planted defect. Examples:
- the footer links move 55–60px when content above them grows (`ho_extra_baggage_calc`, `ho_move_find_trip`);
- 'Baggage info' moves 94px when 'Help centre' is removed;
- the nav links move 45px when 'Check in' is relabelled to a different width.

Each is a real change in where an agent must click, so **false alarms remain 0**. The cost is ticket inflation: one root cause becomes up to 3 extra tickets and 3 extra penalties. A root-cause grouping of moved elements would fix this (next steps).

**Still missed by all three versions:** the cosmetic tint `ho_promo_tint`. Its colour change stays under the per-pixel threshold, and v1's SSIM does not catch it either.

## Regenerated after Task 11 (behaviour layer now also exercises selects and dialog buttons)

Command: `python validate.py --heldout` (v3, v2, v1), 2026-11-13. Data: `docs/heldout_results.json`. Individual scores moved by at most a few thousandths; the conclusions above are unchanged.

| Aggregate | v3 | v2 | v1 |
|---|---|---|---|
| Recall, template / rebuilt | 9/10 / 9/10 | 9/10 / 9/10 | 9/10 / 9/10 |
| Noise gaps (3 runs) | 0 | 0 | 0 |
| High/med gaps not in the expect lists, template / rebuilt | 10 / 10 | 1 / 1 | 1 / 1 |
| Mean score of the 10 template clones | 0.905 | 0.925 | 0.967 |
| The two ≥40px moves (template) | 0.979, 0.912 | 0.999, 0.989 | 0.999, 0.996 |

## After Task 15 (grouped moved-target tickets, flaky-click re-measurement)

Command: `python validate.py --heldout`. Recall unchanged: 9/10 template, 9/10 rebuilt, for every version; 0 noise gaps. High/medium tickets not in the expect lists, v3: 4 per clone type (was 10). All are real: one flow break caused by the nav relabel, and three knock-on moves, each now a single ticket (for example, "3 click targets moved together ~55px down (one layout change): 'About us', 'Help centre', 'Baggage info'"). Total tickets across the 20 held-out clones, v3: 169 → 157; moved-target tickets 22 → 10.
