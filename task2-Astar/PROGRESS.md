# Progress Report: Astar Island Operator (Task 2)

## 0. Latest Session Update (2026-03-22, Sunday ~01:05 Oslo)

- Added full machine-readable Task 2 history archive under `task2-Astar/history/`:
  - `raw/api_snapshot_full.json.gz`
  - `summary/api_snapshot_summary.json`
  - `summary/my_rounds_raw.json`
  - `summary/api_snapshot_meta.json`
  - `summary/round_seed_diagnostics.json`
- Added history tooling:
  - `task2-Astar/history/export_api_snapshot.py`
  - `task2-Astar/history/build_diagnostics_from_snapshot.py`
  - `task2-Astar/history/README.md`
- Updated `task2-Astar/AGENT.md` with explicit next-thread loading/refresh paths:
  - read `AGENT.md` -> `PROGRESS.md` -> `PastRounds.md` -> `SPEC.md`
  - then load history summaries from `task2-Astar/history/summary/`
  - refresh command documented:
    - `cd task2-Astar/history && python3 export_api_snapshot.py && python3 build_diagnostics_from_snapshot.py`
- Handoff intent:
  - future sessions should not rely only on screenshots; use `PastRounds.md` + history summaries together before tuning.

## 0.1 Previous Session Update (2026-03-22, Sunday ~00:25 Oslo)

- Expanded `task2-Astar/PastRounds.md` with a new API-derived historical archive section covering all rounds (`1..18` at fetch time).
- Added round-by-round team ledger from authenticated API (`my-rounds`), including submitted and non-submitted rounds:
  - status, weight, score, seeds submitted, queries used, analysis availability, and prediction availability.
- Added full completed-round (`1..17`) ground-truth dynamics table:
  - per-round mean entropy
  - per-round mean class distribution
  - per-round dynamic mass (`Settlement+Port+Ruin`)
- Added global priors derived from API analysis:
  - overall class means across all completed rounds
  - per-initial-terrain-code (`1/2/4/5/10/11`) entropy and class means
- Added API bias diagnostics for submitted rounds 16 and 17:
  - explicit `prediction_mean - ground_truth_mean` deltas per class
  - confirmed persistent overprediction of `Port`/`Ruin` and residual overprediction of `Mountain`
  - confirmed Round 17 settlement underprediction remains a major lever
- Operational outcome:
  - we now have enough historical signal to tune priors from real ground-truth statistics instead of screenshot-only inference.

## 0.2 Previous Session Update (2026-03-21, Saturday ~23:35 Oslo)

- Created new long-form screenshot memory file:
  - `task2-Astar/PastRounds.md`
- Ingested all available post-round screenshots into structured memory with explicit tags:
  - `OBSERVED`, `INFERRED`, `ASSUMPTION`, `DECISION`
  - source folder: `task2-Astar/screenshots/`
  - files covered: 22 total (`Round16_*` and `Round17_*`, including overview + all seed a/b splits)
- `PastRounds.md` now includes:
  - strict update protocol and evidence legend
  - complete screenshot inventory with coverage checks
  - round-level and seed-level analysis for Round 16 and Round 17
  - per-seed class-bias matrices (Empty/Settlement/Port/Ruin/Forest/Mountain)
  - cross-round synthesis and high-confidence tuning priorities
  - operator-ready next-round checklist and quick-loader section
- Updated handoff docs to make screenshot intelligence first-class:
  - `task2-Astar/AGENT.md` read order now includes `PastRounds.md`
  - added guardrail: ingest new screenshots into `PastRounds.md` before model-tuning decisions
  - added screenshot source/path conventions to the startup workflow
- Explicit process reminder:
  - after every completed round, save screenshots to `task2-Astar/screenshots/` and update `task2-Astar/PastRounds.md` in the same session to avoid knowledge loss.

## 0.3 Previous Session Update (2026-03-21, Saturday ~23:00 Oslo)

