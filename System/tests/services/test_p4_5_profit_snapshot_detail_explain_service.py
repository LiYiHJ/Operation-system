from __future__ import annotations

from ecom_v51.services.batch_runtime_service import BatchRuntimeService
from ecom_v51.services.batch_service import BatchService
from ecom_v51.services.economics_config_service import EconomicsConfigService
from ecom_v51.services.economics_intake_service import EconomicsIntakeService
from ecom_v51.services.import_batch_workspace import ImportBatchWorkspaceService
from ecom_v51.services.import_service import ImportService
from ecom_v51.services.object_assembly_service import ObjectAssemblyService
from ecom_v51.services.profit_snapshot_service import ProfitSnapshotService

CSV_CONTENT = """posting_number,order_id,order_status,created_at,product_name,offer_id,sku,quantity,price,currency,warehouse_name
POST-001,1001,delivered,2026-03-20T10:00:00Z,Demo Product,OFF-001,SKU-001,2,199.5,CNY,Main
POST-002,1002,delivered,2026-03-20T10:05:00Z,Other Product,OFF-002,,1,88.0,CNY,Main
"""


def _reset_sqlite(monkeypatch, tmp_path):
    from ecom_v51.config.settings import settings
    from ecom_v51.db import session as session_module

    db_path = tmp_path / 'economics_profit_snapshot_detail.db'
    db_url = f'sqlite:///{db_path.as_posix()}'

    monkeypatch.setattr(settings, 'DATABASE_URL', db_url, raising=False)
    monkeypatch.setattr(settings, 'database_url', db_url, raising=False)

    engine = getattr(session_module, '_ENGINE', None)
    if engine is not None:
        engine.dispose()
    session_module._ENGINE = None
    session_module.SessionLocal.configure(bind=None)

    from ecom_v51.db.init_db import init_db
    init_db()


def test_profit_snapshot_detail_and_explain_service(tmp_path, monkeypatch):
    _reset_sqlite(monkeypatch, tmp_path)

    source_file = tmp_path / 'orders_report.csv'
    source_file.write_text(CSV_CONTENT, encoding='utf-8')

    root_dir = tmp_path
    import_service = ImportService()
    workspace_service = ImportBatchWorkspaceService(root_dir)
    batch_service = BatchService(root_dir)
    runtime = BatchRuntimeService(root_dir=root_dir, import_service=import_service, workspace_service=workspace_service, batch_service=batch_service)

    upload_info = runtime.run_upload(
        file_path=str(source_file),
        shop_id=1,
        operator='pytest',
        dataset_kind='orders',
        import_profile='ozon_orders_report',
        trace_id='trc_test_p4_5',
        idempotency_key='idem_test_p4_5',
        source_mode='server_file',
    )
    batch_ref = str(upload_info['batchId'])

    runtime.confirm_batch(
        batch_ref=batch_ref,
        operator='pytest',
        gate_mode='manual_continue',
        notes='p4.5',
        trace_id='trc_test_p4_5_confirm',
        idempotency_key='idem_test_p4_5_confirm',
        manual_overrides=[],
    )

    object_service = ObjectAssemblyService(root_dir, batch_service=batch_service, import_service=import_service, workspace_service=workspace_service)
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
    config_service.upsert_sku_cost_card({
        'shopId': 1,
        'canonicalSku': 'SKU-001',
        'profileCode': 'default_profit_v1',
        'currencyCode': 'CNY',
        'adsCostAmount': 6.6,
        'otherCostAmount': 1.4,
        'sourceMode': 'manual_override',
        'confidence': 0.9,
        'componentValues': {'ads_cost': 6.6, 'other_variable_cost': 1.4},
        'overrideReason': 'pytest_seed_p4_5',
    })

    intake_service = EconomicsIntakeService(root_dir, object_service=object_service, config_service=config_service)
    snapshot_service = ProfitSnapshotService(root_dir, economics_service=intake_service)

    saved = snapshot_service.save_batch_profit_snapshot(
        batch_ref,
        source='pricing_recommend',
        operator='pytest',
        note='p4.5 detail explain',
        filters={'strategyMode': 'balanced_profit', 'constraints': {'minMargin': 0.08}},
    )
    assert saved is not None

    detail = snapshot_service.get_batch_profit_snapshot_detail(batch_ref, saved['snapshotId'])
    assert detail is not None
    assert detail['contractVersion'] == 'p4.profit_snapshot_detail.v1'
    assert detail['summary']['itemCount'] == 2
    assert detail['readiness']['configBoundRowCount'] == 1
    assert detail['items'][0]['canonicalSku'] == 'SKU-001'

    explain = snapshot_service.get_batch_profit_snapshot_explain(batch_ref, saved['snapshotId'], canonical_sku='SKU-001')
    assert explain is not None
    assert explain['contractVersion'] == 'p4.profit_snapshot_explain.v1'
    assert explain['selectedCanonicalSku'] == 'SKU-001'
    assert explain['explanationReady'] is True
    assert explain['priceContext']['recommendedPrice'] == 99.75
    assert 'whyNotLower' in explain['explanation']
