from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_pricing_recommend_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.economics_service,
        'get_batch_pricing_recommend',
        lambda batch_ref, strategy_mode='balanced_profit', constraints=None, limit=50, offset=0, view='all': {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p4.pricing_recommend.v1',
            'strategyMode': strategy_mode,
            'constraints': constraints or {'minMargin': 0.08},
            'pagination': {'offset': offset, 'limit': limit, 'returned': 1, 'total': 1, 'hasMore': False},
            'recommendSummary': {'rowCount': 1, 'recommendationReadyRowCount': 1, 'configBoundRowCount': 1, 'fallbackRowCount': 0},
            'items': [{
                'canonicalSku': 'SKU-001',
                'solveSourceMode': 'config_resolve',
                'currentUnitPrice': 99.75,
                'floorPrice': 10.0063,
                'targetPrice': 99.75,
                'ceilingPrice': 99.75,
                'recommendedPrice': 99.75,
                'recommendationState': 'recommended_hold_current_price',
            }],
        },
    )
    monkeypatch.setattr(
        economics_module.economics_service,
        'get_batch_pricing_recommend_contract',
        lambda batch_ref, strategy_mode='balanced_profit': {
            'batchId': int(batch_ref),
            'datasetKind': 'orders',
            'contractVersion': 'p4.pricing_recommend.v1',
            'strategyMode': strategy_mode,
            'consumerContract': {
                'contractName': 'economics_pricing_recommend',
                'contractVersion': 'p4.pricing_recommend.v1',
                'priceLineFields': ['floorPrice', 'targetPrice', 'ceilingPrice', 'recommendedPrice'],
            },
        },
    )

    resp = client.post('/api/v1/economics/pricing/recommend', json={'batchRef': '21', 'strategyMode': 'balanced_profit', 'constraints': {'minMargin': 0.08}})
    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload['data']['contractVersion'] == 'p4.pricing_recommend.v1'
    assert payload['data']['items'][0]['recommendedPrice'] == 99.75

    c_resp = client.get('/api/v1/economics/pricing/recommend/contract?batchRef=21&strategyMode=balanced_profit')
    c_payload = c_resp.get_json()
    assert c_resp.status_code == 200
    assert c_payload['data']['consumerContract']['contractVersion'] == 'p4.pricing_recommend.v1'
    assert 'recommendedPrice' in c_payload['data']['consumerContract']['priceLineFields']
