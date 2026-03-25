from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_profit_snapshot_explain_includes_consistency_block(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.profit_snapshot_service,
        'get_batch_profit_snapshot_explain',
        lambda batch_ref, snapshot_id, canonical_sku=None: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'snapshotId': int(snapshot_id),
            'snapshotVersion': 2,
            'snapshotKey': f'{batch_ref}::pricing_recommend::default_profit_v1',
            'derivedFromSnapshotId': 900,
            'explainSchemaVersion': 'p4.6.explain.v1',
            'contractVersion': 'p4.profit_snapshot_explain.v1',
            'source': 'pricing_recommend',
            'profileCode': 'default_profit_v1',
            'requestedCanonicalSku': canonical_sku,
            'selectedCanonicalSku': canonical_sku or 'SKU-001',
            'explanationReady': True,
            'recommendationState': 'recommended_hold_current_price',
            'solveSourceMode': 'config_resolve',
            'dominantRiskDriver': '',
            'priceContext': {'currentUnitPrice': 99.75, 'floorPrice': 88.0, 'targetPrice': 99.75, 'ceilingPrice': 108.0, 'recommendedPrice': 99.75},
            'economicsContext': {'netMarginRate': 0.1125, 'riskAdjustedProfit': 7.0, 'profitConfidence': 0.91},
            'explanation': {'summary': 'demo', 'whyNotLower': 'floor', 'whyNotHigher': 'ceiling'},
            'risks': [{'code': 'none', 'message': 'stable'}],
            'consistency': {
                'explainSchemaVersion': 'p4.6.explain.v1',
                'whyNotLower': [{'code': 'floor_price_guard', 'message': 'floor'}],
                'whyNotHigher': [{'code': 'ceiling_price_guard', 'message': 'ceiling'}],
                'constraints': [
                    {'code': 'floor_price_guard', 'active': False, 'value': 88.0},
                    {'code': 'ceiling_price_guard', 'active': False, 'value': 108.0},
                ],
                'risks': [{'code': 'none', 'message': 'stable'}],
                'metrics': {
                    'currentUnitPrice': 99.75,
                    'floorPrice': 88.0,
                    'targetPrice': 99.75,
                    'ceilingPrice': 108.0,
                    'recommendedPrice': 99.75,
                    'netMarginRate': 0.1125,
                    'riskAdjustedProfit': 7.0,
                    'profitConfidence': 0.91,
                },
            },
        },
    )

    explain_resp = client.get('/api/v1/economics/batches/21/profit-snapshots/901/explain?canonicalSku=SKU-001')
    explain_payload = explain_resp.get_json()
    assert explain_resp.status_code == 200
    assert explain_payload['data']['snapshotVersion'] == 2
    assert explain_payload['data']['explainSchemaVersion'] == 'p4.6.explain.v1'
    assert explain_payload['data']['consistency']['whyNotLower'][0]['message'] == 'floor'
    assert explain_payload['data']['consistency']['metrics']['recommendedPrice'] == 99.75
