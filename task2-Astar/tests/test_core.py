import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core import (
    cell_distribution,
    clamp_viewport,
    normalize_with_floor,
    terrain_code_to_class,
    validate_prediction_tensor,
)


def test_terrain_mapping():
    assert terrain_code_to_class(10) == 0
    assert terrain_code_to_class(11) == 0
    assert terrain_code_to_class(0) == 0
    assert terrain_code_to_class(1) == 1
    assert terrain_code_to_class(5) == 5


def test_normalize_with_floor():
    dist = normalize_with_floor([1.0, 0.0, 0.0, 0.0, 0.0, 0.0], floor=0.01)
    assert len(dist) == 6
    assert abs(sum(dist) - 1.0) < 1e-9
    assert min(dist) >= 0.01


def test_cell_distribution_no_zeros():
    dist = cell_distribution(
        initial_code=11,
        observed_counts=[0, 0, 0, 0, 0, 0],
        near_settlement=True,
        aggressive=False,
        floor=0.01,
    )
    assert len(dist) == 6
    assert all(v > 0 for v in dist)
    assert abs(sum(dist) - 1.0) < 1e-8


def test_validate_prediction_tensor_passes():
    pred = [[[1 / 6] * 6 for _ in range(2)] for _ in range(2)]
    out = validate_prediction_tensor(prediction=pred, height=2, width=2, floor=0.01)
    assert out["submit_ready"]


def test_validate_prediction_tensor_fails_bad_shape():
    pred = [[[1 / 6] * 6 for _ in range(3)] for _ in range(2)]
    out = validate_prediction_tensor(prediction=pred, height=2, width=2, floor=0.01)
    assert not out["submit_ready"]
    assert not out["shape_ok"]


def test_clamp_viewport_bounds():
    x, y, w, h = clamp_viewport(-4, 99, 40, 1, width=40, height=40)
    assert (x, y, w, h) == (0, 35, 15, 5)
