# Progress Report: NorgesGruppen Object Detection (Task 3)

## 0. Documentation Sync Contract (Mandatory)

- `AGENT.md` and `PROGRESS.md` must be reviewed and updated together in the same commit whenever either file changes.
- Timestamped leaderboard evidence must be appended when baseline status changes.
- Before ending a Task 3 session, docs updates must be pushed to GitHub to avoid local-only data loss.

## 1. Latest Session Update (2026-03-22, Sunday 01:10 CET)

- Guarded Task 3 submission succeeded.
- `OBSERVED`: Submission history shows score `0.7626`, file size `138.2 MB`, runtime `17.5s`, status `Completed/Final`.
- `OBSERVED` (operator-reported): Task 3 rank improved from `#309` to `#249`.
- `OBSERVED` (operator-reported): Overall rank improved to `#230` out of `467` teams with points.
- `OBSERVED`: Overall columns shown were `Detection 82.4`, `Tripletex 32.3`, `Astar Island 54.1`, `Total 56.3`.
- `INFERRED`: ONNX post-processing reliability fixes were the highest-impact short-term lever.
- `DECISION`: Keep this candidate as current safe baseline and run only bounded follow-up tuning if there is clear expected gain.

## 1.1 GCP Execution Pattern Used This Session (No Secrets)

- Connectivity and VM ops used `CLOUDSDK_CONFIG=/tmp/gcloud-config`.
- SSH/SCP used explicit key file `--ssh-key-file=/tmp/gce_key`.
- Because `/home/devstar17301/...` is not writable by `kenneth`, execution used:
  - source artifacts from `/home/devstar17301/nm-ai-2026/task3-Norgesgruppen`
  - writable workspace `~/task3-recovery`
- Runtime validation used `/opt/conda/bin/python`.
- VM-local ONNX CUDA provider warning (cuDNN mismatch) was handled by CPU fallback for validation.

## 1.2 Candidate Build and Validation (2026-03-22, Sunday 00:42 CET)

- Implemented a new Task 3 `run.py` ONNX inference pipeline in repo:
  - letterbox pre-processing with ratio/padding tracking
  - corrected decode path for `(channels, boxes)` ONNX output
  - class-aware NMS (`torchvision.ops.nms`)
  - bbox clipping and strict JSON schema output
- VM smoke test (`12` images) succeeded:
  - runtime `8s`
  - output schema check: `bad_records 0`
- VM full dry run succeeded:
  - input images: `248`
  - runtime `45s` (well below `300s` timeout)
  - output predictions: `23,956`
- Prepared guarded submission artifact:
  - VM: `~/submission_task3_guarded.zip`
  - Local: `task3-Norgesgruppen/submission_task3_guarded.zip` (`138 MB`)
  - Archive content verified: `run.py` + `best.onnx` at zip root.
- `DECISION`: Candidate is ready for one guarded Task 3 submission.

## 1.3 Prior Checkpoint (2026-03-22, Sunday 00:02 Oslo)

- Leaderboard checkpoint recorded from operator-shared overall screenshot.
- `OBSERVED`: Team row shows rank `#273`.
- `OBSERVED`: Overall columns shown were `Detection 19.3`, `Tripletex 31.8`, `Astar Island 54.5`, `Total 35.2`.
- `DECISION`: Preserve this checkpoint in Task 3 documentation to maintain cross-task context while prioritizing Task 3 score recovery.

## 1.4 Task 3 Baseline Re-Verification (2026-03-21, Saturday 22:48 Oslo)

- `OBSERVED`: Task 3 score `0.1786` mAP.
- `OBSERVED`: Task 3 rank `#301` out of `313` teams with points.
- `OBSERVED`: Task 3 submission count shown was `1`.
- `INFERRED`: Previously imported `#157` rank is stale historical context.

## 1.5 Documentation Hardening Update (2026-03-21, Saturday ~23:55 Oslo)

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

## 1.6 Historical Baseline Imported (Stale Until Re-Verified)

- Last known historical Task 3 status from prior AGENT notes:
  - score `0.1786` mAP
  - rank `#157`
  - ONNX-based submission (`run.py` + `best.onnx`)
  - likely error source hypothesis: ONNX output parsing/classification mismatch
- Important:
  - this baseline was not actively maintained after Friday morning and must be re-verified before using as current truth.

## 2. Next Actions

1. Preserve `0.7626` as current Task 3 baseline; do not regress.
2. If submission quota allows and expected value is high, run one bounded tuning attempt (confidence/NMS threshold only).
3. Keep changes in a fresh PR whenever non-markdown files are involved.
4. Continue same-session doc sync (`AGENT.md` + `PROGRESS.md` + `PastSubmissions.md`) with exact timestamps.
