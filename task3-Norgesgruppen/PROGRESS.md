# Progress Report: NorgesGruppen Object Detection (Task 3)

## 0. Latest Session Update (2026-03-21, Saturday ~23:55 Oslo)

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

## 0.1 Historical Baseline Imported (Stale Until Re-Verified)

- Last known historical Task 3 status from prior AGENT notes:
  - score `0.1786` mAP
  - rank `#157`
  - ONNX-based submission (`run.py` + `best.onnx`)
  - likely error source hypothesis: ONNX output parsing/classification mismatch
- Important:
  - this baseline was not actively maintained after Friday morning and must be re-verified before using as current truth.

## 1. Next Actions

1. Re-verify current Task 3 score/rank and submission quota with exact timestamp.
2. Run a bounded inference-correctness pass (output decoding + category mapping + post-processing validation).
3. Prepare one controlled submission candidate and log it in `PastSubmissions.md`.
4. Keep changes in a fresh PR and preserve rollback path.
