from __future__ import annotations

import os


def load_env() -> None:
    """
    Load `.env` into process environment (best-effort).
    Keep this in `models/` so "config comes from models" per project convention.
    """
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    load_dotenv(override=False)


def env(name: str, default: str | None = None) -> str | None:
    load_env()
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    return str(v)

