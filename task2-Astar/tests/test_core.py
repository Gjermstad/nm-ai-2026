import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core import (
    cell_distribution,
    clamp_viewport,
    normalize_with_floor,
    prior_distribution,
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


def test_unknown_terrain_prior_stays_empty_dominant():
    safe = prior_distribution(initial_code=0, near_settlement=False, aggressive=False)
    aggr = prior_distribution(initial_code=0, near_settlement=False, aggressive=True)
    assert safe[0] >= 0.8
    assert aggr[0] >= 0.75
    assert (aggr[1] + aggr[2] + aggr[3]) <= 0.2


def test_near_settlement_aggressive_prior_is_bounded():
    near = prior_distribution(initial_code=0, near_settlement=True, aggressive=True)
    assert near[0] >= 0.65
    assert (near[1] + near[2] + near[3]) <= 0.3


def test_validate_prediction_tensor_passes():
    pred = [[[1 / 6] * 6 for _ in range(2)] for _ in range(2)]
    out = validate_prediction_tensor(prediction=pred, height=2, width=2, floor=0.01)
    assert out["submit_ready"]


def test_validate_prediction_tensor_tolerates_float_roundoff_near_floor():
    # 0.009999999999999998 is a common floating representation of 0.01.
    cell = [0.009999999999999998, 0.19, 0.2, 0.2, 0.2, 0.2]
    pred = [[cell]]
    out = validate_prediction_tensor(prediction=pred, height=1, width=1, floor=0.01)
    assert out["floor_ok"]
    assert out["submit_ready"]


def test_validate_prediction_tensor_fails_bad_shape():
    pred = [[[1 / 6] * 6 for _ in range(3)] for _ in range(2)]
    out = validate_prediction_tensor(prediction=pred, height=2, width=2, floor=0.01)
    assert not out["submit_ready"]
    assert not out["shape_ok"]


def test_clamp_viewport_bounds():
    x, y, w, h = clamp_viewport(-4, 99, 40, 1, width=40, height=40)
    assert (x, y, w, h) == (0, 35, 15, 5)