- Round 17 final organizer result confirmed from screenshots:
  - average: `51.7` points
  - per-seed: `52.1`, `51.2`, `50.4`, `51.4`, `53.4`
  - usage/submission: `50/50` queries, `5/5` submitted
- PR/deploy continuity:
  - PR #35 merged (floor-tolerance hardening + hosted recovery notes)
  - PR #36 merged (Round 16 screenshot-driven calibration)
  - deployed merged code to Cloud Run revision `astar-operator-00003-xmc`
  - deploy performed via local `gcloud` CLI using `CLOUDSDK_CONFIG=/tmp/gcloud-config` (not Cloud Shell)
- Round 18 operations completed so far:
  - `run_enabled=true`, `deadline_guard_enabled=true`, `profile=safe`
  - progressed to `40/50`, executed baseline `draft/rebuild` + `submit/all` (`failed=[]`)
  - progressed to `48/50`, `submitted_count=5`
  - service intentionally pauses auto-query at `48/50` while `seconds_to_close > 30m` due built-in guard in `_run_query_cycle_if_needed`
  - current live handoff status snapshot:
    - `queries.used/max=48/50`
    - `submitted_count=5`
    - `run_enabled=true`
    - `deadline_guard_enabled=true`
    - `last_error=null`
    - `seconds_to_close=6362.694253`
- Operator preferences captured for future sessions:
  - never reuse merged PRs; always create a fresh PR for follow-up changes
  - do not block the chat by waiting in long hold loops; arm run and return availability
  - if operator says “wait with submit”, do not call submit endpoints until explicit go-ahead

## 0.4 Previous Session Update (2026-03-21, Saturday ~20:50 Oslo)

- Incorporated Round 16 post-mortem screenshots (all 5 seeds, layer-analysis) for calibration:
  - consistent pattern found: `Empty` underprediction and overly diffuse `Settlement`/`Port`/`Ruin` mass
- Applied calibration patch in `task2-Astar/core.py` (no architecture changes):
  - reduced dynamic-heavy priors for non-water/non-mountain cells
  - reduced near-settlement dynamic spread boost
  - reduced aggressive global dynamic boost
  - increased posterior smoothing (`alpha`) to suppress noisy over-spread
- Added regression guards in `task2-Astar/tests/test_core.py`:
  - `test_unknown_terrain_prior_stays_empty_dominant`
  - `test_near_settlement_aggressive_prior_is_bounded`
- Validation:
  - `python3 -m py_compile task2-Astar/core.py task2-Astar/backend.py task2-Astar/main.py` passed
  - `pytest -q task2-Astar/tests/test_core.py` => `9 passed`
- Deployment status:
  - tuning patch prepared and pushed to PR branch for review
  - intentionally not auto-deployed mid-round.

## 0.5 Previous Session Update (2026-03-21, Saturday ~20:38 Oslo)

- Goal for this pass: maximize Round 17 score while preserving deadline safety.
- Live hosted optimization run executed on `https://astar-operator-u4ol5cv7ra-lz.a.run.app`:
  - profile switched to `aggressive`
  - run mode enabled and monitored
  - query usage increased from `3/50` to `48/50`
  - run mode stopped before deadline-risk window
- Issue encountered during aggressive rebuild:
  - `/status` reported `floor_ok=false` + `submit_ready=false` across seeds
  - validation errors were near-floor drift (`0.009999...`) rather than hard logic failures
  - stale error observed: `last_error=\"Submit failed for seed 4\"`
- Live recovery used for active round safety (no mid-round redeploy):
  - switched profile to `safe`
  - `POST /draft/rebuild` => succeeded
  - `/status` confirmed `floor_ok_all=true` and `submit_ready_all=true`
  - `POST /submit/all` => accepted for all seeds (`failed=[]`)
- Final hosted state after recovery submit:
  - `queries.used/max=48/50`
  - `submitted_count=5`
  - `run_enabled=false`
  - `last_error=null`
  - `seconds_to_close=4222.116424`
  - per-seed query distribution: seed0 `11`, seed1 `8`, seed2 `8`, seed3 `10`, seed4 `10`
