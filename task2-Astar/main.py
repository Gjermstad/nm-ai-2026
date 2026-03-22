from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import ApiError, AstarService

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
RUNTIME_DIR = BASE_DIR / "runtime"

service = AstarService(runtime_dir=str(RUNTIME_DIR), poll_seconds=2.0)


@asynccontextmanager
async def lifespan(_: FastAPI):
    service.start()
    try:
        yield
    finally:
        service.stop()


app = FastAPI(title="Astar Island Operator", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class RunToggleRequest(BaseModel):
    enabled: bool


class ProfileRequest(BaseModel):
    profile: str = Field(pattern="^(safe|aggressive)$")


class SeedSubmitRequest(BaseModel):
    seed_index: int = Field(ge=0, le=99)


class DeadlineGuardRequest(BaseModel):
    enabled: bool


class TokenRequest(BaseModel):
    access_token: Optional[str] = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> Dict[str, Any]:
    status = service.get_status()
    return {
        "status": "ok",
        "run_enabled": status["run_enabled"],
        "active_round": status["active_round"],
        "token_present": status["token_present"],
    }


@app.get("/status")
def get_status() -> Dict[str, Any]:
    return service.get_status()


@app.get("/seed/{seed_index}")
def get_seed(seed_index: int) -> Dict[str, Any]:
    try:
        return service.get_seed_detail(seed_index)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown seed {seed_index}") from exc


@app.post("/run/start")
def run_start() -> Dict[str, Any]:
    return service.set_run_enabled(True)


@app.post("/run/stop")
def run_stop() -> Dict[str, Any]:
    return service.set_run_enabled(False)


@app.post("/run/set")
def run_set(body: RunToggleRequest) -> Dict[str, Any]:
    return service.set_run_enabled(body.enabled)


@app.post("/profile/set")
def set_profile(body: ProfileRequest) -> Dict[str, Any]:
    try:
        return service.set_profile(body.profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/draft/rebuild")
def draft_rebuild() -> Dict[str, Any]:
    return service.rebuild_drafts()


@app.post("/submit/seed")
def submit_seed(body: SeedSubmitRequest) -> Dict[str, Any]:
    try:
        return service.submit_seed(body.seed_index, reason="manual")
    except ApiError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "payload": exc.payload, "status": exc.status_code}) from exc


@app.post("/submit/all")
def submit_all() -> Dict[str, Any]:
    return service.submit_all(reason="manual")


@app.post("/guard/set")
def guard_set(body: DeadlineGuardRequest) -> Dict[str, Any]:
    return service.set_deadline_guard(body.enabled)


@app.get("/model/status")
def model_status() -> Dict[str, Any]:
    return service.get_model_status()


@app.post("/model/reload")
def model_reload() -> Dict[str, Any]:
    return service.reload_model()


@app.post("/auth/token")
def auth_token(body: TokenRequest) -> Dict[str, Any]:
    if os.getenv("ALLOW_TOKEN_UPDATE", "true").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=403, detail="Token update endpoint disabled")
    return service.set_access_token(body.access_token)


@app.get("/logs/recent")
def logs_recent(level: Optional[str] = Query(default=None), limit: int = Query(default=200, ge=1, le=2000)) -> Dict[str, Any]:
    if level and level not in {"debug", "info", "warning", "error"}:
        raise HTTPException(status_code=400, detail="Invalid level")
    return {"items": service.logs.recent(limit=limit, level=level)}
