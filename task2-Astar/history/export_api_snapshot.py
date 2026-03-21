#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests


def require_token() -> str:
    token = os.getenv("ASTAR_ACCESS_TOKEN", "").strip()
    if not token:
        raise SystemExit("Missing ASTAR_ACCESS_TOKEN in environment")
    return token


def main() -> None:
    token = require_token()
    base_url = os.getenv("ASTAR_BASE_URL", "https://api.ainm.no/astar-island").rstrip("/")

    root = Path(__file__).resolve().parent
    raw_dir = root / "raw"
    summary_dir = root / "summary"
    raw_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token}"

    fetched_at = datetime.now(timezone.utc).isoformat()

    my_rounds_resp = session.get(f"{base_url}/my-rounds", timeout=30)
    my_rounds_resp.raise_for_status()
    rounds: List[Dict[str, Any]] = sorted(
        my_rounds_resp.json(),
        key=lambda r: int(r.get("round_number", 0)),
    )

    snapshot: Dict[str, Any] = {
        "fetched_at": fetched_at,
        "source": {
            "base_url": base_url,
            "endpoints": [
                "my-rounds",
                "my-predictions/{round_id}",
                "analysis/{round_id}/{seed_index}",
            ],
        },
        "my_rounds": rounds,
        "my_predictions_by_round": {},
        "analysis_by_round_seed": {},
        "errors": [],
    }

    for round_item in rounds:
        round_id = round_item["id"]
        round_number = int(round_item["round_number"])
        round_key = str(round_number)

        try:
            pred_resp = session.get(f"{base_url}/my-predictions/{round_id}", timeout=45)
            if pred_resp.status_code == 200:
                snapshot["my_predictions_by_round"][round_key] = pred_resp.json()
            else:
                snapshot["my_predictions_by_round"][round_key] = {
                    "status_code": pred_resp.status_code,
                    "body": pred_resp.text,
                }
                snapshot["errors"].append(
                    {
                        "round": round_number,
                        "endpoint": "my-predictions",
                        "status": pred_resp.status_code,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            snapshot["my_predictions_by_round"][round_key] = {"error": str(exc)}
            snapshot["errors"].append(
                {
                    "round": round_number,
                    "endpoint": "my-predictions",
                    "error": str(exc),
                }
            )

        seeds_count = int(round_item.get("seeds_count", 5) or 5)
        snapshot["analysis_by_round_seed"][round_key] = {}
        for seed_index in range(seeds_count):
            try:
                analysis_resp = session.get(
                    f"{base_url}/analysis/{round_id}/{seed_index}",
                    timeout=90,
                )
                if analysis_resp.status_code == 200:
                    snapshot["analysis_by_round_seed"][round_key][str(seed_index)] = analysis_resp.json()
                else:
                    snapshot["analysis_by_round_seed"][round_key][str(seed_index)] = {
                        "status_code": analysis_resp.status_code,
                        "body": analysis_resp.text,
                    }
                    snapshot["errors"].append(
                        {
                            "round": round_number,
                            "seed": seed_index,
                            "endpoint": "analysis",
                            "status": analysis_resp.status_code,
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                snapshot["analysis_by_round_seed"][round_key][str(seed_index)] = {"error": str(exc)}
                snapshot["errors"].append(
                    {
                        "round": round_number,
                        "seed": seed_index,
                        "endpoint": "analysis",
                        "error": str(exc),
                    }
                )

    full_path = raw_dir / "api_snapshot_full.json.gz"
    with gzip.open(full_path, "wt", encoding="utf-8") as handle:
        json.dump(snapshot, handle)

    summary: Dict[str, Any] = {
        "fetched_at": fetched_at,
        "rounds": [],
        "global": {
            "class_mean_completed": None,
            "avg_entropy_completed": None,
            "by_initial_code": {},
        },
        "bias_on_submitted_rounds": {},
    }

    global_cells = 0
    global_class_sum = [0.0] * 6
    global_entropy_sum = 0.0
    by_initial_code: Dict[int, Dict[str, Any]] = {}

    for round_item in rounds:
        round_number = int(round_item.get("round_number", 0))
        round_key = str(round_number)

        row: Dict[str, Any] = {
            "round_number": round_number,
            "id": round_item["id"],
            "status": round_item.get("status"),
            "event_date": round_item.get("event_date"),
            "round_weight": round_item.get("round_weight"),
            "round_score": round_item.get("round_score"),
            "seed_scores": round_item.get("seed_scores"),
            "rank": round_item.get("rank"),
            "total_teams": round_item.get("total_teams"),
            "seeds_count": round_item.get("seeds_count"),
            "seeds_submitted": round_item.get("seeds_submitted"),
            "queries_used": round_item.get("queries_used"),
            "queries_max": round_item.get("queries_max"),
            "started_at": round_item.get("started_at"),
            "closes_at": round_item.get("closes_at"),
            "prediction_window_minutes": round_item.get("prediction_window_minutes"),
            "analysis_ok_seeds": 0,
            "prediction_present_seeds": 0,
            "avg_entropy": None,
            "class_mean": None,
        }

        class_sum = [0.0] * 6
        entropy_sum = 0.0
        cells = 0
        pred_present = 0

        for analysis in (snapshot["analysis_by_round_seed"].get(round_key) or {}).values():
            if not isinstance(analysis, dict) or "ground_truth" not in analysis:
                continue

            row["analysis_ok_seeds"] += 1
            if analysis.get("prediction") is not None:
                pred_present += 1

            ground_truth = analysis["ground_truth"]
            initial_grid = analysis.get("initial_grid")

            height = len(ground_truth)
            width = len(ground_truth[0]) if height else 0

            for y in range(height):
                for x in range(width):
                    dist = ground_truth[y][x]
                    entropy = 0.0
                    for prob in dist:
                        if prob > 0:
                            entropy -= prob * math.log(prob)
                    entropy_sum += entropy
                    cells += 1
                    for i, prob in enumerate(dist):
                        class_sum[i] += prob

                    if initial_grid is not None:
                        terrain = int(initial_grid[y][x])
                        accum = by_initial_code.setdefault(
                            terrain,
                            {"cells": 0, "class_sum": [0.0] * 6, "entropy_sum": 0.0},
                        )
                        accum["cells"] += 1
                        accum["entropy_sum"] += entropy
                        for i, prob in enumerate(dist):
                            accum["class_sum"][i] += prob

        row["prediction_present_seeds"] = pred_present
        if cells:
            row["avg_entropy"] = entropy_sum / cells
            row["class_mean"] = [value / cells for value in class_sum]
            if round_item.get("status") == "completed":
                global_cells += cells
                global_entropy_sum += entropy_sum
                for i, value in enumerate(class_sum):
                    global_class_sum[i] += value

        if row["prediction_present_seeds"] > 0:
            gt_sum = [0.0] * 6
            pred_sum = [0.0] * 6
            diff_cells = 0
            for analysis in (snapshot["analysis_by_round_seed"].get(round_key) or {}).values():
                if (
                    not isinstance(analysis, dict)
                    or "ground_truth" not in analysis
                    or analysis.get("prediction") is None
                ):
                    continue
                gt = analysis["ground_truth"]
                pred = analysis["prediction"]
                height = len(gt)
                width = len(gt[0]) if height else 0
                for y in range(height):
                    for x in range(width):
                        diff_cells += 1
                        for i in range(6):
                            gt_sum[i] += gt[y][x][i]
                            pred_sum[i] += pred[y][x][i]
            if diff_cells:
                gt_mean = [value / diff_cells for value in gt_sum]
                pred_mean = [value / diff_cells for value in pred_sum]
                summary["bias_on_submitted_rounds"][round_key] = {
                    "gt_mean": gt_mean,
                    "prediction_mean": pred_mean,
                    "diff_prediction_minus_gt": [pred_mean[i] - gt_mean[i] for i in range(6)],
                }

        summary["rounds"].append(row)

    if global_cells:
        summary["global"]["class_mean_completed"] = [value / global_cells for value in global_class_sum]
        summary["global"]["avg_entropy_completed"] = global_entropy_sum / global_cells

    for terrain, accum in sorted(by_initial_code.items()):
        n = accum["cells"]
        summary["global"]["by_initial_code"][str(terrain)] = {
            "cells": n,
            "avg_entropy": (accum["entropy_sum"] / n) if n else None,
            "class_mean": ([value / n for value in accum["class_sum"]] if n else None),
        }

    (summary_dir / "api_snapshot_summary.json").write_text(json.dumps(summary, indent=2))
    (summary_dir / "my_rounds_raw.json").write_text(json.dumps(rounds, indent=2))

    meta = {
        "fetched_at": fetched_at,
        "full_snapshot_gz": full_path.name,
        "summary_file": "api_snapshot_summary.json",
        "round_count": len(rounds),
        "errors_count": len(snapshot.get("errors", [])),
    }
    (summary_dir / "api_snapshot_meta.json").write_text(json.dumps(meta, indent=2))

    print(f"wrote {full_path}")
    print(f"wrote {summary_dir / 'api_snapshot_summary.json'}")
    print(f"wrote {summary_dir / 'my_rounds_raw.json'}")
    print(f"wrote {summary_dir / 'api_snapshot_meta.json'}")
    print(f"errors {len(snapshot.get('errors', []))}")


if __name__ == "__main__":
    main()