- Local code hardening prepared (not redeployed mid-round to avoid state loss risk):
  - `task2-Astar/core.py`: numeric floor handling improved to avoid `0.009999...` false floor failures
  - `task2-Astar/tests/test_core.py`: added regression for near-floor float roundoff in validation
  - local tests: `pytest -q task2-Astar/tests/test_core.py` => `7 passed`

## 0.6 Previous Session Update (2026-03-21, Saturday ~20:12 Oslo)

- Continued Task 2 with required file-read order:
  - `task2-Astar/AGENT.md`
  - `task2-Astar/PROGRESS.md`
  - `task2-Astar/SPEC.md`
- Executed hosted-first smoke against:
  - `https://astar-operator-u4ol5cv7ra-lz.a.run.app`
- Hosted checks and actions:
  - `/health` confirmed `status=ok`, active round 17, `token_present=true`
  - initial `/status` confirmed active round 17 with `queries.used/max=2/50`, `submitted_count=5`, `run_enabled=false`, `last_error=null`
  - `POST /run/start` succeeded; during run `/status` showed query progression `2 -> 3`
  - `POST /run/stop` succeeded (`run_enabled=false`)
  - `POST /draft/rebuild` succeeded (`{"status":"ok","seeds":5}`)
  - post-rebuild `/status` confirmed per-seed `validation.submit_ready=true` for all 5 seeds
  - `POST /submit/seed` with `seed_index=0` accepted
  - `POST /submit/all` accepted (`failed=[]`, all seeds accepted)
- Final hosted state captured from `/status`:
  - `queries.used/max=3/50`
  - `submitted_count=5`
  - `run_enabled=false`
  - `last_error=null`
  - `seconds_to_close=5788.32158`
- Hosted blocker + fix in this environment:
  - initial sandboxed DNS call to `run.app` failed (`Could not resolve host`)
  - fixed by rerunning hosted smoke with unrestricted network execution; local fallback was not required because hosted flow succeeded end-to-end.
- Reliability constraints preserved:
  - no architecture changes
  - floor safety (`0.01`) and deadline guard behavior unchanged

## 0.7 Previous Session Update (2026-03-21, Saturday ~20:02 Oslo)

- Deployed Task 2 service to Cloud Run in GCP project `ai-nm26osl-1730`:
  - service: `astar-operator`
  - region: `europe-north1`
  - URL: `https://astar-operator-u4ol5cv7ra-lz.a.run.app`
  - active revision after env update: `astar-operator-00002-6zj`
- Completed hosted end-to-end smoke on active Round 17 (`id=3eb0c25d-28fa-48ca-b8e1-fc249e3918e9`):
  - `/health` and `/status` confirmed active round and healthy service
  - token set via hosted `/auth/token`, then persisted as Cloud Run env var
  - `run/start` increased query count (`0 -> 1`, later `2/50` confirmed)
  - `run/stop`, `draft/rebuild`, `submit/seed` and `submit/all` all succeeded
  - final hosted status during smoke: `submitted_count=5/5`, `run_enabled=false`, `last_error=null`, `token_present=true`
- Environment and deploy blockers found + fixed:
  - `gcloud` CLI missing locally -> installed `gcloud-cli`
  - installer failed due missing Python path -> upgraded `python@3.13`, reran install successfully
  - gcloud session initially unauthenticated -> completed `gcloud auth login --no-launch-browser`
  - used isolated Cloud SDK config (`CLOUDSDK_CONFIG=/tmp/gcloud-config`) for deterministic auth/project behavior in session
  - Cloud SDK in this environment required explicit `--project ai-nm26osl-1730` on commands
  - sandbox DNS blocked `run.app` checks -> used unrestricted network execution for hosted smoke verification
- Why this matters:
  - removes laptop dependency during live rounds
  - gives a stable hosted operator path with repeatable run/submit workflow
  - preserves a ready fallback: local app still works if Cloud Run has transient issues

### 0.1 Cloud Resume Commands (verified)

