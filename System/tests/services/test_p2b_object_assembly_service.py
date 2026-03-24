from __future__ import annotations

from pathlib import Path

from ecom_v51.db.base import Base
from ecom_v51.db.session import get_engine
from ecom_v51.services.batch_runtime_service import BatchRuntimeService
from ecom_v51.services.batch_service import BatchService
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
    from ecom_v51.db import ingest_models, models, object_models  # noqa: F401

    db_path = tmp_path / 'ecom_v51_test.db'
    monkeypatch.setattr(settings, 'database_url', f'sqlite:///{db_path}', raising=False)
    monkeypatch.setattr(settings, 'DATABASE_URL', f'sqlite:///{db_path}', raising=False)
    db_session._ENGINE = None
    db_session.SessionLocal.configure(bind=None)
    Base.metadata.create_all(bind=get_engine())


def test_object_assembly_persists_minimal_order_layer(tmp_path, monkeypatch):
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
        trace_id='trc_test_p2b_round1',
        idempotency_key='idem_test_p2b_round1',
        source_mode='server_file',
    )
    batch_ref = str(upload_info['batchId'])

    confirm_info = runtime.confirm_batch(
        batch_ref=batch_ref,
        operator='pytest',
        gate_mode='manual_continue',
        notes='p2b round1',
        trace_id='trc_test_p2b_round1_confirm',
        idempotency_key='idem_test_p2b_round1_confirm',
        manual_overrides=[],
    )
    assert confirm_info['batchId'] == int(batch_ref)

    object_service = ObjectAssemblyService(
        root_dir,
        batch_service=batch_service,
        import_service=import_service,
        workspace_service=workspace_service,
    )
    summary = object_service.assemble_batch(batch_ref, operator='pytest')

    assert summary['status'] == 'completed'
    assert summary['orderHeaderCount'] == 2
    assert summary['orderLineCount'] == 2
    assert summary['skuCount'] == 2
    assert summary['identityCount'] >= 6
    assert summary['lastAssemblyEvent']['payload']['rowsAssembled'] == 2

    order_lines = summary['items']['orderLines']
    assert order_lines[0]['canonicalSku'] == 'SKU-001'
    assert order_lines[0]['qtyOrdered'] == 2.0
    assert order_lines[0]['salesAmount'] == 199.5


def test_object_assembly_exposes_diagnostics_for_surrogate_identity(tmp_path, monkeypatch):
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
        trace_id='trc_test_p2b_round2',
        idempotency_key='idem_test_p2b_round2',
        source_mode='server_file',
    )
    batch_ref = str(upload_info['batchId'])

    confirm_info = runtime.confirm_batch(
        batch_ref=batch_ref,
        operator='pytest',
        gate_mode='manual_continue',
        notes='p2b round2',
        trace_id='trc_test_p2b_round2_confirm',
        idempotency_key='idem_test_p2b_round2_confirm',
        manual_overrides=[],
    )
    assert confirm_info['batchId'] == int(batch_ref)

    object_service = ObjectAssemblyService(
        root_dir,
        batch_service=batch_service,
        import_service=import_service,
        workspace_service=workspace_service,
    )
    object_service.assemble_batch(batch_ref, operator='pytest')

    from sqlalchemy import select
    from ecom_v51.db.object_models import EntityIdentityMap, OrderLine, SkuIdentityBridge
    from ecom_v51.db.session import get_session

    with get_session() as session:
        line = session.execute(select(OrderLine).order_by(OrderLine.id.asc())).scalars().first()
        line.sku_id = None
        line.canonical_sku = 'batch-1-row-1'
        line.payload = {'providerCode': 'generic'}

        bridge = session.execute(select(SkuIdentityBridge).order_by(SkuIdentityBridge.id.asc())).scalars().first()
        bridge.primary_source_key = 'surrogate'

        identity = session.execute(select(EntityIdentityMap).order_by(EntityIdentityMap.id.asc())).scalars().first()
        identity.canonical_entity_id = 'batch-1-row-1'
        identity.match_confidence = 0.55

    diagnostics = object_service.get_batch_object_diagnostics(batch_ref)

    assert diagnostics is not None
    assert diagnostics['aggregateMetrics']['orderLineCount'] == 2
    assert diagnostics['aggregateMetrics']['salesAmountTotal'] == 287.5
    assert diagnostics['identityDiagnostics']['surrogateIdentityCount'] >= 1
    assert diagnostics['identityDiagnostics']['surrogateBridgeCount'] == 1
    assert diagnostics['identityDiagnostics']['lowConfidenceIdentityCount'] >= 1
    assert diagnostics['identityDiagnostics']['unresolvedLineCount'] == 1
    assert diagnostics['identityDiagnostics']['unresolvedLineSamples'][0]['reason'] == 'surrogate_canonical_sku'
    assert diagnostics['assemblyEventHistory'][0]['eventStatus'] == 'completed'


