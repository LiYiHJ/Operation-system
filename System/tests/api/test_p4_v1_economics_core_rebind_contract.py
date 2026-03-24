from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_economics_core_rebind_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.economics_service,
        'get_batch_economics_core',
        lambda batch_ref, limit=50, offset=0, view='all': {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p4.economics_core_rebind.v1',
            'view': view,
            'columnOrder': ['canonicalSku', 'resolvedProfileCode', 'coreBindingMode', 'resolvedVariableCostAmount', 'variableCostAmount', 'grossProfitAmount'],
            'pagination': {'offset': offset, 'limit': limit, 'returned': 1, 'total': 1, 'hasMore': False},
            'aggregateMetrics': {'orderLineCount': 2},
            'identityDiagnostics': {'resolvedIdentityCount': 1},
            'factReadiness': {'factRowCount': 2, 'factReadyRowCount': 2},
            'coreReadiness': {'coreRowCount': 2, 'coreReadyRowCount': 2, 'configBoundRowCount': 1, 'fallbackRowCount': 1},
            'coreSummary': {'rowCount': 2, 'configBoundRowCount': 1, 'fallbackRowCount': 1},
            'costCoverageSummary': {'configBoundRowCount': 1, 'fallbackImportRowCount': 1},
            'configResolveSummary': {'defaultProfileCode': 'default_profit_v1', 'configReadyRowCount': 1},
            'sourceConfigContract': {'consumerContract': {'contractName': 'economics_config_resolve'}},
            'items': [{
                'canonicalSku': 'SKU-001',
                'resolvedProfileCode': 'default_profit_v1',
                'coreBindingMode': 'config_resolve',
                'resolvedVariableCostAmount': 28.0,
                'variableCostAmount': 28.0,
                'grossProfitAmount': 71.5,
            }],
        },
    )
    monkeypatch.setattr(
        economics_module.economics_service,
        'get_batch_economics_core_contract',
        lambda batch_ref: {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p4.economics_core_rebind.v1',
            'consumerContract': {
                'contractName': 'economics_core_minimal_margin',
                'contractVersion': 'p4.economics_core_rebind.v1',
                'configBindingFields': ['resolvedProfileCode', 'coreBindingMode', 'resolvedVariableCostAmount'],
            },
            'sourceConfigContract': {'consumerContract': {'contractName': 'economics_config_resolve'}},
        },
    )

    core_resp = client.get('/api/v1/economics/batches/18/core?view=all')
    core_payload = core_resp.get_json()
    assert core_resp.status_code == 200
    assert core_payload['data']['contractVersion'] == 'p4.economics_core_rebind.v1'
    assert core_payload['data']['items'][0]['coreBindingMode'] == 'config_resolve'
    assert core_payload['data']['items'][0]['resolvedVariableCostAmount'] == 28.0

    contract_resp = client.get('/api/v1/economics/batches/18/core/contract')
    contract_payload = contract_resp.get_json()
    assert contract_resp.status_code == 200
    assert contract_payload['data']['consumerContract']['contractVersion'] == 'p4.economics_core_rebind.v1'
    assert 'coreBindingMode' in contract_payload['data']['consumerContract']['configBindingFields']
