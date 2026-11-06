"""Background simulation runner and polling endpoints."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..services import simulator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sim", tags=["sim"])

_lock = threading.Lock()
_thread: threading.Thread | None = None


def _blank_state() -> dict[str, Any]:
    return {
        "state": "idle",
        "round": 0,
        "total": 0,
        "off": [],
        "on": [],
        "beliefs": [],
        "summary": None,
        "error": None,
        "run_id": None,
        "mode": None,
    }


_state: dict[str, Any] = _blank_state()


def _worker(rounds: int, seed: int, fake: bool, run_id: str) -> None:
    def on_event(kind: str, payload: dict[str, Any]) -> None:
        with _lock:
            if kind == "round":
                _state["round"] = payload["round"]
                _state["off"].append(payload["off"])
                _state["on"].append(payload["on"])
            elif kind == "belief":
                _state["beliefs"].append(payload)

    try:
        result = simulator.run_simulation(
            rounds=rounds,
            seed=seed,
            fake=fake,
            run_id=run_id,
            on_event=on_event,
        )
        simulator.save_result(result)
        with _lock:
            _state["state"] = "done"
            _state["round"] = rounds
            _state["summary"] = result["summary"]
    except Exception as exc:
        logger.warning("Simulation run failed (%s)", type(exc).__name__)
        with _lock:
            _state["state"] = "error"
            _state["error"] = f"{type(exc).__name__}: {exc}"


@router.post("/run")
def start_run(
    rounds: int = Query(40, ge=1, le=500),
    seed: int = Query(7),
    fake: bool = Query(False),
) -> dict[str, str]:
    global _thread

    with _lock:
        if _state["state"] == "running":
            raise HTTPException(
                status_code=409, detail="A simulation is already running"
            )

        run_id = uuid.uuid4().hex[:12]
        _state.clear()
        _state.update(_blank_state())
        _state["state"] = "running"
        _state["total"] = rounds
        _state["run_id"] = run_id
        _state["mode"] = "fake" if fake else "real"

        thread = threading.Thread(
            target=_worker,
            args=(rounds, seed, fake, run_id),
            daemon=True,
            name=f"sim-{run_id}",
        )
        _thread = thread

    thread.start()
    return {"run_id": run_id}


@router.get("/status")
def simulation_status() -> dict[str, Any]:
    with _lock:
        return {
            "state": _state["state"],
            "round": _state["round"],
            "total": _state["total"],
            "off": list(_state["off"]),
            "on": list(_state["on"]),
            "beliefs": list(_state["beliefs"]),
            "summary": _state["summary"],
            "error": _state["error"],
            "run_id": _state["run_id"],
            "mode": _state["mode"],
        }


@router.get("/cached")
def cached_run() -> dict[str, Any]:
    path = simulator.DATA_DIR / simulator.CACHED_FILENAME
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "No cached simulation run yet. Run a real simulation "
                "(fake=false) to create data/cached_run.json."
            ),
        )

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Cached simulation file is not valid JSON",
        ) from exc
