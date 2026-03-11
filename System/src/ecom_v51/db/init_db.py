from __future__ import annotations

from sqlalchemy import text

from ecom_v51.db.base import Base
from ecom_v51.db.session import get_engine

# 这一句很关键：必须导入 models，SQLAlchemy 才知道有哪些表要注册
from ecom_v51.db import models  # noqa: F401


def main() -> None:
    engine = get_engine()

    print("Connecting to database...")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.commit()
    print("Database connection OK.")

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")


if __name__ == "__main__":
    main()