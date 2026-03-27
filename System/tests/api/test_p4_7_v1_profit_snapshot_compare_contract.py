from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_profit_snapshot_compare_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.profit_snapshot_service,
        'get_batch_profit_snapshot_compare',
        lambda batch_ref, left_snapshot_id, right_snapshot_id, canonical_sku=None: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'contractVersion': 'p4.profit_snapshot_compare.v1',
            'requestedCanonicalSku': canonical_sku,
            'selectedCanonicalSku': canonical_sku or 'SKU-001',
            'leftSnapshot': {
                'snapshotId': int(left_snapshot_id),
                'snapshotVersion': 1,
                'snapshotKey': f'{batch_ref}::pricing_recommend::default_profit_v1',
                'savedSource': 'pricing_recommend',
                'source': 'pricing_recommend',
                'profileCode': 'default_profit_v1',
                'savedAt': '2026-03-24T10:00:00+00:00',
            },
            'rightSnapshot': {
                'snapshotId': int(right_snapshot_id),
                'snapshotVersion': 2,
                'snapshotKey': f'{batch_ref}::pricing_recommend::default_profit_v1',
                'savedSource': 'pricing_recommend',
                'source': 'pricing_recommend',
                'profileCode': 'default_profit_v1',
                'savedAt': '2026-03-24T11:00:00+00:00',
            },
            'summaryComparison': {
                'left': {'skuCount': 2, 'avgMargin': 0.1125, 'lossSkuCount': 0, 'currency': 'CNY', 'itemCount': 2},
                'right': {'skuCount': 2, 'avgMargin': 0.125, 'lossSkuCount': 0, 'currency': 'CNY', 'itemCount': 2},
                'delta': {'skuCount': 0, 'avgMargin': 0.0125, 'lossSkuCount': 0, 'itemCount': 0},
            },
            'selection': {
                'leftPresent': True,
                'rightPresent': True,
                'sharedCanonicalSkuCount': 2,
                'skuAdded': [],
                'skuRemoved': [],
                'skuUnionCount': 2,
            },
            'selectedItemComparison': {
                'left': {'recommendedPrice': 99.75, 'riskAdjustedProfit': 7.0},
                'right': {'recommendedPrice': 102.5, 'riskAdjustedProfit': 8.4},
                'delta': {'recommendedPrice': 2.75, 'riskAdjustedProfit': 1.4},
            },
            'changedFields': ['summary.avgMargin', 'selectedItem.recommendedPrice'],
        },
    )

    response = client.get('/api/v1/economics/batches/21/profit-snapshots/compare?leftSnapshotId=900&rightSnapshotId=901&canonicalSku=SKU-001')
    payload = response.get_json()
    assert response.status_code == 200
    assert payload['data']['contractVersion'] == 'p4.profit_snapshot_compare.v1'
    assert payload['data']['selectedCanonicalSku'] == 'SKU-001'
    assert payload['data']['summaryComparison']['delta']['avgMargin'] == 0.0125
    assert payload['data']['selectedItemComparison']['delta']['recommendedPrice'] == 2.75
