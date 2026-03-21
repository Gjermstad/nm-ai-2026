from __future__ import annotations

import copy
import json
import os
import random
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import requests

from core import (
    CLASS_NAMES,
    cell_distribution,
    clamp_viewport,
    classify_deadline_risk,
    entropy,
    generate_window_positions,
    iso_now,
    terrain_code_to_class,
    validate_prediction_tensor,
    viewport_class_counts,
    window_key,
)


class ApiError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, payload: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class StructuredLogBuffer:
    def __init__(self, max_entries: int = 2000):
        self._entries: Deque[Dict[str, Any]] = deque(maxlen=max_entries)
        self._lock = threading.RLock()

    def add(self, level: str, event: str, message: str, **details: Any) -> None:
        entry = {
            "ts": iso_now(),
            "level": level.lower(),
            "event": event,
            "message": message,
            "details": details,
        }
        with self._lock:
            self._entries.append(entry)

    def recent(self, limit: int = 200, level: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            entries = list(self._entries)
        if level:
            entries = [e for e in entries if e["level"] == level.lower()]
        return entries[-limit:]


class AstarApiClient:
    def __init__(self, base_url: str, access_token: Optional[str], logs: StructuredLogBuffer):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.logs = logs
        self.session = requests.Session()
        if access_token:
            self.session.headers["Authorization"] = f"Bearer {access_token}"
            self.session.cookies.set("access_token", access_token)

        self._rate_lock = threading.RLock()
        self._last_call: Dict[str, float] = {}
        self._rate_limits = {
            "simulate": 5.0,
            "submit": 2.0,
            "default": 10.0,
        }

    def set_access_token(self, token: Optional[str]) -> None:
        self.access_token = token
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
            self.session.cookies.set("access_token", token)
        else:
            self.session.headers.pop("Authorization", None)
            self.session.cookies.pop("access_token", None)

    def _respect_rate_limit(self, bucket: str) -> None:
        rps = self._rate_limits.get(bucket, self._rate_limits["default"])
        min_interval = 1.0 / max(rps, 0.1)
        with self._rate_lock:
            now = time.monotonic()
            last = self._last_call.get(bucket, 0.0)
            wait = min_interval - (now - last)
            if wait > 0:
                time.sleep(wait)
            self._last_call[bucket] = time.monotonic()

    def _request(
        self,
        method: str,
        path: str,
        *,
        bucket: str = "default",
        requires_auth: bool = False,
        retries: int = 4,
        **kwargs: Any,
    ) -> Any:
        if requires_auth and not self.access_token:
            raise ApiError("Missing ASTAR_ACCESS_TOKEN", status_code=401)

        url = f"{self.base_url}{path}"
        backoff = 0.5
        for attempt in range(retries + 1):
            self._respect_rate_limit(bucket)
            try:
                resp = self.session.request(method, url, timeout=30, **kwargs)
            except requests.RequestException as exc:
                if attempt >= retries:
                    raise ApiError(f"Network error: {exc}") from exc
                time.sleep(backoff)
                backoff *= 2
                continue

            if resp.status_code == 429 and attempt < retries:
                self.logs.add(
                    "warning",
                    "api_rate_limit",
                    "Received 429, retrying with backoff",
                    path=path,
                    attempt=attempt,
                )
                time.sleep(backoff + random.random() * 0.2)
                backoff = min(backoff * 2, 6.0)
                continue

            if resp.status_code >= 400:
                payload: Any
                try:
                    payload = resp.json()
                except ValueError:
                    payload = resp.text
                raise ApiError(
                    f"API error {resp.status_code} on {path}",
                    status_code=resp.status_code,
                    payload=payload,
                )

            if resp.status_code == 204:
                return {}
            try:
                return resp.json()
            except ValueError:
                return {"raw": resp.text}

        raise ApiError(f"Exceeded retries for {path}")

    def get_rounds(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/rounds", requires_auth=False)

    def get_round_details(self, round_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/rounds/{round_id}", requires_auth=False)

    def get_budget(self) -> Dict[str, Any]:
        return self._request("GET", "/budget", requires_auth=True)

    def simulate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/simulate", bucket="simulate", requires_auth=True, json=payload)

    def submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/submit", bucket="submit", requires_auth=True, json=payload)


class AstarService:
    def __init__(self, runtime_dir: str, poll_seconds: float = 2.0):
        self.runtime_dir = Path(runtime_dir)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.runtime_dir / "state.json"
        self.poll_seconds = poll_seconds

        self.logs = StructuredLogBuffer()
        base_url = os.getenv("ASTAR_BASE_URL", "https://api.ainm.no/astar-island")
        token = os.getenv("ASTAR_ACCESS_TOKEN")
        self.api = AstarApiClient(base_url=base_url, access_token=token, logs=self.logs)

        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self.state: Dict[str, Any] = {
            "run_enabled": False,
            "profile": "safe",
            "deadline_guard_enabled": True,
            "active_round": None,
            "queries": {"used": 0, "max": 50, "remaining": 50},
            "seeds": {},
            "scouting_plan": [],
            "last_error": None,
            "last_error_action": None,
            "token_present": bool(token),
            "started_at": iso_now(),
        }
        self._load_state()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        self.logs.add("info", "service_start", "Astar service started")

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self.logs.add("info", "service_stop", "Astar service stopped")

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text())
        except Exception as exc:
            self.logs.add("warning", "state_load_failed", "Could not load persisted state", error=str(exc))
            return

        for key in [
            "run_enabled",
            "profile",
            "deadline_guard_enabled",
            "active_round",
            "queries",
            "seeds",
            "scouting_plan",
            "last_error",
            "last_error_action",
            "started_at",
        ]:
            if key in data:
                self.state[key] = data[key]
        self.state["token_present"] = bool(self.api.access_token)

    def _persist_state(self) -> None:
        persist = {
            "run_enabled": self.state["run_enabled"],
            "profile": self.state["profile"],
            "deadline_guard_enabled": self.state["deadline_guard_enabled"],
            "active_round": self.state["active_round"],
            "queries": self.state["queries"],
            "seeds": self.state["seeds"],
            "scouting_plan": self.state["scouting_plan"],
            "last_error": self.state["last_error"],
            "last_error_action": self.state["last_error_action"],
            "started_at": self.state["started_at"],
        }
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(persist))
        tmp.replace(self.state_path)

    def _set_error(self, message: str, action: str) -> None:
        self.state["last_error"] = message
        self.state["last_error_action"] = action

    def _clear_error(self) -> None:
        self.state["last_error"] = None
        self.state["last_error_action"] = None

    def _worker_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    return
            try:
                self._tick()
            except Exception as exc:
                with self._lock:
                    self._set_error(str(exc), "Check logs and retry")
                self.logs.add("error", "worker_tick_failed", "Background tick failed", error=str(exc))
            time.sleep(self.poll_seconds)

    def _tick(self) -> None:
        with self._lock:
            self.state["token_present"] = bool(self.api.access_token)

        self._refresh_round()
        self._refresh_budget()

        with self._lock:
            run_enabled = self.state["run_enabled"]
            active_round = self.state["active_round"]

        if not active_round:
            return

        if run_enabled:
            self._run_query_cycle_if_needed()
        self._deadline_guard_check()

    def _refresh_round(self) -> None:
        rounds = self.api.get_rounds()
        active = next((r for r in rounds if r.get("status") == "active"), None)

        with self._lock:
            current = self.state.get("active_round")

        if not active:
            with self._lock:
                self.state["active_round"] = None
            return

        if current and current.get("id") == active.get("id"):
            with self._lock:
                current.update(
                    {
                        "status": active.get("status"),
                        "closes_at": active.get("closes_at"),
                        "round_number": active.get("round_number"),
                    }
                )
            return

        detail = self.api.get_round_details(active["id"])
        width = int(detail.get("map_width", 40))
        height = int(detail.get("map_height", 40))
        seeds_count = int(detail.get("seeds_count", 5))

        new_round = {
            "id": detail["id"],
            "round_number": detail.get("round_number"),
            "status": detail.get("status", "active"),
            "width": width,
            "height": height,
            "seeds_count": seeds_count,
            "closes_at": active.get("closes_at"),
            "started_at": active.get("started_at"),
        }

        seeds_state: Dict[str, Any] = {}
        initial_states = detail.get("initial_states", [])
        for seed_index in range(seeds_count):
            init_state = initial_states[seed_index] if seed_index < len(initial_states) else {}
            initial_grid = init_state.get("grid", [[11 for _ in range(width)] for _ in range(height)])
            settlements = init_state.get("settlements", [])
            seeds_state[str(seed_index)] = self._new_seed_state(seed_index, width, height, initial_grid, settlements)

        scouting_plan = self._generate_scouting_plan(seeds_state, width, height)

        with self._lock:
            self.state["active_round"] = new_round
            self.state["seeds"] = seeds_state
            self.state["queries"] = {"used": 0, "max": 50, "remaining": 50}
            self.state["scouting_plan"] = scouting_plan
            self._clear_error()
            self._persist_state()

        self.logs.add("info", "round_changed", "Loaded new active round", round_id=new_round["id"])
        self.rebuild_drafts()

    def _refresh_budget(self) -> None:
        if not self.api.access_token:
            return
        with self._lock:
            if not self.state.get("active_round"):
                return
        try:
            budget = self.api.get_budget()
        except ApiError as exc:
            self.logs.add("warning", "budget_failed", "Failed to fetch budget", error=str(exc), status=exc.status_code)
            return

        with self._lock:
            self.state["queries"] = {
                "used": int(budget.get("queries_used", self.state["queries"]["used"])),
                "max": int(budget.get("queries_max", self.state["queries"]["max"])),
                "remaining": int(budget.get("queries_max", 50)) - int(budget.get("queries_used", 0)),
            }

    def _new_seed_state(
        self,
        seed_index: int,
        width: int,
        height: int,
        initial_grid: List[List[int]],
        settlements: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        near_mask = [[False for _ in range(width)] for _ in range(height)]
        for s in settlements:
            sx = int(s.get("x", 0))
            sy = int(s.get("y", 0))
            for y in range(max(0, sy - 3), min(height, sy + 4)):
                for x in range(max(0, sx - 3), min(width, sx + 4)):
                    near_mask[y][x] = True

        visits = [[0 for _ in range(width)] for _ in range(height)]
        counts = [[[0 for _ in range(6)] for _ in range(width)] for _ in range(height)]
        argmax_grid = [[0 for _ in range(width)] for _ in range(height)]
        uncertainty_grid = [[0.0 for _ in range(width)] for _ in range(height)]
        draft = [[[1.0 / 6.0 for _ in range(6)] for _ in range(width)] for _ in range(height)]
        return {
            "seed_index": seed_index,
            "width": width,
            "height": height,
            "initial_grid": initial_grid,
            "initial_settlements": settlements,
            "near_settlement_mask": near_mask,
            "observed_visits": visits,
            "observed_counts": counts,
            "queried_windows": {},
            "last_viewport": None,
            "last_viewport_counts": {str(i): 0 for i in range(6)},
            "draft": draft,
            "argmax_grid": argmax_grid,
            "uncertainty_grid": uncertainty_grid,
            "validation": {
                "shape_ok": True,
                "non_negative_ok": True,
                "sum_ok": True,
                "floor_ok": True,
                "submit_ready": True,
                "errors": [],
            },
            "submitted": False,
            "submitted_at": None,
            "submit_status": "not_submitted",
            "queries_used": 0,
            "coverage_pct": 0.0,
            "avg_entropy": 0.0,
            "avg_confidence": 1.0 / 6.0,
            "latest_settlement_count": len(settlements),
            "latest_alive_settlement_count": len([s for s in settlements if s.get("alive", True)]),
        }

    def _generate_scouting_plan(self, seeds_state: Dict[str, Any], width: int, height: int) -> List[Dict[str, Any]]:
        per_seed: Dict[int, List[Tuple[int, int]]] = {}
        base_positions = [(0, 0), (12, 0), (25, 0), (0, 12), (12, 12), (25, 12), (0, 25), (12, 25), (25, 25)]
        for seed_key, seed_state in seeds_state.items():
            sidx = int(seed_key)
            seen = set()
            positions: List[Tuple[int, int]] = []

            for st in seed_state.get("initial_settlements", [])[:12]:
                x = int(st.get("x", 0)) - 7
                y = int(st.get("y", 0)) - 7
                cx, cy, _, _ = clamp_viewport(x, y, 15, 15, width, height)
                if (cx, cy) not in seen:
                    positions.append((cx, cy))
                    seen.add((cx, cy))

            for x, y in base_positions:
                cx, cy, _, _ = clamp_viewport(x, y, 15, 15, width, height)
                if (cx, cy) not in seen:
                    positions.append((cx, cy))
                    seen.add((cx, cy))

            per_seed[sidx] = positions

        plan: List[Dict[str, Any]] = []
        exhausted = False
        i = 0
        while not exhausted:
            exhausted = True
            for seed_index in sorted(per_seed.keys()):
                arr = per_seed[seed_index]
                if i < len(arr):
                    exhausted = False
                    x, y = arr[i]
                    plan.append({"seed_index": seed_index, "viewport_x": x, "viewport_y": y, "viewport_w": 15, "viewport_h": 15})
            i += 1

        return plan

    def _seconds_to_close(self) -> Optional[float]:
        with self._lock:
            round_state = self.state.get("active_round")
            if not round_state or not round_state.get("closes_at"):
                return None
            closes_at = round_state["closes_at"]
        try:
            dt = datetime.fromisoformat(closes_at.replace("Z", "+00:00"))
        except ValueError:
            return None
        return (dt - datetime.now(timezone.utc)).total_seconds()

    def _run_query_cycle_if_needed(self) -> None:
        if not self.api.access_token:
            with self._lock:
                self._set_error("Missing ASTAR_ACCESS_TOKEN", "Set ASTAR_ACCESS_TOKEN and restart")
            return

        with self._lock:
            queries = copy.deepcopy(self.state["queries"])
            active_round = copy.deepcopy(self.state["active_round"])
            if not active_round:
                return

        seconds_left = self._seconds_to_close()
        if queries["remaining"] <= 0:
            return
        if queries["used"] >= 48 and (seconds_left is None or seconds_left > 30 * 60):
            return

        next_query = self._select_next_query(queries_used=queries["used"])
        if not next_query:
            return

        payload = {
            "round_id": active_round["id"],
            "seed_index": next_query["seed_index"],
            "viewport_x": next_query["viewport_x"],
            "viewport_y": next_query["viewport_y"],
            "viewport_w": next_query["viewport_w"],
            "viewport_h": next_query["viewport_h"],
        }

        try:
            sim = self.api.simulate(payload)
        except ApiError as exc:
            self.logs.add(
                "warning",
                "simulate_failed",
                "Simulation query failed",
                status=exc.status_code,
                payload=exc.payload,
                seed_index=next_query["seed_index"],
            )
            with self._lock:
                self._set_error(
                    f"Simulate failed ({exc.status_code})",
                    "Check auth/budget/rate limits and retry",
                )
            return

        self._ingest_simulation(next_query["seed_index"], sim)

        with self._lock:
            self.state["queries"]["used"] = int(sim.get("queries_used", self.state["queries"]["used"] + 1))
            self.state["queries"]["max"] = int(sim.get("queries_max", self.state["queries"]["max"]))
            self.state["queries"]["remaining"] = self.state["queries"]["max"] - self.state["queries"]["used"]

        self.logs.add(
            "info",
            "simulate_ok",
            "Simulation query succeeded",
            seed_index=next_query["seed_index"],
            viewport=sim.get("viewport"),
            queries_used=self.state["queries"]["used"],
        )

        self.rebuild_drafts()

    def _select_next_query(self, queries_used: int) -> Optional[Dict[str, int]]:
        with self._lock:
            profile = self.state["profile"]
            active_round = self.state.get("active_round")
            seeds = self.state.get("seeds", {})
            scouting_plan = self.state.get("scouting_plan", [])
        if not active_round:
            return None

        # Phase A: scouting across all seeds.
        if queries_used < 25:
            for item in scouting_plan:
                seed = seeds.get(str(item["seed_index"]))
                if not seed:
                    continue
                key = window_key(item["seed_index"], item["viewport_x"], item["viewport_y"], item["viewport_w"], item["viewport_h"])
                if key not in seed["queried_windows"]:
                    return item

        # Phase B: uncertainty-focused windows.
        best_item = None
        best_score = float("-inf")
        width = int(active_round["width"])
        height = int(active_round["height"])
        for seed_key, seed in seeds.items():
            sidx = int(seed_key)
            positions = generate_window_positions(width, height, window_size=15, step=5)
            for x, y in positions:
                x, y, w, h = clamp_viewport(x, y, 15, 15, width, height)
                key = window_key(sidx, x, y, w, h)
                repeat_penalty = seed["queried_windows"].get(key, 0)

                entropy_sum = 0.0
                unvisited = 0
                settlement_mass = 0
                for yy in range(y, y + h):
                    for xx in range(x, x + w):
                        entropy_sum += float(seed["uncertainty_grid"][yy][xx])
                        if seed["observed_visits"][yy][xx] == 0:
                            unvisited += 1
                        if seed["near_settlement_mask"][yy][xx]:
                            settlement_mass += 1

                score = entropy_sum + 0.05 * unvisited + 0.08 * settlement_mass - repeat_penalty * 2.0
                if profile == "aggressive":
                    score = entropy_sum * 1.6 + 0.12 * settlement_mass + 0.02 * unvisited - repeat_penalty * 1.0

                if score > best_score:
                    best_score = score
                    best_item = {
                        "seed_index": sidx,
                        "viewport_x": x,
                        "viewport_y": y,
                        "viewport_w": w,
                        "viewport_h": h,
                    }

        return best_item

    def _ingest_simulation(self, seed_index: int, sim: Dict[str, Any]) -> None:
        viewport = sim.get("viewport") or {}
        x = int(viewport.get("x", 0))
        y = int(viewport.get("y", 0))
        w = int(viewport.get("w", 15))
        h = int(viewport.get("h", 15))
        grid = sim.get("grid", [])
        settlements = sim.get("settlements", [])

        with self._lock:
            seed = self.state["seeds"].get(str(seed_index))
            if not seed:
                return

            width = seed["width"]
            height = seed["height"]
            x, y, w, h = clamp_viewport(x, y, w, h, width, height)
            for dy, row in enumerate(grid[:h]):
                for dx, code in enumerate(row[:w]):
                    gx = x + dx
                    gy = y + dy
                    if 0 <= gx < width and 0 <= gy < height:
                        klass = terrain_code_to_class(int(code))
                        seed["observed_counts"][gy][gx][klass] += 1
                        seed["observed_visits"][gy][gx] += 1

            seed["last_viewport"] = {"x": x, "y": y, "w": w, "h": h}
            seed["last_viewport_counts"] = {str(k): v for k, v in viewport_class_counts(grid).items()}
            key = window_key(seed_index, x, y, w, h)
            seed["queried_windows"][key] = int(seed["queried_windows"].get(key, 0)) + 1
            seed["queries_used"] += 1

            seed["latest_settlement_count"] = len(settlements)
            seed["latest_alive_settlement_count"] = len([s for s in settlements if s.get("alive", True)])

            total_cells = width * height
            observed_cells = sum(1 for row in seed["observed_visits"] for v in row if v > 0)
            seed["coverage_pct"] = (100.0 * observed_cells / total_cells) if total_cells else 0.0

            self._persist_state()

    def rebuild_drafts(self) -> Dict[str, Any]:
        with self._lock:
            seeds = self.state.get("seeds", {})
            profile = self.state.get("profile", "safe")

            for seed in seeds.values():
                width = seed["width"]
                height = seed["height"]
                floor = 0.01
                entropy_sum = 0.0
                confidence_sum = 0.0

                for y in range(height):
                    for x in range(width):
                        initial_code = int(seed["initial_grid"][y][x])
                        near = bool(seed["near_settlement_mask"][y][x])
                        counts = seed["observed_counts"][y][x]
                        dist = cell_distribution(
                            initial_code=initial_code,
                            observed_counts=counts,
                            near_settlement=near,
                            aggressive=(profile == "aggressive"),
                            floor=floor,
                        )
                        seed["draft"][y][x] = dist
                        argmax_i = max(range(6), key=lambda i: dist[i])
                        seed["argmax_grid"][y][x] = argmax_i
                        h_val = entropy(dist)
                        seed["uncertainty_grid"][y][x] = h_val
                        entropy_sum += h_val
                        confidence_sum += max(dist)

                validation = validate_prediction_tensor(seed["draft"], height=height, width=width, floor=floor)
                seed["validation"] = validation
                denom = max(width * height, 1)
                seed["avg_entropy"] = entropy_sum / denom
                seed["avg_confidence"] = confidence_sum / denom

            self._persist_state()

        return {"status": "ok", "seeds": len(seeds)}

    def _submit_seed_internal(self, seed_index: int, reason: str) -> Dict[str, Any]:
        with self._lock:
            round_state = self.state.get("active_round")
            if not round_state:
                raise ApiError("No active round")
            seed = self.state["seeds"].get(str(seed_index))
            if not seed:
                raise ApiError(f"Unknown seed {seed_index}")
            validation = seed.get("validation") or {}
            if not validation.get("submit_ready", False):
                raise ApiError("Draft validation failed", payload=validation)
            payload = {
                "round_id": round_state["id"],
                "seed_index": seed_index,
                "prediction": seed["draft"],
            }

        resp = self.api.submit(payload)

        with self._lock:
            seed = self.state["seeds"][str(seed_index)]
            seed["submitted"] = True
            seed["submitted_at"] = iso_now()
            seed["submit_status"] = "submitted"
            self._persist_state()

        self.logs.add("info", "submit_ok", "Seed submitted", seed_index=seed_index, reason=reason)
        return {"seed_index": seed_index, "response": resp}

    def submit_seed(self, seed_index: int, reason: str = "manual") -> Dict[str, Any]:
        try:
            return self._submit_seed_internal(seed_index, reason=reason)
        except ApiError as exc:
            with self._lock:
                seed = self.state.get("seeds", {}).get(str(seed_index))
                if seed:
                    seed["submit_status"] = "error"
                self._set_error(f"Submit failed for seed {seed_index}", "Inspect logs and retry submit")
            self.logs.add(
                "error",
                "submit_failed",
                "Seed submission failed",
                seed_index=seed_index,
                status=exc.status_code,
                payload=exc.payload,
            )
            raise

    def submit_all(self, reason: str = "manual") -> Dict[str, Any]:
        with self._lock:
            seed_indices = sorted(int(k) for k in self.state.get("seeds", {}).keys())

        results = []
        failures = []
        for seed_index in seed_indices:
            try:
                result = self.submit_seed(seed_index, reason=reason)
                results.append(result)
            except ApiError as exc:
                failures.append({"seed_index": seed_index, "error": str(exc), "status": exc.status_code})

        return {
            "submitted": len(results),
            "failed": failures,
            "results": results,
        }

    def _deadline_guard_check(self) -> None:
        with self._lock:
            guard_enabled = bool(self.state.get("deadline_guard_enabled"))
            active_round = copy.deepcopy(self.state.get("active_round"))
            seeds = copy.deepcopy(self.state.get("seeds", {}))

        if not guard_enabled or not active_round or not self.api.access_token:
            return

        seconds_left = self._seconds_to_close()
        if seconds_left is None or seconds_left > 20 * 60:
            return

        pending = []
        for seed_key, seed in seeds.items():
            if seed.get("submitted"):
                continue
            if not (seed.get("validation") or {}).get("submit_ready", False):
                continue
            pending.append(int(seed_key))

        for seed_index in pending:
            try:
                self.submit_seed(seed_index, reason="deadline_guard")
            except ApiError:
                # Keep trying on future ticks.
                pass

    def set_run_enabled(self, enabled: bool) -> Dict[str, Any]:
        with self._lock:
            self.state["run_enabled"] = bool(enabled)
            self._persist_state()
        self.logs.add("info", "run_toggle", "Run mode updated", enabled=enabled)
        if enabled:
            self.rebuild_drafts()
        return {"run_enabled": enabled}

    def set_profile(self, profile: str) -> Dict[str, Any]:
        if profile not in {"safe", "aggressive"}:
            raise ValueError("Profile must be 'safe' or 'aggressive'")
        with self._lock:
            self.state["profile"] = profile
            self._persist_state()
        self.logs.add("info", "profile_set", "Profile updated", profile=profile)
        self.rebuild_drafts()
        return {"profile": profile}

    def set_deadline_guard(self, enabled: bool) -> Dict[str, Any]:
        with self._lock:
            self.state["deadline_guard_enabled"] = bool(enabled)
            self._persist_state()
        self.logs.add("info", "guard_set", "Deadline guard updated", enabled=enabled)
        return {"deadline_guard_enabled": enabled}

    def set_access_token(self, token: Optional[str]) -> Dict[str, Any]:
        self.api.set_access_token(token)
        with self._lock:
            self.state["token_present"] = bool(token)
            self._persist_state()
        self.logs.add("info", "token_set", "Access token updated", present=bool(token))
        return {"token_present": bool(token)}

    def _seed_summary(self, seed: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "seed_index": seed["seed_index"],
            "queries_used": seed["queries_used"],
            "coverage_pct": round(float(seed.get("coverage_pct", 0.0)), 2),
            "submitted": bool(seed.get("submitted")),
            "submitted_at": seed.get("submitted_at"),
            "submit_status": seed.get("submit_status", "not_submitted"),
            "validation": seed.get("validation", {}),
            "avg_entropy": round(float(seed.get("avg_entropy", 0.0)), 4),
            "avg_confidence": round(float(seed.get("avg_confidence", 0.0)), 4),
            "last_viewport": seed.get("last_viewport"),
            "last_viewport_counts": seed.get("last_viewport_counts", {}),
            "latest_settlement_count": seed.get("latest_settlement_count", 0),
            "latest_alive_settlement_count": seed.get("latest_alive_settlement_count", 0),
        }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            data = copy.deepcopy(self.state)

        active_round = data.get("active_round")
        submitted = 0
        total = 0
        seed_summaries = []
        for seed in data.get("seeds", {}).values():
            total += 1
            if seed.get("submitted"):
                submitted += 1
            seed_summaries.append(self._seed_summary(seed))

        seconds_left = self._seconds_to_close()
        risk = classify_deadline_risk(seconds_left if seconds_left is not None else 999999, submitted=submitted, total=max(total, 1))

        return {
            "run_enabled": data.get("run_enabled"),
            "profile": data.get("profile"),
            "deadline_guard_enabled": data.get("deadline_guard_enabled"),
            "active_round": active_round,
            "queries": data.get("queries"),
            "submitted_count": submitted,
            "seed_count": total,
            "seconds_to_close": seconds_left,
            "deadline_risk": risk,
            "token_present": data.get("token_present"),
            "last_error": data.get("last_error"),
            "last_error_action": data.get("last_error_action"),
            "seeds": sorted(seed_summaries, key=lambda s: s["seed_index"]),
        }

    def get_seed_detail(self, seed_index: int) -> Dict[str, Any]:
        with self._lock:
            seed = copy.deepcopy(self.state.get("seeds", {}).get(str(seed_index)))
            if not seed:
                raise KeyError(seed_index)
        return {
            "seed_index": seed_index,
            "width": seed["width"],
            "height": seed["height"],
            "initial_grid": seed["initial_grid"],
            "argmax_grid": seed["argmax_grid"],
            "uncertainty_grid": seed["uncertainty_grid"],
            "observed_visits": seed["observed_visits"],
            "last_viewport": seed["last_viewport"],
            "last_viewport_counts": seed["last_viewport_counts"],
            "latest_settlement_count": seed.get("latest_settlement_count", 0),
            "latest_alive_settlement_count": seed.get("latest_alive_settlement_count", 0),
            "class_names": CLASS_NAMES,
        }
