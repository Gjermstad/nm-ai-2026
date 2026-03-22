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

## 0.3 Bounded IOU Pass + Overnight High-Upside Track (2026-03-22, Sunday 02:48 CET)

- `OBSERVED`: Applied one-variable code change in `task3-Norgesgruppen/run.py`:
  - `IOU_THRESHOLD`: `0.70` -> `0.65`
  - kept `CONF_THRESHOLD=0.20`
  - kept `CLASS_AGNOSTIC_NMS=False` (class-aware)
- `OBSERVED`: VM full dry run on `248` images:
  - runtime: `45.683s`
  - predictions: `25,568`
  - schema validity: `bad_records=0`
- `OBSERVED`: Custom local proxy (IoU>=0.5 matching, weighted `70/30`) comparison:
  - `conf020` combo proxy: `0.824353`
  - `iou065` combo proxy: `0.824723` (`+0.000370`)
- `OBSERVED`: Candidate artifact prepared and verified:
  - VM: `~/submission_task3_iou065.zip`
  - Local: `task3-Norgesgruppen/submission_task3_iou065.zip` (`138 MB`)
  - archive root contains `run.py`, `best.onnx`
- `OBSERVED` (operator instruction): only `4` submissions remain and priority is larger gains over marginal improvements.
- `OBSERVED`: Overnight high-upside retraining job launched on VM at `2026-03-22 02:39 CET`:
  - PID: `649159`
  - script: `~/task3-recovery/overnight_bigtrain.py`
  - log: `~/task3-recovery/overnight_bigtrain.log`
  - summary target: `/home/kenneth/task3-overnight/overnight_summary.txt`
- `INFERRED`: IOU pass is technically safe but expected leaderboard gain is likely small relative to remaining submission budget.
- `DECISION`: Keep `0.7780` selected final for now; prioritize overnight retraining outputs for next submission candidate.

## 0.4 Overnight Continuity Check Before Laptop Close (2026-03-22, Sunday 02:57 CET)

- `OBSERVED`: VM process `PID 649159` is alive with `PPID=1`, `TTY=?`, state `Sl` (`/opt/conda/bin/python /home/kenneth/task3-recovery/overnight_bigtrain.py`).
- `OBSERVED`: VM instance status is `RUNNING` (`yolo-training-vm`, zone `europe-west1-c`, machine `g2-standard-4`, `PREEMPTIBLE` empty/non-preemptible).
- `OBSERVED`: GPU is actively used during training (`NVIDIA L4`, utilization around `69%`, memory `9431 MiB / 23034 MiB`).
- `OBSERVED`: Log file is still advancing over time:
  - `LOG_MTIME_BEFORE=1774144553`, `LOG_MTIME_AFTER=1774144573`
  - `LOG_SIZE_BEFORE=633204`, `LOG_SIZE_AFTER=645924`
- `INFERRED`: Overnight job is detached from the local client and continues independently on VM.
- `DECISION`: Safe to close laptop; continue monitoring/review in next session via `~/task3-recovery/overnight_bigtrain.log` and `/home/kenneth/task3-overnight/overnight_summary.txt`.

## 0.5 Morning Recovery and Strong Candidate Build (2026-03-22, Sunday 10:32 CET)

- `OBSERVED`: Overnight training script completed both runs and wrote summary, but each run ended with a PyTorch 2.6 `weights_only` error during Ultralytics post-processing (`strip_optimizer`), not during training epochs.
- `OBSERVED`: Despite that error, both checkpoints were produced:
  - `/home/kenneth/task3-overnight/ft_beststripped_img960_e220/weights/best.pt`
  - `/home/kenneth/task3-overnight/ft_yolov8l_img960_e260/weights/best.pt`
- `OBSERVED`: Final validation metrics from `results.csv`:
  - `ft_beststripped_img960_e220`: precision `0.87966`, recall `0.80345`, mAP50 `0.87416`, mAP50-95 `0.68282`
  - `ft_yolov8l_img960_e260`: precision `0.85289`, recall `0.78110`, mAP50 `0.84180`, mAP50-95 `0.64973`
- `OBSERVED`: Exported ONNX from stronger run:
  - source: `/home/kenneth/task3-overnight/ft_beststripped_img960_e220/weights/best.pt`
  - output: `/home/kenneth/task3-overnight/ft_beststripped_img960_e220/weights/best.onnx` (`167.6 MB`)
- `OBSERVED`: Benchmarked with current production inference pipeline (`run.py`, `CONF_THRESHOLD=0.20`, class-aware NMS):
  - runtime: `45.991s` on `248` images
  - predictions: `24,446`
  - schema validity: `bad_records=0`
