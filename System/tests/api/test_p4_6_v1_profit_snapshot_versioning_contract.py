from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_profit_snapshot_list_and_detail_include_versioning(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.profit_snapshot_service,
        'list_batch_profit_snapshots',
        lambda batch_ref, limit=20: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'contractVersion': 'p4.profit_snapshot.v1',
            'pagination': {'limit': limit, 'returned': 1, 'total': 1, 'hasMore': False},
            'items': [{
                'snapshotId': 901,
                'snapshotVersion': 2,
                'snapshotKey': f'{batch_ref}::pricing_recommend::default_profit_v1',
                'savedSource': 'pricing_recommend',
                'explainSchemaVersion': 'p4.6.explain.v1',
                'batchRef': str(batch_ref),
                'batchId': int(batch_ref),
                'source': 'pricing_recommend',
                'profileCode': 'default_profit_v1',
                'savedAt': '2026-03-24T00:00:00+00:00',
                'itemCount': 2,
                'summary': {'skuCount': 2, 'avgMargin': 0.1125, 'lossSkuCount': 0, 'currency': 'CNY'},
            }],
        },
    )
    monkeypatch.setattr(
        economics_module.profit_snapshot_service,
        'get_batch_profit_snapshot_detail',
        lambda batch_ref, snapshot_id: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'snapshotId': int(snapshot_id),
            'snapshotVersion': 2,
            'snapshotKey': f'{batch_ref}::pricing_recommend::default_profit_v1',
            'derivedFromSnapshotId': 900,
            'savedSource': 'pricing_recommend',
            'explainSchemaVersion': 'p4.6.explain.v1',
            'contractVersion': 'p4.profit_snapshot_detail.v1',
            'source': 'pricing_recommend',
            'profileCode': 'default_profit_v1',
            'savedAt': '2026-03-24T00:00:00+00:00',
            'operator': 'pytest',
            'note': 'detail',
            'filters': {'strategyMode': 'balanced_profit'},
            'summary': {'skuCount': 2, 'avgMargin': 0.1125, 'lossSkuCount': 0, 'currency': 'CNY', 'itemCount': 2},
            'readiness': {'itemCount': 2, 'recommendationReadyRowCount': 2, 'fallbackRowCount': 0, 'configBoundRowCount': 2},
            'items': [],
        },
    )

    list_resp = client.get('/api/v1/economics/batches/21/profit-snapshots')
    list_payload = list_resp.get_json()
    assert list_resp.status_code == 200
    assert list_payload['data']['items'][0]['snapshotVersion'] == 2
    assert list_payload['data']['items'][0]['snapshotKey'].endswith('default_profit_v1')
    assert list_payload['data']['items'][0]['explainSchemaVersion'] == 'p4.6.explain.v1'

    detail_resp = client.get('/api/v1/economics/batches/21/profit-snapshots/901')
    detail_payload = detail_resp.get_json()
    assert detail_resp.status_code == 200
    assert detail_payload['data']['snapshotVersion'] == 2
    assert detail_payload['data']['derivedFromSnapshotId'] == 900
    assert detail_payload['data']['savedSource'] == 'pricing_recommend'
