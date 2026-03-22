# PastSubmissions.md — Task 3 Submission Memory

## 1. Purpose
This file preserves Task 3 submission knowledge across sessions.

Use it to track:
- what was submitted,
- what changed,
- what the hypothesis was,
- what the outcome was,
- and what to do next.

Goal: any new session can recover the latest high-confidence direction in under 2 minutes.

## 2. Evidence Tags (Strict)
- `OBSERVED`: direct fact from UI/log/output.
- `INFERRED`: reasoned interpretation from evidence.
- `ASSUMPTION`: unresolved but necessary working assumption.
- `DECISION`: chosen next action.

## 3. Update Protocol
For every submission cycle:
1. Add or update an entry before submission with hypothesis + exact artifact.
2. Add outcome after scoring/feedback with timestamp.
3. Record whether hypothesis was supported or falsified.
4. Keep old entries; append corrections rather than rewriting history.

## 4. Submission Log

### Entry T3-BASELINE-001
- Date window: Friday morning context (exact timestamp unknown)
- `OBSERVED`: Score approximately `0.1786` mAP.
- `OBSERVED`: Rank approximately `#157`.
- `OBSERVED`: Submission package used ONNX flow (`run.py` + `best.onnx`).
- `INFERRED`: Main score gap likely from ONNX output parsing/classification mismatch.
- `ASSUMPTION`: This baseline may be stale now and must be re-verified before guiding major decisions.
- `DECISION`: Re-verify current score/rank and reproduce one deterministic inference sample before next submission.

### Entry T3-BASELINE-002
- Timestamp: `2026-03-21 22:48` (Oslo)
- Evidence source: operator-shared Task 3 leaderboard screenshot
- `OBSERVED`: Score `0.1786` mAP.
- `OBSERVED`: Rank `#301` out of `313` teams with points.
- `OBSERVED`: Submission count shown as `1`.
- `INFERRED`: Earlier `#157` baseline is stale historical context, not current standing.
- `DECISION`: Prioritize inference-correctness fixes (ONNX decode + class mapping + post-processing) before consuming another submission.

### Entry T3-CHECKPOINT-003
- Timestamp: `2026-03-22 00:02` (Oslo)
- Evidence source: operator-shared overall leaderboard screenshot
- `OBSERVED`: Team row shows rank `#273`.
- `OBSERVED`: Overall columns shown were `Detection 19.3`, `Tripletex 31.8`, `Astar Island 54.5`, `Total 35.2`.
- `INFERRED`: Task 3 remains a primary drag on overall placement and should be prioritized for rapid score recovery.
- `DECISION`: Keep Task 3 docs synchronized and GitHub-pushed each session to avoid losing baseline/evidence state.

### Entry T3-CANDIDATE-004
- Timestamp: `2026-03-22 00:42` (CET, Oslo)
- Evidence source: direct VM run logs + local artifact verification
- `OBSERVED`: Implemented new `run.py` inference pipeline with letterbox-aware scaling + class-aware NMS + bbox clipping + JSON schema-safe output.
- `OBSERVED`: VM smoke run on `12` images completed in `8s`; schema check reported `bad_records 0`.
- `OBSERVED`: VM full dry run on `248` images completed in `45s` and produced `23,956` predictions.
- `OBSERVED`: Guarded artifact built and verified:
  - VM path: `~/submission_task3_guarded.zip`
  - Local path: `task3-Norgesgruppen/submission_task3_guarded.zip`
  - Size: `138 MB`
  - Zip root contents: `run.py`, `best.onnx`
- `INFERRED`: Prior score bottleneck likely came from post-processing quality, and this candidate is materially safer than the previous baseline.
- `DECISION`: Use this as the next controlled single submission candidate and log post-submit score/rank delta immediately.

