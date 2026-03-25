from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_profit_snapshot_save_and_list(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.profit_snapshot_service,
        'save_batch_profit_snapshot',
        lambda batch_ref, source='solve', operator='frontend_user', note=None, filters=None: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'contractVersion': 'p4.profit_snapshot.v1',
            'snapshotId': 501,
            'source': source,
            'profileCode': 'default_profit_v1',
            'savedAt': '2026-03-24T00:00:00+00:00',
            'itemCount': 2,
            'summary': {'skuCount': 2, 'avgMargin': 0.1125, 'lossSkuCount': 0, 'currency': 'CNY'},
        },
    )
    monkeypatch.setattr(
        economics_module.profit_snapshot_service,
        'list_batch_profit_snapshots',
        lambda batch_ref, limit=20: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'contractVersion': 'p4.profit_snapshot.v1',
            'pagination': {'limit': limit, 'returned': 1, 'total': 1, 'hasMore': False},
            'items': [{
                'snapshotId': 501,
                'batchRef': str(batch_ref),
                'batchId': int(batch_ref),
                'source': 'solve',
                'profileCode': 'default_profit_v1',
                'savedAt': '2026-03-24T00:00:00+00:00',
                'itemCount': 2,
                'summary': {'skuCount': 2, 'avgMargin': 0.1125, 'lossSkuCount': 0, 'currency': 'CNY'},
            }],
        },
    )

    save_resp = client.post('/api/v1/economics/batches/21/profit-snapshots', json={
        'source': 'pricing_recommend',
        'operator': 'pytest',
        'note': 'round6 snapshot',
        'filters': {'strategyMode': 'balanced_profit', 'constraints': {'minMargin': 0.08}},
    })
    save_payload = save_resp.get_json()
    assert save_resp.status_code == 201
    assert save_payload['data']['contractVersion'] == 'p4.profit_snapshot.v1'
    assert save_payload['data']['source'] == 'pricing_recommend'
    assert save_payload['data']['summary']['skuCount'] == 2

    list_resp = client.get('/api/v1/economics/batches/21/profit-snapshots?limit=10')
    list_payload = list_resp.get_json()
    assert list_resp.status_code == 200
    assert list_payload['data']['contractVersion'] == 'p4.profit_snapshot.v1'
    assert list_payload['data']['items'][0]['snapshotId'] == 501
    assert list_payload['data']['pagination']['returned'] == 1
