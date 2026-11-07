"""Environment-backed configuration helpers."""

from __future__ import annotations

import os

DEFAULT_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
DEFAULT_RATE_PER_MIN = 8
DEFAULT_DAILY_CAP = 300


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def public_demo_enabled() -> bool:
    return env_bool("PUBLIC_DEMO", False)


def allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if origins:
        return origins
    return [
        origin.strip()
        for origin in DEFAULT_ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ]


def env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)
