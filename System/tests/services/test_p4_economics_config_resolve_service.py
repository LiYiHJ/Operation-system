from __future__ import annotations

from pathlib import Path

from ecom_v51.db.base import Base
from ecom_v51.db.session import get_engine
from ecom_v51.services.batch_runtime_service import BatchRuntimeService
from ecom_v51.services.batch_service import BatchService
from ecom_v51.services.economics_config_service import EconomicsConfigService
from ecom_v51.services.economics_intake_service import EconomicsIntakeService
from ecom_v51.services.import_batch_workspace import ImportBatchWorkspaceService
from ecom_v51.services.import_service import ImportService
from ecom_v51.services.object_assembly_service import ObjectAssemblyService


CSV_CONTENT = """sku,platform_sku,seller_sku,orders,order_amount
SKU-001,PLAT-001,SELL-001,2,199.5
SKU-002,PLAT-002,SELL-002,1,88
"""


def _reset_sqlite(monkeypatch, tmp_path: Path) -> None:
    import ecom_v51.db.session as db_session
    from ecom_v51.config.settings import settings
    from ecom_v51.db import economics_models, ingest_models, models, object_models  # noqa: F401

    db_path = tmp_path / 'ecom_v51_test.db'
    monkeypatch.setattr(settings, 'database_url', f'sqlite:///{db_path}', raising=False)
    monkeypatch.setattr(settings, 'DATABASE_URL', f'sqlite:///{db_path}', raising=False)
    db_session._ENGINE = None
    db_session.SessionLocal.configure(bind=None)
    Base.metadata.create_all(bind=get_engine())


def test_economics_config_resolve_reads_cost_cards_and_backfills_intake_core(tmp_path, monkeypatch):
    _reset_sqlite(monkeypatch, tmp_path)

    source_file = tmp_path / 'orders_report.csv'
    source_file.write_text(CSV_CONTENT, encoding='utf-8')

    root_dir = tmp_path
    import_service = ImportService()
    workspace_service = ImportBatchWorkspaceService(root_dir)
    batch_service = BatchService(root_dir)
    runtime = BatchRuntimeService(
        root_dir=root_dir,
        import_service=import_service,
        workspace_service=workspace_service,
        batch_service=batch_service,
    )

    upload_info = runtime.run_upload(
        file_path=str(source_file),
        shop_id=1,
        operator='pytest',
        dataset_kind='orders',
        import_profile='ozon_orders_report',
        trace_id='trc_test_p4_round2',
        idempotency_key='idem_test_p4_round2',
        source_mode='server_file',
    )
    batch_ref = str(upload_info['batchId'])

    runtime.confirm_batch(
        batch_ref=batch_ref,
        operator='pytest',
        gate_mode='manual_continue',
        notes='p4 round2',
        trace_id='trc_test_p4_round2_confirm',
        idempotency_key='idem_test_p4_round2_confirm',
        manual_overrides=[],
    )

    object_service = ObjectAssemblyService(
        root_dir,
        batch_service=batch_service,
        import_service=import_service,
        workspace_service=workspace_service,
    )
    object_service.assemble_batch(batch_ref, operator='pytest')

    from sqlalchemy import select
    from ecom_v51.db.object_models import EntityIdentityMap, OrderLine
    from ecom_v51.db.session import get_session

    with get_session() as session:
        lines = session.execute(select(OrderLine).order_by(OrderLine.id.asc())).scalars().all()
        first, second = lines[0], lines[1]
        first.platform_fee_amount = 12.5
        first.fulfillment_fee_amount = 7.5
        first.payload = {'providerCode': 'generic'}

        second.sku_id = None
        second.canonical_sku = 'batch-1-row-2'
        second.platform_fee_amount = 10.0
        second.fulfillment_fee_amount = 8.0
        second.payload = {'providerCode': 'generic'}

        identities = session.execute(select(EntityIdentityMap).order_by(EntityIdentityMap.id.asc())).scalars().all()
        surrogate_identity = identities[-1]
        surrogate_identity.canonical_entity_id = 'batch-1-row-2'
        surrogate_identity.match_confidence = 0.55

    config_service = EconomicsConfigService(root_dir)
    config_service.upsert_sku_cost_card(
        {
            'shopId': 1,
            'canonicalSku': 'SKU-001',
            'profileCode': 'default_profit_v1',
            'currencyCode': 'CNY',
            'adsCostAmount': 6.6,
            'otherCostAmount': 1.4,
            'sourceMode': 'manual_override',
            'confidence': 0.9,
            'componentValues': {'ads_cost': 6.6, 'other_variable_cost': 1.4},
            'overrideReason': 'pytest_seed_round2',
        }
    )

    resolved = config_service.get_batch_config_resolve(batch_ref, limit=10, offset=0, view='all')
    assert resolved is not None
    assert resolved['contractVersion'] == 'p4.economics_config_resolve.v1'
    assert resolved['resolveSummary']['sourceFactRowCount'] == 2
    assert resolved['resolveSummary']['configReadyRowCount'] == 1
    assert resolved['resolveSummary']['missingCostCardRowCount'] == 1
    assert resolved['resolveSummary']['defaultProfileCode'] == 'default_profit_v1'
    assert resolved['items'][0]['canonicalSku'] == 'SKU-001'
    assert resolved['items'][0]['costCardFound'] is True
    assert resolved['items'][0]['configReady'] is True
    assert resolved['items'][0]['resolvedComponentMap']['ads_cost']['value'] == 6.6

    issues = config_service.get_batch_config_resolve(batch_ref, limit=10, offset=0, view='issues')
    assert issues is not None
    assert issues['pagination']['total'] == 1
    assert issues['items'][0]['canonicalSku'] == 'batch-1-row-2'
    assert 'missing_cost_card' in issues['items'][0]['configBlockers']

    intake_service = EconomicsIntakeService(root_dir, object_service=object_service, config_service=config_service)
    intake = intake_service.get_batch_economics_intake(batch_ref, limit=10, offset=0, view='all')
    assert intake is not None
    assert intake['configResolveSummary']['defaultProfileCode'] == 'default_profit_v1'
    assert intake['configResolveSummary']['configReadyRowCount'] == 1
    assert intake['sourceConfigContract']['consumerContract']['contractName'] == 'economics_config_resolve'

    core = intake_service.get_batch_economics_core(batch_ref, limit=10, offset=0, view='all')
    assert core is not None
    assert core['configResolveSummary']['missingCostCardRowCount'] == 1
    assert core['sourceConfigContract']['consumerContract']['contractVersion'] == 'p4.economics_config_resolve.v1'
