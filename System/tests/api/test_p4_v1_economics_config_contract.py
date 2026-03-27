from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_economics_config_contract_and_writes(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.economics_config_service,
        'get_config_contract',
        lambda: {
            'contractName': 'economics_config_contract',
            'contractVersion': 'p4.economics_config.v1',
            'status': 'ready',
            'transitionalCorePolicy': {
                'p3CoreKept': True,
                'expandP3CoreFurther': False,
                'targetDirection': 'config_driven_profit_engine',
            },
            'tables': ['registry_cost_component', 'registry_profit_profile', 'sku_cost_card'],
            'defaultCostComponents': ['platform_fee', 'fulfillment_fee', 'ads_cost'],
            'defaultProfitProfile': 'default_profit_v1',
        },
    )
    monkeypatch.setattr(
        economics_module.economics_config_service,
        'list_cost_components',
        lambda active_only=True: {
            'contractVersion': 'p4.economics_config.v1',
            'itemCount': 2,
            'items': [
                {'componentCode': 'platform_fee', 'componentName': '平台费', 'isRequired': True},
                {'componentCode': 'fulfillment_fee', 'componentName': '履约费', 'isRequired': True},
            ],
        },
    )
    monkeypatch.setattr(
        economics_module.economics_config_service,
        'list_profit_profiles',
        lambda active_only=True: {
            'contractVersion': 'p4.economics_config.v1',
            'itemCount': 1,
            'items': [
                {'profileCode': 'default_profit_v1', 'profileName': '默认三层利润口径 V1', 'isDefault': True},
            ],
        },
    )
    monkeypatch.setattr(
        economics_module.economics_config_service,
        'list_sku_cost_cards',
        lambda shop_id=None, canonical_sku=None, profile_code=None, active_only=True: {
            'contractVersion': 'p4.economics_config.v1',
            'itemCount': 1,
            'items': [
                {
                    'shopId': shop_id,
                    'canonicalSku': canonical_sku,
                    'profileCode': profile_code or 'default_profit_v1',
                    'adsCostAmount': 5.5,
                    'otherCostAmount': 1.2,
                }
            ],
        },
    )
    monkeypatch.setattr(
        economics_module.economics_config_service,
        'upsert_sku_cost_card',
        lambda payload: {
            'shopId': int(payload['shopId']),
            'canonicalSku': payload['canonicalSku'],
            'profileCode': payload['profileCode'],
            'adsCostAmount': float(payload['adsCostAmount']),
            'otherCostAmount': float(payload['otherCostAmount']),
            'sourceMode': payload['sourceMode'],
        },
    )

    contract_resp = client.get('/api/v1/economics/config/contract')
    contract_payload = contract_resp.get_json()
    assert contract_resp.status_code == 200
    assert contract_payload['data']['contractVersion'] == 'p4.economics_config.v1'
    assert contract_payload['data']['transitionalCorePolicy']['expandP3CoreFurther'] is False

    components_resp = client.get('/api/v1/economics/config/cost-components')
    components_payload = components_resp.get_json()
    assert components_resp.status_code == 200
    assert components_payload['data']['itemCount'] == 2
    assert components_payload['data']['items'][0]['componentCode'] == 'platform_fee'

    profiles_resp = client.get('/api/v1/economics/config/profit-profiles')
    profiles_payload = profiles_resp.get_json()
    assert profiles_resp.status_code == 200
    assert profiles_payload['data']['items'][0]['profileCode'] == 'default_profit_v1'

    cards_resp = client.get('/api/v1/economics/config/sku-cost-cards?shopId=1&canonicalSku=SKU-001&profileCode=default_profit_v1')
    cards_payload = cards_resp.get_json()
    assert cards_resp.status_code == 200
    assert cards_payload['data']['items'][0]['canonicalSku'] == 'SKU-001'

    write_resp = client.post(
        '/api/v1/economics/config/sku-cost-cards',
        json={
            'shopId': 1,
            'canonicalSku': 'SKU-001',
            'profileCode': 'default_profit_v1',
            'adsCostAmount': 5.5,
            'otherCostAmount': 1.2,
            'sourceMode': 'manual_override',
        },
    )
    write_payload = write_resp.get_json()
    assert write_resp.status_code == 200
    assert write_payload['data']['canonicalSku'] == 'SKU-001'
    assert write_payload['data']['adsCostAmount'] == 5.5
