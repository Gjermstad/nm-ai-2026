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

### Entry T3-CANDIDATE-008
- Timestamp: `2026-03-22 02:05` (CET, Oslo)
- Evidence source: direct VM baseline-vs-candidate logs on identical 248-image train set
- `OBSERVED`: Candidate restores class-aware NMS and changes one lever only: `CONF_THRESHOLD 0.25 -> 0.20`.
- `OBSERVED`: Baseline dry-run runtime `45.781s`; candidate runtime `45.768s`.
- `OBSERVED`: Baseline predictions `23,956`; candidate predictions `25,712`.
- `OBSERVED`: Schema check for both outputs returned `bad_records=0`.
- `OBSERVED`: Proxy weighted AP (`70/30`) improved from `0.761466` to `0.782002` in local IoU>=0.5 matching evaluation.
- `OBSERVED`: Candidate artifact built and verified:
  - VM path: `~/submission_task3_conf020.zip`
  - Local path: `task3-Norgesgruppen/submission_task3_conf020.zip`
  - Size: `139 MB`
  - Zip root contents: `run.py`, `best.onnx`
- `INFERRED`: Lower confidence threshold may recover recall/classification opportunities while keeping runtime stable.
- `DECISION`: Submit exactly one bounded follow-up using `submission_task3_conf020.zip`; keep `0.7626` selected final unless this beats it.

### Entry T3-RESULT-009
- Timestamp: `2026-03-22 02:10` (Oslo, submission completion shown in UI)
- Evidence source: operator-shared submission history screenshot
- `OBSERVED`: Candidate submission score `0.7780` (improved from `0.7626`).
- `OBSERVED`: Candidate runtime `19.1s`.
- `OBSERVED`: Candidate size `138.2 MB`.
- `OBSERVED`: Submission row time window shown: `22. mars, 02:09 — 22. mars, 02:10`.
- `OBSERVED`: This newest row is selected as final in UI.
- `INFERRED`: Lowering confidence threshold while keeping class-aware NMS yielded a net gain on organizer scoring.
- `DECISION`: Promote `submission_task3_conf020.zip` as current baseline/final; only continue with one-variable bounded attempts.

### Entry T3-IDEA-010
- Timestamp: `2026-03-22 02:22` (Oslo)
- Evidence source: peer tip + repository review (`stephansturges/WALDO`)
- `OBSERVED`: WALDO targets overhead/drone-style objects and different class space.
- `INFERRED`: Direct model swap is not practical for Task 3 grocery SKU detection.
- `INFERRED`: Only selected implementation ideas (e.g., tiling/sliding-window patterns) may be reusable.
- `DECISION`: Keep WALDO out of immediate submission path; continue optimizing existing Task 3 ONNX pipeline.

### Entry T3-TRAINING-011
- Timestamp: `2026-03-22 02:39` (CET, Oslo)
- Evidence source: direct VM launch + process/log checks
- `OBSERVED`: Started overnight high-upside retraining pipeline on VM (`PID 649159`):
  - launcher: `~/task3-recovery/overnight_bigtrain.py`
  - log: `~/task3-recovery/overnight_bigtrain.log`
  - summary target: `/home/kenneth/task3-overnight/overnight_summary.txt`
  - run order: `ft_beststripped_img960_e220` then `ft_yolov8l_img960_e260`
- `OBSERVED`: GPU confirmed active during run (`NVIDIA L4`, high utilization).
- `INFERRED`: This track has materially higher upside than minor post-processing tweaks and matches reduced remaining submission budget.
- `DECISION`: Keep training running overnight and evaluate resulting ONNX exports before using additional submission slots.

### Entry T3-CANDIDATE-012
- Timestamp: `2026-03-22 02:48` (CET, Oslo)
- Evidence source: direct VM run logs + artifact packaging
- `OBSERVED`: One-variable candidate changed only `IOU_THRESHOLD` in `run.py` (`0.70 -> 0.65`) while keeping class-aware NMS and `CONF_THRESHOLD=0.20`.
- `OBSERVED`: VM full dry-run runtime `45.683s` on `248` images.
- `OBSERVED`: Candidate output produced `25,568` predictions with `bad_records=0`.
- `OBSERVED`: Custom proxy evaluation (IoU>=0.5 weighted `70/30`) moved from `0.824353` (`conf020`) to `0.824723` (`iou065`), delta `+0.000370`.
- `OBSERVED`: Candidate artifact built and verified:
  - VM path: `~/submission_task3_iou065.zip`
  - Local path: `task3-Norgesgruppen/submission_task3_iou065.zip`
  - Size: `138 MB`
  - Zip root contents: `run.py`, `best.onnx`
