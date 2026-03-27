from __future__ import annotations

from pathlib import Path

from ecom_v51.db.base import Base
from ecom_v51.db.session import get_engine
from ecom_v51.services.batch_runtime_service import BatchRuntimeService
from ecom_v51.services.batch_service import BatchService
from ecom_v51.services.economics_intake_service import EconomicsIntakeService
from ecom_v51.services.import_batch_workspace import ImportBatchWorkspaceService
from ecom_v51.services.import_service import ImportService
from ecom_v51.services.object_assembly_service import ObjectAssemblyService


CSV_CONTENT = """sku,platform_sku,seller_sku,orders,order_amount\nSKU-001,PLAT-001,SELL-001,2,199.5\nSKU-002,PLAT-002,SELL-002,1,88\n"""


def _reset_sqlite(monkeypatch, tmp_path: Path) -> None:
    import ecom_v51.db.session as db_session
    from ecom_v51.config.settings import settings
    from ecom_v51.db import ingest_models, models, object_models  # noqa: F401

    db_path = tmp_path / 'ecom_v51_test.db'
    monkeypatch.setattr(settings, 'database_url', f'sqlite:///{db_path}', raising=False)
    monkeypatch.setattr(settings, 'DATABASE_URL', f'sqlite:///{db_path}', raising=False)
    db_session._ENGINE = None
    db_session.SessionLocal.configure(bind=None)
    Base.metadata.create_all(bind=get_engine())


