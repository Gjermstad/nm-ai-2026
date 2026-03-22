# AGENT.md — Task 2: Astar Island Operator

> NM i AI 2026 — Task 2 handoff/control file
> Last updated: 2026-03-22 (Sunday, Oslo)
> Status: PR #57 is merged to `main`; Task2 history archive commit `cd86f02` is present on `origin/main`; latest verified Cloud Run revision is `astar-operator-00004-bcv`. Recent completed results: Round 20 `62.8`, Round 21 `66.4`, Round 22 `59.3` (`#213/278`, weight `2.9253x`). Round 23 is active (`id=93c39605-628f-4706-abd9-08582f8b61d7`) and short-final close is `2026-03-22 15:00 CET`. Latest live snapshot (`2026-03-22 13:24 CET`): `queries.used/max=48/50`, `submitted_count=5`, `profile=aggressive`, `run_enabled=true`, `deadline_guard_enabled=true`, `last_error=null`, `fallback_mode=model_artifact_missing`. VM autopilot is patched for controlled push (`aggressive` query mode, `safe` checkpoint submit mode).

---

## 0. Mission and Context

This folder contains a reliability-first operator system for `Astar Island`:
- use direct Task 2 API (`/rounds`, `/simulate`, `/submit`)
- auto query + auto draft prediction generation
- manual submit by default
- deadline guard auto-submit missing seeds at T-20m
- web UI with 4 core tabs: Dashboard, Explorer, Submit, Logs

Primary objective now is not architecture redesign. Primary objective is to validate in live rounds and ship stable score-producing operation before competition close.

---

## 1. Competition-Critical Rules (Do Not Forget)

1. `50` total queries per round across all `5` seeds.
2. Rate limits: `simulate` max `5 rps`, `submit` max `2 rps`.
3. Submit all seeds. Missing seed = major score loss.
4. Never output zero probability. Enforce floor (`0.01`) and renormalize.
5. Round deadline is hard; deadline guard is intentional risk mitigation.

---

## 2. Current Implementation Snapshot

Implemented components:
- Backend service: `main.py`, `backend.py`, `core.py`
- UI: `static/index.html`, `static/app.js`, `static/styles.css`
- Docs: `SPEC.md`, `README.md`, `PROGRESS.md`, `PastRounds.md`
- Tests: `tests/test_core.py` + `tests/test_backend_model.py` (16 passing)

Implemented internal endpoints:
- `GET /health`, `GET /status`, `GET /seed/{seed_index}`
- `POST /run/start`, `POST /run/stop`, `POST /profile/set`, `POST /draft/rebuild`
- `POST /submit/seed`, `POST /submit/all`, `POST /guard/set`, `POST /auth/token`
- `GET /model/status`, `POST /model/reload`
- `GET /logs/recent`

Persisted runtime state:
- `runtime/state.json`

Merged PRs (recent):
- `https://github.com/Gjermstad/nm-ai-2026/pull/19`
- `https://github.com/Gjermstad/nm-ai-2026/pull/57`

Open PR (current):
- none; create a fresh PR for any new non-doc Task 2 code changes

---

## 3. What To Do First In A New Session

Run this exact order:

1. Read these files in order:
   - `task2-Astar/AGENT.md`
   - `task2-Astar/PROGRESS.md`
   - `task2-Astar/PastRounds.md`
   - `task2-Astar/SPEC.md`
2. Check hosted service first (`/health`, `/status`, `/model/status`) and report:
   - `queries.used/max`, `submitted_count`, `run_enabled`, `deadline_guard_enabled`, `last_error`, `seconds_to_close`, `active_round.id/number`, `model_version`, `fallback_mode`.
3. If hosted is unhealthy, start app locally as fallback and verify UI loads.
4. Verify VM autopilot health:
   - `pgrep -af task2_round_autopilot.py`
   - `tail -n 40 /home/kenneth/task2_round_autopilot.log`
   - script should include `FINAL_ROUND_NUMBER = 23` and controlled-profile toggles (`QUERY_PROFILE=aggressive`, `SUBMIT_PROFILE=safe`).
5. For active rounds, prefer monitor-first reliability flow; intervene manually only on severe failures (for example `run_enabled=false`, guard disabled, or submit failures).
6. Do not run long hold loops in-session; arm run/automation and return.
7. Final verify after actions: `submitted_count=5/5`, `run_enabled=true|false` as intended, `last_error=null`.

Screenshot source for post-round analysis:
- `task2-Astar/screenshots/` (expected naming: `Round1X_overview.png`, `Round1X_SeedY_a.png`, `Round1X_SeedY_b.png`)

