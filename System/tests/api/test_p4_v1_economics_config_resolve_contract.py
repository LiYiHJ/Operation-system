from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_economics_config_resolve_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.economics_config_service,
        'get_batch_config_resolve',
        lambda batch_ref, limit=50, offset=0, view='all': {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p4.economics_config_resolve.v1',
            'view': view,
            'columnOrder': ['canonicalSku', 'profileCode', 'costCardFound', 'configReady', 'resolvedComponents'],
            'pagination': {'offset': offset, 'limit': limit, 'returned': 1, 'total': 1, 'hasMore': False},
            'factReadiness': {'factRowCount': 2, 'factReadyRowCount': 1},
            'defaultProfile': {'profileCode': 'default_profit_v1'},
            'resolveSummary': {
                'sourceFactRowCount': 1,
                'configReadyRowCount': 1,
                'blockedRowCount': 0,
                'costCardAttachedRowCount': 1,
                'missingCostCardRowCount': 0,
                'defaultProfileCode': 'default_profit_v1',
                'componentCoverage': [
                    {'componentCode': 'platform_fee', 'coveredRowCount': 1, 'missingRowCount': 0, 'required': True, 'sourceModes': ['import_value']},
                    {'componentCode': 'ads_cost', 'coveredRowCount': 1, 'missingRowCount': 0, 'required': False, 'sourceModes': ['manual_override']},
                ],
            },
            'issueBuckets': [],
            'items': [{
                'canonicalSku': 'SKU-001',
                'profileCode': 'default_profit_v1',
                'costCardFound': True,
                'configReady': True,
                'configBlockers': [],
                'resolvedComponents': [
                    {'componentCode': 'platform_fee', 'coverageState': 'covered', 'sourceMode': 'import_value', 'value': 12.5},
                    {'componentCode': 'ads_cost', 'coverageState': 'covered', 'sourceMode': 'manual_override', 'value': 6.6},
                ],
            }],
        },
    )
    monkeypatch.setattr(
        economics_module.economics_config_service,
        'get_batch_config_resolve_contract',
        lambda batch_ref: {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'consumerContract': {
                'contractName': 'economics_config_resolve',
                'contractVersion': 'p4.economics_config_resolve.v1',
                'defaultProfileCode': 'default_profit_v1',
                'componentCodes': ['platform_fee', 'fulfillment_fee', 'ads_cost', 'other_variable_cost'],
            },
        },
    )

    resolve_resp = client.get('/api/v1/economics/batches/12/resolve?view=ready')
    resolve_payload = resolve_resp.get_json()
    assert resolve_resp.status_code == 200
    assert resolve_payload['data']['contractVersion'] == 'p4.economics_config_resolve.v1'
    assert resolve_payload['data']['resolveSummary']['defaultProfileCode'] == 'default_profit_v1'
    assert resolve_payload['data']['items'][0]['resolvedComponents'][1]['componentCode'] == 'ads_cost'

    contract_resp = client.get('/api/v1/economics/batches/12/resolve/contract')
    contract_payload = contract_resp.get_json()
    assert contract_resp.status_code == 200
    assert contract_payload['data']['consumerContract']['contractName'] == 'economics_config_resolve'
    assert 'ads_cost' in contract_payload['data']['consumerContract']['componentCodes']