def test_economics_intake_exposes_minimal_summary(tmp_path, monkeypatch):
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
        trace_id='trc_test_p3_round1',
        idempotency_key='idem_test_p3_round1',
        source_mode='server_file',
    )
    batch_ref = str(upload_info['batchId'])

    runtime.confirm_batch(
        batch_ref=batch_ref,
        operator='pytest',
        gate_mode='manual_continue',
        notes='p3 round1',
        trace_id='trc_test_p3_round1_confirm',
        idempotency_key='idem_test_p3_round1_confirm',
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
        line = session.execute(select(OrderLine).order_by(OrderLine.id.asc())).scalars().first()
        line.sku_id = None
        line.canonical_sku = 'batch-1-row-1'
        line.discount_amount = 5.0
        line.refund_amount = 12.5
        line.payload = {'providerCode': 'generic'}

        identity = session.execute(select(EntityIdentityMap).order_by(EntityIdentityMap.id.asc())).scalars().first()
        identity.canonical_entity_id = 'batch-1-row-1'
        identity.match_confidence = 0.55

    service = EconomicsIntakeService(root_dir, object_service=object_service)
    intake = service.get_batch_economics_intake(batch_ref, limit=10, offset=0, view='ready')

    assert intake is not None
    assert intake['contractVersion'] == 'p3.economics_intake.v1'
    assert intake['view'] == 'ready'
    assert intake['sourcePreset'] == 'economics_v1'
    assert intake['pagination']['total'] == 1
    assert intake['intakeSummary']['sourceFactRowCount'] == 1
    assert intake['intakeSummary']['factReadyRowCount'] == 1
    assert intake['intakeSummary']['economicsReadyRowCount'] == 0
    assert intake['intakeSummary']['missingCostCardRowCount'] == 1
    assert intake['intakeSummary']['netSalesAmountTotal'] == 88.0
    assert intake['issueBuckets'][0]['reason'] == 'missing_cost_card'
    assert intake['items'][0]['canonicalSku'] == 'SKU-002'
    assert intake['items'][0]['economicsReady'] is False
    assert intake['items'][0]['economicsBlockers'] == ['missing_cost_card']

    issues = service.get_batch_economics_intake(batch_ref, limit=10, offset=0, view='issues')
    assert issues is not None
    assert issues['pagination']['total'] == 1
    assert issues['items'][0]['canonicalSku'] == 'batch-1-row-1'
    assert issues['items'][0]['economicsBlockers'][0] == 'surrogate_canonical_sku'
    assert 'missing_cost_card' in issues['items'][0]['economicsBlockers']

    contract = service.get_batch_economics_intake_contract(batch_ref)
    assert contract is not None
    assert contract['consumerContract']['contractName'] == 'economics_intake_skeleton'
    assert contract['consumerContract']['sourcePreset'] == 'economics_v1'
    assert contract['consumerContract']['defaultView'] == 'ready'
    assert contract['consumerContract']['readinessRules']['economicsReadyField'] == 'economicsReady'



def test_economics_core_builds_minimal_margin_summary(tmp_path, monkeypatch):
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
        trace_id='trc_test_p3_round2',
        idempotency_key='idem_test_p3_round2',
        source_mode='server_file',
    )
    batch_ref = str(upload_info['batchId'])

    runtime.confirm_batch(
        batch_ref=batch_ref,
        operator='pytest',
        gate_mode='manual_continue',
        notes='p3 round2',
        trace_id='trc_test_p3_round2_confirm',
        idempotency_key='idem_test_p3_round2_confirm',
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
        assert len(lines) >= 2
        first, second = lines[0], lines[1]
        first.platform_fee_amount = 12.5
        first.fulfillment_fee_amount = 7.5
        first.discount_amount = 5.0
        first.refund_amount = 0.0
        first.payload = {'providerCode': 'generic'}

        second.sku_id = None
        second.canonical_sku = 'batch-1-row-2'
        second.platform_fee_amount = 10.0
        second.fulfillment_fee_amount = 8.0
        second.discount_amount = 0.0
        second.refund_amount = 12.5
        second.payload = {'providerCode': 'generic'}

        identities = session.execute(select(EntityIdentityMap).order_by(EntityIdentityMap.id.asc())).scalars().all()
        surrogate_identity = identities[-1]
        surrogate_identity.canonical_entity_id = 'batch-1-row-2'
        surrogate_identity.match_confidence = 0.55

    service = EconomicsIntakeService(root_dir, object_service=object_service)
    core = service.get_batch_economics_core(batch_ref, limit=10, offset=0, view='all')

    assert core is not None
    assert core['contractVersion'] == 'p3.economics_core.v1'
    assert core['pagination']['total'] == 2
    assert core['coreReadiness']['coreReadyRowCount'] == 1
    assert core['costCoverageSummary']['missingCostCardRowCount'] == 2
    assert core['costCoverageSummary']['blockedByFactIssuesRowCount'] == 1
    assert core['coreSummary']['revenueAmountTotal'] == 270.0
    assert core['coreSummary']['variableCostAmountTotal'] == 38.0
    assert core['coreSummary']['grossProfitAmountTotal'] == 232.0

    ready = service.get_batch_economics_core(batch_ref, limit=10, offset=0, view='ready')
    assert ready is not None
    assert ready['pagination']['total'] == 1
    assert ready['items'][0]['canonicalSku'] == 'SKU-001'
    assert ready['items'][0]['variableCostAmount'] == 20.0
    assert ready['items'][0]['grossProfitAmount'] == 174.5
    assert ready['items'][0]['grossMarginRate'] == 0.8972
    assert ready['items'][0]['coreCalculationState'] == 'calculated_partial_costs'

    issues = service.get_batch_economics_core(batch_ref, limit=10, offset=0, view='issues')
    assert issues is not None
    assert issues['pagination']['total'] == 1
    assert issues['items'][0]['canonicalSku'] == 'batch-1-row-2'
    assert issues['items'][0]['coreReady'] is False
    assert issues['items'][0]['coreCalculationState'] == 'blocked_fact_quality'

    contract = service.get_batch_economics_core_contract(batch_ref)
    assert contract is not None
    assert contract['consumerContract']['contractName'] == 'economics_core_minimal_margin'
    assert contract['consumerContract']['readinessRules']['coreReadyField'] == 'coreReady'
