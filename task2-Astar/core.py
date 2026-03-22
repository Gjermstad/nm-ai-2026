from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

CLASS_NAMES = ["Empty", "Settlement", "Port", "Ruin", "Forest", "Mountain"]
FLOAT_EPS = 1e-12


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

    # Final tiny numerical correction without re-scaling all classes.
    # Re-scaling can push exact-floor classes to 0.009999... and trip strict floor checks.
    s = sum(probs)
    if s <= 0:
        return [1.0 / n] * n
    residual = 1.0 - s
    if abs(residual) > FLOAT_EPS:
        i_max = max(range(n), key=lambda i: probs[i])
        probs[i_max] += residual

    # Clamp tiny floating negatives to zero and run one final floor repair pass if needed.
    probs = [0.0 if (-FLOAT_EPS < p < 0.0) else p for p in probs]
    if any(p + FLOAT_EPS < floor for p in probs):
        return normalize_with_floor(probs, floor=floor)
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
        base = [0.30, 0.05, 0.02, 0.04, 0.54, 0.05]
    elif initial_code == 3:
        base = [0.22, 0.14, 0.08, 0.34, 0.18, 0.04]
    elif initial_code == 2:
        base = [0.22, 0.12, 0.36, 0.08, 0.18, 0.04]
    elif initial_code == 1:
        base = [0.22, 0.34, 0.12, 0.10, 0.18, 0.04]
    else:
        base = [0.84, 0.05, 0.02, 0.03, 0.04, 0.02]

    if near_settlement and initial_code not in (5, 10):
        dynamic_boost = 0.025 if not aggressive else 0.04
        base[1] += dynamic_boost
        base[2] += dynamic_boost * 0.5
        base[3] += dynamic_boost * 0.35
        base[0] -= dynamic_boost * 1.85

    if aggressive and initial_code not in (5, 10):
        base[1] += 0.015
        base[3] += 0.01
        base[0] -= 0.02
        base[4] -= 0.005

    return normalize_with_floor(base, floor=0.001)


def cell_distribution(
    initial_code: int,
    observed_counts: Sequence[int],
    near_settlement: bool,
    aggressive: bool,
    floor: float,
) -> List[float]:
    prior = prior_distribution(initial_code, near_settlement, aggressive)
    alpha = 5.5 if aggressive else 9.0
    posterior = [prior[i] * alpha + float(observed_counts[i]) for i in range(6)]
    distribution = normalize_with_floor(posterior, floor=floor)

    observed_total = int(sum(max(0.0, float(v)) for v in observed_counts[:6]))
    rare_obs = sum(max(0.0, float(observed_counts[i])) for i in (2, 3, 5))

    # In low-evidence cells, keep rare tails conservative unless we have direct rare-class evidence.
    if initial_code not in (2, 3, 5) and observed_total <= 1 and rare_obs <= 0:
        caps = {2: 0.03, 3: 0.04, 5: 0.015}
        reclaimed = 0.0
        for i, cap in caps.items():
            if distribution[i] > cap:
                reclaimed += distribution[i] - cap
                distribution[i] = cap

        if reclaimed > FLOAT_EPS:
            receivers = [0, 1, 4]  # Empty, Settlement, Forest
            weights = [0.55, 0.15, 0.30]
            for idx, weight in zip(receivers, weights):
                distribution[idx] += reclaimed * weight
            distribution = normalize_with_floor(distribution, floor=floor)

    return distribution


def _apply_temperature(distribution: Sequence[float], temperature: float, floor: float) -> List[float]:
    bounded_temp = max(0.05, min(float(temperature), 3.0))
    power = 1.0 / bounded_temp
    scaled = [max(float(p), FLOAT_EPS) ** power for p in distribution]
    return normalize_with_floor(scaled, floor=floor)


def apply_learned_adjustments(
    distribution: Sequence[float],
    initial_code: int,
    near_settlement: bool,
    model: Dict[str, Any] | None,
    floor: float,
) -> List[float]:
    if not model:
        return list(distribution)

    prediction_cfg = model.get("prediction")
    if not isinstance(prediction_cfg, dict):
        return list(distribution)

    probs = normalize_with_floor([max(float(v), 0.0) for v in distribution], floor=floor)
    max_abs = max(0.0, min(float(prediction_cfg.get("max_abs_correction", 0.12)), 0.5))

    terrain_corr = prediction_cfg.get("terrain_prior_corrections", {})
    if isinstance(terrain_corr, dict):
        entry = terrain_corr.get(str(initial_code))
        if isinstance(entry, dict):
            key = "near" if near_settlement else "far"
            corr = entry.get(key) or entry.get("far")
            if isinstance(corr, list) and len(corr) == 6:
                probs = [
                    max(0.0, probs[i] + max(-max_abs, min(max_abs, float(corr[i]))))
                    for i in range(6)
                ]
                probs = normalize_with_floor(probs, floor=floor)

    global_bias = prediction_cfg.get("global_class_bias_correction")
    if isinstance(global_bias, list) and len(global_bias) == 6:
        probs = [
            max(0.0, probs[i] + max(-max_abs, min(max_abs, float(global_bias[i]))))
            for i in range(6)
        ]
        probs = normalize_with_floor(probs, floor=floor)

    temperature = float(prediction_cfg.get("confidence_temperature", 1.0))
    if abs(temperature - 1.0) > FLOAT_EPS:
        probs = _apply_temperature(probs, temperature=temperature, floor=floor)

    return normalize_with_floor(probs, floor=floor)


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
            if any(v + FLOAT_EPS < floor for v in cell):
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
