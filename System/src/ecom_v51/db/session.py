from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ecom_v51.config.settings import settings


_ENGINE: Engine | None = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False)


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(settings.database_url, future=True)
        SessionLocal.configure(bind=_ENGINE)
    return _ENGINE


@contextmanager
def get_session() -> Iterator[Session]:
    if SessionLocal.kw.get("bind") is None:
        get_engine()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

"""""
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://ecom_user:strong_password@127.0.0.1:5432/ecom_v51",
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)
"""""