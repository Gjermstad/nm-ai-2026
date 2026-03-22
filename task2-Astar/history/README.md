# Task 2 API History Archive

This folder stores machine-readable historical exports from authenticated Task 2 APIs.

## Files

- `raw/api_snapshot_full.json.gz`
  - Full archive payload from:
    - `GET /astar-island/my-rounds`
    - `GET /astar-island/my-predictions/{round_id}`
    - `GET /astar-island/analysis/{round_id}/{seed_index}` (all rounds/seeds)
  - Includes full 40x40x6 tensors where available.

- `summary/api_snapshot_summary.json`
  - Compact derived archive:
    - round ledger with metadata
    - per-round entropy/class means
    - global priors
    - submitted-round prediction-vs-ground-truth bias deltas

- `summary/round_seed_diagnostics.json`
  - Per-round/per-seed diagnostics derived from the raw snapshot:
    - confidence stats (`mean/std/p10/p50/p90`)
    - argmax class histograms
    - GT/prediction entropy and class means
    - alignment metrics (`KL`, cross-entropy, Brier-like squared error, L1)
    - dynamic-mass comparison (`Settlement+Port+Ruin`)

- `summary/my_rounds_raw.json`
  - Direct `my-rounds` payload snapshot.

- `summary/api_snapshot_meta.json`
  - Snapshot metadata (timestamp, file names, error count).

- `models/latest_linear_v1.json`
  - Runtime-consumable learned artifact (lightweight linear corrections + query weights).

- `summary/replay_eval_linear_v1.json`
  - Offline replay report comparing heuristic baseline vs learned artifact.

- `train_linear_model.py`
  - Deterministic trainer that builds `models/latest_linear_v1.json` from summary files.

- `replay_evaluate_model.py`
  - Offline evaluator that replays completed rounds from raw snapshot and reports KL/xent/L1/Brier deltas.

## Refresh Command

Set token in your shell, then run:

```bash
cd task2-Astar/history
ASTAR_ACCESS_TOKEN='<JWT>' python3 export_api_snapshot.py
python3 build_diagnostics_from_snapshot.py
python3 train_linear_model.py
python3 replay_evaluate_model.py
```

Expected note:
- Active round analysis endpoints may return `400` before round completion; this is normal and recorded in `errors_count`.

## Usage

- Human-readable synthesis should live in:
  - `task2-Astar/PastRounds.md`
- This folder is the raw + structured source backing those notes.
