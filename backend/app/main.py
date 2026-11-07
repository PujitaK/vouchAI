"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .config import allowed_origins
from .db import SessionLocal, init_db
from .models import Agent
from .routers import agents, imports, loans, memory, sim
from .schemas import HealthOut
from .seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        if db.scalar(select(Agent.id).limit(1)) is None:
            seed()
    yield


app = FastAPI(title="VouchAI API", version="1.0.0", lifespan=lifespan)

_origins = allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok")


app.include_router(agents.router)
app.include_router(imports.router)
app.include_router(loans.router)
app.include_router(memory.router)
app.include_router(sim.router)
