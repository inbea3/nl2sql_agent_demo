from __future__ import annotations

from models.env import env


def _env_int(name: str, default: int) -> int:
    v = env(name)
    if v is None:
        return default
    try:
        return int(str(v).strip())
    except Exception:
        return default


DB_CONFIG = {
    "host": env("NL2SQL_DB_HOST", "") or "",
    "database": env("NL2SQL_DB_DATABASE", "") or "",
    "user": env("NL2SQL_DB_USER", "") or "",
    "password": env("NL2SQL_DB_PASSWORD", "") or "",
    "port": _env_int("NL2SQL_DB_PORT", 5432),
    "sslmode": env("NL2SQL_DB_SSLMODE", "require") or "require",
}
