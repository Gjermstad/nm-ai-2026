# Task 2 Astar Island SPEC (Time-Constrained, Reliable-First)

## 1. Summary
- Goal: deliver a robust Task 2 system that can run with low operator load and avoid deadline failures before **Sunday, March 22, 2026, 15:00 CET**.
- Submission contract: use direct Task 2 API calls (`/rounds`, `/simulate`, `/submit`) from `api.ainm.no/astar-island`; do not build around validator `/solve` for this task.
- Operating mode:
1. Default behavior is **auto query + auto draft generation**.
2. Submission is manual by default.
3. If operator is unavailable, **auto-submit missing seeds at T-20m**.
- UI scope: **4-tab web dashboard v1** (`Dashboard`, `Explorer`, `Submit`, `Logs`) with extensible tab registry for future `Rounds`, `Metrics`, `Backtest`, `Research`, `Autoiterate`.

## 2. Architecture
- Recommended architecture: Cloud Run hosted orchestrator + web dashboard.
1. Why appropriate: highest reliability while sleeping/fatigued, remote access, low ops friction, still simple.
2. Alternatives considered: local-only runner is faster to start but more fragile; full advanced research system is too risky for time.
3. Best under limited time: smallest architecture that meaningfully reduces “missed submission” risk.
- Simpler fallback architecture: local script + minimal local web page.
1. Use when Cloud Run deployment blocks.
2. Keep same core engine and UI contracts so migration to Cloud Run is trivial.
3. Lower reliability accepted only as contingency.

## 3. Interfaces and Data Contracts
- Internal service endpoints:
1. `GET /health`: process and dependency health.
2. `GET /status`: active round info, budget, seed readiness, mode, deadline guard state.
3. `POST /run/start`: begin orchestration for active round.
4. `POST /run/stop`: halt queries and draft updates.
5. `POST /profile/set`: set `safe` or `aggressive`.
6. `POST /draft/rebuild`: rebuild all seed tensors from current observations.
7. `POST /submit/seed`: submit one seed.
8. `POST /submit/all`: submit all unsubmitted/selected seeds.
9. `GET /logs/recent`: structured run events and last blocking error.
10. `GET /seed/{seed_index}`: detailed map/uncertainty/coverage for explorer.
11. `POST /guard/set`: enable/disable deadline guard.
12. `POST /auth/token`: runtime token update (optional, controlled by env).
- External competition API used by engine:
1. `GET /astar-island/rounds`
2. `GET /astar-island/rounds/{round_id}`
3. `GET /astar-island/budget`
4. `POST /astar-island/simulate`
5. `POST /astar-island/submit`
- Core in-memory/persisted objects:
1. `RoundState`: round id, status, closes_at, width, height, seeds_count.
2. `SeedState`: initial grid, observed windows, settlement snapshots, coverage stats, draft tensor, submit status.
3. `RunState`: profile, queries_used, queries_remaining, rate-limit trackers, last_error, deadline_guard.
4. `DraftValidation`: shape_ok, non_negative_ok, sum_ok, floor_ok, submit_ready.

## 4. Query and Prediction Strategy
- Safe profile (default for early rounds): **2-phase adaptive**.
1. Phase A scouting: 25 queries total across all seeds to sample high-information windows and calibrate dynamics.
2. Phase B focus: 25 queries allocated to highest-uncertainty/high-settlement regions by seed.
3. Constraints enforced: max 5 rps, strict budget accounting, reserve 2 queries for last-minute correction where possible.
- Aggressive profile (for leaderboard pushes):
1. More budget concentrated on high-entropy/frontier/coastal conflict zones.
2. Higher-confidence bets in dynamic cells, still with probability floor safeguards.
3. Trigger manually from UI only.
- Draft probability rules:
1. Always output `40x40x6` per seed.
2. Never allow 0.0 class probabilities; enforce floor (default `0.01`) and renormalize.
3. Static terrain priors anchor class-0/forest/mountain behavior.
4. Observed dynamic patterns adjust settlement/port/ruin mass.
- Submission policy:
1. Early draft for all 5 seeds generated ASAP.
2. Manual submit preferred once validations are green.
3. Re-submit supported per seed to improve before close.
4. Deadline guard auto-submits missing seeds at T-20m.

