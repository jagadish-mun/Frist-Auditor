# Clone Fidelity Auditor: one-page summary

**What it is.** A tool that compares a cloned website with the real one (screenshots, elements, click behaviour, multi-step flows) and lists every difference as a ticket with screenshots from both sites, in about 18 seconds. Validated on a self-hosted fictional airline site. Demo: `make demo`.

**Five key numbers**
1. **0 tickets** for the real site audited against itself, 3 runs out of 3 (`python validate.py`).
2. **9/10** held-out defects found on each of two clone types; a separate agent wrote them, frozen before any audit (`python validate.py --heldout`).
3. **0** high/medium false alarms on the held-out set and an agent-made first-draft clone (hand-checked).
4. **ρ ≈ 0.1–0.3, not significant:** the overall 0–1 number does not predict scripted agents' success on tasks independent of the audit's flows, because most defects are off the task's path (`docs/CORRELATION_DIAGNOSIS.md`).
5. **F1 0.91 [0.79, 0.98] (n = 22 failures) and 1.00 (n = 14; recall 95% CI 0.77–1.00):** on held-out clones, tickets on a task's path predict which tasks two agents fail, against about 0.1 for the overall number; predictor frozen before its held-out run (`docs/TASK_PREDICTION.md`).

**Three caveats**
1. **One fictional site.** Nothing has run on a real Frist clone yet; that is the next step we are asking for.
2. **Scripted proxy agents** on 14 short tasks, not RL or LLM agents. Tickets predict these agents' failures, not what a learning agent learns.
3. **Blind spots.** Faint colour-only changes go unreported. The single number is an audit-coverage summary, not a measure of training value.
