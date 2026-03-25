from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_profit_snapshot_review_surface_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.profit_snapshot_service,
        'get_batch_profit_snapshot_review_surface',
        lambda batch_ref, snapshot_id, canonical_sku=None: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'snapshotId': int(snapshot_id),
            'snapshotVersion': 2,
            'snapshotKey': f'{batch_ref}::pricing_recommend::default_profit_v1',
            'canonicalSku': canonical_sku or 'SKU-001',
            'contractVersion': 'p4.profit_snapshot_review_surface.v1',
            'savedSource': 'pricing_recommend',
            'pricing': {
                'floorPrice': 95.0,
                'targetPrice': 101.0,
                'ceilingPrice': 105.0,
                'recommendedPrice': 102.5,
            },
            'profit': {
                'grossMargin': 0.22,
                'contributionMargin': 0.17,
                'netMargin': 0.125,
            },
            'explanation': {
                'whyNotLower': [{'code': 'margin_guard', 'message': 'margin floor'}],
                'whyNotHigher': [{'code': 'competition_guard', 'message': 'competition pressure'}],
                'constraints': [{'code': 'floor_price_guard', 'active': False, 'value': 95.0}],
                'risks': [{'code': 'competition', 'message': 'competition pressure'}],
                'metrics': {'recommendedPrice': 102.5, 'netMarginRate': 0.125},
            },
            'reviewSurface': {
                'summary': 'raise recommended price with guardrails',
                'decisionHints': ['candidate_raise', 'competition'],
                'riskFlags': ['competition'],
                'source': 'pricing_recommend',
            },
        },
    )

    response = client.get('/api/v1/economics/batches/21/profit-snapshots/901/review?canonicalSku=SKU-001')
    payload = response.get_json()
    assert response.status_code == 200
    assert payload['data']['contractVersion'] == 'p4.profit_snapshot_review_surface.v1'
    assert payload['data']['pricing']['recommendedPrice'] == 102.5
    assert payload['data']['reviewSurface']['riskFlags'] == ['competition']
