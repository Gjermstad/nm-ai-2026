# AGENT.md — Task 2: Astar Island Operator

> NM i AI 2026 — Task 2 handoff/control file
> Last updated: 2026-03-21 (Saturday, Oslo)
> Status: Round 17 optimization run completed with `48/50` queries and refreshed `5/5` hosted submissions (~20:38 Oslo). Aggressive-profile floor validation drift was mitigated live by switching back to safe profile before rebuild+submit; local numeric floor-tolerance patch is prepared and tested.

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
- Docs: `SPEC.md`, `README.md`, `PROGRESS.md`
- Tests: `tests/test_core.py` (7 passing)

Implemented internal endpoints:
- `GET /health`, `GET /status`, `GET /seed/{seed_index}`
- `POST /run/start`, `POST /run/stop`, `POST /profile/set`, `POST /draft/rebuild`
- `POST /submit/seed`, `POST /submit/all`, `POST /guard/set`, `POST /auth/token`
- `GET /logs/recent`

Persisted runtime state:
- `runtime/state.json`

Merged PR:
- `https://github.com/Gjermstad/nm-ai-2026/pull/19`

---

## 3. What To Do First In A New Session

Run this exact order:

1. Read these files in order:
   - `task2-Astar/AGENT.md`
   - `task2-Astar/PROGRESS.md`
   - `task2-Astar/SPEC.md`
2. Check hosted service first (`/health`, `/status`) and confirm active round + token present.
3. If hosted is unhealthy, start app locally as fallback and verify UI loads.
4. Start run-mode and confirm budget/coverage changes.
5. Rebuild draft and verify all seed validations are ready.
6. Submit one seed manually, then submit all seeds.
7. Final verify: `submitted_count=5/5`, `run_enabled=false`, `last_error=null`.

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

### Current hosted deployment (verified 2026-03-21)

- Project: `ai-nm26osl-1730`
- Region: `europe-north1`
- Service: `astar-operator`
- URL: `https://astar-operator-u4ol5cv7ra-lz.a.run.app`
- Latest verified revision: `astar-operator-00002-6zj`

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

---

## 7. Quick Handoff Prompt (for a new chat)

Use this when starting a new session:

"Continue Task 2 Astar from `task2-Astar`. Read `AGENT.md`, `PROGRESS.md`, and `SPEC.md` first, then run a hosted-first smoke workflow (`/health`, `/status`, `run/start`, query progression, `run/stop`, `draft/rebuild`, `submit/seed`, `submit/all`) and only fall back to local if hosted is blocked. Report final `queries.used/max`, `submitted_count`, `run_enabled`, `last_error`, and `seconds_to_close`. Keep the existing architecture; optimize for fast reliable competition execution."