- `INFERRED`: Candidate is low risk and valid, but expected gain is likely too small to prioritize with `4` submissions remaining.
- `DECISION`: Hold as optional fallback candidate; prioritize higher-upside retraining outputs for next submit.

### Entry T3-RESULT-013
- Timestamp: `2026-03-22 10:40` (Oslo, submission completion shown in UI)
- Evidence source: operator-shared submission history screenshot
- `OBSERVED`: Submitted artifact `submission_task3_overnightA_conf020.zip` scored `0.8621`.
- `OBSERVED`: Submission runtime `19.0s`; size `138.2 MB`.
- `OBSERVED`: Submission row time window shown: `22. mars, 10:34 — 22. mars, 10:40`.
- `OBSERVED`: Newest row is selected as final in UI.
- `OBSERVED`: Previous final score was `0.7780`; delta is `+0.0841`.
- `INFERRED`: Overnight retraining delivered a high-impact model upgrade while preserving runtime stability near prior best.
- `INFERRED`: Assuming prior remaining attempts were `4`, remaining attempts are now approximately `3`.
- `DECISION`: Promote `0.8621` as the new baseline/final and reserve remaining submissions for high-upside candidates only.

### Entry T3-CANDIDATE-014
- Timestamp: `2026-03-22 10:58` (CET, Oslo)
- Evidence source: direct VM one-variable sweep logs + artifact packaging
- `OBSERVED`: Ran one-variable sweep on overnight best ONNX with class-aware NMS and `IOU_THRESHOLD=0.70`; only `CONF_THRESHOLD` changed.
- `OBSERVED`: Sweep result (`CONF -> combo proxy`):
  - `0.12 -> 0.964259`
  - `0.15 -> 0.962253`
  - `0.18 -> 0.960124`
  - `0.20 -> 0.958365`
  - `0.22 -> 0.956549`
  - `0.24 -> 0.954702`
  - `0.26 -> 0.953064`
- `OBSERVED`: Best setting was `CONF_THRESHOLD=0.12` with runtime `46.564s`, predictions `25,802`, `bad_records=0`.
- `OBSERVED`: Candidate artifact built and verified:
  - VM path: `~/submission_task3_overnightA_conf012.zip`
  - Local path: `task3-Norgesgruppen/submission_task3_overnightA_conf012.zip`
  - Size: `138 MB`
  - Zip root contents: `run.py`, `best.onnx`
- `INFERRED`: Lower threshold appears beneficial on the stronger retrained model and is a plausible next high-upside submission.
- `DECISION`: If taking another attempt, prioritize `submission_task3_overnightA_conf012.zip` next.

### Entry T3-CANDIDATE-015
- Timestamp: `2026-03-22 11:15` (CET, Oslo)
- Evidence source: direct VM one-variable CONF sweep logs + artifact packaging
- `OBSERVED`: Continued one-variable CONF sweep on overnight best ONNX with class-aware NMS and `IOU_THRESHOLD=0.70`.
- `OBSERVED`: Lower-confidence points outperformed earlier settings in proxy ranking; selected bounded candidate `CONF_THRESHOLD=0.06`.
- `OBSERVED`: Candidate artifact built and verified:
  - Local path: `task3-Norgesgruppen/submission_task3_overnightA_conf006.zip`
  - Size: `138.2 MB`
  - Zip root contents: `run.py`, `best.onnx`
- `INFERRED`: Lowering confidence further may recover hard detections without breaking runtime budget.
- `DECISION`: Submit `submission_task3_overnightA_conf006.zip` as next high-upside one-variable attempt.

### Entry T3-RESULT-016
- Timestamp: `2026-03-22 11:20` (Oslo, submission completion shown in UI)
- Evidence source: operator-shared submission result screenshot
- `OBSERVED`: Submitted artifact `submission_task3_overnightA_conf006.zip` scored `0.8798`.
- `OBSERVED`: Submission runtime `18.0s`; size `138.2 MB`.
- `OBSERVED`: Submission row time window shown: `22. mars, 11:19 — 22. mars, 11:20`.
- `OBSERVED`: Newest row is selected as `Final` in UI.
- `OBSERVED`: UI shows `2 of 6 submissions remaining today`.
- `OBSERVED`: Previous final score was `0.8621`; delta is `+0.0177`.
- `INFERRED`: Confidence reduction from `0.20`/`0.12` to `0.06` transferred strongly to leaderboard score while keeping fast runtime.
- `DECISION`: Promote `0.8798` as baseline/final and reserve last two attempts for high-upside single-variable passes only.