```bash
# one-time auth (if needed)
gcloud auth login devstar17301@gcplab.me --no-launch-browser
gcloud config set project ai-nm26osl-1730
gcloud config set run/region europe-north1

# deploy/update task2 service
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

gcloud run services update astar-operator \
  --project ai-nm26osl-1730 \
  --region europe-north1 \
  --update-env-vars ASTAR_ACCESS_TOKEN=<JWT>,ALLOW_TOKEN_UPDATE=true
```

- Synced local organizer docs in `task2-Astar/task2_docs_*.md` against live MCP resources:
  - `challenge://astar-island/overview`
  - `challenge://astar-island/mechanics`
  - `challenge://astar-island/endpoint`
  - `challenge://astar-island/scoring`
  - `challenge://astar-island/quickstart`
- Applied merge + sanitize policy:
  - adopted upstream content for all 5 docs
  - preserved local operator note in overview (round replay/history after round close)
  - removed upstream artifact text `Stashed changes` from scoring
- Added future reliability rule in `AGENT.md` for doc sync:
  - use retries + fresh MCP `initialize` per resource because endpoint occasionally returns `Session not found`.

- Completed full authenticated local live smoke on active Round 16 (`id=8f664aed-8839-4c85-bed0-77a2cac7c6f5`):
  - token set via `/auth/token`
  - run mode started and query progression confirmed (`0 -> 7`, coverage increased per seed)
  - draft rebuild succeeded
  - per-seed readiness confirmed (`submit_ready=true` for all seeds after fix)
  - `submit one` succeeded (`seed 0`)
  - `submit all` succeeded with no failures (`5/5` accepted)
- Production blocker found and fixed:
  - issue: after live queries, multiple cells fell below floor `0.01`, causing validation failure and blocked submit for 4 seeds.
  - root cause: `normalize_with_floor()` floored values before renormalization, then renormalization pushed some values below floor.
  - fix: replaced normalization with strict floor-preserving redistribution in `task2-Astar/core.py`.
  - test hardening: `test_normalize_with_floor` now enforces `min(prob) >= 0.01`.
- Additional reliability fix in `task2-Astar/backend.py`:
  - successful submit now clears stale `"Submit failed ..."` `last_error` state.
- Regression checks after fixes:
  - `py_compile` passed for `core.py`, `backend.py`, `main.py`
  - `pytest task2-Astar/tests/test_core.py` => `6 passed`

### 0.2 Previous Session Snapshot (2026-03-21, Saturday ~17:50 Oslo)

- Re-ran the requested local live smoke workflow against a real active round:
  - app started, active round detected (`round_number=16`)
  - run mode toggled and monitored
  - draft rebuild completed
  - per-seed validation readiness confirmed green (`5/5`)
  - `submit one` and `submit all` flows executed
- Primary blocker found: no `ASTAR_ACCESS_TOKEN` available in the local runtime, so query progression stayed at `0/50` and submit calls returned `401`.
- Reliability patch applied in `task2-Astar/backend.py`:
  - missing-token recovery action now points to env or `/auth/token` (no misleading “restart” text)
  - setting token at runtime now clears stale `Missing ASTAR_ACCESS_TOKEN` error state.
- Regression checks passed after patch:
  - `py_compile` passed for `core.py`, `backend.py`, `main.py`
  - `pytest task2-Astar/tests/test_core.py` => `6 passed`

### 0.3 Previous Session Snapshot (2026-03-21, Saturday ~17:19 Oslo)

- PR #19 is merged to `main`, and the feature branch was deleted after merge.
- The implemented Task 2 stack is now the baseline in repository `main`.
- Current local workspace is clean for tracked files; only unrelated untracked `.claude/` exists.
- New `task2-Astar/AGENT.md` has been added to support fresh-session handoff for this task.
- Immediate focus remains live validation during active round windows (query progression, draft readiness, submit flow, and deadline guard behavior).

### New Session Prompt (copy/paste)

