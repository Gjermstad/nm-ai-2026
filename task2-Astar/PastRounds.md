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

## 11. API-Derived Historical Archive (Rounds 1-18)

### 11.1 Source and Timestamp
- `OBSERVED`: Data source is authenticated Task 2 API calls:
  - `GET /astar-island/my-rounds`
  - `GET /astar-island/analysis/{round_id}/{seed_index}` for seeds `0..4`
- `OBSERVED`: Snapshot fetched at `2026-03-21T23:19:53.519327+00:00` (UTC), which is `2026-03-22 00:19:53` in Oslo time.
- `OBSERVED`: At snapshot time, Round 18 was still active (`49/50` queries, `5/5` submitted).

### 11.2 Full Round Ledger (Team-Specific)

| Round | Status | Weight | Score | Seeds Submitted | Queries Used | `analysis` seeds OK | `prediction` present seeds |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | completed | 1.0500 | - | 0 | 0/50 | 5 | 0 |
| 2 | completed | 1.1025 | - | 0 | 0/50 | 5 | 0 |
| 3 | completed | 1.1576 | - | 0 | 0/50 | 5 | 0 |
| 4 | completed | 1.2155 | - | 0 | 0/50 | 5 | 0 |
| 5 | completed | 1.2763 | - | 0 | 0/50 | 5 | 0 |
| 6 | completed | 1.3401 | - | 0 | 0/50 | 5 | 0 |
| 7 | completed | 1.4071 | - | 0 | 0/50 | 5 | 0 |
| 8 | completed | 1.4775 | - | 0 | 0/50 | 5 | 0 |
| 9 | completed | 1.5513 | - | 0 | 0/50 | 5 | 0 |
| 10 | completed | 1.6289 | - | 0 | 0/50 | 5 | 0 |
| 11 | completed | 1.7103 | - | 0 | 0/50 | 5 | 0 |
| 12 | completed | 1.7959 | - | 0 | 0/50 | 5 | 0 |
| 13 | completed | 1.8856 | - | 0 | 0/50 | 5 | 0 |
| 14 | completed | 1.9799 | - | 0 | 0/50 | 5 | 0 |
| 15 | completed | 2.0789 | - | 0 | 0/50 | 5 | 0 |
| 16 | completed | 2.1829 | 45.6109 | 5 | 50/50 | 5 | 5 |
| 17 | completed | 2.2920 | 51.6942 | 5 | 50/50 | 5 | 5 |
| 18 | active | 2.4066 | - | 5 | 49/50 | - | - |

Interpretation:
- `OBSERVED`: Rounds 1-15 have no team submissions, but full ground truth is still available through `analysis`.
- `INFERRED`: This gives a large training/calibration dataset even without historical predictions from our team.

### 11.3 Ground-Truth Dynamics by Round (Completed Rounds 1-17)

Class order used below:
- `[Empty, Settlement, Port, Ruin, Forest, Mountain]`

`dynamic_mass` = `Settlement + Port + Ruin` (classes 1+2+3)

| Round | Avg Entropy | Class Mean | Dynamic Mass |
|---:|---:|---|---:|
| 1 | 0.5538 | [0.6304, 0.1397, 0.0121, 0.0109, 0.1856, 0.0214] | 0.1626 |
| 2 | 0.6919 | [0.6166, 0.1686, 0.0125, 0.0164, 0.1686, 0.0173] | 0.1975 |
| 3 | 0.0681 | [0.7586, 0.0023, 0.0001, 0.0005, 0.2195, 0.0190] | 0.0029 |
| 4 | 0.4654 | [0.6778, 0.0805, 0.0056, 0.0081, 0.2058, 0.0222] | 0.0942 |
| 5 | 0.4818 | [0.6559, 0.1112, 0.0077, 0.0116, 0.1928, 0.0209] | 0.1304 |
| 6 | 0.8082 | [0.5573, 0.2158, 0.0146, 0.0280, 0.1627, 0.0217] | 0.2583 |
| 7 | 0.3917 | [0.6571, 0.1322, 0.0086, 0.0097, 0.1748, 0.0177] | 0.1504 |
| 8 | 0.2697 | [0.7361, 0.0222, 0.0009, 0.0037, 0.2197, 0.0174] | 0.0268 |
| 9 | 0.6114 | [0.6447, 0.1204, 0.0075, 0.0144, 0.1949, 0.0181] | 0.1422 |
| 10 | 0.1120 | [0.7509, 0.0091, 0.0003, 0.0012, 0.2207, 0.0177] | 0.0107 |
| 11 | 0.6822 | [0.5599, 0.2368, 0.0134, 0.0155, 0.1525, 0.0217] | 0.2658 |
| 12 | 0.2687 | [0.6528, 0.1270, 0.0081, 0.0050, 0.1866, 0.0206] | 0.1400 |
| 13 | 0.5082 | [0.6743, 0.0866, 0.0049, 0.0112, 0.2042, 0.0189] | 0.1026 |
| 14 | 0.6770 | [0.5625, 0.2266, 0.0122, 0.0222, 0.1621, 0.0145] | 0.2609 |
| 15 | 0.6662 | [0.6103, 0.1560, 0.0083, 0.0166, 0.1892, 0.0196] | 0.1808 |
| 16 | 0.3210 | [0.6970, 0.0718, 0.0040, 0.0055, 0.2061, 0.0156] | 0.0813 |
| 17 | 0.7757 | [0.5487, 0.2348, 0.0156, 0.0184, 0.1607, 0.0217] | 0.2688 |

