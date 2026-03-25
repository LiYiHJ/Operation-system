
from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_profit_snapshot_decision_surface_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.profit_snapshot_review_service,
        'get_batch_profit_snapshot_decision_surface',
        lambda batch_ref, snapshot_id, canonical_sku=None: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'snapshotId': int(snapshot_id),
            'snapshotVersion': 3,
            'savedSource': 'pricing_recommend',
            'canonicalSku': canonical_sku or 'SKU-001',
            'contractVersion': 'p4.9.review_decision_surface.v1',
            'decisionHint': 'ready_for_manual_decision',
            'headline': {
                'recommendedPrice': 119.0,
                'targetMargin': 0.23,
                'currentMargin': 0.18,
                'deltaToTarget': 0.05,
            },
            'readiness': {
                'isReady': True,
                'reviewLevel': 'normal',
                'confidence': 'medium',
                'blockingReasons': [],
                'requiredFields': [],
            },
            'constraints': [],
            'risks': [],
            'metrics': {'recommendedPrice': 119.0, 'netMarginRate': 0.18},
            'timelineSummary': {'available': True, 'currentSnapshotId': int(snapshot_id), 'latestPreviousSnapshotId': 900, 'changeHints': ['recommendedPrice:up']},
            'compareEntry': {'available': True, 'latestPreviousSnapshotId': 900},
        },
    )

    response = client.get('/api/v1/economics/batches/21/profit-snapshots/901/decision?canonicalSku=SKU-001')
    payload = response.get_json()
    assert response.status_code == 200
    assert payload['data']['contractVersion'] == 'p4.9.review_decision_surface.v1'
    assert payload['data']['decisionHint'] == 'ready_for_manual_decision'
    assert payload['data']['timelineSummary']['latestPreviousSnapshotId'] == 900
