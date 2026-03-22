#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
TASK_DIR = ROOT.parent
sys.path.append(str(TASK_DIR))

from core import prior_distribution  # noqa: E402

CLASS_LABELS = ["Empty", "Settlement", "Port", "Ruin", "Forest", "Mountain"]
TERRAIN_CODES = [1, 2, 4, 5, 10, 11]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _avg_bias(summary: Dict[str, Any], diagnostics: Dict[str, Any]) -> List[float]:
    agg = diagnostics.get("aggregates", {})
    from_diag = agg.get("avg_diff_prediction_minus_gt_on_submitted_seeds")
    if isinstance(from_diag, list) and len(from_diag) == 6:
        return [float(v) for v in from_diag]

    from_summary = summary.get("bias_on_submitted_rounds", {})
    rows = []
    if isinstance(from_summary, dict):
        for payload in from_summary.values():
            diff = payload.get("diff_prediction_minus_gt") if isinstance(payload, dict) else None
            if isinstance(diff, list) and len(diff) == 6:
                rows.append([float(v) for v in diff])
    if not rows:
        return [0.0] * 6
    return [_mean([row[i] for row in rows]) for i in range(6)]


def _terrain_corrections(summary: Dict[str, Any], avg_bias: List[float]) -> Dict[str, Dict[str, List[float]]]:
    by_code = ((summary.get("global") or {}).get("by_initial_code") or {})
    near_settlement_boost = _clamp(max(0.0, -avg_bias[1]) * 0.25, 0.0, 0.04)
    out: Dict[str, Dict[str, List[float]]] = {}

    for code in TERRAIN_CODES:
        key = str(code)
        row = by_code.get(key) or {}
        gt = row.get("class_mean")
        cells = int(row.get("cells", 0) or 0)

        if not (isinstance(gt, list) and len(gt) == 6):
            out[key] = {"far": [0.0] * 6, "near": [0.0] * 6}
            continue

        base_far = prior_distribution(code, near_settlement=False, aggressive=False)
        shrink = _clamp(0.12 + min(cells, 60000) / 60000 * 0.38, 0.12, 0.5)
        far = [_clamp((float(gt[i]) - base_far[i]) * shrink, -0.15, 0.15) for i in range(6)]
        near = list(far)

        # Near settlement cells should recover settlement mass when diagnostics show underprediction.
        if code not in (5, 10):
            near[1] = _clamp(near[1] + near_settlement_boost, -0.15, 0.15)
            near[0] = _clamp(near[0] - near_settlement_boost * 0.75, -0.15, 0.15)
            near[4] = _clamp(near[4] - near_settlement_boost * 0.25, -0.15, 0.15)

        out[key] = {
            "far": [round(v, 6) for v in far],
            "near": [round(v, 6) for v in near],
        }

    return out


def _global_bias_correction(avg_bias: List[float]) -> List[float]:
    corr = [_clamp(-0.5 * float(v), -0.08, 0.08) for v in avg_bias]
    mean_corr = _mean(corr)
    corr = [_clamp(v - mean_corr, -0.08, 0.08) for v in corr]
    return [round(v, 6) for v in corr]


def _query_policy(avg_bias: List[float], diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    conf_corr = float((diagnostics.get("aggregates") or {}).get("confidence_vs_seed_score_correlation", 0.0) or 0.0)
    conf_signal = max(0.0, -conf_corr)
    settlement_under = max(0.0, -avg_bias[1])
    rare_over = max(0.0, avg_bias[2]) + max(0.0, avg_bias[3]) + max(0.0, avg_bias[5])

    safe = {
        "w_entropy": round(1.0 + 0.25 * conf_signal, 6),
        "w_unvisited": round(0.05 + 0.03 * conf_signal, 6),
        "w_settlement": round(0.08 + 0.45 * settlement_under, 6),
        "w_repeat": 2.0,
        "w_late_settlement": round(0.10 + 0.20 * settlement_under + 0.05 * rare_over, 6),
    }
    aggressive = {
        "w_entropy": round(1.6 + 0.20 * conf_signal, 6),
        "w_unvisited": round(0.02 + 0.02 * conf_signal, 6),
        "w_settlement": round(0.12 + 0.65 * settlement_under, 6),
        "w_repeat": 1.0,
        "w_late_settlement": round(0.18 + 0.30 * settlement_under + 0.05 * rare_over, 6),
    }
    fairness_boost = round(0.40 + 0.30 * conf_signal, 6)
    return {
        "safe": safe,
        "aggressive": aggressive,
        "fairness_boost": fairness_boost,
        "late_phase_bound": 0.9,
    }


def build_model(summary: Dict[str, Any], diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    avg_bias = _avg_bias(summary, diagnostics)
    mean_abs_bias = _mean([abs(v) for v in avg_bias])
    confidence_temperature = round(_clamp(1.0 + mean_abs_bias * 2.0, 1.0, 1.35), 6)

    return {
        "schema_version": "linear_v1",
        "model_version": f"linear_v1_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_set_version": "pred_v1_query_v1",
        "class_labels": CLASS_LABELS,
        "source": {
            "api_snapshot_summary": str((ROOT / "summary" / "api_snapshot_summary.json").relative_to(TASK_DIR)),
            "round_seed_diagnostics": str((ROOT / "summary" / "round_seed_diagnostics.json").relative_to(TASK_DIR)),
        },
        "prediction": {
            "max_abs_correction": 0.12,
            "global_class_bias_correction": _global_bias_correction(avg_bias),
            "terrain_prior_corrections": _terrain_corrections(summary, avg_bias),
            "confidence_temperature": confidence_temperature,
        },
        "query_policy": _query_policy(avg_bias, diagnostics),
        "training_signals": {
            "avg_diff_prediction_minus_gt": [round(v, 6) for v in avg_bias],
            "confidence_vs_seed_score_correlation": float(
                (diagnostics.get("aggregates") or {}).get("confidence_vs_seed_score_correlation", 0.0) or 0.0
            ),
        },
    }


def main() -> None:
    summary_path = ROOT / "summary" / "api_snapshot_summary.json"
    diagnostics_path = ROOT / "summary" / "round_seed_diagnostics.json"
    model_dir = ROOT / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    summary = _read_json(summary_path)
    diagnostics = _read_json(diagnostics_path)
    model = build_model(summary, diagnostics)

    versioned = model_dir / f"{model['model_version']}.json"
    latest = model_dir / "latest_linear_v1.json"
    encoded = json.dumps(model, indent=2, sort_keys=True)
    versioned.write_text(encoded + "\n")
    latest.write_text(encoded + "\n")

    print(f"wrote {versioned}")
    print(f"wrote {latest}")


if __name__ == "__main__":
    main()