Interpretation:
- `OBSERVED`: Round volatility differs significantly by round (entropy range `0.0681` to `0.8082`).
- `INFERRED`: A single static dynamic-prior setting is suboptimal across all rounds.
- `DECISION`: keep a conservative baseline prior, then adapt dynamic lift mainly from observed evidence rather than globally high default tails.

### 11.4 Global Ground-Truth Priors Across Completed Rounds (1-17)

- `OBSERVED`: Global mean class distribution over all completed-round cells:
  - `Empty=0.6465`
  - `Settlement=0.1260`
  - `Port=0.0080`
  - `Ruin=0.0117`
  - `Forest=0.1886`
  - `Mountain=0.0192`
- `OBSERVED`: Global mean entropy across completed rounds: `0.4914`

`INFERRED`:
- Port/Ruin are truly low-mass classes globally.
- Mountain is effectively deterministic only on mountain-initial cells; non-zero mountain elsewhere is mostly floor-related hedge.

### 11.5 Ground-Truth by Initial Terrain Code (Completed Rounds 1-17)

| Initial Code | Cells | Avg Entropy | Mean Distribution [E,S,P,R,F,M] |
|---:|---:|---:|---|
| 1 (Settlement) | 3784 | 1.0515 | [0.4345, 0.3258, 0.0041, 0.0263, 0.2093, 0.0000] |
| 2 (Port) | 146 | 1.1967 | [0.4693, 0.0965, 0.1832, 0.0221, 0.2288, 0.0000] |
| 4 (Forest) | 29017 | 0.6277 | [0.0769, 0.1465, 0.0092, 0.0137, 0.7537, 0.0000] |
| 5 (Mountain) | 2610 | 0.0000 | [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 1.0000] |
| 10 (Ocean) | 17669 | 0.0000 | [1.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000] |
| 11 (Plains) | 82774 | 0.5371 | [0.8012, 0.1405, 0.0094, 0.0132, 0.0357, 0.0000] |

Interpretation:
- `OBSERVED`: On plains (`11`), GT average Port+Ruin is `~2.26%` combined (`0.0094+0.0132`).
- `INFERRED`: Any large default Port/Ruin tails on plains are likely overestimation.
- `OBSERVED`: On forest (`4`), GT still has meaningful settlement mass (`0.1465`) while forest remains dominant (`0.7537`).
- `DECISION`: forest priors should allow settlement possibility, but avoid high ruin/port leakage.

### 11.6 Submitted-Round Bias Diagnostics (API, Not Screenshot)

For submitted rounds, we computed `prediction_mean - ground_truth_mean` (class-level absolute mass delta):

Round 16:
- `OBSERVED`: diff = `[-0.1221, +0.0406, +0.0504, +0.0592, -0.0542, +0.0262]`
- `INFERRED`: strong Empty/Forest underprediction, strong Port/Ruin overprediction.

Round 17:
- `OBSERVED`: diff = `[-0.0016, -0.0971, +0.0422, +0.0502, -0.0192, +0.0255]`
- `INFERRED`: Empty mismatch largely fixed; Settlement now underpredicted while Port/Ruin/Mountain remain overpredicted.

