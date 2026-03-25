from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_profit_snapshot_timeline_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.profit_snapshot_service,
        'get_batch_profit_snapshot_timeline',
        lambda batch_ref, canonical_sku=None, limit=50: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'contractVersion': 'p4.profit_snapshot_timeline.v1',
            'canonicalSku': canonical_sku or 'SKU-001',
            'items': [
                {
                    'snapshotId': 900,
                    'snapshotVersion': 1,
                    'snapshotKey': f'{batch_ref}::pricing_recommend::default_profit_v1',
                    'savedSource': 'pricing_recommend',
                    'derivedFromSnapshotId': None,
                    'savedAt': '2026-03-24T10:00:00+00:00',
                    'profileCode': 'default_profit_v1',
                    'recommendedPrice': 99.75,
                    'avgMargin': 0.1125,
                    'lossSkuCount': 0,
                    'changeHints': [],
                },
                {
                    'snapshotId': 901,
                    'snapshotVersion': 2,
                    'snapshotKey': f'{batch_ref}::pricing_recommend::default_profit_v1',
                    'savedSource': 'pricing_recommend',
                    'derivedFromSnapshotId': 900,
                    'savedAt': '2026-03-24T11:00:00+00:00',
                    'profileCode': 'default_profit_v1',
                    'recommendedPrice': 102.5,
                    'avgMargin': 0.125,
                    'lossSkuCount': 0,
                    'changeHints': ['recommendedPrice:up', 'avgMargin:up'],
                },
            ],
        },
    )

    response = client.get('/api/v1/economics/batches/21/profit-snapshots/timeline?canonicalSku=SKU-001')
    payload = response.get_json()
    assert response.status_code == 200
    assert payload['data']['contractVersion'] == 'p4.profit_snapshot_timeline.v1'
    assert payload['data']['canonicalSku'] == 'SKU-001'
    assert payload['data']['items'][1]['changeHints'] == ['recommendedPrice:up', 'avgMargin:up']