API source for historical analysis (when authenticated token is available):
- `GET /astar-island/my-rounds`
- `GET /astar-island/analysis/{round_id}/{seed_index}` for seeds `0..4`
- Store derived aggregates in `task2-Astar/PastRounds.md` (Section 11).
- Store machine-readable archive in `task2-Astar/history/`:
  - `raw/api_snapshot_full.json.gz`
  - `summary/api_snapshot_summary.json`
  - `summary/round_seed_diagnostics.json`
- Refresh history files with:
  - `cd task2-Astar/history && python3 export_api_snapshot.py && python3 build_diagnostics_from_snapshot.py`

---

## 4. Operational Commands

### Local run

```bash
cd task2-Astar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ASTAR_ACCESS_TOKEN="<JWT>"
uvicorn main:app --reload --port 8080
```

### Tests / checks

```bash
python3 -m py_compile task2-Astar/core.py task2-Astar/backend.py task2-Astar/main.py
task1-Tripletex/.venv/bin/python -m pytest -q task2-Astar/tests/test_core.py
```

### Cloud Run deploy

If `gcloud` behaves inconsistently with local config, use an isolated config and always pass explicit project:

```bash
export CLOUDSDK_CONFIG=/tmp/gcloud-config
```

```bash
cd task2-Astar
gcloud run deploy astar-operator \
  --project ai-nm26osl-1730 \
  --source . \
  --region europe-north1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 300 \
  --min-instances 1 \
  --set-env-vars ALLOW_TOKEN_UPDATE=true
```

```bash
gcloud run services update astar-operator \
  --project ai-nm26osl-1730 \
  --region europe-north1 \
  --update-env-vars ASTAR_ACCESS_TOKEN=<JWT>,ALLOW_TOKEN_UPDATE=true
```

### Cloud Run quick smoke (hosted)

```bash
BASE="https://astar-operator-u4ol5cv7ra-lz.a.run.app"
curl -sS "$BASE/health"
curl -sS "$BASE/status"
curl -sS -X POST "$BASE/run/start"
sleep 6
curl -sS -X POST "$BASE/run/stop"
curl -sS -X POST "$BASE/draft/rebuild"
curl -sS -X POST "$BASE/submit/seed" -H 'Content-Type: application/json' --data '{"seed_index":0}'
curl -sS -X POST "$BASE/submit/all"
curl -sS "$BASE/status"
```

### Current hosted deployment (verified 2026-03-22)

- Project: `ai-nm26osl-1730`
- Region: `europe-north1`
- Service: `astar-operator`
- URL: `https://astar-operator-u4ol5cv7ra-lz.a.run.app`
- Latest verified revision: `astar-operator-00004-bcv`

### Latest live competition snapshot (2026-03-22, active Round 23 controlled push)

- Active round:
  - `active_round.number=23`
  - `active_round.id=93c39605-628f-4706-abd9-08582f8b61d7`
  - `closes_at=2026-03-22T14:00:00+00:00` (`15:00 CET`)
- Latest live status at `2026-03-22 13:24 CET`:
  - `queries.used/max=48/50`
  - `submitted_count=5`
  - `profile=aggressive`
  - `run_enabled=true`
  - `deadline_guard_enabled=true`
  - `last_error=null`
  - `fallback_mode=model_artifact_missing`
- VM autopilot (`/home/kenneth/task2_round_autopilot.py`) runtime behavior:
  - controlled push patch active: `aggressive` during query collection, `safe` only for `rebuild+submit`, then back to `aggressive`
  - log-confirmed checkpoint execution:
    - baseline `q>=6` => `ok=True`
    - mid `q>=30` => `ok=True`
    - late `q>=48` => `ok=True`
  - final checkpoint remains armed for `T-15m`.
- Last completed-round diagnostics fetched live from API (`rounds 19..22`) show persistent class bias:
  - `Empty` underprediction (`-0.044791`)
  - `Forest` underprediction (`-0.058783`)
  - `Settlement` overprediction (`+0.033254`)
  - `Port` overprediction (`+0.024095`)
  - `Ruin` overprediction (`+0.02833`)
  - `Mountain` overprediction (`+0.017895`)

### Previous between-round snapshot (2026-03-22, pre-Round 23)

- Organizer-confirmed completed rounds:
  - Round 20: `62.8`
  - Round 21: `66.4`
  - Round 22: `59.3` (`#213/278`, weight `2.9253x`)
- Hosted between-round status (after Round 22 close):
  - `active_round=null`
  - `queries.used/max=50/50`
  - `submitted_count=5`
  - `run_enabled=true`
  - `deadline_guard_enabled=true`
  - `last_error=null`
  - `model_version=null`
  - `fallback_mode=model_artifact_missing`
