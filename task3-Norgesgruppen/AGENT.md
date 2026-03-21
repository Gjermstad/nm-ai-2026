# AGENT.md — Task 3: NorgesGruppen Object Detection

> NM i AI 2026 — Task 3 handoff/control file
> Last updated: 2026-03-21 (Saturday, Oslo)
> Status: Task 3 context was not actively maintained after Friday morning; baseline must be re-verified before new submissions.

---

## 0. Preferences (Read First)

### Workflow
1. Never reuse merged PRs; always create a new PR for follow-up work.
2. Do not push code directly to `main`; use branch + PR.
3. Assume parallel sessions can merge at any time; always verify branch freshness before editing.
4. Update `task3-Norgesgruppen/AGENT.md` and `task3-Norgesgruppen/PROGRESS.md` after meaningful changes.
5. Preserve a durable memory trail in `task3-Norgesgruppen/PastSubmissions.md`.

### Session behavior
1. Do not block the session with long hold loops.
2. If operator says to wait with submit, do not package/upload/submit until explicit go-ahead.
3. Keep logs concise and actionable, with exact commands and paths.

### Security and hygiene
1. Do not paste raw tokens/credentials/secrets in docs, logs, or PR text.
2. Keep environment-specific patches clearly documented (what/where/why).

---

## 1. Mission and Context

Task 3 is a constrained object-detection submission challenge where `run.py` must generate valid `predictions.json` inside organizer sandbox constraints.

Primary objective:
- maximize competition score while preserving submission reliability and reproducibility.

Secondary objective:
- keep every change attributable via submission history and post-mortem notes.

---

## 2. Environment and Infrastructure

- GCP Project ID: `ai-nm26osl-1730`
- Cloud Run region (if needed for related services): `europe-north1`
- Storage bucket: `gs://ai-nm26osl-1730-nmd-dataset/`
- Training VM: `yolo-training-vm`
- VM zone: `europe-west1-c` (not `europe-west1-b`)
- Working directory on VM: `~/nm-ai-2026/task3-Norgesgruppen`
- Repo: `https://github.com/Gjermstad/nm-ai-2026`

Sandbox constraints (organizer):
- Python `3.11`
- No network
- 300s timeout
- NVIDIA L4 / CUDA 12.4
- Blocked imports include `os`, `sys`, `subprocess`, `socket` (use `pathlib`)
- Required compatibility targets previously noted: `ultralytics==8.1.0`, `torch==2.6.0`

---

## 3. Required Start-of-Session Checklist

Run this exact sequence before making changes:

1. Verify git freshness:
   - `git log --oneline -5 main`
   - `git log --oneline -5 HEAD`
   - If `HEAD` is behind main, create a fresh branch from `origin/main`.
2. Read these files in order:
   - `task3-Norgesgruppen/AGENT.md`
   - `task3-Norgesgruppen/PROGRESS.md`
   - `task3-Norgesgruppen/PastSubmissions.md`
   - `task3-Norgesgruppen/task3_docs_overview.md`
   - `task3-Norgesgruppen/task3_docs_scoring.md`
   - `task3-Norgesgruppen/task3_docs_osubmission-format.md`
   - `task3-Norgesgruppen/task3_docs_examples-tips.md`
3. Confirm latest known baseline status is still valid (score/rank/submission quota/runtime assumptions).
4. Decide if current pass is:
   - reliability fix,
   - score optimization,
   - or submission packaging only.

---

## 4. Current Baseline Snapshot (Needs Re-Verification)

Last known (historical baseline from older Task 3 context):
- Score: `0.1786` mAP
- Rank: `#157`
- Submission artifact: ONNX-based `run.py` + `best.onnx`
- Hypothesis then: ONNX output parsing/classification likely incorrect

Important:
- Treat these numbers as stale until re-checked in the current competition UI.
- Always include exact "last verified" timestamp when updating these fields.

---

## 5. Known Task-Specific Technical Notes

From prior working notes:
1. VM zone for training is `europe-west1-c`.
2. `train.py` expected dataset path: `dataset/train/data.yaml`.
3. Ultralytics patch previously needed in VM env for torch 2.6.0 loader behavior.
4. `data.yaml` was previously required with absolute path on VM.
5. `numpy<2` and uninstalling `ray` were prior environment stabilizers.

Treat these as prior operational notes; re-validate before relying on them in a fresh environment.

---

## 6. Packaging and Submission Flow

On training VM:
```bash
cd ~/nm-ai-2026/task3-Norgesgruppen
zip -j ~/submission.zip run.py best.onnx
```

From Cloud Shell:
```bash
gcloud compute scp yolo-training-vm:~/submission.zip ~/submission.zip --zone=europe-west1-c
```

Then download `~/submission.zip` and submit in app UI.

---

## 7. Pre-Submit Validation Checklist

Before any submission attempt:
1. Archive shape is correct: `run.py` at zip root.
2. Model artifact is included and path-compatible with `run.py`.
3. `run.py` does not import blocked modules.
4. Output format is correct:
   - JSON array
   - each item has `image_id`, `category_id`, `bbox` (`[x,y,w,h]`), `score`
5. Local/VM smoke run produces valid `predictions.json` without runtime crash.
6. Submission size is within competition limit.
7. Submission is approved by operator if they previously asked to wait.

---

## 8. Generic Improvement Priorities

1. Fix inference correctness before heavier retraining.
2. Favor deterministic, reproducible changes over large coupled changes.
3. Keep one variable changed per submission cycle when possible.
4. Log each submission with exact artifact, hypothesis, and outcome in `PastSubmissions.md`.

---

## 9. Guardrails

1. Keep changes traceable: one PR per coherent improvement pass.
2. Do not overwrite historical notes; append with date and rationale.
3. If environment assumptions are uncertain, mark them explicitly and verify before submit.
4. Never treat old score/rank values as current without date-stamped verification.
5. If a change affects runtime risk, prioritize a reliability pass before optimization.

---

## 10. Quick Handoff Prompt

Use this when starting a new Task 3 chat:

"Continue Task 3 from `task3-Norgesgruppen`. First run git freshness check (`main` vs `HEAD`). Then read `AGENT.md`, `PROGRESS.md`, `PastSubmissions.md`, and Task 3 docs. Re-verify current score/rank and submission constraints with exact timestamps. Propose one bounded improvement pass with clear hypothesis, validation steps, and rollback path. If operator says to wait with submit, do not submit until explicit approval."
