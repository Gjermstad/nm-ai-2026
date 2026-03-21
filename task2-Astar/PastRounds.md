# PastRounds.md — Task 2 Screenshot Intelligence Memory

## 1. Purpose
This file is the long-lived memory backbone for post-round screenshot analysis in Task 2 (`Astar Island`).

Use it to preserve:
- direct screenshot facts,
- explicit inferences,
- explicit assumptions,
- and explicit calibration decisions.

Goal: future LLM/operator sessions should recover prior learning in under 2 minutes without re-opening all images.

## 2. Update Protocol (Required)
When new round screenshots are available:
1. Add new files to `/Users/kenneth/git/annet/nmiai/nm-ai-2026/task2-Astar/screenshots`.
2. Extend the inventory table in Section 4.
3. Add/refresh round section with full evidence tags (`OBSERVED`, `INFERRED`, `ASSUMPTION`, `DECISION`).
4. Record class-level bias direction and confidence per seed.
5. Add cross-round synthesis updates (Section 7).
6. Update `AGENT.md` and `PROGRESS.md` to reference the refresh.

Do not delete older evidence unless the source file was wrong/corrupted; append corrections with date and rationale.

## 3. Evidence Legend (Strict)
- `OBSERVED`: direct, visible screenshot fact (text, number, visual pattern).
- `INFERRED`: reasoned interpretation from visual evidence.
- `ASSUMPTION`: unresolved but necessary working assumption.
- `DECISION`: chosen action/calibration to apply in future rounds.

## 4. Screenshot Inventory (Rounds 16-17)
Source directory: `/Users/kenneth/git/annet/nmiai/nm-ai-2026/task2-Astar/screenshots`

| Round | Type | Seed | Part | File |
|---|---|---:|---|---|
| 16 | overview | - | full | `screenshots/Round16_overview.png` |
| 16 | seed | 1 | a | `screenshots/Round16_Seed1_a.png` |
| 16 | seed | 1 | b | `screenshots/Round16_Seed1_b.png` |
| 16 | seed | 2 | a | `screenshots/Round16_Seed2_a.png` |
| 16 | seed | 2 | b | `screenshots/Round16_Seed2_b.png` |
| 16 | seed | 3 | a | `screenshots/Round16_Seed3_a.png` |
| 16 | seed | 3 | b | `screenshots/Round16_Seed3_b.png` |
| 16 | seed | 4 | a | `screenshots/Round16_Seed4_a.png` |
| 16 | seed | 4 | b | `screenshots/Round16_Seed4_b.png` |
| 16 | seed | 5 | a | `screenshots/Round16_Seed5_a.png` |
| 16 | seed | 5 | b | `screenshots/Round16_Seed5_b.png` |
| 17 | overview | - | full | `screenshots/Round17_overview.png` |
| 17 | seed | 1 | a | `screenshots/Round17_Seed1_a.png` |
| 17 | seed | 1 | b | `screenshots/Round17_Seed1_b.png` |
| 17 | seed | 2 | a | `screenshots/Round17_Seed2_a.png` |
| 17 | seed | 2 | b | `screenshots/Round17_Seed2_b.png` |
| 17 | seed | 3 | a | `screenshots/Round17_Seed3_a.png` |
| 17 | seed | 3 | b | `screenshots/Round17_Seed3_b.png` |
| 17 | seed | 4 | a | `screenshots/Round17_Seed4_a.png` |
| 17 | seed | 4 | b | `screenshots/Round17_Seed4_b.png` |
| 17 | seed | 5 | a | `screenshots/Round17_Seed5_a.png` |
| 17 | seed | 5 | b | `screenshots/Round17_Seed5_b.png` |

Coverage check:
- `OBSERVED`: 22 files present and reviewed (2 overview + 10 seed-pairs).
- `ASSUMPTION`: Screenshot naming uses 1-based seed labels matching UI (`Seed 1..5`).
- `OBSERVED`: API/internal seed indexing remains 0-based (`seed_index 0..4`).

## 5. Round 16 (Completed)

