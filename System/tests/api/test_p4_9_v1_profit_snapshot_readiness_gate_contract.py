
from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_profit_snapshot_readiness_gate_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.profit_snapshot_review_service,
        'get_batch_profit_snapshot_readiness_gate',
        lambda batch_ref, snapshot_id, canonical_sku=None: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'snapshotId': int(snapshot_id),
            'snapshotVersion': 3,
            'canonicalSku': canonical_sku or 'SKU-001',
            'savedSource': 'pricing_recommend',
            'contractVersion': 'p4.9.review_readiness.v1',
            'isReady': True,
            'reviewLevel': 'normal',
            'confidence': 'medium',
            'blockingReasons': [],
            'requiredFields': [],
            'evidence': {
                'hasExplain': True,
                'hasMetrics': True,
                'hasConstraints': True,
                'hasRisks': True,
                'hasVersioning': True,
                'hasTimeline': True,
            },
        },
    )

    response = client.get('/api/v1/economics/batches/21/profit-snapshots/901/readiness?canonicalSku=SKU-001')
    payload = response.get_json()
    assert response.status_code == 200
    assert payload['data']['contractVersion'] == 'p4.9.review_readiness.v1'
    assert payload['data']['isReady'] is True
    assert payload['data']['evidence']['hasTimeline'] is True
