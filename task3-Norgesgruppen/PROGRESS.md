# Progress Report: NorgesGruppen Object Detection (Task 3)

## 0. Documentation Sync Contract (Mandatory)

- `AGENT.md` and `PROGRESS.md` must be reviewed and updated together in the same commit whenever either file changes.
- Timestamped leaderboard evidence must be appended when baseline status changes.
- Before ending a Task 3 session, docs updates must be pushed to GitHub to avoid local-only data loss.

## 0.1 Submission Outcome Update (2026-03-22, Sunday 02:10 CET)

- `OBSERVED`: `CONF_THRESHOLD=0.20` candidate submission completed (`22. mars 02:09–02:10` in UI).
- `OBSERVED`: Score improved to `0.7780` (from previous best `0.7626`).
- `OBSERVED`: Runtime `19.1s`; file size `138.2 MB`.
- `OBSERVED`: New row is selected as final in UI.
- `INFERRED`: Lowering confidence threshold on class-aware pipeline improved organizer scoring despite a small runtime increase.
- `DECISION`: Freeze `0.7780` as current baseline/final while running only one-variable follow-up passes.

## 0.2 External Idea Check (2026-03-22, Sunday 02:22 CET)

- `OBSERVED`: Peer tip reviewed: WALDO repository (`stephansturges/WALDO`).
- `INFERRED`: Not a direct swap candidate for Task 3 due domain/class mismatch (overhead/drone classes vs 357 grocery SKUs).
- `INFERRED`: Potentially useful only for generic ideas (tiling/sliding-window patterns).
- `DECISION`: Keep WALDO out of direct submission path; retain ONNX grocery-specific pipeline.

## 1. Latest Session Update (2026-03-22, Sunday 02:05 CET)

- Restored known-good NMS mode and changed one tuning lever only:
  - `CLASS_AGNOSTIC_NMS=False` (class-aware, same as `0.7626` baseline behavior)
  - `CONF_THRESHOLD`: `0.25` -> `0.20`
- VM full dry-run comparison on `248` images:
  - baseline runtime: `45.781s`
  - candidate runtime: `45.768s`
  - baseline predictions: `23,956`
  - candidate predictions: `25,712`
  - schema validity: `bad_records=0` for both
- Proxy evaluation (IoU>=0.5 matching, weighted `70/30` combo proxy):
  - baseline combo AP proxy: `0.761466`
  - candidate combo AP proxy: `0.782002`
- Prepared candidate artifact:
  - VM: `~/submission_task3_conf020.zip`
  - Local: `task3-Norgesgruppen/submission_task3_conf020.zip` (`139 MB`)
  - archive contents verified at zip root: `run.py`, `best.onnx`
- `DECISION`: Submit `submission_task3_conf020.zip` as the next bounded attempt.

## 1.1 Submission Outcome Update (2026-03-22, Sunday 01:52 CET)

- `OBSERVED`: Class-agnostic NMS candidate submission completed (`22. mars 01:51–01:52` in UI).
- `OBSERVED`: Score `0.7619` (vs baseline `0.7626`).
- `OBSERVED`: Runtime `18.9s` (vs baseline `17.5s`).
- `OBSERVED`: File size `138.2 MB`.
- `INFERRED`: Offline proxy improvement did not transfer to competition scoring distribution.
- `DECISION`: Keep `0.7626` submission selected as final in UI (no rollback re-upload needed).

## 1.2 Latest Session Update (2026-03-22, Sunday 01:29 CET)

- Applied one bounded code change in `task3-Norgesgruppen/run.py`:
  - switched NMS from class-aware to class-agnostic
  - no other preprocessing/decode/threshold/runtime logic changed
  - rollback is one-flag (`CLASS_AGNOSTIC_NMS = False`)
- VM validation reused existing Task 3 pattern:
  - `CLOUDSDK_CONFIG=/tmp/gcloud-config`
  - `gcloud compute ssh/scp ... --ssh-key-file=/tmp/gce_key`
  - source model from `/home/devstar17301/nm-ai-2026/task3-Norgesgruppen/best.onnx`
  - writable workspace `~/task3-recovery`
  - runtime with `/opt/conda/bin/python`
- Full dry-run comparison on `248` images:
  - baseline runtime: `45.741s`
  - candidate runtime: `45.674s`
  - baseline predictions: `23,956`
  - candidate predictions: `21,710`
  - schema validity: `bad_records=0` for both