### 5.1 Overview Metrics
- `OBSERVED`: Round `16`, status `completed`, map `40x40`, seeds `5`, weight `2.1829`, date `2026-03-21`.
- `OBSERVED`: Round score `45.6` points, rank `#223 of 272`.
- `OBSERVED`: Queries used `50/50`, submitted `5/5`.
- `OBSERVED`: Per-seed scores: Seed1 `44.5`, Seed2 `45.6`, Seed3 `46.4`, Seed4 `44.0`, Seed5 `47.7`.

### 5.2 Seed-Level Notes

#### Seed 1 (UI Seed 1 / API `seed_index=0`)
- `OBSERVED`: score `44.5`, submitted `18:31:19` (local UI timestamp).
- `OBSERVED`: In layer analysis, prediction vs ground truth shows more diffuse dynamic class activation (Port/Ruin) than GT.
- `INFERRED`: Empty appears underweighted in contested dynamic regions.
- `INFERRED`: Settlement probability appears too speckled and less blob-like than GT (fragmented spatial prior).
- `DECISION`: reduce diffuse dynamic prior mass away from strong settlement evidence.
- `ASSUMPTION`: Risk note: low risk (calibration-only).

#### Seed 2 (UI Seed 2 / API `seed_index=1`)
- `OBSERVED`: score `45.6`, submitted `18:31:19`.
- `OBSERVED`: Layer panel indicates GT settlement is denser and more continuous than prediction.
- `OBSERVED`: Example cell readout visible in screenshot bottom: prediction has higher Port/Ruin and lower Empty than GT for selected cell.
- `INFERRED`: Over-allocation to Port/Ruin tails is a repeated error, likely from aggressive near-settlement diffusion.
- `DECISION`: tighten Port/Ruin uplift coefficients in near-settlement prior.
- `ASSUMPTION`: Risk note: medium-low (could slightly reduce upside on high-chaos rounds).

#### Seed 3 (UI Seed 3 / API `seed_index=2`)
- `OBSERVED`: score `46.4`, submitted `18:31:21`.
- `OBSERVED`: Empty class map in prediction is darker/noisier mismatch vs GT in dynamic corridors.
- `INFERRED`: Empty baseline still too low where no direct dynamic evidence exists.
- `DECISION`: increase class-0 anchoring for plains/empty cells with low visits.
- `ASSUMPTION`: Risk note: low.

#### Seed 4 (UI Seed 4 / API `seed_index=3`)
- `OBSERVED`: score `44.0` (round worst), submitted `18:31:23`.
- `OBSERVED`: Selected-cell readout in screenshot shows strong Settlement underprediction and Empty underprediction.
- `INFERRED`: Worst-seed behavior is dominated by diffuse uncertainty and over-dispersed non-empty tails.
- `DECISION`: ensure lower entropy default outside high-evidence windows; discourage broad non-empty spread.
- `ASSUMPTION`: Risk note: medium (can hurt if round dynamics are globally high-chaos).

#### Seed 5 (UI Seed 5 / API `seed_index=4`)
- `OBSERVED`: score `47.7` (round best), submitted `18:31:25`.
- `OBSERVED`: Selected-cell readout still shows Empty underprediction and elevated Settlement/Port/Ruin tails.
- `INFERRED`: Even best seed still carries systematic dynamic over-dispersion.
- `DECISION`: global correction should be applied across all seeds, not only low-scoring seeds.
- `ASSUMPTION`: Risk note: low.

### 5.3 Round 16 Per-Seed Class Bias Matrix

Bias direction format: `under` = predicted probability generally below GT, `over` = above GT.

| Seed | Empty | Settlement | Port | Ruin | Forest | Mountain |
|---|---|---|---|---|---|---|
| 1 | under (high) | under (high) | over (high) | over (high) | under (medium) | over (medium) |
| 2 | under (high) | under (high) | over (high) | over (high) | near/under (medium) | over (medium) |
| 3 | under (high) | under (high) | over (high) | over (high) | near/under (medium) | over (medium) |
| 4 | under (high) | under (high) | over (medium-high) | over (medium-high) | near/under (medium) | over (medium) |
| 5 | under (high) | under (medium) | over (medium) | over (medium) | near (medium) | over (medium) |

