from __future__ import annotations

import argparse
from datetime import datetime

from sqlalchemy import inspect, text

from ecom_v51.db.base import Base
from ecom_v51.db.models import DimPlatform
from ecom_v51.db.session import get_engine, get_session

# 必须导入 models，确保 metadata 注册完整
from ecom_v51.db import models  # noqa: F401
from ecom_v51.db import ingest_models  # noqa: F401
from ecom_v51.services.batch_service import BatchService
from ecom_v51.config.settings import settings


def _seed_platform(platform_code: str, platform_name: str) -> None:
    with get_session() as session:
        row = session.query(DimPlatform).filter(DimPlatform.platform_code == platform_code).one_or_none()
        if row:
            updated = False
            if row.platform_name != platform_name:
                row.platform_name = platform_name
                updated = True
            if not row.is_active:
                row.is_active = True
                updated = True
            if updated:
                print(f"Updated dim_platform: code={platform_code} name={platform_name}")
            else:
                print(f"Exists dim_platform: code={platform_code} id={row.id}")
            return

        row = DimPlatform(
            platform_code=platform_code,
            platform_name=platform_name,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(row)
        session.flush()
        print(f"Inserted dim_platform: code={platform_code} id={row.id}")


def init_db(seed_ozon: bool = True) -> None:
    engine = get_engine()

    print("Connecting to database...")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.commit()
    print("Database connection OK.")

    print("Creating tables from Base.metadata...")
    Base.metadata.create_all(bind=engine)
    print("Table creation done.")

    inspector = inspect(engine)
    table_names = sorted(inspector.get_table_names())
    print(f"Total tables: {len(table_names)}")
    for name in [
        'dim_platform',
        'dim_shop',
        'dim_category',
        'dim_sku',
        'import_batch',
        'ingest_batch',
        'registry_dataset',
        'registry_profile',
        'registry_field',
        'registry_gate_policy',
        'batch_gate_result',
        'batch_audit_event',
        'batch_profile_candidate',
        'batch_business_key_candidate',
        'batch_quarantine_row',
        'mapping_feedback',
        'raw_record',
        'replay_job',
        'job_event',
        'external_data_source_config',
        'sync_run_log',
        'push_delivery_log',
    ]:
        print(f" - {name}: {'OK' if name in table_names else 'MISSING'}")

    batch_service = BatchService(settings.BASE_DIR)
    seeded = batch_service.sync_registry_from_yaml()
    print(f"Registry seed summary: {seeded}")

    if seed_ozon:
        _seed_platform(platform_code='ozon', platform_name='Ozon')


def main() -> None:
    parser = argparse.ArgumentParser(description='Initialize ecom_v51 database schema and seed base dictionaries.')
    parser.add_argument('--no-seed-ozon', action='store_true', help='Do not seed dim_platform with ozon record.')
    args = parser.parse_args()

    init_db(seed_ozon=not args.no_seed_ozon)


if __name__ == '__main__':
    main()
