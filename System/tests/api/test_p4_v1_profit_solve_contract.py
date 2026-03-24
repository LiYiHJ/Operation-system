from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_profit_solve_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.economics_service,
        'get_batch_profit_solve',
        lambda batch_ref, limit=50, offset=0, view='all': {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p4.profit_solve.v1',
            'view': view,
            'columnOrder': [
                'canonicalSku', 'resolvedProfileCode', 'solveSourceMode',
                'baseContributionProfit', 'profitAfterAds', 'riskAdjustedProfit', 'profitConfidence',
            ],
            'pagination': {'offset': offset, 'limit': limit, 'returned': 1, 'total': 1, 'hasMore': False},
            'aggregateMetrics': {'orderLineCount': 2},
            'identityDiagnostics': {'resolvedIdentityCount': 1},
            'factReadiness': {'factRowCount': 2, 'factReadyRowCount': 2},
            'coreReadiness': {'coreRowCount': 2, 'coreReadyRowCount': 2},
            'solveReadiness': {'solveRowCount': 2, 'solveReadyRowCount': 2, 'configBoundRowCount': 1, 'fallbackRowCount': 1},
            'solveSummary': {'rowCount': 2, 'configBoundRowCount': 1, 'fallbackRowCount': 1},
            'configResolveSummary': {'defaultProfileCode': 'default_profit_v1', 'configReadyRowCount': 1},
            'sourceConfigContract': {'consumerContract': {'contractName': 'economics_config_resolve'}},
            'sourceCoreContract': {'contractName': 'economics_core_minimal_margin', 'contractVersion': 'p3.economics_core.v1'},
            'items': [{
                'canonicalSku': 'SKU-001',
                'resolvedProfileCode': 'default_profit_v1',
                'solveSourceMode': 'config_resolve',
                'baseContributionProfit': 178.1,
                'profitAfterAds': 171.5,
                'riskAdjustedProfit': 171.5,
                'profitConfidence': 0.75,
            }],
        },
    )
    monkeypatch.setattr(
        economics_module.economics_service,
        'get_batch_profit_solve_contract',
        lambda batch_ref: {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p4.profit_solve.v1',
            'consumerContract': {
                'contractName': 'economics_profit_solve',
                'contractVersion': 'p4.profit_solve.v1',
                'layerFields': ['baseContributionProfit', 'profitAfterAds', 'riskAdjustedProfit'],
            },
            'sourceCoreContract': {'contractName': 'economics_core_minimal_margin', 'contractVersion': 'p3.economics_core.v1'},
            'sourceConfigContract': {'consumerContract': {'contractName': 'economics_config_resolve'}},
        },
    )

    solve_resp = client.get('/api/v1/economics/batches/21/solve?view=all')
    solve_payload = solve_resp.get_json()
    assert solve_resp.status_code == 200
    assert solve_payload['data']['contractVersion'] == 'p4.profit_solve.v1'
    assert solve_payload['data']['items'][0]['solveSourceMode'] == 'config_resolve'
    assert solve_payload['data']['items'][0]['profitAfterAds'] == 171.5

    contract_resp = client.get('/api/v1/economics/batches/21/solve/contract')
    contract_payload = contract_resp.get_json()
    assert contract_resp.status_code == 200
    assert contract_payload['data']['consumerContract']['contractVersion'] == 'p4.profit_solve.v1'
    assert 'riskAdjustedProfit' in contract_payload['data']['consumerContract']['layerFields']
