from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import objects as objects_module


def test_v1_object_assembly_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        objects_module.object_service,
        'assemble_batch',
        lambda batch_ref, operator='frontend_user': {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p2b.v1',
            'status': 'completed',
            'orderHeaderCount': 2,
            'orderLineCount': 2,
            'skuCount': 2,
            'identityCount': 6,
        },
    )
    monkeypatch.setattr(
        objects_module.object_service,
        'get_batch_object_summary',
        lambda batch_ref: {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p2b.v1',
            'status': 'completed',
            'orderHeaderCount': 2,
            'orderLineCount': 2,
            'skuCount': 2,
            'identityCount': 6,
            'aggregateMetrics': {'salesAmountTotal': 287.5},
        },
    )

    assemble_resp = client.post('/api/v1/objects/assemble', json={'batchRef': '12', 'operator': 'pytest'})
    assemble_payload = assemble_resp.get_json()
    assert assemble_resp.status_code == 202
    assert assemble_payload['data']['batchId'] == 12
    assert assemble_payload['data']['contractVersion'] == 'p2b.v1'

    monkeypatch.setattr(
        objects_module.object_service,
        'get_batch_object_diagnostics',
        lambda batch_ref: {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p2b.v1',
            'status': 'completed',
            'aggregateMetrics': {'salesAmountTotal': 287.5},
            'identityDiagnostics': {
                'surrogateIdentityCount': 1,
                'unresolvedLineCount': 1,
            },
            'assemblyEventHistory': [{'eventStatus': 'completed'}],
        },
    )
    monkeypatch.setattr(
        objects_module.object_service,
        'get_batch_object_details',
        lambda batch_ref, section='orderLines', limit=50, offset=0: {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p2b.v1',
            'status': 'completed',
            'section': section,
            'pagination': {'offset': offset, 'limit': limit, 'returned': 1, 'total': 2, 'hasMore': True},
            'aggregateMetrics': {'salesAmountTotal': 287.5},
            'identityDiagnostics': {'unresolvedLineCount': 1},
            'items': [{'orderLineId': 101, 'canonicalSku': 'SKU-001', 'unresolvedReason': None}],
        },
    )
    monkeypatch.setattr(
        objects_module.object_service,
        'get_batch_object_rollups',
        lambda batch_ref: {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p2b.v1',
            'status': 'completed',
            'aggregateMetrics': {'salesAmountTotal': 287.5, 'orderLineCount': 2},
            'identityDiagnostics': {'unresolvedLineCount': 1},
            'rollups': {
                'orderStatusBuckets': [{'orderStatusNormalized': 'reported', 'orderHeaderCount': 2, 'orderLineCount': 2}],
                'currencyBuckets': [{'currencyCode': 'CNY', 'orderLineCount': 2, 'netSalesAmountTotal': 287.5}],
                'providerBuckets': [{'providerCode': 'generic', 'identityCount': 6, 'unresolvedLineCount': 1}],
                'unresolvedReasonBuckets': [{'reason': 'resolved', 'lineCount': 1}, {'reason': 'surrogate_canonical_sku', 'lineCount': 1}],
                'identityConfidenceBuckets': [{'bucket': 'high', 'identityCount': 5}, {'bucket': 'low', 'identityCount': 1}],
                'sourceKeyTypeBuckets': [{'sourceKeyType': 'sku', 'identityCount': 2}],
            },
        },
    )
    summary_resp = client.get('/api/v1/objects/batches/12/summary')
    summary_payload = summary_resp.get_json()
    assert summary_resp.status_code == 200
    assert summary_payload['data']['status'] == 'completed'
    assert summary_payload['data']['orderLineCount'] == 2
    assert summary_payload['data']['aggregateMetrics']['salesAmountTotal'] == 287.5

    diagnostics_resp = client.get('/api/v1/objects/batches/12/diagnostics')
    diagnostics_payload = diagnostics_resp.get_json()
    assert diagnostics_resp.status_code == 200
    assert diagnostics_payload['data']['identityDiagnostics']['surrogateIdentityCount'] == 1
    assert diagnostics_payload['data']['identityDiagnostics']['unresolvedLineCount'] == 1

    details_resp = client.get('/api/v1/objects/batches/12/details?section=orderLines&limit=1&offset=0')
    details_payload = details_resp.get_json()
    assert details_resp.status_code == 200
    assert details_payload['data']['section'] == 'orderLines'
    assert details_payload['data']['pagination']['returned'] == 1
    assert details_payload['data']['pagination']['hasMore'] is True
    assert details_payload['data']['items'][0]['orderLineId'] == 101

    rollups_resp = client.get('/api/v1/objects/batches/12/rollups')
    rollups_payload = rollups_resp.get_json()
    assert rollups_resp.status_code == 200
    assert rollups_payload['data']['aggregateMetrics']['orderLineCount'] == 2
    assert rollups_payload['data']['rollups']['currencyBuckets'][0]['currencyCode'] == 'CNY'
    assert rollups_payload['data']['rollups']['unresolvedReasonBuckets'][1]['reason'] == 'surrogate_canonical_sku'