`Continue Task 2 Astar from task2-Astar. Read AGENT.md, PROGRESS.md, and SPEC.md first, then run a live smoke workflow: start local app, verify active round + query progression, rebuild drafts, validate per-seed readiness, submit one seed then submit all, and report blockers with fixes. Keep the existing architecture; optimize for fast reliable competition execution.`

---

## 1. Current State (as of 2026-03-21)

A complete v1 implementation exists in `task2-Astar/` for a direct API-driven operator service and web dashboard.

This implementation follows the agreed fast/reliable plan:
- direct `api.ainm.no/astar-island` integration (`/rounds`, `/simulate`, `/submit`)
- 4-tab web UI (`Dashboard`, `Explorer`, `Submit`, `Logs`)
- auto query + auto draft generation
- manual submit by default
- deadline guard auto-submits missing seeds at T-20m

No legacy task2 code existed before this work. This is a greenfield implementation.

---

## 2. What Was Implemented

### 2.1 Backend service and orchestration

Implemented in:
- `task2-Astar/main.py`
- `task2-Astar/backend.py`
- `task2-Astar/core.py`

#### Service responsibilities

- Poll active round and round metadata.
- Load map initial states for all seeds.
- Track query budget (`used`, `max`, `remaining`).
- Execute query planner in background when run-mode is enabled.
- Ingest stochastic viewport observations and update cell-wise counts.
- Build per-seed `40x40x6` prediction tensors.
- Validate draft tensors before submit.
- Submit one seed or all seeds.
- Auto-submit pending valid seeds when `seconds_to_close <= 20 minutes` and deadline guard is enabled.
- Persist runtime state to disk (`runtime/state.json`) so service restarts do not wipe session progress.

#### API client behavior

- Supports bearer/cookie token via `ASTAR_ACCESS_TOKEN`.
- Built-in per-endpoint rate control buckets:
  - `simulate`: 5 rps
  - `submit`: 2 rps
- Retries with exponential backoff on transient network failures and 429.
- Raises structured `ApiError` with status + payload for UI/logging.

### 2.2 Query strategy implemented

#### Safe profile (default)

- Two-phase behavior:
1. Scouting phase for first 25 queries:
   - mixed windows from settlement-centered and map coverage positions
   - interleaves across seeds
2. Focus phase after 25 queries:
   - scores candidate windows by uncertainty + unvisited cells + settlement proximity
   - penalizes repeated windows

#### Aggressive profile

- Same planner framework, different scoring weights to prioritize dynamic/high-entropy zones more heavily.
- Manual toggle via API/UI only.

### 2.3 Prediction logic implemented

- Terrain-to-class mapping from docs:
  - `10,11,0 -> class 0`
  - `1..5 -> class 1..5`
- Prior distributions derived from initial terrain and settlement proximity.
- Posterior-like update with observation counts (`observed_counts`) and profile-dependent smoothing (`alpha`).
- Hard safety floor for all classes (`0.01`) + renormalization.
- Per-cell uncertainty (entropy) and confidence (`max prob`) computed for UI and planner.

### 2.4 Validation and submit safety

`validate_prediction_tensor()` checks:
- shape = `H x W x 6`
- non-negative values
- sum per cell ~= 1.0 (`±0.01`)
- floor compliance

Submit actions reject non-ready drafts.

### 2.5 Web dashboard (v1)

Implemented in:
- `task2-Astar/static/index.html`
- `task2-Astar/static/app.js`
- `task2-Astar/static/styles.css`

#### Tabs

- `Dashboard`: round/deadline/budget/submissions/control panel + per-seed summary
- `Explorer`: seed tabs (`0..4`) with layer toggle and viewport overlay
- `Submit`: per-seed readiness cards + submit controls
- `Logs`: structured log feed with level filter

#### Extensibility implemented

Tab registry includes planned future tabs as disabled:
- `Rounds`, `Metrics`, `Backtest`, `Research`, `Autoiterate`

This was done intentionally so we can enable/attach future pages without refactoring tab plumbing.

### 2.6 Spec and docs

- `task2-Astar/SPEC.md` created and filled with the agreed design/constraints.
- `task2-Astar/README.md` created with run/deploy instructions.
- `task2-Astar/PROGRESS.md` (this file) created for LLM/operator handoff.