- Final-round operations note:
  - organizers announced Round 23 is shorter and closes exactly `15:00 CET`
  - scores are hidden until final leaderboard reveal (~`17:00 CET`)
  - unattended VM autopilot is armed with Round 23 checkpoints: baseline `q>=6`, mid `q>=30`, late `q>=48`, final `T-15m`.

### Latest hosted smoke snapshot (2026-03-21 ~20:12 Oslo)

- Active round verified:
  - `round_number=17`
  - `round_id=3eb0c25d-28fa-48ca-b8e1-fc249e3918e9`
  - `token_present=true`
- Hosted-first flow executed:
  - `/health` and `/status` confirmed healthy active round
  - `POST /run/start` then `POST /run/stop` succeeded
  - query progression confirmed while run mode enabled: `queries.used 2 -> 3`
  - `POST /draft/rebuild` succeeded
  - per-seed validation confirmed `submit_ready=true` for all 5 seeds
  - `POST /submit/seed` (`seed_index=0`) succeeded
  - `POST /submit/all` succeeded with `failed=[]`
- Final status fields (post-smoke):
  - `queries.used/max=3/50`
  - `submitted_count=5`
  - `run_enabled=false`
  - `last_error=null`
  - `seconds_to_close=5788.32158`

### Round 17 optimization + recovery (2026-03-21 ~20:25-20:38 Oslo)

- Optimization run:
  - set profile to `aggressive`
  - ran hosted query loop from `3/50` to `48/50`
  - coverage reached: seed0 `79.12%`, seed1 `73.06%`, seed2 `73.31%`, seed3 `66.38%`, seed4 `79.75%`
- Incident observed:
  - aggressive rebuild produced `floor_ok=false`/`submit_ready=false` across seeds due numeric near-floor drift (`0.009999...` style values)
- Live recovery (no redeploy during active round):
  - stopped run mode immediately
  - switched profile back to `safe`
  - rebuilt drafts and confirmed `floor_ok_all=true`, `submit_ready_all=true`
  - executed `submit/all` successfully (`failed=[]`)
  - final hosted state: `run_enabled=false`, `queries.used/max=48/50`, `submitted_count=5`, `last_error=null`

### Round 16 screenshot calibration (prepared locally, 2026-03-21 late session)

- Inputs reviewed:
  - full layer-analysis captures for all 5 seeds from Round 16
- Observed bias:
  - consistent `Empty` underprediction
  - diffuse overprediction of `Settlement`/`Port`/`Ruin`
- Calibration patch applied in `core.py`:
  - reduced dynamic-heavy priors (especially non-dynamic/forest starting cells)
  - reduced near-settlement and aggressive dynamic boosts
  - increased posterior smoothing (`alpha`) to reduce noisy class spread
- Regression tests extended in `tests/test_core.py`:
  - guard unknown-terrain empty dominance
  - bound aggressive near-settlement dynamic mass
