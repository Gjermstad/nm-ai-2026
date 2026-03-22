# Task 2 Astar Island SPEC (Reliable-First + History-Aware Learning)

## 0. Current State Snapshot (2026-03-22)
- The operator service is live with direct Task 2 API integration and the reliability safeguards are active:
1. strict probability floor (`0.01`) + validation,
2. deadline guard auto-submit behavior,
3. hosted run/stop/rebuild/submit controls.
- History data is now rich and machine-readable under `task2-Astar/history/`:
1. raw snapshot export,
2. summary aggregates,
3. per-round/per-seed diagnostics,
4. replay evaluation output.
- Gap identified: until this pass, history was mostly used manually for analysis docs; runtime prediction and query planning remained mostly static heuristics.
- Operational lesson:
1. Round 18 (completed 2026-03-21) dropped to `25.2` points and highlighted model-quality fragility,
2. Round 19 (active 2026-03-22) was baseline-locked early (`submit/all`) to de-risk missed submissions while iteration continues.

## 1. Summary
- Goal: maximize reliable score production for Task 2 by combining:
1. existing robust operator controls,
2. lightweight learned calibration from archived history,
3. strict fallback to heuristic behavior when learned artifacts are missing/invalid.
- Submission contract remains unchanged:
1. use direct Task 2 API (`/rounds`, `/simulate`, `/submit`) from `api.ainm.no/astar-island`,
2. do not rely on validator `/solve` for this task.
- Rollout policy:
1. default: between-round deploys only,
2. exception: at most one emergency hotfix mid-round for severe regressions.

## 2. Architecture
- Runtime architecture remains Cloud Run hosted orchestrator + web dashboard.
- New learning architecture layer:
1. offline deterministic trainer builds a versioned model artifact from history summaries,
2. runtime loader consumes `history/models/latest_linear_v1.json`,
3. runtime falls back to heuristic scoring/prediction if artifact is absent, invalid, or incompatible.
- Design constraint: no architecture rewrite; learned layer augments current system and can be disabled by fallback.

## 3. Interfaces and Data Contracts
- Existing internal endpoints remain:
1. `GET /health`
2. `GET /status`
3. `POST /run/start`
4. `POST /run/stop`
5. `POST /profile/set`
6. `POST /draft/rebuild`
7. `POST /submit/seed`
8. `POST /submit/all`
9. `GET /logs/recent`
10. `GET /seed/{seed_index}`
11. `POST /guard/set`
12. `POST /auth/token`
- Added model endpoints:
13. `GET /model/status`: learned model load status, version, fallback mode, active query policy.
14. `POST /model/reload`: reload model artifact from disk.
- `GET /status` contract extension:
1. `model_version`
2. `feature_set_version`
3. `fallback_mode`
4. `query_policy` summary (active profile weights, fairness boost, late-phase bound).
- Model artifact contract (`linear_v1`):
1. terrain-conditioned prior corrections,
2. global class-bias correction,
3. confidence temperature scalar,
4. learned phase-B query weights and fairness/non-stationarity controls.

## 4. Query and Prediction Strategy
- Submission safety policy remains:
1. baseline early submit for all 5 seeds,
2. optional mid-round rebuild/resubmit,
3. final pre-deadline rebuild/resubmit,
4. deadline guard remains enabled.
- Prediction strategy:
1. base posterior from observed counts + terrain priors,
2. apply learned corrections when model is loaded,
3. enforce floor and validation unchanged.
- Query strategy:
1. Phase A unchanged: scouting-first behavior,
2. Phase B upgraded: learned linear score over entropy, unvisited area, settlement-proximity, repeat penalty,
3. one bounded non-stationarity feature (`queries_used / queries_max`) influences late-round behavior,
4. fairness boost prevents seed starvation under equal-weight scoring.

## 5. Monitoring UI and Operator Controls
- Dashboard/Explorer/Submit/Logs remain the primary operator surfaces.
- Model-awareness requirement in status panels:
1. show `model_version` + `fallback_mode`,
2. surface query-policy summary,
3. keep last blocking error and recovery action visible.

## 6. Feature Priority (Updated)
- Must have:
1. active round detection and query/submit reliability,
2. strict prediction validation with floor guarantees,
3. deadline guard behavior,
4. learned-model runtime loading with strict fallback,
5. status visibility of model/fallback state.
- Should have:
1. deterministic trainer from archived history,
2. replay evaluator with metric deltas (KL/xent/L1/Brier),
3. query fairness controls and non-stationarity feature.
- Nice to have:
1. richer learned models beyond linear v1,
2. automated per-round coefficient retraining and canary promotion.

## 7. Risks, Consequences, Prevention, Fallback
- Risk: learned artifact degrades live behavior.
- Consequence: score regression despite healthy submission flow.
- Prevention:
1. replay gate against heuristic baseline,
2. strict artifact validation,
3. between-round rollout default.
- Fallback: auto-revert to heuristic mode (`fallback_mode`) by missing/invalid artifact handling.
- Risk: mid-round operational failure (auth/network/rate-limit).
- Consequence: missed updates/submits.
- Prevention:
1. early baseline submit,
2. guard on,
3. explicit status monitoring.
- Fallback: emergency hotfix limit = one mid-round patch only when severe.

## 8. Implementation Plan (Forward)
- Step 1: Keep history export/diagnostics refresh workflow current each round close.
- Step 2: Train lightweight linear model artifact (`train_linear_model.py`) from summary diagnostics.
- Step 3: Integrate runtime loader and strict fallback controls.
- Step 4: Apply learned prediction corrections in draft build path.
- Step 5: Replace fixed phase-B constants with learned query weights + fairness + bounded non-stationarity feature.
- Step 6: Add model endpoints (`/model/status`, `/model/reload`) and extend `/status`.
- Step 7: Add replay evaluator (`replay_evaluate_model.py`) and metric gates.
- Step 8: Validate with unit tests + replay checks before round-to-round deployment.

## 9. Test Plan and Acceptance Criteria
- Unit tests:
1. artifact parse/validation + fallback path,
2. learned adjustment still produces valid probability vectors,
3. fairness boost behavior in phase-B query selection,
4. existing floor/shape/sum validation invariants remain green.
- Replay/backtest gates:
1. compare learned vs heuristic on completed rounds,
2. track `KL`, `cross-entropy`, `L1`, `Brier`, and class-bias deltas,
3. learned model must not regress core metrics before promotion.
- Live safety checks:
1. baseline submit remains successful for all seeds,
2. no increase in submit-readiness failures,
3. no new runtime error classes from model loading.
- Acceptance criteria:
1. operator can identify model/fallback mode quickly from `/status`,
2. system remains fully functional in heuristic fallback mode,
3. learned mode produces measurable offline non-regression before live promotion.

## 10. Operational Defaults
- Default runtime profile: `safe`.
- Default guard mode: enabled.
- Floor safety: fixed at `0.01` submit contract.
- Deployment posture:
1. no routine mid-round deploys,
2. one emergency hotfix allowed only for severe issues.
- Round discipline:
1. early baseline submit,
2. mid-round refresh,
3. final pre-deadline refresh.

## 11. Assumptions
- Task 2 map remains `40x40` with `5` seeds unless API changes.
- Historical exports remain available through authenticated API calls.
- Lightweight linear model family is sufficient for first learning integration pass.
- Spec target file remains `task2-Astar/SPEC.md`.