- `OBSERVED`: Custom proxy comparison (IoU>=0.5 weighted `70/30`):
  - current `conf020`: `0.824353`
  - overnight candidate: `0.958365`
- `OBSERVED`: Prepared upload-ready artifact:
  - VM: `~/submission_task3_overnightA_conf020.zip`
  - Local: `task3-Norgesgruppen/submission_task3_overnightA_conf020.zip` (`138 MB`)
- `INFERRED`: Candidate appears materially stronger than current baseline and deserves immediate submission priority.
- `DECISION`: Use `submission_task3_overnightA_conf020.zip` as the next Task 3 submission candidate.

## 0.6 Submission Outcome Update (2026-03-22, Sunday 10:40 CET)

- `OBSERVED`: `submission_task3_overnightA_conf020.zip` completed in submission history (`22. mars 10:34–10:40` in UI).
- `OBSERVED`: Score improved to `0.8621` (from previous final `0.7780`).
- `OBSERVED`: Runtime `19.0s`; file size `138.2 MB`.
- `OBSERVED`: Newest row is selected as `Final` in UI.
- `INFERRED`: Overnight retraining plus stable inference pipeline delivered a major step-change improvement.
- `INFERRED`: If pre-submit remaining attempts were `4`, remaining attempts are now approximately `3`.
- `DECISION`: Promote `0.8621` as new baseline/final and spend remaining submissions only on high-upside candidates.

## 0.7 One-Variable CONF Sweep on New Baseline Model (2026-03-22, Sunday 10:58 CET)

- `OBSERVED`: Ran full one-variable sweep on overnight best ONNX with class-aware NMS + `IOU_THRESHOLD=0.70`; changed only `CONF_THRESHOLD`.
- `OBSERVED`: Sweep points (`CONF_THRESHOLD -> combo proxy`, IoU>=0.5 weighted `70/30`):
  - `0.12 -> 0.964259`
  - `0.15 -> 0.962253`
  - `0.18 -> 0.960124`
  - `0.20 -> 0.958365` (current submitted `0.8621` config)
  - `0.22 -> 0.956549`
  - `0.24 -> 0.954702`
  - `0.26 -> 0.953064`
- `OBSERVED`: Best sweep setting was `CONF_THRESHOLD=0.12` with:
  - runtime `46.564s`
  - predictions `25,802`
  - schema validity `bad_records=0`
- `OBSERVED`: Prepared next candidate artifact:
  - VM: `~/submission_task3_overnightA_conf012.zip`
  - Local: `task3-Norgesgruppen/submission_task3_overnightA_conf012.zip` (`138 MB`)
- `INFERRED`: Lower confidence threshold appears to increase recall/classification opportunities on the stronger retrained model.
- `DECISION`: `submission_task3_overnightA_conf012.zip` is the next high-upside candidate if we use another submission.

## 0.8 Submission Outcome Update (2026-03-22, Sunday 11:20 CET)

- `OBSERVED`: `submission_task3_overnightA_conf006.zip` completed in submission history (`22. mars 11:19–11:20` in UI).
- `OBSERVED`: Score improved to `0.8798` (from previous final `0.8621`).
- `OBSERVED`: Runtime `18.0s`; file size `138.2 MB`.
- `OBSERVED`: Newest row is selected as `Final` in UI.
- `OBSERVED`: UI indicates `2 of 6 submissions remaining today`.
- `INFERRED`: Lowering confidence from `0.20`/`0.12` down to `0.06` unlocked another substantial gain while reducing runtime.
- `DECISION`: Promote `0.8798` as current baseline/final and spend remaining attempts on one-variable, high-upside follow-ups only.

## 0.9 One-Variable IOU Sweep at CONF=0.06 (2026-03-22, Sunday 11:15 CET)

- `OBSERVED`: Ran one-variable sweep with overnight best ONNX + class-aware NMS; kept `CONF_THRESHOLD=0.06` fixed and changed only `IOU_THRESHOLD`.
- `OBSERVED`: Best proxy setting from sweep was `IOU_THRESHOLD=0.60` (with `0.55` effectively tied, but second-best).
- `OBSERVED`: Prepared next candidate artifacts:
  - `task3-Norgesgruppen/submission_task3_overnightA_conf006_iou060.zip`
  - `task3-Norgesgruppen/submission_task3_overnightA_conf006_iou055.zip`
