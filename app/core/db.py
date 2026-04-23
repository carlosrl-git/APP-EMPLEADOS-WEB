from typing import Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

def fetch_all(query: str, params: dict[str, Any] | None = None) -> list[dict]:
    params = params or {}
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

def fetch_one(query: str, params: dict[str, Any] | None = None) -> dict | None:
    params = params or {}
    with engine.connect() as conn:
        result = conn.execute(text(query), params).mappings().first()
        return dict(result) if result else None

def execute(query: str, params: dict[str, Any] | None = None) -> None:
    params = params or {}
    with engine.begin() as conn:
        conn.execute(text(query), params)

def execute_returning_id(query: str, params: dict[str, Any] | None = None) -> int | None:
    params = params or {}
    with engine.begin() as conn:
        result = conn.execute(text(query), params)

        try:
            row = result.first()
            if row:
                return int(row[0])
        except Exception:
            pass

        try:
            lastrowid = result.lastrowid
            if lastrowid:
                return int(lastrowid)
        except Exception:
            pass

        return None