### 5.4 Round 16 Class-Bias Summary
- `OBSERVED`: Empty class map generally mismatched with GT in dynamic zones.
- `INFERRED`: `Empty` underprediction (high confidence).
- `INFERRED`: `Settlement` underprediction and over-fragmented spatial distribution (high confidence).
- `INFERRED`: `Port` overprediction (high confidence).
- `INFERRED`: `Ruin` overprediction (high confidence).
- `INFERRED`: `Forest` roughly close but slightly underweighted in places (medium confidence).
- `INFERRED`: `Mountain` has low-level diffuse probability where GT is sparse/structural; mostly floor-driven artifact (medium confidence).

## 6. Round 17 (Completed)

### 6.1 Overview Metrics
- `OBSERVED`: Round `17`, status `completed`, map `40x40`, seeds `5`, weight `2.292`, date `2026-03-21`.
- `OBSERVED`: Round score `51.7` points, rank `#228 of 283`.
- `OBSERVED`: Queries used `50/50`, submitted `5/5`.
- `OBSERVED`: Per-seed scores: Seed1 `52.1`, Seed2 `51.2`, Seed3 `50.4`, Seed4 `51.4`, Seed5 `53.4`.

### 6.2 Seed-Level Notes

#### Seed 1 (UI Seed 1 / API `seed_index=0`)
- `OBSERVED`: score `52.1`, submitted `21:19:33`.
- `OBSERVED`: Empty/Forest layer alignment looks visibly closer than Round 16 counterparts.
- `INFERRED`: Calibration from prior round reduced the strongest Empty underprediction failure mode.
- `DECISION`: keep conservative class-0 anchoring introduced after Round 16.
- `ASSUMPTION`: Risk note: low.

#### Seed 2 (UI Seed 2 / API `seed_index=1`)
- `OBSERVED`: score `51.2`, submitted `21:19:34`.
- `OBSERVED`: Settlement layer still smoother and denser in GT than prediction.
- `INFERRED`: Settlement mass remains under-allocated vs GT despite overall round gain.
- `DECISION`: add controlled settlement mass recovery where repeated observations support dynamic survival.
- `ASSUMPTION`: Risk note: medium.

#### Seed 3 (UI Seed 3 / API `seed_index=2`)
- `OBSERVED`: score `50.4` (round lowest), submitted `21:19:35`.
- `OBSERVED`: Port layer still visibly brighter in prediction than GT for large areas.
- `INFERRED`: Residual Port overprediction remains a key limiter.
- `DECISION`: reduce global Port tail prior and gate Port uplift more strongly by coastal/observed evidence.
- `ASSUMPTION`: Risk note: medium.

#### Seed 4 (UI Seed 4 / API `seed_index=3`)
- `OBSERVED`: score `51.4`, submitted `21:19:35`.
- `OBSERVED`: Empty layer nearly aligned; Ruin/Port still slightly over-diffuse in prediction.
- `INFERRED`: Base model is now competitive, but still over-hedged on rare dynamic classes.
- `DECISION`: additional entropy reduction in unobserved cells is likely beneficial.
- `ASSUMPTION`: Risk note: medium-low.

#### Seed 5 (UI Seed 5 / API `seed_index=4`)
- `OBSERVED`: score `53.4` (round best), submitted `21:19:37`.
- `OBSERVED`: Best visual alignment among seeds across Empty/Settlement/Forest.
- `INFERRED`: Query allocation and map structure can produce >53 with current architecture when class balance is favorable.
- `DECISION`: use high-performing seed behavior as target profile for calibration tests.
- `ASSUMPTION`: Risk note: low.

### 6.3 Round 17 Per-Seed Class Bias Matrix

Bias direction format: `under` = predicted probability generally below GT, `over` = above GT.

| Seed | Empty | Settlement | Port | Ruin | Forest | Mountain |
|---|---|---|---|---|---|---|
| 1 | near/under (medium) | under (medium) | over (medium) | over (low-medium) | near (medium-high) | over (low) |
| 2 | near (medium) | under (medium-high) | over (medium-high) | over (medium) | near (medium-high) | over (low) |
| 3 | near/under (medium) | under (high) | over (high) | over (medium) | near (medium) | over (low) |
| 4 | near (medium) | under (medium) | over (medium) | over (low-medium) | near (medium-high) | over (low) |
| 5 | near (medium) | under (low-medium) | over (medium) | over (low-medium) | near/slight over (medium) | over (low) |