### 11.7 Additional Decisions Enabled by API Archive

1. `DECISION`: add a low-cap regularizer on global Port and Ruin mass in unobserved/low-visit cells.
2. `DECISION`: reduce mountain tail outside mountain-initial cells (keep only floor-level hedge unless evidence supports otherwise).
3. `DECISION`: increase settlement recovery in repeatedly observed dynamic clusters instead of increasing global dynamic priors.
4. `DECISION`: when available, use early-round observed entropy signals to decide whether to keep conservative vs moderately dynamic behavior.
5. `DECISION`: keep this API archive section updated after every completed round (including rounds with no submission).

### 11.8 Applied Calibration Pass (2026-03-22, Round 19 Active)

- `OBSERVED`: API summary + diagnostics continue to show rare-class overprediction on submitted rounds:
  - Round 17 class deltas (`prediction - GT`): `Port +0.0422`, `Ruin +0.0502`, `Mountain +0.0255`.
  - Cross-submitted aggregate deltas: `Port +0.0463`, `Ruin +0.0547`, `Mountain +0.0258`.
- `DECISION`: implement a minimal low-evidence rare-tail guard in `core.py`:
  - applies only when `observed_total <= 1`, no direct `Port/Ruin/Mountain` observations, and non-`Port/Ruin/Mountain` initial terrain.
  - enforce caps `Port <= 0.03`, `Ruin <= 0.04`, `Mountain <= 0.015`.
  - redistribute reclaimed mass to `Empty`/`Settlement`/`Forest`, then re-normalize with existing floor logic.
- `OBSERVED`: local measurable check (plains, near-settlement, aggressive, zero observations):
  - before patch: `[0.746, 0.105, 0.040, 0.054, 0.035, 0.020]` => rare-tail mass `0.114`.
  - after patch: `[0.762, 0.109, 0.030, 0.040, 0.044, 0.015]` => rare-tail mass `0.085`.
- `OBSERVED`: evidence override preserved:
  - with direct Port observations (`observed_counts=[0,0,3,0,0,0]`), Port stays high (`0.265`), confirming cap skip logic.
- `ASSUMPTION`: this conservative correction should reduce KL loss from diffuse rare tails on low-evidence cells while preserving upside where rare-class evidence is explicit.

### 11.9 History-Aware Linear Model v1 (2026-03-22)

- `OBSERVED`: deterministic trainer and artifact now exist:
  - trainer: `task2-Astar/history/train_linear_model.py`
  - artifact: `task2-Astar/history/models/latest_linear_v1.json`
- `DECISION`: runtime uses learned corrections only when artifact validation passes; otherwise fallback remains heuristic-safe.
- `OBSERVED`: replay evaluation file generated:
  - `task2-Astar/history/summary/replay_eval_linear_v1.json`
  - rows evaluated: `136000` completed-round cells (`1..17`).
- `OBSERVED`: replay baseline vs learned deltas (`learned - baseline`):
  - cross-entropy: `-0.0604`
  - KL: `-0.0604`
  - L1: `-0.0251`
  - Brier: `-0.0133`
- `OBSERVED`: all replay gates passed (`cross_entropy_non_regression`, `kl_non_regression`, `l1_non_regression`, `brier_non_regression` = `true`).
- `DECISION`: promote linear v1 as default artifact for between-round deployment, with one emergency hotfix max mid-round only for severe regressions.

### 11.10 Round 18 Drop + Round 19 Baseline-Lock Lesson

- `OBSERVED`: Round 18 completed at `25.2` points (UI snapshot date `2026-03-21`), a material drop from Round 17 (`51.7`).
- `INFERRED`: reliability of submissions stayed intact (`5/5`), but prediction quality variance remains high across round dynamics.
- `OBSERVED`: Round 19 active status snapshot (`2026-03-22`, Oslo) shows:
  - `queries.used/max=40/50`
  - `submitted_count=5`
  - `run_enabled=true`
  - `deadline_guard_enabled=true`
  - `last_error=null`
- `DECISION`: retain baseline-lock workflow as default safety pattern:
  1. early baseline submit for all seeds,
  2. one mid-round rebuild/resubmit checkpoint,
  3. one pre-deadline rebuild/resubmit checkpoint.
