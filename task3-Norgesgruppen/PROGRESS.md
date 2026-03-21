# Progress Report: NorgesGruppen Object Detection (Task 3)

## 0. Documentation Sync Contract (Mandatory)

- `AGENT.md` and `PROGRESS.md` must be reviewed and updated together in the same commit whenever either file changes.
- Timestamped leaderboard evidence must be appended when baseline status changes.
- Before ending a Task 3 session, docs updates must be pushed to GitHub to avoid local-only data loss.

## 1. Latest Session Update (2026-03-22, Sunday 00:02 Oslo)

- Leaderboard checkpoint recorded from operator-shared overall screenshot.
- `OBSERVED`: Team row shows rank `#273`.
- `OBSERVED`: Overall columns shown were `Detection 19.3`, `Tripletex 31.8`, `Astar Island 54.5`, `Total 35.2`.
- `DECISION`: Preserve this checkpoint in Task 3 documentation to maintain cross-task context while prioritizing Task 3 score recovery.

## 1.1 Task 3 Baseline Re-Verification (2026-03-21, Saturday 22:48 Oslo)

- `OBSERVED`: Task 3 score `0.1786` mAP.
- `OBSERVED`: Task 3 rank `#301` out of `313` teams with points.
- `OBSERVED`: Task 3 submission count shown was `1`.
- `INFERRED`: Previously imported `#157` rank is stale historical context.

## 1.2 Documentation Hardening Update (2026-03-21, Saturday ~23:55 Oslo)

- Refactored Task 3 handoff documentation for cross-session reliability.
- Rewrote `task3-Norgesgruppen/AGENT.md` to add generic workflow protections proven in Task 1/2:
  - new PR per follow-up
  - start-of-session branch freshness check
  - required read order
  - no long blocking loops
  - explicit "wait with submit" rule
  - secret hygiene and date-stamped status discipline
- Added `task3-Norgesgruppen/PastSubmissions.md` as durable memory for submission outcomes and hypotheses.
- Established required workflow: append new submission evidence to `PastSubmissions.md` before/after each submission cycle.
- No runtime code changes in this session; documentation/process hardening only.

## 1.3 Historical Baseline Imported (Stale Until Re-Verified)

- Last known historical Task 3 status from prior AGENT notes:
  - score `0.1786` mAP
  - rank `#157`
  - ONNX-based submission (`run.py` + `best.onnx`)
  - likely error source hypothesis: ONNX output parsing/classification mismatch
- Important:
  - this baseline was not actively maintained after Friday morning and must be re-verified before using as current truth.

## 2. Next Actions

1. Run a bounded inference-correctness pass (output decoding + category mapping + post-processing validation).
2. Prepare one controlled submission candidate and log it in `PastSubmissions.md`.
3. Re-check daily quota/in-flight availability immediately before submitting.
4. Keep changes in a fresh PR and preserve rollback path.
