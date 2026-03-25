from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import economics as economics_module


def test_v1_profit_snapshot_detail_and_explain(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        economics_module.profit_snapshot_service,
        'get_batch_profit_snapshot_detail',
        lambda batch_ref, snapshot_id: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'snapshotId': int(snapshot_id),
            'contractVersion': 'p4.profit_snapshot_detail.v1',
            'source': 'pricing_recommend',
            'profileCode': 'default_profit_v1',
            'savedAt': '2026-03-24T00:00:00+00:00',
            'operator': 'pytest',
            'note': 'detail',
            'filters': {'strategyMode': 'balanced_profit'},
            'summary': {'skuCount': 2, 'avgMargin': 0.1125, 'lossSkuCount': 0, 'currency': 'CNY', 'itemCount': 2},
            'readiness': {'itemCount': 2, 'recommendationReadyRowCount': 2, 'fallbackRowCount': 0, 'configBoundRowCount': 2},
            'items': [{
                'canonicalSku': 'SKU-001',
                'currentUnitPrice': 99.75,
                'recommendedPrice': 99.75,
                'explanation': {'summary': 'demo', 'whyNotLower': 'floor', 'whyNotHigher': 'ceiling'},
                'risks': [],
            }],
        },
    )
    monkeypatch.setattr(
        economics_module.profit_snapshot_service,
        'get_batch_profit_snapshot_explain',
        lambda batch_ref, snapshot_id, canonical_sku=None: {
            'batchRef': str(batch_ref),
            'batchId': int(batch_ref),
            'snapshotId': int(snapshot_id),
            'contractVersion': 'p4.profit_snapshot_explain.v1',
            'source': 'pricing_recommend',
            'profileCode': 'default_profit_v1',
            'requestedCanonicalSku': canonical_sku,
            'selectedCanonicalSku': canonical_sku or 'SKU-001',
            'explanationReady': True,
            'recommendationState': 'recommended_hold_current_price',
            'solveSourceMode': 'config_resolve',
            'dominantRiskDriver': '',
            'priceContext': {'currentUnitPrice': 99.75, 'floorPrice': 88.0, 'targetPrice': 99.75, 'ceilingPrice': 99.75, 'recommendedPrice': 99.75},
            'economicsContext': {'netMarginRate': 0.1125, 'riskAdjustedProfit': 7.0, 'profitConfidence': 0.91},
            'explanation': {'summary': 'demo', 'whyNotLower': 'floor', 'whyNotHigher': 'ceiling'},
            'risks': [],
        },
    )

    detail_resp = client.get('/api/v1/economics/batches/21/profit-snapshots/501')
    detail_payload = detail_resp.get_json()
    assert detail_resp.status_code == 200
    assert detail_payload['data']['contractVersion'] == 'p4.profit_snapshot_detail.v1'
    assert detail_payload['data']['summary']['skuCount'] == 2
    assert detail_payload['data']['items'][0]['canonicalSku'] == 'SKU-001'

    explain_resp = client.get('/api/v1/economics/batches/21/profit-snapshots/501/explain?canonicalSku=SKU-001')
    explain_payload = explain_resp.get_json()
    assert explain_resp.status_code == 200
    assert explain_payload['data']['contractVersion'] == 'p4.profit_snapshot_explain.v1'
    assert explain_payload['data']['selectedCanonicalSku'] == 'SKU-001'
    assert explain_payload['data']['priceContext']['recommendedPrice'] == 99.75
