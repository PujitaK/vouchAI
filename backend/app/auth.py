"""Admin API key authentication dependency."""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, status


def verify_admin_key(
    x_api_key: str | None = Header(None, alias="X-API-Key")
) -> None:
    """Validate X-API-Key against ADMIN_KEY environment variable.

    If ADMIN_KEY is not configured or empty, requests are permitted.
    If ADMIN_KEY is set and X-API-Key is missing or mismatched, 401 is raised.
    """
    admin_key = os.getenv("ADMIN_KEY", "").strip()
    if not admin_key:
        return

    if not x_api_key or x_api_key.strip() != admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
