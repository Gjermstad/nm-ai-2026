#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CLASS_LABELS = ["Empty", "Settlement", "Port", "Ruin", "Forest", "Mountain"]


def entropy_of_dist(dist: List[float]) -> float:
    value = 0.0
    for p in dist:
        if p > 0:
            value -= p * math.log(p)
    return value


def percentile(sorted_values: List[float], q: float) -> Optional[float]:
    if not sorted_values:
        return None
    if q <= 0:
        return sorted_values[0]
    if q >= 1:
        return sorted_values[-1]
    pos = q * (len(sorted_values) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_values[lo]
    w = pos - lo
    return sorted_values[lo] * (1.0 - w) + sorted_values[hi] * w


def confidence_stats(grid: Optional[List[List[float]]]) -> Dict[str, Optional[float]]:
    if not grid:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "p10": None,
            "p50": None,
            "p90": None,
        }

    values = [float(v) for row in grid for v in row]
    n = len(values)
    if n == 0:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "p10": None,
            "p50": None,
            "p90": None,
        }

    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    sorted_values = sorted(values)

    return {
        "count": n,
        "mean": mean,
        "std": math.sqrt(var),
        "min": sorted_values[0],
        "max": sorted_values[-1],
        "p10": percentile(sorted_values, 0.10),
        "p50": percentile(sorted_values, 0.50),
        "p90": percentile(sorted_values, 0.90),
    }


def argmax_stats(grid: Optional[List[List[int]]]) -> Dict[str, Any]:
    if not grid:
        return {"count": 0, "hist_counts": {}, "hist_ratio": {}}

    flat = [int(v) for row in grid for v in row]
    n = len(flat)
    if n == 0:
        return {"count": 0, "hist_counts": {}, "hist_ratio": {}}

    counts = Counter(flat)
    hist_counts = {str(i): int(counts.get(i, 0)) for i in range(6)}
    hist_ratio = {str(i): (hist_counts[str(i)] / n) for i in range(6)}
    return {"count": n, "hist_counts": hist_counts, "hist_ratio": hist_ratio}


def compute_grid_means(grid: List[List[List[float]]]) -> Tuple[int, List[float], float]:
    class_sum = [0.0] * 6
    entropy_sum = 0.0
    cells = 0
    for row in grid:
        for dist in row:
            cells += 1
            entropy_sum += entropy_of_dist(dist)
            for i in range(6):
                class_sum[i] += float(dist[i])
    if cells == 0:
        return 0, [0.0] * 6, 0.0
    return cells, [x / cells for x in class_sum], entropy_sum / cells


def compute_alignment(gt: List[List[List[float]]], pred: List[List[List[float]]]) -> Dict[str, Any]:
    eps = 1e-12
    gt_sum = [0.0] * 6
    pred_sum = [0.0] * 6
    cross_entropy_sum = 0.0
    gt_entropy_sum = 0.0
    sqerr_sum = 0.0
    absdiff_sum = 0.0
    cells = 0

    h = len(gt)
    w = len(gt[0]) if h else 0
    for y in range(h):
        for x in range(w):
            gt_dist = gt[y][x]
            pred_dist = pred[y][x]
            cells += 1
            for i in range(6):
                g = float(gt_dist[i])
                p = max(float(pred_dist[i]), eps)
                gt_sum[i] += g
                pred_sum[i] += p
                cross_entropy_sum += -g * math.log(p)
                if g > 0:
                    gt_entropy_sum += -g * math.log(g)
                d = p - g
                sqerr_sum += d * d
                absdiff_sum += abs(d)

    if cells == 0:
        return {
            "cells": 0,
            "gt_mean": [0.0] * 6,
            "prediction_mean": [0.0] * 6,
            "diff_prediction_minus_gt": [0.0] * 6,
            "dynamic_mass_gt": 0.0,
            "dynamic_mass_prediction": 0.0,
            "avg_cross_entropy": None,
            "avg_kl_gt_to_prediction": None,
            "avg_brier_sum_sq": None,
            "avg_l1_sum_abs": None,
        }

    gt_mean = [x / cells for x in gt_sum]
    pred_mean = [x / cells for x in pred_sum]
    diff = [pred_mean[i] - gt_mean[i] for i in range(6)]

    avg_cross_entropy = cross_entropy_sum / cells
    avg_gt_entropy = gt_entropy_sum / cells
    avg_kl = avg_cross_entropy - avg_gt_entropy

    return {
        "cells": cells,
        "gt_mean": gt_mean,
        "prediction_mean": pred_mean,
        "diff_prediction_minus_gt": diff,
        "dynamic_mass_gt": gt_mean[1] + gt_mean[2] + gt_mean[3],
        "dynamic_mass_prediction": pred_mean[1] + pred_mean[2] + pred_mean[3],
        "avg_cross_entropy": avg_cross_entropy,
        "avg_kl_gt_to_prediction": avg_kl,
        "avg_brier_sum_sq": sqerr_sum / cells,
        "avg_l1_sum_abs": absdiff_sum / cells,
    }