- Proxy evaluation (IoU>=0.5 matching, weighted `70/30` combo proxy):
  - baseline combo AP proxy: `0.761466`
  - candidate combo AP proxy: `0.765064`
  - baseline cross-class duplicate overlaps (IoU>=0.8): `2069`
  - candidate cross-class duplicate overlaps (IoU>=0.8): `0`
- Prepared candidate artifact:
  - VM: `~/submission_task3_agnostic_nms.zip`
  - Local: `task3-Norgesgruppen/submission_task3_agnostic_nms.zip` (`139 MB`)
  - archive contents verified at zip root: `run.py`, `best.onnx`
- `DECISION`: Candidate is technically safe and likely positive; keep `submission_task3_guarded.zip` as immediate rollback option.

## 1.3 Prior Session Update (2026-03-22, Sunday 01:10 CET)

- Guarded Task 3 submission succeeded.
- `OBSERVED`: Submission history shows score `0.7626`, file size `138.2 MB`, runtime `17.5s`, status `Completed/Final`.
- `OBSERVED` (operator-reported): Task 3 rank improved from `#309` to `#249`.
- `OBSERVED` (operator-reported): Overall rank improved to `#230` out of `467` teams with points.
- `OBSERVED`: Overall columns shown were `Detection 82.4`, `Tripletex 32.3`, `Astar Island 54.1`, `Total 56.3`.
- `INFERRED`: ONNX post-processing reliability fixes were the highest-impact short-term lever.
- `DECISION`: Keep this candidate as current safe baseline and run only bounded follow-up tuning if there is clear expected gain.

## 1.4 GCP Execution Pattern Used This Session (No Secrets)

- Connectivity and VM ops used `CLOUDSDK_CONFIG=/tmp/gcloud-config`.
- SSH/SCP used explicit key file `--ssh-key-file=/tmp/gce_key`.
- Because `/home/devstar17301/...` is not writable by `kenneth`, execution used:
  - source artifacts from `/home/devstar17301/nm-ai-2026/task3-Norgesgruppen`
  - writable workspace `~/task3-recovery`
- Runtime validation used `/opt/conda/bin/python`.
- VM-local ONNX CUDA provider warning (cuDNN mismatch) was handled by CPU fallback for validation.

## 1.5 Candidate Build and Validation (2026-03-22, Sunday 00:42 CET)

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

## 1.6 Prior Checkpoint (2026-03-22, Sunday 00:02 Oslo)

- Leaderboard checkpoint recorded from operator-shared overall screenshot.
- `OBSERVED`: Team row shows rank `#273`.
- `OBSERVED`: Overall columns shown were `Detection 19.3`, `Tripletex 31.8`, `Astar Island 54.5`, `Total 35.2`.
- `DECISION`: Preserve this checkpoint in Task 3 documentation to maintain cross-task context while prioritizing Task 3 score recovery.

## 1.7 Task 3 Baseline Re-Verification (2026-03-21, Saturday 22:48 Oslo)

- `OBSERVED`: Task 3 score `0.1786` mAP.
- `OBSERVED`: Task 3 rank `#301` out of `313` teams with points.
- `OBSERVED`: Task 3 submission count shown was `1`.
- `INFERRED`: Previously imported `#157` rank is stale historical context.

## 1.8 Documentation Hardening Update (2026-03-21, Saturday ~23:55 Oslo)

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

## 1.9 Historical Baseline Imported (Stale Until Re-Verified)

- Last known historical Task 3 status from prior AGENT notes:
  - score `0.1786` mAP
  - rank `#157`
  - ONNX-based submission (`run.py` + `best.onnx`)
  - likely error source hypothesis: ONNX output parsing/classification mismatch
- Important:
  - this baseline was not actively maintained after Friday morning and must be re-verified before using as current truth.

## 2. Next Actions

1. Keep `0.7780` row selected as final in UI.
2. If another attempt is made, keep it one-variable only and predefine rollback criteria (`must beat 0.7780`).
3. Continue using GCP aggressively for validation/sweeps (no token/credit limit) while preserving submission discipline.
4. Record each submission result in `PastSubmissions.md` with exact timestamp + `OBSERVED/INFERRED/DECISION`.