## 5. Monitoring UI (Web v1)
- Target users: tired operator during live rounds, optionally teammate observer.
- Purpose: quick understanding, low-risk controls, clear failure visibility.
- Tabs and screens:
1. `Dashboard`: active round, countdown, budget, submissions `x/5`, profile, guard status, one-screen health.
2. `Explorer`: seed tabs `0..4`, map grid, viewport rectangle, coverage %, viewport class counts, per-seed settlement summary.
3. `Submit`: per-seed readiness cards, validation checks, confidence/risk indicators, buttons (`Rebuild Draft`, `Submit Seed`, `Submit All`).
4. `Logs`: timestamped events, API failures, retry/backoff events, filter to errors/warnings.
- Key status indicators:
1. Budget used/remaining and projected completion.
2. Seed readiness state (`not started`, `draft ready`, `submitted`, `error`).
3. Deadline risk (`safe`, `warning`, `critical`) based on remaining time and submission completeness.
4. Last blocking error with exact recovery action.
- Manual controls:
1. Start/Stop run.
2. Switch profile safe/aggressive.
3. Rebuild draft.
4. Submit seed.
5. Submit all.
6. Enable/disable deadline guard.

## 6. Feature Priority
- Must have:
1. Active-round detection and timing.
2. Query orchestration with budget/rate-limit safety.
3. 2-phase safe query strategy.
4. Valid tensor generation with floor + renormalization.
5. Per-seed readiness and submit status.
6. Manual submit controls and submit-all flow.
7. Deadline guard auto-submit at T-20m.
8. Blocking error visibility and structured logs.
- Should have:
1. Aggressive profile toggle.
2. Per-seed uncertainty heatmap.
3. Retry queue with exponential backoff and jitter.
4. Draft diff view between last and current prediction.
- Nice to have:
1. Historical round comparison panel.
2. Basic post-round calibration helper.
3. Planned but disabled tabs (`Rounds`, `Metrics`, `Backtest`, `Research`, `Autoiterate`).

## 7. Risks, Consequences, Prevention, Fallback
- Risk: wrong integration assumption (`/solve` endpoint).
- Consequence: wasted implementation time.
- Prevention: lock direct Task 2 API contract from task docs and UI wording.
- Fallback: keep thin adapter layer if endpoint mode is later required.
- Risk: missing one or more seeds before close.
- Consequence: zero score for missing seeds.
- Prevention: early all-seed drafts + readiness gate + countdown alerts.
- Fallback: deadline guard auto-submit missing seeds at T-20m.
- Risk: invalid probabilities (shape/sum/negative/zeros).
- Consequence: rejected submit or catastrophic KL loss.
- Prevention: strict validator before any submit.
- Fallback: auto-repair and immediate revalidate.
- Risk: budget waste in low-information windows.
- Consequence: weak predictions.
- Prevention: 2-phase adaptive query planner with hotspot ranking.
- Fallback: switch to fixed hotspot template if planner misbehaves.
- Risk: auth/session expiry.
- Consequence: pipeline stalls.
- Prevention: startup auth check + periodic auth probe.
- Fallback: manual token refresh flow and resume.
- Risk: Cloud Run or network outage.
- Consequence: missed operations.
- Prevention: `min-instances=1`, health probes, low dependency stack.
- Fallback: local runner contingency script with same core engine.

## 8. Implementation Plan
- Step 1: Establish base app skeleton and tab registry; wire `Dashboard/Explorer/Submit/Logs`.
- Step 2: Implement round watcher and API client with auth handling, retries, and rate limits.
- Step 3: Implement seed state store and observation ingestion from `/simulate`.
- Step 4: Implement safe profile query planner (25 scouting + 25 focused).
- Step 5: Implement prediction builder with floor/renormalization and pre-submit validator.
- Step 6: Implement submit controller (single seed, submit all, overwrite support).
- Step 7: Implement deadline guard logic (`T-20m` auto-submit missing seeds).
- Step 8: Implement logs/error panel and recovery hints.
- Step 9: Deploy to Cloud Run (`europe-north1`, `min-instances=1`) and smoke test full loop.
- Step 10: Run first live round in safe profile; only then enable aggressive mode for selected rounds.

## 9. Test Plan and Acceptance Criteria
- Functional scenarios:
1. Active round is detected and visible with accurate countdown.
2. Query loop respects `50` budget and `5 rps` simulate limit.
3. Every seed receives a valid `40x40x6` draft.
4. Manual submit updates status for each seed.
5. Missing seeds auto-submit at T-20m when guard is enabled.
- Failure scenarios:
1. 429 rate-limit bursts trigger retry/backoff and recovery.
2. 401/403 auth errors are surfaced immediately with actionable status.
3. Partial submit failure retries only failed seeds.
4. Service restart restores state and does not forget submitted seeds.
- Acceptance criteria:
1. Operator can understand round health in <30 seconds from dashboard.
2. No invalid payload reaches `/submit` in smoke tests.
3. System can complete all 5 submissions in one round without manual debugging.
4. Safe mode is default and stable; aggressive mode is manual-only.

## 10. Assumptions and Defaults
- Task 2 uses direct API submission, not validator-called `/solve`.
- Map size remains `40x40`, seeds remain 5 unless API says otherwise.
- Default runtime profile is `safe`.
- Default UI is web dashboard.
- Deadline guard default is enabled.
- Spec target file is `task2-Astar/SPEC.md`.
