# Talk track: Clone Fidelity Auditor (10 minutes)

For Frist employees. Seven sections, following `docs/PRESENTATION_NOTES.md`. Each section says what to show on screen, what to say, and the one number to land. Before starting, run `make demo-classic` once so both reports exist (`runs/demo_live/clone_mid/iter_00` and `iter_01`).

## 1. The problem (1 min)

**Show:** the real Harbor Air fares page next to the clone_mid fares page.

**Say:** "These look the same. The clone calls the Core fare 'Main', its Fare rules button does nothing, and a nav link is missing. An agent trained here learns a site that doesn't exist. Today we catch this by eye. This tool catches it automatically and gives you a ticket for each difference."

**Key number:** one audit covers 7 pages, 2 screen sizes and 3 flows in about 18 seconds.

## 2. The four layers (1 min)

**Show:** the top of `runs/demo_live/clone_mid/iter_00/report.html`: layer bars and the ticket counts.

**Say:** "Four checks. Visual compares screenshots and ignores shifts of a few pixels. Elements matches every link, button and field by role, name and position. Behaviour clicks each control on both sites, including select options and buttons inside dialogs. Flows replays whole tasks, like booking up to the Pay button, which it never clicks. Every difference becomes a ticket with a screenshot from each site."

**Key number:** clone_mid gets 2 high and 5 medium tickets.

## 3. How we validated it (2 min)

**Show:** the table in section 3 of the presentation notes.

**Say:** "First, noise: the real site against itself gives zero tickets, three runs in a row. Then planted defects: 14 of 14 found in the real app, 4 of 4 in a clone I rebuilt from screenshots. Those I designed myself, so the honest test is the next row. A separate agent wrote 10 defects I never saw, and they were frozen in git before anything ran. The tool found 9 of 10 on both clone types. Then a separate agent built a whole clone in three minutes. I read every ticket by hand: all real differences. Across held-out and draft, not one high or medium ticket was a false alarm. One blind spot: a faint colour tint it doesn't see at all."

**Key number:** 9 of 10 unseen defects found; 0 high/medium false alarms.

## 4. What we learned: the single number doesn't predict agent success (2 min)

**Show:** `docs/img/correlation_final.png`, then the diagnosis table in `docs/CORRELATION_DIAGNOSIS.md`.

**Say:** "We wanted the number to predict how well an agent trained on the clone does on the real site. We tested it with two scripted agents and 14 tasks. On the tasks that don't overlap the audit's own flows, the correlation is between 0.1 and 0.3 and statistically indistinguishable from zero. We dug into why. Only 19 of 315 clone-task pairs have a defect on something the task actually uses. Agents succeed 93 to 95 percent of the time anyway. And when a defect *is* on the task's path, the task fails in 16 of 19 cases. So the information is there, but averaging every difference into one number throws it away. That's why the report now calls the number an audit-coverage summary, not a predictor."

**Key number:** only 19 of 315 pairs have a defect on the task's path.

## 5. What does work: read the tickets per task (1.5 min)

**Show:** the table in section 5 of the notes.

**Say:** "So we turned it around. Record once what each task clicks and fills on the real site. Then predict that the task fails on a clone if the audit has a serious ticket on one of those elements. I wrote this rule before seeing the diagnosis numbers, tuned it only on the original clones, and froze it in git before running it on the held-out clones. On the held-out clones it predicts the coordinate agent's failures with F1 0.91 and the name-based agent's with 1.00. The clone-level number gets about 0.1. That's the claim I'd make to you: specific tickets predict specific task failures."

**Key number:** F1 0.91 and 1.00 on held-out clones, against about 0.1 for the score.

## 6. The demo (1.5 min)

**Show:** run `make demo` live (about 25 s, see "Live demo" below), then open the two prepared `make demo-classic` reports side by side.

**Say:** "One command: start the real site and a clone, audit, fix the top ticket, audit again. The top ticket is the broken Fare rules button. After one fix the high tickets go from 2 to 1 and the summary from 0.635 to 0.800. Here is a grouped ticket: several links moved together because one nav item disappeared, so it's one ticket, not four. And this is gaps.json: each ticket names its element or flow step, which is what the per-task prediction reads."

**Key number:** 0.635 → 0.800 after one fix; four fixes take it to 0.997.

### Live demo (`make demo`)

**What each run does:** picks a random seed (printed on screen; `SEED=<n> make demo` replays it), generates a brand-new small site (airline, grocery or bank) and a clone of it with 4–6 hidden planted defects, at least one element, behaviour, flow-breaking and visual-only. It audits the clone and prints a scorecard: planted, found, missed, extra tickets. The report opens from `runs/demo_live/<timestamp>_seed<N>/`, and the real site (http://localhost:8101) and clone (http://localhost:8102) open next to it and **stay up** for clicking around during questions, even if the terminal is closed. `make demo-status` shows what is running; `make end-demo` stops both and deletes the generated sites (the report stays). A second `make demo` ends the first automatically.

**Click-through to try:** open the ticket at the top of the report, then the same page on both sites. For example, a dead button: click it on 8101 (a dialog opens) and on 8102 (nothing happens).

**Say:** "This site didn't exist a minute ago, and the auditor has never seen it. The generator hid some defects in the clone and wrote down what they were; the scorecard checks the tickets against that list."

**Caveat (say it):** "The clone comes from the same generator, so the only differences are the planted ones. This shows the auditor finds known differences on an unseen site. It doesn't show how it copes with a messy real rebuild; that's what the rebuilt and first-draft clones in the validation are for."

**If it fails live:** run `make demo-classic`, or `SEED=<a seed from the gate> make demo`. A failed or interrupted run cleans up after itself. **After the talk:** `make end-demo`.

## 7. Next steps (1 min)

**Show:** section 7 of the notes.

**Say:** "Everything I've shown runs on one fictional site with scripted agents. Two things would turn it into something you can rely on. First, a real clone and its real site from you, so we can count false alarms in practice. Second, your real agents on your real tasks, to see whether per-task tickets predict their failures the way they predict these proxies'. If they do, every clone audit can come with a list of which tasks it will break."

**Key number:** asking for 1 real clone pair and 1 real agent run.

## If asked

- **"Why not just use the score?"** Section 4: it averages relevant and irrelevant differences. Use the tickets for the tasks you care about.
- **"How do you know the held-out test is fair?"** The defects were written by a separate agent that saw only the app code, and committed before any run. Scoring v3 and the predictor were each committed before their first held-out run. One leak: I knew the ten defect categories.
- **"What breaks it?"**
  - faint colour changes;
  - pages and controls not in the config;
  - a ticket on an element a task only *reads* (the "Core" heading next to the button it clicks);
  - a renamed button breaks any task whose success is defined by that name, even for an agent that clicks by position; the predictor misses that case (2 of its 4 held-out errors).
- **"Is it stable?"** Three full runs in a row gave identical results. Every retry is counted in the report. One early crash on day one was never explained.
- **"Which scoring version?"** v3 by default, because its moved-button tickets explain the coordinate agent's failures (F1 0.91 vs 0.62 with v2 tickets). v1 and v2 are one config line away.
