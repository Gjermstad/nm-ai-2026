# AGENT.md — Task 2: Astar Island Operator

> NM i AI 2026 — Task 2 handoff/control file
> Last updated: 2026-03-21 (Saturday, Oslo)
> Status: local authenticated live smoke completed on Round 16 with successful 5/5 submissions. Fast reliability fixes applied for floor enforcement and stale submit errors.

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
- Tests: `tests/test_core.py` (6 passing)

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
2. Start app locally and verify UI loads.
3. Set token and verify active round detection.
4. Start run-mode and confirm budget/coverage changes.
5. Rebuild draft and verify all seed validations are ready.
6. Submit one seed manually, then submit all seeds.
7. If stable, deploy/update Cloud Run and repeat smoke test.

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

---

## 5. Known Gaps To Address Next

1. Cloud Run live smoke test still pending for task2 service.
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

---

## 7. Quick Handoff Prompt (for a new chat)

Use this when starting a new session:

"Continue Task 2 Astar from `task2-Astar`. Read `AGENT.md`, `PROGRESS.md`, and `SPEC.md` first, then run a live smoke workflow: start local app, verify active round + query progression, rebuild drafts, validate per-seed readiness, submit one seed then submit all, and report blockers with fixes. Keep the existing architecture; optimize for fast reliable competition execution."