def test_object_assembly_exposes_batch_detail_readside(tmp_path, monkeypatch):
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
        trace_id='trc_test_p2b_round3',
        idempotency_key='idem_test_p2b_round3',
        source_mode='server_file',
    )
    batch_ref = str(upload_info['batchId'])

    runtime.confirm_batch(
        batch_ref=batch_ref,
        operator='pytest',
        gate_mode='manual_continue',
        notes='p2b round3',
        trace_id='trc_test_p2b_round3_confirm',
        idempotency_key='idem_test_p2b_round3_confirm',
        manual_overrides=[],
    )

    object_service = ObjectAssemblyService(
        root_dir,
        batch_service=batch_service,
        import_service=import_service,
        workspace_service=workspace_service,
    )
    object_service.assemble_batch(batch_ref, operator='pytest')

    details = object_service.get_batch_object_details(batch_ref, section='orderLines', limit=1, offset=0)
    assert details is not None
    assert details['section'] == 'orderLines'
    assert details['pagination']['returned'] == 1
    assert details['pagination']['total'] == 2
    assert details['pagination']['hasMore'] is True
    assert details['items'][0]['canonicalSku'] == 'SKU-001'
    assert details['items'][0]['unresolvedReason'] is None

    identity_details = object_service.get_batch_object_details(batch_ref, section='identities', limit=10, offset=0)
    assert identity_details is not None
    assert identity_details['section'] == 'identities'
    assert identity_details['pagination']['total'] >= 6
    assert identity_details['items'][0]['sourceKeyType'] in {'sku', 'platform_sku', 'seller_sku'}