### Entry T3-CANDIDATE-017
- Timestamp: `2026-03-22 11:22` (CET, Oslo)
- Evidence source: direct VM one-variable IOU sweep logs at fixed conf
- `OBSERVED`: Ran one-variable IOU sweep on overnight best ONNX at fixed `CONF_THRESHOLD=0.06` and class-aware NMS.
- `OBSERVED`: Proxy ranking selected `IOU_THRESHOLD=0.60` as best; `IOU_THRESHOLD=0.55` was effectively tied and second-best.
- `OBSERVED`: Candidate artifacts built and verified:
  - Local path: `task3-Norgesgruppen/submission_task3_overnightA_conf006_iou060.zip`
  - Local path: `task3-Norgesgruppen/submission_task3_overnightA_conf006_iou055.zip`
  - Each archive size: `138.2 MB`
  - Zip root contents: `run.py`, `best.onnx`
- `INFERRED`: IOU tuning on top of strong low-conf baseline offers bounded upside with low implementation risk.
- `DECISION`: Next submission candidate is `submission_task3_overnightA_conf006_iou060.zip`; keep `...iou055.zip` as final fallback only if needed.

### Entry T3-RESULT-018
- Timestamp: `2026-03-22 11:26` (Oslo, submission completion shown in UI)
- Evidence source: operator-shared submission result screenshot
- `OBSERVED`: Submitted artifact `submission_task3_overnightA_conf006_iou060.zip` scored `0.8808`.
- `OBSERVED`: Submission runtime `17.7s`; size `138.2 MB`.
- `OBSERVED`: Submission row time window shown: `22. mars, 11:25 — 22. mars, 11:26`.
- `OBSERVED`: Newest row is selected as `Final` in UI.
- `OBSERVED`: UI shows `1 of 6 submissions remaining today`.
- `OBSERVED`: Previous final score was `0.8798`; delta is `+0.0010`.
- `INFERRED`: Lowering IoU from `0.70` to `0.60` at fixed `CONF=0.06` helps, but only marginally.
- `DECISION`: Keep `0.8808` as baseline/final and spend last attempt on a higher-variance one-variable pass.

### Entry T3-CANDIDATE-019
- Timestamp: `2026-03-22 11:29` (CET, Oslo)
- Evidence source: local artifact derivation from latest final package
- `OBSERVED`: Built one-variable final-shot candidate from latest final settings:
  - base: `CONF_THRESHOLD=0.06`, `IOU_THRESHOLD=0.60`, class-aware NMS
  - changed only: `CONF_THRESHOLD=0.04`
- `OBSERVED`: Candidate artifact built and verified:
  - Local path: `task3-Norgesgruppen/submission_task3_overnightA_conf004_iou060.zip`
  - Size: `138 MB`
  - Zip root contents: `run.py`, `best.onnx`
  - Syntax check: `python3 -m py_compile run.py` passed
- `HYPOTHESIS`: Extra recall at `conf=0.04` can produce a larger upside than conservative `iou055` fallback.
- `ROLLBACK`: If score regresses, keep `0.8808` row selected as final (no code rollback needed).
- `RISK`: Increased false positives may reduce precision enough to underperform despite stable runtime.
- `DECISION`: Use `submission_task3_overnightA_conf004_iou060.zip` as the final all-out submission candidate.

### Entry T3-RESULT-020
- Timestamp: `2026-03-22 11:37` (Oslo, submission completion shown in UI)
- Evidence source: operator-shared submission result screenshot
- `OBSERVED`: Submitted artifact `submission_task3_overnightA_conf004_iou060.zip` scored `0.8818`.
- `OBSERVED`: Submission runtime `18.0s`; size `138.2 MB`.
- `OBSERVED`: Submission row time window shown: `22. mars, 11:37 — 22. mars, 11:37`.
- `OBSERVED`: Newest row is selected as `Final` in UI.
- `OBSERVED`: Previous final score was `0.8808`; delta is `+0.0010`.
- `OBSERVED`: UI shows `0 of 6 submissions remaining today` and daily limit reached.
- `INFERRED`: The high-variance last-shot pass was positive and became the day’s best final result.
- `DECISION`: Freeze `0.8818` as final Task 3 result for today; continue only with documentation sync and next-session planning.

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