def main() -> None:
    root = Path(__file__).resolve().parent
    raw_path = root / "raw" / "api_snapshot_full.json.gz"
    out_path = root / "summary" / "round_seed_diagnostics.json"

    if not raw_path.exists():
        raise SystemExit(f"Missing snapshot: {raw_path}")

    with gzip.open(raw_path, "rt", encoding="utf-8") as handle:
        snapshot = json.load(handle)

    rounds = sorted(snapshot.get("my_rounds", []), key=lambda r: int(r.get("round_number", 0)))
    predictions_by_round = snapshot.get("my_predictions_by_round", {})
    analysis_by_round_seed = snapshot.get("analysis_by_round_seed", {})

    diag_rounds: List[Dict[str, Any]] = []
    diag_seeds: List[Dict[str, Any]] = []

    submitted_seed_scores: List[Tuple[float, float]] = []
    submitted_diff_sum = [0.0] * 6
    submitted_diff_n = 0

    for round_item in rounds:
        round_number = int(round_item.get("round_number", 0))
        round_key = str(round_number)
        seeds_count = int(round_item.get("seeds_count", 5) or 5)

        pred_entries = predictions_by_round.get(round_key)
        pred_by_seed: Dict[int, Dict[str, Any]] = {}
        if isinstance(pred_entries, list):
            for entry in pred_entries:
                try:
                    sidx = int(entry.get("seed_index"))
                except Exception:  # noqa: BLE001
                    continue
                pred_by_seed[sidx] = entry

        round_seed_rows: List[Dict[str, Any]] = []

        for seed_index in range(seeds_count):
            analysis = (analysis_by_round_seed.get(round_key) or {}).get(str(seed_index), {})
            pred_entry = pred_by_seed.get(seed_index)

            seed_row: Dict[str, Any] = {
                "round_number": round_number,
                "round_id": round_item.get("id"),
                "seed_index": seed_index,
                "status": round_item.get("status"),
                "my_prediction_available": pred_entry is not None,
                "analysis_available": isinstance(analysis, dict) and "status_code" not in analysis and "error" not in analysis,
                "submitted_at": pred_entry.get("submitted_at") if pred_entry else None,
                "seed_score_from_predictions": pred_entry.get("score") if pred_entry else None,
                "seed_score_from_analysis": analysis.get("score") if isinstance(analysis, dict) else None,
                "prediction_confidence": confidence_stats(pred_entry.get("confidence_grid") if pred_entry else None),
                "prediction_argmax": argmax_stats(pred_entry.get("argmax_grid") if pred_entry else None),
                "analysis_error": None,
                "ground_truth_stats": None,
                "prediction_stats": None,
                "alignment": None,
            }

            if isinstance(analysis, dict) and ("status_code" in analysis or "error" in analysis):
                seed_row["analysis_error"] = {
                    "status_code": analysis.get("status_code"),
                    "error": analysis.get("error"),
                    "body": analysis.get("body"),
                }

            gt_grid = analysis.get("ground_truth") if isinstance(analysis, dict) else None
            pred_grid = analysis.get("prediction") if isinstance(analysis, dict) else None

            if isinstance(gt_grid, list) and gt_grid:
                gt_cells, gt_mean, gt_entropy = compute_grid_means(gt_grid)
                seed_row["ground_truth_stats"] = {
                    "cells": gt_cells,
                    "class_mean": gt_mean,
                    "avg_entropy": gt_entropy,
                    "dynamic_mass": gt_mean[1] + gt_mean[2] + gt_mean[3],
                }

            if isinstance(pred_grid, list) and pred_grid:
                pr_cells, pr_mean, pr_entropy = compute_grid_means(pred_grid)
                seed_row["prediction_stats"] = {
                    "cells": pr_cells,
                    "class_mean": pr_mean,
                    "avg_entropy": pr_entropy,
                    "dynamic_mass": pr_mean[1] + pr_mean[2] + pr_mean[3],
                }

            if isinstance(gt_grid, list) and gt_grid and isinstance(pred_grid, list) and pred_grid:
                alignment = compute_alignment(gt_grid, pred_grid)
                seed_row["alignment"] = alignment

                conf_mean = seed_row["prediction_confidence"].get("mean")
                score = seed_row.get("seed_score_from_predictions")
                if isinstance(conf_mean, (int, float)) and isinstance(score, (int, float)):
                    submitted_seed_scores.append((float(conf_mean), float(score)))

                diff = alignment.get("diff_prediction_minus_gt")
                if isinstance(diff, list) and len(diff) == 6:
                    for i in range(6):
                        submitted_diff_sum[i] += float(diff[i])
                    submitted_diff_n += 1

            round_seed_rows.append(seed_row)
            diag_seeds.append(seed_row)

        round_summary: Dict[str, Any] = {
            "round_number": round_number,
            "id": round_item.get("id"),
            "status": round_item.get("status"),
            "round_weight": round_item.get("round_weight"),
            "round_score": round_item.get("round_score"),
            "rank": round_item.get("rank"),
            "total_teams": round_item.get("total_teams"),
            "queries_used": round_item.get("queries_used"),
            "queries_max": round_item.get("queries_max"),
            "seeds_submitted": round_item.get("seeds_submitted"),
            "seed_rows": round_seed_rows,
            "analysis_ok_seeds": sum(1 for r in round_seed_rows if r.get("ground_truth_stats") is not None),
            "analysis_with_prediction_seeds": sum(1 for r in round_seed_rows if r.get("alignment") is not None),
        }
        diag_rounds.append(round_summary)

    score_conf_corr: Optional[float] = None
    if len(submitted_seed_scores) >= 2:
        xs = [x for x, _ in submitted_seed_scores]
        ys = [y for _, y in submitted_seed_scores]
        mx = sum(xs) / len(xs)
        my = sum(ys) / len(ys)
        cov = sum((x - mx) * (y - my) for x, y in submitted_seed_scores)
        vx = sum((x - mx) ** 2 for x in xs)
        vy = sum((y - my) ** 2 for y in ys)
        if vx > 0 and vy > 0:
            score_conf_corr = cov / math.sqrt(vx * vy)

    avg_diff = None
    if submitted_diff_n > 0:
        avg_diff = [x / submitted_diff_n for x in submitted_diff_sum]

    output: Dict[str, Any] = {
        "snapshot_fetched_at": snapshot.get("fetched_at"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "class_labels": CLASS_LABELS,
        "coverage": {
            "round_count": len(diag_rounds),
            "seed_rows": len(diag_seeds),
            "submitted_alignment_rows": submitted_diff_n,
            "errors_count": len(snapshot.get("errors", [])),
        },
        "aggregates": {
            "confidence_vs_seed_score_correlation": score_conf_corr,
            "avg_diff_prediction_minus_gt_on_submitted_seeds": avg_diff,
        },
        "rounds": diag_rounds,
        "seed_rows": diag_seeds,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
