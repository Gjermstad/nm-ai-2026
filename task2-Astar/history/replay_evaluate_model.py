#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
TASK_DIR = ROOT.parent
sys.path.append(str(TASK_DIR))

from core import apply_learned_adjustments, prior_distribution  # noqa: E402


def _empty_mask(width: int, height: int) -> List[List[bool]]:
    return [[False for _ in range(width)] for _ in range(height)]


def _near_settlement_mask(width: int, height: int, settlements: List[Dict[str, Any]]) -> List[List[bool]]:
    mask = _empty_mask(width, height)
    for st in settlements:
        sx = int(st.get("x", 0))
        sy = int(st.get("y", 0))
        for y in range(max(0, sy - 3), min(height, sy + 4)):
            for x in range(max(0, sx - 3), min(width, sx + 4)):
                mask[y][x] = True
    return mask


def _metrics(gt: List[float], pred: List[float]) -> Dict[str, float]:
    eps = 1e-12
    xent = 0.0
    l1 = 0.0
    brier = 0.0
    for i in range(6):
        g = float(gt[i])
        p = max(float(pred[i]), eps)
        xent += -g * math.log(p)
        d = p - g
        l1 += abs(d)
        brier += d * d
    gt_entropy = 0.0
    for g in gt:
        if g > 0:
            gt_entropy += -g * math.log(g)
    return {
        "cross_entropy": xent,
        "kl": xent - gt_entropy,
        "l1": l1,
        "brier": brier,
    }


def evaluate(snapshot: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, Any]:
    rows = 0
    base_totals = {"cross_entropy": 0.0, "kl": 0.0, "l1": 0.0, "brier": 0.0}
    learned_totals = {"cross_entropy": 0.0, "kl": 0.0, "l1": 0.0, "brier": 0.0}
    gt_sum = [0.0] * 6
    base_sum = [0.0] * 6
    learned_sum = [0.0] * 6
    per_round: Dict[str, Dict[str, Any]] = {}

    rounds = sorted(snapshot.get("my_rounds", []), key=lambda r: int(r.get("round_number", 0)))
    for round_item in rounds:
        if round_item.get("status") != "completed":
            continue
        round_number = int(round_item.get("round_number", 0))
        round_key = str(round_number)
        analyses = (snapshot.get("analysis_by_round_seed", {}) or {}).get(round_key, {})
        round_rows = 0
        round_base = {"cross_entropy": 0.0, "kl": 0.0, "l1": 0.0, "brier": 0.0}
        round_learned = {"cross_entropy": 0.0, "kl": 0.0, "l1": 0.0, "brier": 0.0}

        for seed_analysis in analyses.values():
            if not isinstance(seed_analysis, dict):
                continue
            gt_grid = seed_analysis.get("ground_truth")
            initial_grid = seed_analysis.get("initial_grid")
            if not (isinstance(gt_grid, list) and gt_grid and isinstance(initial_grid, list) and initial_grid):
                continue

            h = len(gt_grid)
            w = len(gt_grid[0]) if h else 0
            near_mask = _near_settlement_mask(w, h, seed_analysis.get("initial_settlements", []))
            for y in range(h):
                for x in range(w):
                    init_code = int(initial_grid[y][x])
                    near = bool(near_mask[y][x])
                    gt = gt_grid[y][x]
                    base = prior_distribution(init_code, near_settlement=near, aggressive=False)
                    learned = apply_learned_adjustments(
                        distribution=base,
                        initial_code=init_code,
                        near_settlement=near,
                        model=model,
                        floor=0.01,
                    )

                    bm = _metrics(gt, base)
                    lm = _metrics(gt, learned)
                    for key in base_totals:
                        base_totals[key] += bm[key]
                        learned_totals[key] += lm[key]
                        round_base[key] += bm[key]
                        round_learned[key] += lm[key]
                    for i in range(6):
                        gt_sum[i] += gt[i]
                        base_sum[i] += base[i]
                        learned_sum[i] += learned[i]
                    rows += 1
                    round_rows += 1

        if round_rows > 0:
            per_round[round_key] = {
                "rows": round_rows,
                "baseline": {k: round_base[k] / round_rows for k in round_base},
                "learned": {k: round_learned[k] / round_rows for k in round_learned},
            }

    if rows == 0:
        raise SystemExit("No completed rows available for replay evaluation")

    baseline = {k: base_totals[k] / rows for k in base_totals}
    learned = {k: learned_totals[k] / rows for k in learned_totals}
    gt_mean = [v / rows for v in gt_sum]
    base_mean = [v / rows for v in base_sum]
    learned_mean = [v / rows for v in learned_sum]

    gates = {
        "cross_entropy_non_regression": learned["cross_entropy"] <= baseline["cross_entropy"],
        "kl_non_regression": learned["kl"] <= baseline["kl"],
        "l1_non_regression": learned["l1"] <= baseline["l1"],
        "brier_non_regression": learned["brier"] <= baseline["brier"],
    }

    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "baseline": baseline,
        "learned": learned,
        "delta_learned_minus_baseline": {k: learned[k] - baseline[k] for k in baseline},
        "class_labels": ["Empty", "Settlement", "Port", "Ruin", "Forest", "Mountain"],
        "class_bias_baseline_pred_minus_gt": [base_mean[i] - gt_mean[i] for i in range(6)],
        "class_bias_learned_pred_minus_gt": [learned_mean[i] - gt_mean[i] for i in range(6)],
        "per_round": per_round,
        "gates": gates,
    }


def main() -> None:
    raw_path = ROOT / "raw" / "api_snapshot_full.json.gz"
    model_path = ROOT / "models" / "latest_linear_v1.json"
    out_path = ROOT / "summary" / "replay_eval_linear_v1.json"
    if not raw_path.exists():
        raise SystemExit(f"Missing snapshot file: {raw_path}")
    if not model_path.exists():
        raise SystemExit(f"Missing model artifact: {model_path}")

    with gzip.open(raw_path, "rt", encoding="utf-8") as handle:
        snapshot = json.load(handle)
    model = json.loads(model_path.read_text())
    result = evaluate(snapshot, model)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
