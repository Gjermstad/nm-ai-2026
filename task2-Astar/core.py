from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

CLASS_NAMES = ["Empty", "Settlement", "Port", "Ruin", "Forest", "Mountain"]


def terrain_code_to_class(code: int) -> int:
    if code in (10, 11, 0):
        return 0
    if code in (1, 2, 3, 4, 5):
        return code
    return 0


def clamp_viewport(x: int, y: int, w: int, h: int, width: int, height: int) -> Tuple[int, int, int, int]:
    w = min(max(w, 5), 15)
    h = min(max(h, 5), 15)
    x = max(0, min(x, max(0, width - w)))
    y = max(0, min(y, max(0, height - h)))
    return x, y, w, h


def normalize_with_floor(values: Sequence[float], floor: float = 0.01) -> List[float]:
    n = len(values)
    if n == 0:
        return []
    if floor < 0:
        floor = 0.0
    if floor * n >= 1.0:
        return [1.0 / n] * n

    # Start with a regular normalization.
    clipped = [max(float(v), 0.0) for v in values]
    total = sum(clipped)
    if total <= 0:
        probs = [1.0 / n] * n
    else:
        probs = [v / total for v in clipped]

    # Enforce a strict per-class floor while preserving sum=1.
    while True:
        low = [i for i, p in enumerate(probs) if p < floor]
        if not low:
            break

        high = [i for i in range(n) if i not in low]
        fixed_mass = floor * len(low)
        remaining = max(0.0, 1.0 - fixed_mass)

        for i in low:
            probs[i] = floor

        if not high:
            break

        high_mass = sum(probs[i] for i in high)
        if high_mass <= 0:
            share = remaining / len(high)
            for i in high:
                probs[i] = share
        else:
            scale = remaining / high_mass
            for i in high:
                probs[i] *= scale

    # Final tiny numerical correction.
    s = sum(probs)
    if s > 0:
        probs = [p / s for p in probs]
    return probs


def entropy(probs: Sequence[float]) -> float:
    h = 0.0
    for p in probs:
        if p > 0:
            h -= p * math.log(p)
    return h


def prior_distribution(initial_code: int, near_settlement: bool, aggressive: bool = False) -> List[float]:
    if initial_code == 10:
        base = [0.94, 0.01, 0.01, 0.01, 0.01, 0.02]
    elif initial_code == 5:
        base = [0.03, 0.01, 0.01, 0.01, 0.01, 0.93]
    elif initial_code == 4:
        base = [0.24, 0.08, 0.03, 0.08, 0.52, 0.05]
    elif initial_code == 3:
        base = [0.16, 0.20, 0.10, 0.44, 0.07, 0.03]
    elif initial_code == 2:
        base = [0.16, 0.18, 0.47, 0.10, 0.06, 0.03]
    elif initial_code == 1:
        base = [0.16, 0.44, 0.16, 0.13, 0.08, 0.03]
    else:
        base = [0.75, 0.08, 0.04, 0.05, 0.05, 0.03]

    if near_settlement and initial_code not in (5, 10):
        dynamic_boost = 0.06 if not aggressive else 0.12
        base[1] += dynamic_boost
        base[2] += dynamic_boost * 0.7
        base[3] += dynamic_boost * 0.6
        base[0] -= dynamic_boost * 1.6

    if aggressive and initial_code not in (5, 10):
        base[1] += 0.04
        base[3] += 0.03
        base[0] -= 0.05

    return normalize_with_floor(base, floor=0.001)


def cell_distribution(
    initial_code: int,
    observed_counts: Sequence[int],
    near_settlement: bool,
    aggressive: bool,
    floor: float,
) -> List[float]:
    prior = prior_distribution(initial_code, near_settlement, aggressive)
    alpha = 3.0 if aggressive else 8.0
    posterior = [prior[i] * alpha + float(observed_counts[i]) for i in range(6)]
    return normalize_with_floor(posterior, floor=floor)


def validate_prediction_tensor(
    prediction: Sequence[Sequence[Sequence[float]]],
    height: int,
    width: int,
    floor: float = 0.01,
) -> Dict[str, object]:
    out: Dict[str, object] = {
        "shape_ok": True,
        "non_negative_ok": True,
        "sum_ok": True,
        "floor_ok": True,
        "submit_ready": True,
        "errors": [],
    }

    if len(prediction) != height:
        out["shape_ok"] = False
        out["errors"].append(f"Expected {height} rows, got {len(prediction)}")

    for y, row in enumerate(prediction[:height]):
        if len(row) != width:
            out["shape_ok"] = False
            out["errors"].append(f"Row {y}: expected {width} cols, got {len(row)}")
            continue
        for x, cell in enumerate(row):
            if len(cell) != 6:
                out["shape_ok"] = False
                out["errors"].append(f"Cell ({y},{x}): expected 6 probs, got {len(cell)}")
                continue
            if any(v < 0 for v in cell):
                out["non_negative_ok"] = False
                out["errors"].append(f"Cell ({y},{x}): negative probability")
            s = sum(cell)
            if abs(s - 1.0) > 0.01:
                out["sum_ok"] = False
                out["errors"].append(f"Cell ({y},{x}): probs sum to {s:.4f}, expected 1.0")
            if any(v < floor for v in cell):
                out["floor_ok"] = False
                out["errors"].append(f"Cell ({y},{x}): value below floor {floor}")

    out["submit_ready"] = bool(out["shape_ok"] and out["non_negative_ok"] and out["sum_ok"] and out["floor_ok"])
    # Keep response concise for UI.
    if len(out["errors"]) > 25:
        out["errors"] = out["errors"][:25] + [f"... ({len(out['errors']) - 25} more)"]
    return out


def window_key(seed_index: int, x: int, y: int, w: int, h: int) -> str:
    return f"{seed_index}:{x}:{y}:{w}:{h}"


def viewport_class_counts(grid: Sequence[Sequence[int]]) -> Dict[int, int]:
    counts: Dict[int, int] = {i: 0 for i in range(6)}
    for row in grid:
        for code in row:
            counts[terrain_code_to_class(int(code))] += 1
    return counts


def generate_window_positions(width: int, height: int, window_size: int = 15, step: int = 5) -> List[Tuple[int, int]]:
    positions: List[Tuple[int, int]] = []
    y = 0
    while y <= max(0, height - window_size):
        x = 0
        while x <= max(0, width - window_size):
            positions.append((x, y))
            x += step
        y += step
    if not positions:
        positions.append((0, 0))
    return positions


def classify_deadline_risk(seconds_left: float, submitted: int, total: int) -> str:
    if submitted >= total:
        return "safe"
    if seconds_left <= 20 * 60:
        return "critical"
    if seconds_left <= 45 * 60:
        return "warning"
    return "safe"


def iso_now() -> str:
    import datetime as _dt

    return _dt.datetime.now(_dt.timezone.utc).isoformat()