### Entry T3-RESULT-005
- Timestamp: `2026-03-22 01:02` (Oslo, submission completion shown in UI)
- Evidence source: operator-shared submission history + leaderboard screenshots
- `OBSERVED`: Submission score `0.7626` mAP.
- `OBSERVED`: Submission size `138.2 MB`.
- `OBSERVED`: Submission runtime `17.5s`.
- `OBSERVED` (operator-reported): Task 3 rank improved from `#309` to `#249`.
- `OBSERVED` (operator-reported): Overall rank improved to `#230` out of `467` teams with points.
- `OBSERVED`: Overall columns shown: `Detection 82.4`, `Tripletex 32.3`, `Astar Island 54.1`, `Total 56.3`.
- `INFERRED`: ONNX post-processing fixes were a high-impact score lever and produced the current stable baseline.
- `DECISION`: Freeze `submission_task3_guarded.zip` as rollback-safe baseline and only run bounded follow-up tuning passes.

### Entry T3-CANDIDATE-006
- Timestamp: `2026-03-22 01:29` (CET, Oslo)
- Evidence source: direct VM baseline-vs-candidate logs on identical 248-image train set
- `OBSERVED`: Only code change was NMS mode in `run.py` (class-aware -> class-agnostic via `CLASS_AGNOSTIC_NMS = True`).
- `OBSERVED`: Baseline dry-run runtime `45.741s`; candidate runtime `45.674s`.
- `OBSERVED`: Baseline predictions `23,956`; candidate predictions `21,710`.
- `OBSERVED`: Schema check for both outputs returned `bad_records=0`.
- `OBSERVED`: High-overlap cross-class duplicate pairs (IoU>=0.8) dropped from `2069` to `0`.
- `OBSERVED`: Proxy weighted AP (`70/30`) improved from `0.761466` to `0.765064` in local IoU>=0.5 matching evaluation.
- `OBSERVED`: Candidate artifact built and verified:
  - VM path: `~/submission_task3_agnostic_nms.zip`
  - Local path: `task3-Norgesgruppen/submission_task3_agnostic_nms.zip`
  - Size: `139 MB`
  - Zip root contents: `run.py`, `best.onnx`
- `INFERRED`: Candidate is low-risk from runtime/schema perspective and likely improves leaderboard score versus current baseline.
- `DECISION`: Submit exactly one bounded follow-up using `submission_task3_agnostic_nms.zip`, keep `submission_task3_guarded.zip` as immediate rollback if runtime or score regresses.

### Entry T3-RESULT-007
- Timestamp: `2026-03-22 01:52` (Oslo, submission completion shown in UI)
- Evidence source: operator-shared submission history screenshot
- `OBSERVED`: Candidate submission score `0.7619` (no improvement vs `0.7626` baseline).
- `OBSERVED`: Candidate runtime `18.9s` (baseline runtime `17.5s`).
- `OBSERVED`: Candidate size `138.2 MB`.
- `OBSERVED`: Submission row time window shown: `22. mars, 01:51 — 22. mars, 01:52`.
- `INFERRED`: Class-agnostic NMS reduced duplicate predictions but likely removed beneficial class-retention behavior for competition scoring.
- `DECISION`: Keep existing `0.7626` entry selected as final in UI; no rollback re-upload required.

## 5. Active Hypothesis Queue

### HYP-001: ONNX decoding/parsing correctness
- `INFERRED`: Incorrect output parsing likely dominates current error budget.
- Validation plan:
  1. Confirm output tensor interpretation (bbox channels vs class logits).
  2. Confirm coordinate transform and clipping.
  3. Confirm class-id mapping to expected `category_id`.
  4. Confirm post-processing (including NMS policy).
- Success signal:
  - major jump in quality metrics and/or competition score on next controlled submission.

## 6. Operator Checklist Per Submission
1. Confirm operator approval to submit.
2. Record exact artifact names and hash/size when possible.
3. Record command sequence used for packaging.
4. Record immediate sandbox/runtime outcome.
5. Record final score/rank impact when available.

## 7. Quick Loader
Read in this order for Task 3 optimization:
1. `task3-Norgesgruppen/AGENT.md`
2. `task3-Norgesgruppen/PROGRESS.md`
3. `task3-Norgesgruppen/PastSubmissions.md`
4. Task 3 docs in folder (`task3_docs_*.md`)
