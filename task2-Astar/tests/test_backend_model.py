import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend import AstarService


def _valid_model_payload() -> dict:
    return {
        "schema_version": "linear_v1",
        "model_version": "linear_v1_test",
        "feature_set_version": "pred_v1_query_v1",
        "prediction": {
            "max_abs_correction": 0.12,
            "global_class_bias_correction": [0.0, 0.01, -0.01, -0.01, 0.01, 0.0],
            "terrain_prior_corrections": {
                "11": {"far": [0.0, 0.01, -0.01, -0.01, 0.01, 0.0], "near": [0.0, 0.02, -0.01, -0.01, 0.0, 0.0]},
                "10": {"far": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "near": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
            },
            "confidence_temperature": 1.05,
        },
        "query_policy": {
            "safe": {
                "w_entropy": 1.0,
                "w_unvisited": 0.05,
                "w_settlement": 0.08,
                "w_repeat": 2.0,
                "w_late_settlement": 0.10,
            },
            "aggressive": {
                "w_entropy": 1.6,
                "w_unvisited": 0.02,
                "w_settlement": 0.12,
                "w_repeat": 1.0,
                "w_late_settlement": 0.18,
            },
            "fairness_boost": 0.4,
            "late_phase_bound": 0.9,
        },
    }


def test_model_fallback_when_artifact_missing(tmp_path, monkeypatch):
    model_path = tmp_path / "does-not-exist.json"
    monkeypatch.setenv("ASTAR_MODEL_PATH", str(model_path))
    service = AstarService(runtime_dir=str(tmp_path / "runtime"))
    status = service.get_model_status()
    assert status["model_loaded"] is False
    assert status["fallback_mode"] == "model_artifact_missing"


def test_model_loads_when_artifact_valid(tmp_path, monkeypatch):
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(_valid_model_payload()))
    monkeypatch.setenv("ASTAR_MODEL_PATH", str(model_path))
    service = AstarService(runtime_dir=str(tmp_path / "runtime"))
    model_status = service.get_model_status()
    api_status = service.get_status()
    assert model_status["model_loaded"] is True
    assert model_status["model_version"] == "linear_v1_test"
    assert api_status["model_version"] == "linear_v1_test"
    assert api_status["fallback_mode"] == "model_loaded"


def test_phase_b_fairness_boost_prevents_seed_starvation(tmp_path, monkeypatch):
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(_valid_model_payload()))
    monkeypatch.setenv("ASTAR_MODEL_PATH", str(model_path))
    service = AstarService(runtime_dir=str(tmp_path / "runtime"))

    width = 40
    height = 40
    initial_grid = [[11 for _ in range(width)] for _ in range(height)]
    seeds = {}
    for seed_index in range(5):
        seed = service._new_seed_state(seed_index, width, height, initial_grid, [])
        if seed_index == 0:
            seed["queries_used"] = 0
            seed["uncertainty_grid"] = [[0.0 for _ in range(width)] for _ in range(height)]
        else:
            seed["queries_used"] = 10
            seed["uncertainty_grid"] = [[1.0 for _ in range(width)] for _ in range(height)]
        seeds[str(seed_index)] = seed

    service.state["active_round"] = {"id": "r", "width": width, "height": height}
    service.state["profile"] = "safe"
    service.state["queries"] = {"used": 30, "max": 50, "remaining": 20}
    service.state["scouting_plan"] = []
    service.state["seeds"] = seeds
    service.state["query_policy"] = {
        "safe": {
            "w_entropy": 1.0,
            "w_unvisited": 0.0,
            "w_settlement": 0.0,
            "w_repeat": 0.0,
            "w_late_settlement": 0.0,
        },
        "aggressive": {
            "w_entropy": 1.0,
            "w_unvisited": 0.0,
            "w_settlement": 0.0,
            "w_repeat": 0.0,
            "w_late_settlement": 0.0,
        },
        "fairness_boost": 300.0,
        "late_phase_bound": 1.0,
    }

    item = service._select_next_query(queries_used=30)
    assert item is not None
    assert item["seed_index"] == 0
