# Task 2 Astar Island Operator

This folder contains our competition operator for **NM i AI 2026 Task 2 (Astar Island)**.

This README is written for humans and is meant to explain:
- what this task is,
- what we built,
- what worked,
- what did not work,
- what we learned,
- and what we would do better next time.

Important context:
- This text is written on **March 22, 2026**, **before Round 23 is over**.
- Final outcome for Round 23 is therefore unknown at the time of writing.

## What This Task Actually Is

Astar Island is a probabilistic prediction challenge:
- each round has a `40x40` map,
- each round has `5` seeds,
- we get `50` simulation queries total across all seeds,
- we submit a full `H x W x 6` probability tensor per seed.

Scoring is entropy-weighted KL divergence, which means:
- dynamic/high-uncertainty cells matter most,
- overconfident wrong predictions are expensive,
- setting a class probability to `0.0` can destroy score.

Our non-negotiables:
- always submit all 5 seeds,
- always enforce floor `0.01`,
- always keep deadline guard enabled.

## What We Built

### 1) A reliable operator service
- Direct API integration (`/rounds`, `/simulate`, `/submit`) via backend.
- Web UI for live operation:
  - `Dashboard`
  - `Explorer`
  - `Submit`
  - `Logs`
- Runtime controls for:
  - query loop (`run/start`, `run/stop`)
  - profile (`safe`, `aggressive`)
  - rebuild and submit
  - guard toggle
  - health/status/error monitoring

### 2) Safety guardrails
- Hard probability floor `0.01` + validation before submit.
- Deadline guard for forced reliability near close.
- Persistent state in `runtime/state.json`.

### 3) History-aware learning pipeline
- Added history export/diagnostics workflow under `task2-Astar/history/`.
- Added linear model training (`train_linear_model.py`).
- Added replay evaluation (`replay_evaluate_model.py`).
- Added strict fallback mode when model artifact is missing or invalid.

### 4) Unattended VM autopilot for final-round operations
- VM process monitors `/status` and executes checkpoint rebuild+submit.
- Final-round checkpoint strategy:
  - baseline at `q>=6`
  - mid at `q>=30`
  - late at `q>=48`
  - final at `T-15m`

## What Happened During Late Rounds

Recent completed rounds (before Round 23 closes):

| Round | Score | Rank |
|---|---:|---:|
| 19 | 44.0 | 197/228 |
| 20 | 62.8 | 148/181 |
| 21 | 66.4 | 184/225 |
| 22 | 59.3 | 213/278 |

The pattern:
- we recovered strongly from Round 19 to 20/21,
- then dropped again in Round 22.

## What Went Wrong

### 1) We carried persistent class-bias drift for too long
From rounds 19-22 analysis:
- underprediction: `Empty`, `Forest`
- overprediction: `Settlement`, `Port`, `Ruin`, `Mountain`

In plain language:
- we still spread too much probability mass into dynamic/rare classes in many regions,
- and under-anchored more stable classes.

### 2) We had operational friction that cost confidence/time
- Branch/worktree freshness issues between merged PRs and active work.
- Mid-round caution sometimes slowed down experimentation.
- One autopilot behavior conflict: it force-reset profile to `safe`, which blocked the intended controlled aggressive push until patched.

### 3) We depended too much on fragmented memory early
- We initially relied on ad-hoc screenshots and manual recall.
- We got better only after centralizing history snapshots + diagnostics.

## What We Did Right

### 1) Reliability-first mindset
- Baseline submissions happened early.
- Guard stayed enabled.
- We avoided risky architecture rewrites late in the competition.
- We treated missed submissions as unacceptable failure and designed around that.

### 2) Fast iteration with guardrails
- Added tests when we changed sensitive probability logic.
- Kept floor safety invariant throughout.
- Introduced fallback behavior instead of hard dependency on learned artifacts.

### 3) Better operations over time
- Cloud Run deployment stabilized.
- VM autopilot reduced manual babysitting risk.
- Checkpoint-based submitting protected score floor during final-round uncertainty.

## How We Got Better

The biggest improvements came from process, not just model tweaks:
- moved from “guess + react” to “measure + decide,”
- built a durable history archive,
- wrote down assumptions and decisions in task docs,
- codified final-round operations with checkpoints.

In other words:
- less heroics,
- more system.

## What We Could Do Better Next Time

### 1) Bias correction earlier
- We should have quantified class drift earlier and made it a first-class dashboard metric.

### 2) Round-to-round promotion policy
- We need a stricter canary/promotion rule for model changes:
  - clear replay gates,
  - clear rollback trigger,
  - no ambiguous “maybe deploy” moments.

### 3) Autopilot behavior contracts
- Profile behavior should have been explicit from day one:
  - query mode profile,
  - submit mode profile,
  - and no hidden forced overrides.

### 4) Cleaner branch discipline
- Always branch from fresh `origin/main` before new work.
- This avoids stale assumptions, merge noise, and late stress.

## Honest Pre-Close Assessment (Before Round 23 Ends)

As of writing:
- we have a robust reliability baseline,
- we have improved tooling and documentation,
- we still carry known modeling bias risk,
- final competitive outcome depends on how Round 23 scores.

If we win ground in Round 23, it will likely be because:
- reliability was preserved,
- checkpoint submissions were consistent,
- and controlled aggression was applied without breaking safety.

If we miss, it will likely be because:
- the remaining bias pattern was still too strong in high-entropy cells.

## Practical Appendix (Keep This Handy)

### Quick start (local)

```bash
cd task2-Astar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export ASTAR_ACCESS_TOKEN="<your access_token JWT>"
export ASTAR_BASE_URL="https://api.ainm.no/astar-island"
export ALLOW_TOKEN_UPDATE="true"

uvicorn main:app --reload --port 8080
```

Open [http://localhost:8080](http://localhost:8080).

### Core internal API

- `GET /health`
- `GET /status`
- `GET /seed/{seed_index}`
- `POST /run/start`
- `POST /run/stop`
- `POST /profile/set` with `{ "profile": "safe" | "aggressive" }`
- `POST /draft/rebuild`
- `POST /submit/seed` with `{ "seed_index": 0 }`
- `POST /submit/all`
- `POST /guard/set` with `{ "enabled": true | false }`
- `GET /model/status`
- `POST /model/reload`
- `GET /logs/recent?level=error&limit=200`

### History model workflow

```bash
cd task2-Astar/history
python3 train_linear_model.py
python3 replay_evaluate_model.py
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
