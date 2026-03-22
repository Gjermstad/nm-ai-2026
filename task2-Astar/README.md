# Task 2 Astar Island Operator

Fast, robust operator service for `Astar Island` with:
- direct API integration (`/rounds`, `/simulate`, `/submit`)
- web dashboard (`Dashboard`, `Explorer`, `Submit`, `Logs`)
- auto query + auto draft generation
- manual submit by default
- deadline guard auto-submit at `T-20m`

## Quick Start

```bash
cd task2-Astar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Required for team endpoints
export ASTAR_ACCESS_TOKEN="<your access_token JWT>"

# Optional
export ASTAR_BASE_URL="https://api.ainm.no/astar-island"
export ALLOW_TOKEN_UPDATE="true"

uvicorn main:app --reload --port 8080
```

Open [http://localhost:8080](http://localhost:8080).

## Core API

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

## History-Aware Linear Model (v1)

Train/update model artifact from archived history:

```bash
cd task2-Astar/history
python3 train_linear_model.py
```

Run offline replay/backtest comparison:

```bash
cd task2-Astar/history
python3 replay_evaluate_model.py
```

## Deployment (Cloud Run)

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

## Notes

- `runtime/state.json` persists internal state across restarts.
- The service uses a safe default profile and strict probability floor (`0.01`) to prevent KL blowups.
- Future tabs are planned in the UI registry but disabled in v1.
