from __future__ import annotations

from pathlib import Path

from ecom_v51.db.base import Base
from ecom_v51.db.session import get_engine
from ecom_v51.services.batch_runtime_service import BatchRuntimeService
from ecom_v51.services.batch_service import BatchService
from ecom_v51.services.economics_config_service import EconomicsConfigService
from ecom_v51.services.import_batch_workspace import ImportBatchWorkspaceService
from ecom_v51.services.import_service import ImportService
from ecom_v51.services.object_assembly_service import ObjectAssemblyService


CSV_CONTENT = """sku,platform_sku,seller_sku,orders,order_amount\nSKU-001,PLAT-001,SELL-001,2,199.5\nSKU-002,PLAT-002,SELL-002,1,88\n"""


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


def test_economics_config_contract_seeds_defaults(tmp_path, monkeypatch):
    _reset_sqlite(monkeypatch, tmp_path)

    service = EconomicsConfigService(tmp_path)
    contract = service.get_config_contract()

    assert contract['contractVersion'] == 'p4.economics_config.v1'
    assert contract['transitionalCorePolicy']['p3CoreKept'] is True
    assert contract['transitionalCorePolicy']['expandP3CoreFurther'] is False
    assert 'registry_cost_component' in contract['tables']
    assert contract['defaultProfitProfile'] == 'default_profit_v1'

    components = service.list_cost_components(active_only=True)
    assert components['itemCount'] >= 4
    assert any(item['componentCode'] == 'ads_cost' for item in components['items'])

    profiles = service.list_profit_profiles(active_only=True)
    assert profiles['itemCount'] >= 1
    assert profiles['items'][0]['profileCode'] == 'default_profit_v1'


def test_economics_config_service_persists_cost_card_on_object_baseline(tmp_path, monkeypatch):
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
        trace_id='trc_test_p4_round1',
        idempotency_key='idem_test_p4_round1',
        source_mode='server_file',
    )
    batch_ref = str(upload_info['batchId'])

    runtime.confirm_batch(
        batch_ref=batch_ref,
        operator='pytest',
        gate_mode='manual_continue',
        notes='p4 round1',
        trace_id='trc_test_p4_round1_confirm',
        idempotency_key='idem_test_p4_round1_confirm',
        manual_overrides=[],
    )

    object_service = ObjectAssemblyService(
        root_dir,
        batch_service=batch_service,
        import_service=import_service,
        workspace_service=workspace_service,
    )
    object_service.assemble_batch(batch_ref, operator='pytest')

    service = EconomicsConfigService(root_dir)
    card = service.upsert_sku_cost_card(
        {
            'shopId': 1,
            'canonicalSku': 'SKU-001',
            'profileCode': 'default_profit_v1',
            'currencyCode': 'CNY',
            'adsCostAmount': 6.6,
            'otherCostAmount': 1.4,
            'sourceMode': 'manual_override',
            'confidence': 0.9,
            'componentValues': {
                'ads_cost': 6.6,
                'other_variable_cost': 1.4,
            },
            'overrideReason': 'pytest_seed',
        }
    )

    assert card['shopId'] == 1
    assert card['canonicalSku'] == 'SKU-001'
    assert card['adsCostAmount'] == 6.6
    assert card['otherCostAmount'] == 1.4
    assert card['skuId'] is not None

    listed = service.list_sku_cost_cards(shop_id=1, canonical_sku='SKU-001', profile_code='default_profit_v1')
    assert listed['itemCount'] == 1
    assert listed['items'][0]['componentValues']['ads_cost'] == 6.6
    assert listed['items'][0]['sourceMode'] == 'manual_override'