def test_v1_object_facts_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        objects_module.object_service,
        'get_batch_object_facts',
        lambda batch_ref, limit=50, offset=0, view='all', preset='economics_v1': {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p2b.v1',
            'status': 'completed',
            'view': view,
            'preset': preset,
            'columnOrder': ['factDate', 'shopId', 'canonicalSku', 'netSalesAmount', 'factReady'],
            'pagination': {'offset': offset, 'limit': limit, 'returned': 1, 'total': 1, 'hasMore': False},
            'aggregateMetrics': {'salesAmountTotal': 287.5, 'orderLineCount': 2},
            'identityDiagnostics': {'unresolvedLineCount': 1},
            'factReadiness': {'factRowCount': 2, 'factReadyRowCount': 1, 'unresolvedFactRowCount': 1, 'factReadyRate': 0.5},
            'exportSpec': {'fileStem': 'batch_12_object_facts', 'suggestedFileName': 'batch_12_object_facts_economics_v1_ready.json', 'selectedColumns': ['factDate', 'shopId', 'canonicalSku', 'netSalesAmount', 'factReady']},
            'items': [{
                'factDate': '2026-03-23',
                'shopId': 1,
                'canonicalSku': 'SKU-001',
                'netSalesAmount': 199.5,
                'factReady': True,
            }],
        },
    )
    monkeypatch.setattr(
        objects_module.object_service,
        'get_batch_object_fact_contract',
        lambda batch_ref: {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p2b.v1',
            'status': 'completed',
            'factReadiness': {'factRowCount': 2, 'factReadyRowCount': 1, 'unresolvedFactRowCount': 1, 'factReadyRate': 0.5},
            'consumerContract': {
                'contractName': 'order_object_fact_read_model',
                'defaultPreset': 'debug_full',
                'recommendedConsumerPreset': 'economics_v1',
                'defaultView': 'all',
                'availableViews': ['all', 'ready', 'issues'],
                'availablePresets': [
                    {'preset': 'economics_v1', 'fields': ['factDate', 'shopId', 'canonicalSku', 'netSalesAmount', 'factReady']},
                    {'preset': 'ops_review_v1', 'fields': ['factDate', 'canonicalSku', 'unresolvedReason', 'identityConfidenceBucket']},
                    {'preset': 'debug_full', 'fields': None},
                ],
                'primaryKeyFields': ['factDate', 'shopId', 'canonicalSku', 'currencyCode', 'providerCode', 'unresolvedReason'],
            },
        },
    )

    facts_resp = client.get('/api/v1/objects/batches/12/facts?limit=1&offset=0&view=ready&preset=economics_v1')
    facts_payload = facts_resp.get_json()
    assert facts_resp.status_code == 200
    assert facts_payload['data']['view'] == 'ready'
    assert facts_payload['data']['preset'] == 'economics_v1'
    assert facts_payload['data']['columnOrder'] == ['factDate', 'shopId', 'canonicalSku', 'netSalesAmount', 'factReady']
    assert facts_payload['data']['pagination']['returned'] == 1
    assert facts_payload['data']['factReadiness']['factReadyRate'] == 0.5
    assert facts_payload['data']['exportSpec']['suggestedFileName'].endswith('_economics_v1_ready.json')
    assert facts_payload['data']['items'][0]['canonicalSku'] == 'SKU-001'
    assert 'unresolvedReason' not in facts_payload['data']['items'][0]

    contract_resp = client.get('/api/v1/objects/batches/12/facts/contract')
    contract_payload = contract_resp.get_json()
    assert contract_resp.status_code == 200
    assert contract_payload['data']['consumerContract']['defaultPreset'] == 'debug_full'
    assert contract_payload['data']['consumerContract']['recommendedConsumerPreset'] == 'economics_v1'
    assert contract_payload['data']['consumerContract']['availableViews'] == ['all', 'ready', 'issues']
    assert contract_payload['data']['consumerContract']['availablePresets'][1]['preset'] == 'ops_review_v1'