def test_object_assembly_exposes_batch_rollups(tmp_path, monkeypatch):
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
        trace_id='trc_test_p2b_round4',
        idempotency_key='idem_test_p2b_round4',
        source_mode='server_file',
    )
    batch_ref = str(upload_info['batchId'])

    runtime.confirm_batch(
        batch_ref=batch_ref,
        operator='pytest',
        gate_mode='manual_continue',
        notes='p2b round4',
        trace_id='trc_test_p2b_round4_confirm',
        idempotency_key='idem_test_p2b_round4_confirm',
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
        line.refund_amount = 12.5
        line.discount_amount = 5.0
        line.payload = {'providerCode': 'generic'}

        identity = session.execute(select(EntityIdentityMap).order_by(EntityIdentityMap.id.asc())).scalars().first()
        identity.match_confidence = 0.55

    rollups = object_service.get_batch_object_rollups(batch_ref)

    assert rollups is not None
    assert rollups['aggregateMetrics']['orderLineCount'] == 2
    assert rollups['aggregateMetrics']['salesAmountTotal'] == 287.5
    assert rollups['identityDiagnostics']['unresolvedLineCount'] == 1

    order_status_bucket = rollups['rollups']['orderStatusBuckets'][0]
    assert order_status_bucket['orderStatusNormalized'] == 'reported'
    assert order_status_bucket['orderHeaderCount'] == 2
    assert order_status_bucket['orderLineCount'] == 2

    currency_bucket = rollups['rollups']['currencyBuckets'][0]
    assert currency_bucket['currencyCode'] == 'RUB'
    assert currency_bucket['refundAmountTotal'] == 12.5
    assert currency_bucket['discountAmountTotal'] == 5.0
    assert currency_bucket['netSalesAmountTotal'] == 270.0

    provider_bucket = rollups['rollups']['providerBuckets'][0]
    assert provider_bucket['providerCode'] == 'generic'
    assert provider_bucket['orderLineCount'] == 2
    assert provider_bucket['unresolvedLineCount'] == 1

    unresolved_buckets = {row['reason']: row['lineCount'] for row in rollups['rollups']['unresolvedReasonBuckets']}
    assert unresolved_buckets['surrogate_canonical_sku'] == 1
    assert unresolved_buckets['resolved'] == 1

    confidence_buckets = {row['bucket']: row['identityCount'] for row in rollups['rollups']['identityConfidenceBuckets']}
    assert confidence_buckets['low'] >= 1
    assert confidence_buckets['high'] >= 1

    source_key_buckets = {row['sourceKeyType']: row['identityCount'] for row in rollups['rollups']['sourceKeyTypeBuckets']}
    assert source_key_buckets['sku'] >= 2



def test_object_assembly_exposes_fact_read_model(tmp_path, monkeypatch):
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
        trace_id='trc_test_p2b_round5',
        idempotency_key='idem_test_p2b_round5',
        source_mode='server_file',
    )
    batch_ref = str(upload_info['batchId'])

    runtime.confirm_batch(
        batch_ref=batch_ref,
        operator='pytest',
        gate_mode='manual_continue',
        notes='p2b round5',
        trace_id='trc_test_p2b_round5_confirm',
        idempotency_key='idem_test_p2b_round5_confirm',
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

    facts = object_service.get_batch_object_facts(batch_ref, limit=10, offset=0)

    assert facts is not None
    assert facts['pagination']['total'] == 2
    assert facts['factReadiness']['factRowCount'] == 2
    assert facts['factReadiness']['factReadyRowCount'] == 1
    assert facts['factReadiness']['unresolvedFactRowCount'] == 1
    assert facts['factReadiness']['factReadyRate'] == 0.5

    unresolved = next(row for row in facts['items'] if row['factReady'] is False)
    assert unresolved['unresolvedReason'] == 'surrogate_canonical_sku'
    assert unresolved['identityConfidenceBucket'] == 'low'
    assert unresolved['discountAmount'] == 5.0
    assert unresolved['refundAmount'] == 12.5
    assert unresolved['netSalesAmount'] == 182.0

    resolved = next(row for row in facts['items'] if row['factReady'] is True)
    assert resolved['canonicalSku'] == 'SKU-002'
    assert resolved['orderedQty'] == 1.0
    assert resolved['netSalesAmount'] == 88.0


def test_object_assembly_exposes_fact_consumer_contract(tmp_path, monkeypatch):
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
        trace_id='trc_test_p2b_round6',
        idempotency_key='idem_test_p2b_round6',
        source_mode='server_file',
    )
    batch_ref = str(upload_info['batchId'])

    runtime.confirm_batch(
        batch_ref=batch_ref,
        operator='pytest',
        gate_mode='manual_continue',
        notes='p2b round6',
        trace_id='trc_test_p2b_round6_confirm',
        idempotency_key='idem_test_p2b_round6_confirm',
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

    ready_view = object_service.get_batch_object_facts(batch_ref, limit=10, offset=0, view='ready', preset='economics_v1')
    assert ready_view is not None
    assert ready_view['view'] == 'ready'
    assert ready_view['preset'] == 'economics_v1'
    assert ready_view['pagination']['total'] == 1
    assert ready_view['columnOrder'] == [
        'factDate',
        'shopId',
        'skuId',
        'canonicalSku',
        'currencyCode',
        'providerCode',
        'orderedQty',
        'deliveredQty',
        'returnedQty',
        'cancelledQtyEstimated',
        'orderedAmount',
        'deliveredAmountEstimated',
        'discountAmount',
        'refundAmount',
        'platformFeeAmount',
        'fulfillmentFeeAmount',
        'netSalesAmount',
        'factReady',
    ]
    assert ready_view['items'][0]['canonicalSku'] == 'SKU-002'
    assert 'unresolvedReason' not in ready_view['items'][0]
    assert ready_view['exportSpec']['selectedColumns'][-1] == 'factReady'

    issues_view = object_service.get_batch_object_facts(batch_ref, limit=10, offset=0, view='issues', preset='ops_review_v1')
    assert issues_view is not None
    assert issues_view['view'] == 'issues'
    assert issues_view['preset'] == 'ops_review_v1'
    assert issues_view['pagination']['total'] == 1
    assert issues_view['items'][0]['unresolvedReason'] == 'surrogate_canonical_sku'
    assert issues_view['items'][0]['identityConfidenceBucket'] == 'low'
    assert 'discountAmount' not in issues_view['items'][0]

    contract = object_service.get_batch_object_fact_contract(batch_ref)
    assert contract is not None
    assert contract['consumerContract']['defaultPreset'] == 'debug_full'
    assert contract['consumerContract']['recommendedConsumerPreset'] == 'economics_v1'
    assert contract['consumerContract']['defaultView'] == 'all'
    assert contract['consumerContract']['availableViews'] == ['all', 'ready', 'issues']
    assert contract['consumerContract']['availablePresets'][0]['preset'] == 'economics_v1'
    assert contract['consumerContract']['availablePresets'][2]['preset'] == 'debug_full'
    assert contract['consumerContract']['primaryKeyFields'][-1] == 'unresolvedReason'