- Deployment note:
  - calibration patch was merged (PR #36) and deployed to Cloud Run revision `astar-operator-00003-xmc`.

### Round 17/18 operations snapshot (2026-03-21 late session)

- Round 17 final outcome from organizer UI:
  - round score: `51.7`
  - per-seed: `52.1`, `51.2`, `50.4`, `51.4`, `53.4`
  - usage/submission: `50/50` queries, `5/5` submitted
- PR/merge/deploy chain:
  - PR #35 merged (floor tolerance + hosted recovery docs)
  - PR #36 merged (Round 16 screenshot-based calibration)
  - deployed from local `gcloud` CLI (`CLOUDSDK_CONFIG=/tmp/gcloud-config`), not Cloud Shell
- Round 18 live execution:
  - run mode armed and deadline guard enabled
  - reached `40/50`, performed baseline `draft/rebuild` + `submit/all` (`failed=[]`)
  - query loop naturally paused at `48/50` due built-in >30m hold rule in `_run_query_cycle_if_needed`
  - final live state for handoff: `run_enabled=true`, `deadline_guard_enabled=true`, `queries=48/50`, `submitted_count=5`, `last_error=null`

### Round 19 low-evidence tail calibration (local patch, 2026-03-22)

- Added a minimal calibration in `core.py` (no architecture change):
  - for low-evidence cells (`<=1` observations) without direct Port/Ruin/Mountain evidence, cap tails to:
    - `Port <= 0.03`
    - `Ruin <= 0.04`
    - `Mountain <= 0.015`
  - reclaimed mass is redistributed to `Empty`/`Settlement`/`Forest` and re-normalized with existing floor protections.
- Safety constraints preserved:
  - floor safety remains `0.01` in submit paths.
  - deadline guard behavior unchanged.
- Measurable local effect (plains, near-settlement, aggressive, zero observations):
  - rare-tail mass (`Port+Ruin+Mountain`) reduced from `0.114` to `0.085`.
- Regression coverage added in `tests/test_core.py`:
  - cap applies in low-evidence/no-rare-observation case.
  - cap is skipped when direct rare-class evidence exists.

### History-aware linear model v1 integration (2026-03-22)

- Added deterministic trainer and model artifact path:
  - `task2-Astar/history/train_linear_model.py`
  - `task2-Astar/history/models/latest_linear_v1.json`
- Added offline replay evaluator:
  - `task2-Astar/history/replay_evaluate_model.py`
  - output: `task2-Astar/history/summary/replay_eval_linear_v1.json`
- Runtime integration:
  - learned model auto-load at startup with schema validation (`linear_v1`)
  - strict fallback to heuristic mode when artifact is missing/invalid
  - learned corrections applied in `rebuild_drafts` only when model is loaded
  - phase-B query scorer now uses learned weights + fairness boost + bounded late-phase feature
- New runtime observability:
  - `/status` now includes `model_version`, `feature_set_version`, `fallback_mode`, and `query_policy` summary
  - `/model/status` and `/model/reload` are available for live checks/reload

---

## 5. Known Gaps To Address Next

1. Token lifecycle hardening still needed (use Secret Manager + rotation policy instead of static env var).
2. Planner is heuristic baseline; post-round calibration may improve leaderboard upside.
3. No integration tests for API client/service flow yet (only core unit tests).

---

## 6. Guardrails For Future Changes

1. Keep reliability over sophistication unless explicitly requested.
2. Do not remove deadline guard without replacement.
3. Keep probability-floor protections.
4. If changing payload shape logic, re-run validation tests and add new tests.
5. Update both `task2-Astar/AGENT.md` and `task2-Astar/PROGRESS.md` after meaningful changes.
6. When syncing organizer docs through MCP, fetch each resource with retries and a fresh `initialize` session per resource to avoid intermittent `Session not found` failures.
7. Treat organizer docs as canonical, but sanitize obvious upstream artifacts/noise before saving local copies.
8. Do not paste raw access tokens in logs/docs/PR text; store in env/secret systems only.
9. Assume merged PRs are closed; create a fresh branch + new PR for follow-up commits (do not reuse prior merged PR).
10. Do not block the session by waiting in long hold loops (for example, waiting at `48/50` until T-30m). Arm run mode and return control to operator.
11. If operator says to wait before submitting, do not execute submit endpoints until explicit go-ahead.
12. Ingest all newly added round screenshots from `task2-Astar/screenshots/` into `task2-Astar/PastRounds.md` before making new model-tuning choices.
13. Refresh the API-derived archive in `task2-Astar/PastRounds.md` after completed rounds when authenticated access is available, including non-submitted rounds.
14. Keep `task2-Astar/history/raw/api_snapshot_full.json.gz`, `task2-Astar/history/summary/api_snapshot_summary.json`, and `task2-Astar/history/summary/round_seed_diagnostics.json` refreshed so future sessions can recover full historical signal fast.
15. Before model-tuning edits, ingest the latest diagnostics from `task2-Astar/history/summary/round_seed_diagnostics.json` into `task2-Astar/PastRounds.md` and record explicit calibration decisions.
16. Keep low-evidence Port/Ruin/Mountain suppression conservative and measurable; if adjusting caps, update tests and log before/after tail mass in `PastRounds.md`.

---

## 7. Quick Handoff Prompt (for a new chat)

Use this when starting a new session:

"Continue Task 2 Astar only from `task2-Astar`. Read `AGENT.md`, `PROGRESS.md`, `PastRounds.md`, and `SPEC.md` first. Then load `task2-Astar/history/summary/api_snapshot_summary.json`, `task2-Astar/history/summary/round_seed_diagnostics.json`, and `task2-Astar/history/summary/replay_eval_linear_v1.json`. Confirm live `/status` + `/model/status` and report `queries.used/max`, `submitted_count`, `run_enabled`, `deadline_guard_enabled`, `last_error`, `seconds_to_close`, `active_round.id/number`, `model_version`, and `fallback_mode`. Verify VM autopilot (`/home/kenneth/task2_round_autopilot.py`, log `/home/kenneth/task2_round_autopilot.log`) is healthy. For final-round operations, prioritize reliability and only do manual submit interventions on severe failure."
