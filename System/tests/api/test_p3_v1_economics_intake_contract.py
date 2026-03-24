from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_economics_intake_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.economics_service,
        'get_batch_economics_intake',
        lambda batch_ref, limit=50, offset=0, view='ready': {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p3.economics_intake.v1',
            'status': 'completed',
            'view': view,
            'sourcePreset': 'economics_v1',
            'columnOrder': [
                'factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode',
                'orderedQty', 'deliveredQty', 'returnedQty', 'cancelledQtyEstimated',
                'orderedAmount', 'deliveredAmountEstimated', 'discountAmount', 'refundAmount',
                'platformFeeAmount', 'fulfillmentFeeAmount', 'netSalesAmount', 'factReady',
                'costCoverageState', 'economicsReady', 'economicsBlockers',
            ],
            'pagination': {'offset': offset, 'limit': limit, 'returned': 1, 'total': 1, 'hasMore': False},
            'aggregateMetrics': {'salesAmountTotal': 287.5, 'orderLineCount': 2},
            'identityDiagnostics': {'unresolvedLineCount': 1},
            'factReadiness': {'factRowCount': 2, 'factReadyRowCount': 1, 'unresolvedFactRowCount': 1, 'factReadyRate': 0.5},
            'intakeSummary': {
                'sourceFactRowCount': 1,
                'factReadyRowCount': 1,
                'economicsReadyRowCount': 0,
                'blockedRowCount': 1,
                'missingCostCardRowCount': 1,
                'economicsReadyRate': 0.0,
                'netSalesAmountTotal': 88.0,
            },
            'dimensionSummary': {'shopIdCount': 1, 'providerCodeCount': 1, 'currencyCodeCount': 1, 'factDateRange': {'min': '2026-03-23', 'max': '2026-03-23'}},
            'issueBuckets': [{'reason': 'missing_cost_card', 'rowCount': 1}],
            'sourceFactContract': {'contractName': 'order_object_fact_read_model', 'recommendedConsumerPreset': 'economics_v1'},
            'exportSpec': {'fileStem': 'batch_12_economics_intake', 'suggestedFileName': 'batch_12_economics_intake_ready.json', 'selectedColumns': ['factDate', 'shopId', 'canonicalSku']},
            'items': [{
                'factDate': '2026-03-23',
                'shopId': 1,
                'skuId': 2,
                'canonicalSku': 'SKU-002',
                'currencyCode': 'RUB',
                'providerCode': 'generic',
                'orderedQty': 1.0,
                'deliveredQty': 1.0,
                'returnedQty': 0.0,
                'cancelledQtyEstimated': 0.0,
                'orderedAmount': 88.0,
                'deliveredAmountEstimated': 88.0,
                'discountAmount': 0.0,
                'refundAmount': 0.0,
                'platformFeeAmount': 0.0,
                'fulfillmentFeeAmount': 0.0,
                'netSalesAmount': 88.0,
                'factReady': True,
                'costCoverageState': 'missing_cost_card',
                'economicsReady': False,
                'economicsBlockers': ['missing_cost_card'],
            }],
        },
    )
    monkeypatch.setattr(
        economics_module.economics_service,
        'get_batch_economics_intake_contract',
        lambda batch_ref: {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p3.economics_intake.v1',
            'status': 'completed',
            'factReadiness': {'factRowCount': 2, 'factReadyRowCount': 1, 'unresolvedFactRowCount': 1, 'factReadyRate': 0.5},
            'sourceFactContract': {'contractName': 'order_object_fact_read_model', 'recommendedConsumerPreset': 'economics_v1'},
            'consumerContract': {
                'contractName': 'economics_intake_skeleton',
                'defaultView': 'ready',
                'sourcePreset': 'economics_v1',
                'availableViews': ['all', 'ready', 'issues'],
                'readinessRules': {'economicsReadyField': 'economicsReady', 'economicsReadyRequires': ['factReady', 'cost_card_attached']},
            },
        },
    )

    intake_resp = client.get('/api/v1/economics/batches/12/intake?view=ready&limit=1&offset=0')
    intake_payload = intake_resp.get_json()
    assert intake_resp.status_code == 200
    assert intake_payload['data']['contractVersion'] == 'p3.economics_intake.v1'
    assert intake_payload['data']['view'] == 'ready'
    assert intake_payload['data']['sourcePreset'] == 'economics_v1'
    assert intake_payload['data']['intakeSummary']['economicsReadyRowCount'] == 0
    assert intake_payload['data']['issueBuckets'][0]['reason'] == 'missing_cost_card'
    assert intake_payload['data']['items'][0]['economicsReady'] is False
    assert intake_payload['data']['items'][0]['economicsBlockers'] == ['missing_cost_card']

    contract_resp = client.get('/api/v1/economics/batches/12/intake/contract')
    contract_payload = contract_resp.get_json()
    assert contract_resp.status_code == 200
    assert contract_payload['data']['consumerContract']['contractName'] == 'economics_intake_skeleton'
    assert contract_payload['data']['consumerContract']['sourcePreset'] == 'economics_v1'
    assert contract_payload['data']['consumerContract']['defaultView'] == 'ready'
    assert contract_payload['data']['consumerContract']['readinessRules']['economicsReadyRequires'][-1] == 'cost_card_attached'