### 2.7 Project setup and tests

Added:
- `task2-Astar/requirements.txt`
- `task2-Astar/Dockerfile`
- `task2-Astar/tests/test_core.py`

Tested:
- Python compile checks passed for `core.py`, `backend.py`, `main.py`.
- `tests/test_core.py`: 6 passing tests (mapping, floor normalization, validation, viewport clamp).

---

## 3. Why These Choices Were Made

### 3.1 Direct API integration (not `/solve` endpoint)

Reason:
- Task2 docs and app flow indicate direct simulator querying and prediction submission.
- This removes unnecessary integration complexity and gets us to working operations faster.

Tradeoff accepted:
- If competition platform later requires a hosted endpoint for Task2, an adapter layer may be needed.

### 3.2 4-tab UI scope

Reason:
- Time-constrained delivery favors operational reliability over experimentation tooling.
- Dashboard/Explorer/Submit/Logs are enough to operate safely and submit on time.

Tradeoff accepted:
- Less built-in backtesting/research now. These are planned via disabled tabs.

### 3.3 Background orchestrator + manual submit default

Reason:
- Operator fatigue and sleep windows are real risks.
- Automation gathers data/drafts continuously while preserving manual control.

Tradeoff accepted:
- More state management complexity than a one-shot script, but far better operational safety.

### 3.4 T-20m deadline guard

Reason:
- Missing one seed can cause severe score damage.
- Guard is a risk-control mechanism that keeps manual-first workflow but prevents total miss.

Tradeoff accepted:
- Could auto-submit drafts that are not fully optimized. Chosen intentionally over missing deadline.

### 3.5 Probability floor at 0.01

Reason:
- Required to avoid KL divergence blowups from zeros.
- Matches scoring doc guidance.

Tradeoff accepted:
- Slightly less sharp distributions, but dramatically lower catastrophic risk.

---

## 4. Implemented Internal API Surface

From `main.py`:
- `GET /`
- `GET /health`
- `GET /status`
- `GET /seed/{seed_index}`
- `POST /run/start`
- `POST /run/stop`
- `POST /run/set`
- `POST /profile/set`
- `POST /draft/rebuild`
- `POST /submit/seed`
- `POST /submit/all`
- `POST /guard/set`
- `POST /auth/token`
- `GET /logs/recent`

Notes:
- `/auth/token` is controlled by `ALLOW_TOKEN_UPDATE` env var (default true).
- Service starts background loop on app startup via FastAPI lifespan.

---

## 5. Runtime Data Model Summary

Persisted key state fields (`runtime/state.json`):
- global:
  - `run_enabled`, `profile`, `deadline_guard_enabled`
  - `active_round`
  - `queries`
  - `seeds`
  - `scouting_plan`
  - `last_error`, `last_error_action`
- per-seed:
  - `initial_grid`, `initial_settlements`
  - `near_settlement_mask`
  - `observed_visits`, `observed_counts`
  - `queried_windows`, `last_viewport`
  - `draft`, `argmax_grid`, `uncertainty_grid`
  - `validation`
  - `submitted`, `submitted_at`, `submit_status`
  - coverage/confidence/entropy summary metrics

---

## 6. Operational Instructions (for next LLM/operator)

### 6.1 Local run

```bash
cd task2-Astar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ASTAR_ACCESS_TOKEN="<JWT>"
uvicorn main:app --reload --port 8080
```

Open `http://localhost:8080`.

### 6.2 Cloud Run deploy

```bash
cd task2-Astar
gcloud run deploy astar-operator \
  --source . \
  --region europe-north1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 300 \
  --min-instances 1 \
  --set-env-vars ASTAR_ACCESS_TOKEN=<JWT>
```

### 6.3 Recommended live workflow

1. Set token.
2. Verify active round appears on Dashboard.
3. Click `Start Run`.
4. Watch per-seed coverage and validation readiness.
5. Rebuild draft as needed.
6. Submit selected seeds manually.
7. Use `Submit All` when ready.
8. Keep deadline guard enabled as fallback.

