from __future__ import annotations
from datetime import datetime

from ecom_v51.db import Base, DimPlatform
from ecom_v51.db.session import get_engine, get_session

from sqlalchemy import text

from ecom_v51.db.base import Base
from ecom_v51.db.session import get_engine

# 关键：必须导入 models，才能把所有表注册到 Base.metadata
from ecom_v51.db import models  # noqa: F401

def init_db(seed: bool = True) -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    if not seed:
        return

    with get_session() as session:
        exists = session.query(DimPlatform).filter_by(platform_code="ozon").first()
        if not exists:
            session.add(
                DimPlatform(
                    platform_code="ozon",
                    platform_name="Ozon",
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )

def main() -> None:
    print("Connecting to database...")
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.commit()
    print("Database connection OK.")

    print("Creating tables...")
    Base.metadata.create_all(bind=get_engine())
    print("All tables created successfully.")


if __name__ == "__main__":
    main()