def test_v1_economics_core_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.economics_service,
        'get_batch_economics_core',
        lambda batch_ref, limit=50, offset=0, view='all': {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p3.economics_core.v1',
            'status': 'completed',
            'view': view,
            'sourcePreset': 'economics_v1',
            'columnOrder': [
                'factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode',
                'netSalesAmount', 'platformFeeAmount', 'fulfillmentFeeAmount', 'variableCostAmount',
                'grossProfitAmount', 'grossMarginRate', 'factReady', 'costCoverageState',
                'economicsBlockers', 'coreReady', 'coreCalculationState',
            ],
            'pagination': {'offset': offset, 'limit': limit, 'returned': 1, 'total': 1, 'hasMore': False},
            'aggregateMetrics': {'salesAmountTotal': 287.5, 'orderLineCount': 2},
            'identityDiagnostics': {'unresolvedLineCount': 1},
            'factReadiness': {'factRowCount': 2, 'factReadyRowCount': 1, 'unresolvedFactRowCount': 1, 'factReadyRate': 0.5},
            'coreReadiness': {'coreRowCount': 2, 'coreReadyRowCount': 1, 'blockedCoreRowCount': 1, 'coreReadyRate': 0.5},
            'coreSummary': {
                'rowCount': 1,
                'coreReadyRowCount': 1,
                'blockedRowCount': 0,
                'revenueAmountTotal': 88.0,
                'variableCostAmountTotal': 18.0,
                'grossProfitAmountTotal': 70.0,
                'grossMarginRate': 0.7955,
            },
            'costCoverageSummary': {'missingCostCardRowCount': 1, 'partialCostCoverageRowCount': 1, 'blockedByFactIssuesRowCount': 0},
            'issueBuckets': [{'reason': 'missing_cost_card', 'rowCount': 1}],
            'sourceFactContract': {'contractName': 'order_object_fact_read_model', 'recommendedConsumerPreset': 'economics_v1'},
            'sourceIntakeContract': {'contractName': 'economics_intake_skeleton', 'sourcePreset': 'economics_v1'},
            'exportSpec': {'fileStem': 'batch_12_economics_core', 'suggestedFileName': 'batch_12_economics_core_all.json', 'selectedColumns': ['factDate', 'canonicalSku']},
            'items': [{
                'factDate': '2026-03-24',
                'shopId': 1,
                'skuId': 2,
                'canonicalSku': 'SKU-002',
                'currencyCode': 'RUB',
                'providerCode': 'generic',
                'netSalesAmount': 88.0,
                'platformFeeAmount': 10.0,
                'fulfillmentFeeAmount': 8.0,
                'variableCostAmount': 18.0,
                'grossProfitAmount': 70.0,
                'grossMarginRate': 0.7955,
                'factReady': True,
                'costCoverageState': 'missing_cost_card',
                'economicsBlockers': ['missing_cost_card'],
                'coreReady': True,
                'coreCalculationState': 'calculated_partial_costs',
            }],
        },
    )
    monkeypatch.setattr(
        economics_module.economics_service,
        'get_batch_economics_core_contract',
        lambda batch_ref: {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p3.economics_core.v1',
            'status': 'completed',
            'factReadiness': {'factRowCount': 2, 'factReadyRowCount': 1, 'unresolvedFactRowCount': 1, 'factReadyRate': 0.5},
            'coreReadiness': {'coreRowCount': 2, 'coreReadyRowCount': 1, 'blockedCoreRowCount': 1, 'coreReadyRate': 0.5},
            'sourceFactContract': {'contractName': 'order_object_fact_read_model', 'recommendedConsumerPreset': 'economics_v1'},
            'sourceIntakeContract': {'contractName': 'economics_intake_skeleton', 'sourcePreset': 'economics_v1'},
            'consumerContract': {
                'contractName': 'economics_core_minimal_margin',
                'defaultView': 'all',
                'sourcePreset': 'economics_v1',
                'readinessRules': {'coreReadyField': 'coreReady', 'coreReadyRequires': ['factReady']},
            },
        },
    )

    core_resp = client.get('/api/v1/economics/batches/12/core?view=all&limit=1&offset=0')
    core_payload = core_resp.get_json()
    assert core_resp.status_code == 200
    assert core_payload['data']['contractVersion'] == 'p3.economics_core.v1'
    assert core_payload['data']['coreSummary']['grossProfitAmountTotal'] == 70.0
    assert core_payload['data']['items'][0]['variableCostAmount'] == 18.0
    assert core_payload['data']['items'][0]['coreReady'] is True

    contract_resp = client.get('/api/v1/economics/batches/12/core/contract')
    contract_payload = contract_resp.get_json()
    assert contract_resp.status_code == 200
    assert contract_payload['data']['consumerContract']['contractName'] == 'economics_core_minimal_margin'
    assert contract_payload['data']['consumerContract']['defaultView'] == 'all'
    assert contract_payload['data']['consumerContract']['readinessRules']['coreReadyField'] == 'coreReady'