- `INFERRED`: Small but non-zero upside remains from NMS overlap tuning on top of the stronger low-confidence baseline.
- `DECISION`: Next bounded pass should use `submission_task3_overnightA_conf006_iou060.zip` (single variable: `IOU_THRESHOLD 0.70 -> 0.60`).

## 0.10 Submission Outcome Update (2026-03-22, Sunday 11:26 CET)

- `OBSERVED`: `submission_task3_overnightA_conf006_iou060.zip` completed in submission history (`22. mars 11:25–11:26` in UI).
- `OBSERVED`: Score improved to `0.8808` (from previous final `0.8798`).
- `OBSERVED`: Runtime `17.7s`; file size `138.2 MB`.
- `OBSERVED`: Newest row is selected as `Final` in UI.
- `OBSERVED`: UI indicates `1 of 6 submissions remaining today`.
- `INFERRED`: Lowering IoU from `0.70` to `0.60` at fixed low confidence transferred positively, but gain magnitude is small (`+0.0010`).
- `DECISION`: Promote `0.8808` as current baseline/final and use exactly one high-variance final pass.

## 0.11 Last-Shot One-Variable Pass (2026-03-22, Sunday 11:29 CET)

- `OBSERVED`: Built final candidate by changing one variable only from current best config:
  - `CONF_THRESHOLD`: `0.06` -> `0.04`
  - fixed: `IOU_THRESHOLD=0.60`, class-aware NMS
- `OBSERVED`: Candidate artifact prepared and verified:
  - `task3-Norgesgruppen/submission_task3_overnightA_conf004_iou060.zip` (`138 MB`)
  - zip root contents: `run.py`, `best.onnx`
  - syntax check: `python3 -m py_compile run.py` passed
- `HYPOTHESIS`: Extra recall at `conf=0.04` can produce a final leaderboard jump larger than conservative `iou055` fallback.
- `ROLLBACK`: No code rollback needed unless this underperforms; keep `0.8808` row selected final.
- `RISK`: Higher FP rate may hurt precision and regress score despite fast runtime.
- `DECISION`: Use `submission_task3_overnightA_conf004_iou060.zip` as the final all-out submission.

## 0.12 Final Submission Outcome Update (2026-03-22, Sunday 11:37 CET)

- `OBSERVED`: `submission_task3_overnightA_conf004_iou060.zip` completed in submission history (`22. mars 11:37–11:37` in UI).
- `OBSERVED`: Score improved to `0.8818` (from previous final `0.8808`).
- `OBSERVED`: Runtime `18.0s`; file size `138.2 MB`.
- `OBSERVED`: Newest row is selected as `Final` in UI.
- `OBSERVED`: UI indicates `0 of 6 submissions remaining today` and daily limit reached.
- `INFERRED`: High-variance final pass produced a positive but small last-step gain (`+0.0010`).
- `DECISION`: Freeze `0.8818` as final Task 3 score for this submission window.

## 0.13 Retrospective: What We Learned (Task + Agentic AI) (2026-03-22, Sunday 12:10 CET)

- `OBSERVED`: Highest-impact gains came from correctness and model quality, not from repeated micro-tuning:
  - inference reliability fixes: `0.1786 -> 0.7626`
  - retraining + controlled sweeps: `0.7780 -> 0.8621 -> 0.8818`
- `OBSERVED`: One-variable submission discipline made outcomes easy to attribute and reduced rollback complexity.
- `OBSERVED`: One proxy-positive pass (class-agnostic NMS) underperformed on leaderboard, confirming transfer risk.
- `OBSERVED`: Frequent docs synchronization (`AGENT.md`, `PROGRESS.md`, `PastSubmissions.md`) enabled safe recovery across context resets and merged PR transitions.
- `INFERRED`: Best operating pattern is dual-track:
  - baseline-preserving safe track
  - explicitly labeled high-variance exploration track.
- `INFERRED`: Agentic workflows degrade when facts, assumptions, and decisions are mixed; explicit evidence tags reduce this failure mode.
- `DECISION`: Carry forward a hard playbook for future tasks:
  1. freshness gate before edits (`origin/main` sync + read-order check),
  2. one-variable submission changes,
  3. explicit operator approval before irreversible actions,
  4. immediate durable logging after each attempt,
  5. spend limited quota only on high-expected-value experiments.

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

1. Keep `0.8818` row selected as final in UI.
2. Use the new retrospective sections in `AGENT.md` and `PastSubmissions.md` as mandatory startup context for next Task 3 work.
3. Reuse the Agentic AI playbook (freshness gate, bounded experiments, durable logging) across other tasks as standard operating procedure.