### 6.4 Round 17 Class-Bias Summary
- `INFERRED`: `Empty` mismatch improved materially vs Round 16 (high confidence).
- `INFERRED`: `Settlement` still mildly underpredicted and spatially too granular (high confidence).
- `INFERRED`: `Port` still overpredicted (medium-high confidence).
- `INFERRED`: `Ruin` still mildly overpredicted (medium confidence).
- `INFERRED`: `Forest` generally close (medium-high confidence).
- `INFERRED`: `Mountain` low-probability diffuse artifact remains but mostly secondary impact (medium confidence).

## 7. Cross-Round Synthesis (16 -> 17)

### 7.1 Repeated Error Patterns
- `INFERRED`: Dynamic class over-dispersion (especially Port, then Ruin) is persistent across both rounds.
- `INFERRED`: Settlement underprediction is persistent, mainly as missing smooth high-probability clusters.
- `INFERRED`: Empty underprediction was severe in Round 16 and improved in Round 17 after calibration.

### 7.2 What Improved
- `OBSERVED`: Average score increased from `45.6` to `51.7` (+6.1).
- `OBSERVED`: Worst seed increased from `44.0` to `50.4`.
- `INFERRED`: Earlier calibration (reduced dynamic-heavy priors + stronger smoothing) addressed major Empty failure mode.

### 7.3 High-Confidence Tuning Priorities
These are prioritized for `core.py` / planner behavior without architecture changes.

1. `DECISION`: tighten Port prior further in non-coastal/non-observed dynamic cells.
- `INFERRED`: Why: repeated overprediction in both rounds.
- `ASSUMPTION`: Risk: medium (can underfit truly maritime rounds).

2. `DECISION`: moderate Ruin prior in low-evidence cells.
- `INFERRED`: Why: mild persistent overprediction.
- `ASSUMPTION`: Risk: medium-low.

3. `DECISION`: recover settlement mass in evidence-rich clusters.
- `INFERRED`: Why: recurring settlement underprediction despite overall gains.
- `ASSUMPTION`: Risk: medium (can overfit hotspots).

4. `DECISION`: keep strong Empty anchor where observations are sparse.
- `INFERRED`: Why: large gain from Round 16 to 17 likely tied to this correction.
- `ASSUMPTION`: Risk: low.

5. `DECISION`: planner balancing: avoid extreme per-seed query skew unless evidence clearly justifies it.
- `INFERRED`: Why: equal-weight seed scoring penalizes neglected seeds.
- `ASSUMPTION`: Risk: low.

## 8. Operational Defaults and Assumptions
- `ASSUMPTION`: Screenshot UI color and brightness semantics remained consistent between rounds.
- `ASSUMPTION`: All screenshots correspond to final submitted predictions (not intermediate drafts).
- `OBSERVED`: Submission counts are `5/5` in both rounds, so score variance is model quality, not missing seeds.
- `DECISION`: keep floor safety (`0.01`) and deadline guard behavior unchanged during tuning.

## 9. Operator-Ready Next Round Checklist
1. Confirm all screenshots for completed round are saved in `task2-Astar/screenshots`.
2. Ingest screenshots into this file before changing model coefficients.
3. Re-state current dominant biases with tags (`OBSERVED`/`INFERRED`).
4. Apply at most one or two calibration changes per iteration to keep attribution clear.
5. Preserve reliability constraints: no zero probabilities, floor `0.01`, deadline guard on.
6. Keep queries balanced across seeds unless live evidence strongly favors skew.
7. After round closes, append outcomes and compare against this memory.

## 10. Quick Loader for Future LLM Sessions
Read in this order when optimizing predictions:
1. `task2-Astar/AGENT.md`
2. `task2-Astar/PROGRESS.md`
3. `task2-Astar/PastRounds.md`
4. `task2-Astar/SPEC.md`

Then inspect current `/status` and use this file's `Section 7` priorities to choose the next low-risk calibration pass.
