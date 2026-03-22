# Task 3 Retrospective (NorgesGruppen Data)

## Why this file exists
This README is a human-readable wrap-up of our Task 3 journey.
It explains what we did, what worked, what failed, and what we learned.

This was written after the competition submission window was over for us.

## Final outcome
- Final Task 3 score: `0.8818`
- Final runtime: `18.0s`
- Final artifact: `submission_task3_overnightA_conf004_iou060.zip`
- Final row time in UI: `22. mars 11:37 — 22. mars 11:37`
- Daily quota status at end: `0 of 6 submissions remaining`

## Repository note (post-competition)
- This repository stores source code and documentation for reproducibility.
- The final competition zip artifact itself is not committed because it is larger than the standard GitHub file-size limit.
- The tracked `task3-Norgesgruppen/run.py` is synchronized to the final best-scoring submission settings (`CONF_THRESHOLD=0.04`, `IOU_THRESHOLD=0.60`, class-aware NMS).

## Starting point vs end point
- Early verified baseline (2026-03-21 22:48): `0.1786` (rank around #301/313 on task board at that time).
- End state (2026-03-22 11:37): `0.8818`.

The biggest practical takeaway: we did not win by one magic trick. We won by combining reliability work, disciplined experiments, and one high-upside training jump.

## What we actually did
### 1) Fixed inference reliability first
We focused on `run.py` correctness before chasing tuning:
- robust ONNX output decoding,
- letterbox-aware scaling,
- class-aware NMS,
- strict JSON schema-safe output.

This moved us from a very weak baseline to a stable competitive baseline.

### 2) Switched to bounded experiments
After getting stable inference, we changed one variable at a time for each submission pass:
- confidence threshold,
- IoU threshold,
- NMS mode.

This made results explainable and rollbacks easy.

### 3) Spent compute on a high-upside model upgrade
We ran a larger overnight retraining track on GCP.
That gave the biggest single phase jump (`0.7780 -> 0.8621`), then post-processing sweeps pushed further (`0.8798`, `0.8808`, `0.8818`).

### 4) Kept a safe baseline while taking risks
Before each aggressive attempt, we preserved the current best final row.
That allowed us to take a high-variance final shot without risking total regression.

## What went wrong (important)
1. Some early context was stale.
- Old score/rank references can mislead priorities if not re-verified.

2. Offline proxy improvements did not always transfer.
- Example: one NMS change looked better offline but scored lower on leaderboard.

3. Environment quirks created friction.
- VM ONNX CUDA provider mismatch (local VM validation used CPU fallback).
- PyTorch 2.6 `weights_only` behavior affected Ultralytics post-processing (`strip_optimizer`) even though training itself finished.

4. Local-only documentation was risky.
- When notes are not pushed, continuity and handoff quality drop.

5. Submission quota pressure changes strategy.
- With few attempts left, low-upside tweaks become expensive.

## What helped us improve fastest
1. Reliability before optimization.
2. One-variable submissions.
3. Explicit hypothesis + rollback per attempt.
4. Immediate logging of evidence with timestamps.
5. High-upside compute when the baseline was already stable.

## What we learned about using markdown files

### What we did right
- `AGENT.md` gave clear operating rules and guardrails.
- `PROGRESS.md` captured a chronological execution story.
- `PastSubmissions.md` stored per-submission memory with outcomes.
- Using `OBSERVED / INFERRED / DECISION` reduced confusion between facts and opinions.

This was a strong setup, especially for a first serious agentic workflow.

### What we can improve next time
- Keep `AGENT.md` more stable (rules/playbook), and avoid too much timeline detail there.
- Keep `PROGRESS.md` append-only and strictly chronological.
- Keep `PastSubmissions.md` focused on experiment entries and outcomes.
- Add a short "Current Snapshot" section near the top of `PROGRESS.md`:
  - current best score,
  - last verified timestamp,
  - remaining quota,
  - next recommended action.
- Archive older long logs periodically (`archive/`) to keep active docs lightweight.
- Push doc updates sooner to avoid local-only state.

## General advice for future AI-assisted projects
1. Start each session by confirming freshness (`origin/main`, merge status, latest truth).
2. Ask AI for one bounded next step, not ten ideas.
3. Require evidence and verification before trusting suggestions.
4. Keep a rollback path for every risky change.
5. Make each experiment teach you something reusable.

## Suggested read order for this folder
1. `AGENT.md`
2. `PROGRESS.md`
3. `PastSubmissions.md`
4. this `README.md`

## Closing note
This task started rough and ended strong. The biggest improvement was not just the score, but the process quality: we became more deliberate, more evidence-driven, and better at making AI collaboration reliable under pressure.
