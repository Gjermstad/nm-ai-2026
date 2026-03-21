# Progress Report: Astar Island Operator (Task 2)

## 0. Latest Session Update (2026-03-21, Saturday ~17:19 Oslo)

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

Not yet performed (important):
- full end-to-end live API smoke test with real token and active round
- real submit acceptance test against active round
- Cloud Run deployment smoke test for this task2 service

---

## 8. Known Gaps / Risks Remaining

### 8.1 Not yet live-validated against current round

Consequence:
- integration details (auth, payload edge cases, timing) might still need small fixes.

Mitigation:
- run immediate live smoke checklist at start of next active window.

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

1. Run live smoke test with real `ASTAR_ACCESS_TOKEN`:
   - confirm active round load
   - confirm background queries increment budget
   - confirm draft validations are green
2. Submit one seed manually and verify accepted response.
3. Submit all seeds and verify completion state.
4. Deploy to Cloud Run and repeat smoke test against hosted URL.
5. Tune safe/aggressive planner weights based on first observed outcomes.

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
