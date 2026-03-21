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