---

## 7. Verification Performed

Executed successfully:

```bash
python3 -m py_compile task2-Astar/core.py task2-Astar/backend.py task2-Astar/main.py
```

```bash
task1-Tripletex/.venv/bin/python -m pytest -q task2-Astar/tests/test_core.py
# Result: 6 passed
```

Live smoke (local app, 2026-03-21 ~17:45-17:50 Oslo):
- `GET /health` and `GET /status`: active round loaded correctly.
- `POST /run/start` + wait: run enabled, but no token => `last_error=Missing ASTAR_ACCESS_TOKEN`; queries remained unchanged.
- `POST /draft/rebuild`: succeeded.
- Readiness check: all seeds `submit_ready=true`.
- `POST /submit/seed` and `POST /submit/all`: expected auth failures (`401`) without token.
- Targeted patch validation: setting runtime token clears stale missing-token error.

Live smoke + submit (local app, authenticated, 2026-03-21 ~18:00 Oslo):
- Query progression confirmed while run-mode enabled (`queries used 0 -> 7`).
- Pre-fix submit blocker reproduced: `floor_ok=false` after live observations caused submit rejection.
- Post-fix behavior confirmed:
  - all seeds `submit_ready=true` and `floor_ok=true`
  - `POST /submit/seed` accepted
  - `POST /submit/all` accepted with `failed=[]`
  - final submit state `submitted_count=5/5`.

Not yet performed (important):
- Cloud Run deployment smoke test for this task2 service

---

## 8. Known Gaps / Risks Remaining

### 8.1 Cloud Run still not live-validated

Consequence:
- local flow is proven, but hosted deployment can still have env/auth/runtime differences.

Mitigation:
- deploy/update Cloud Run service and run the same smoke checklist immediately.

### 8.2 Planner is heuristic, not model-calibrated

Consequence:
- safe baseline likely solid, but leaderboard ceiling may be limited.

Mitigation:
- once stable, add post-round calibration and profile tuning using analysis data.

### 8.3 Submit-all currently includes all seeds

Consequence:
- by design this is simple and safe, but no UI filter for selective multi-seed submit.

Mitigation:
- add per-seed selection model if needed.

### 8.4 Token handling

Consequence:
- token is in-memory and can be set via UI endpoint.

Mitigation:
- for production hardening, disable runtime token update and inject via secret/env only.

### 8.5 No integration tests with mocked HTTP layer

Consequence:
- regressions in API edge handling may slip.

Mitigation:
- next step add unit/integration tests for `AstarApiClient` and `AstarService` flows.

---

## 9. Immediate Next Actions (Priority Order)

1. Deploy/update Cloud Run and execute the same authenticated smoke checklist there.
2. Verify hosted dashboard shows accurate `submitted_count`, budget, and deadline risk.
3. Add small integration tests around `normalize_with_floor()` and `submit` readiness transitions.
4. Tune safe/aggressive planner weights based on completed-round analysis outputs.

---

## 10. File Map (for another LLM)

Core logic:
- `task2-Astar/core.py`
- `task2-Astar/backend.py`
- `task2-Astar/main.py`

Frontend:
- `task2-Astar/static/index.html`
- `task2-Astar/static/styles.css`
- `task2-Astar/static/app.js`

Config/deploy:
- `task2-Astar/requirements.txt`
- `task2-Astar/Dockerfile`

Docs:
- `task2-Astar/SPEC.md`
- `task2-Astar/README.md`
- `task2-Astar/PROGRESS.md`

Tests:
- `task2-Astar/tests/test_core.py`

---

## 11. Summary for Handoff

The system is implemented and internally validated at core-logic level.

It is designed for reliability-first operations under tight competition time:
- automation for observation and draft generation
- manual-first submit controls
- T-20m guardrail to prevent missed seeds
- clear monitoring UI for budget, readiness, errors, and logs

The highest-value next work is live validation and small integration fixes, not architectural changes.
