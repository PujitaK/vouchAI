"""Lightweight in-process cost guard for Groq and Hindsight endpoints."""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import HTTPException, Request, status

from .config import DEFAULT_DAILY_CAP, DEFAULT_RATE_PER_MIN, env_int

_WINDOW_SECONDS = 60.0

_lock = threading.Lock()
_requests_by_ip: dict[str, deque[float]] = defaultdict(deque)
_daily_date = datetime.now(timezone.utc).date()
_daily_count = 0


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _retry_after_seconds(window: deque[float], now: float) -> int:
    if not window:
        return 60
    return max(1, math.ceil(_WINDOW_SECONDS - (now - window[0])))


def enforce_cost_guard(request: Request) -> None:
    """Limit per-client bursts and global daily use of expensive endpoints."""
    rate_limit = env_int("RATE_PER_MIN", DEFAULT_RATE_PER_MIN)
    daily_cap = env_int("DAILY_CAP", DEFAULT_DAILY_CAP)
    if rate_limit <= 0 and daily_cap <= 0:
        return

    now = time.monotonic()
    today = datetime.now(timezone.utc).date()
    ip = _client_ip(request)

    with _lock:
        global _daily_date, _daily_count

        if today != _daily_date:
            _daily_date = today
            _daily_count = 0

        if daily_cap > 0 and _daily_count >= daily_cap:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Daily request cap reached: maximum {daily_cap} requests "
                    "per day. Please try again tomorrow."
                ),
            )

        window: deque[float] | None = None
        if rate_limit > 0:
            window = _requests_by_ip[ip]
            cutoff = now - _WINDOW_SECONDS
            while window and window[0] <= cutoff:
                window.popleft()

            if len(window) >= rate_limit:
                retry_after = _retry_after_seconds(window, now)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Rate limit exceeded: maximum {rate_limit} requests "
                        f"per minute per client. Retry in {retry_after} seconds."
                    ),
                    headers={"Retry-After": str(retry_after)},
                )

        if window is not None:
            window.append(now)
        if daily_cap > 0:
            _daily_count += 1
