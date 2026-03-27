from __future__ import annotations

from pathlib import Path

from ecom_v51.services.profit_snapshot_service import ProfitSnapshotService


def test_profit_snapshot_timeline_and_review_surface_service(monkeypatch):
    service = ProfitSnapshotService(Path('.'))

    listing = {
        'batchRef': '21',
        'batchId': 21,
        'contractVersion': 'p4.profit_snapshot.v1',
        'pagination': {'limit': 20, 'returned': 2, 'total': 2, 'hasMore': False},
        'items': [
            {
                'snapshotId': 901,
                'snapshotVersion': 2,
                'snapshotKey': '21::pricing_recommend::default_profit_v1',
                'savedSource': 'pricing_recommend',
                'explainSchemaVersion': 'p4.6.explain.v1',
                'batchRef': '21',
                'batchId': 21,
                'source': 'pricing_recommend',
                'profileCode': 'default_profit_v1',
                'savedAt': '2026-03-24T11:00:00+00:00',
                'itemCount': 2,
                'summary': {'skuCount': 2, 'avgMargin': 0.125, 'lossSkuCount': 0, 'currency': 'CNY'},
            },
            {
                'snapshotId': 900,
                'snapshotVersion': 1,
                'snapshotKey': '21::pricing_recommend::default_profit_v1',
                'savedSource': 'pricing_recommend',
                'explainSchemaVersion': 'p4.6.explain.v1',
                'batchRef': '21',
                'batchId': 21,
                'source': 'pricing_recommend',
                'profileCode': 'default_profit_v1',
                'savedAt': '2026-03-24T10:00:00+00:00',
                'itemCount': 2,
                'summary': {'skuCount': 2, 'avgMargin': 0.1125, 'lossSkuCount': 0, 'currency': 'CNY'},
            },
        ],
    }
    details = {
        900: {
            'batchRef': '21', 'batchId': 21, 'snapshotId': 900, 'snapshotVersion': 1,
            'snapshotKey': '21::pricing_recommend::default_profit_v1', 'savedSource': 'pricing_recommend',
            'source': 'pricing_recommend', 'profileCode': 'default_profit_v1', 'savedAt': '2026-03-24T10:00:00+00:00',
            'summary': {'skuCount': 2, 'avgMargin': 0.1125, 'lossSkuCount': 0, 'currency': 'CNY', 'itemCount': 2},
            'items': [
                {'canonicalSku': 'SKU-001', 'recommendedPrice': 99.75, 'floorPrice': 95.0, 'targetPrice': 100.0, 'ceilingPrice': 105.0, 'grossMarginRate': 0.2, 'contributionMarginRate': 0.15, 'netMarginRate': 0.1125},
            ],
        },
        901: {
            'batchRef': '21', 'batchId': 21, 'snapshotId': 901, 'snapshotVersion': 2,
            'snapshotKey': '21::pricing_recommend::default_profit_v1', 'savedSource': 'pricing_recommend',
            'derivedFromSnapshotId': 900,
            'source': 'pricing_recommend', 'profileCode': 'default_profit_v1', 'savedAt': '2026-03-24T11:00:00+00:00',
            'summary': {'skuCount': 2, 'avgMargin': 0.125, 'lossSkuCount': 0, 'currency': 'CNY', 'itemCount': 2},
            'items': [
                {'canonicalSku': 'SKU-001', 'recommendedPrice': 102.5, 'floorPrice': 95.0, 'targetPrice': 101.0, 'ceilingPrice': 105.0, 'grossMarginRate': 0.22, 'contributionMarginRate': 0.17, 'netMarginRate': 0.125},
            ],
        },
    }
    explains = {
        901: {
            'batchRef': '21', 'batchId': 21, 'snapshotId': 901, 'snapshotVersion': 2,
            'snapshotKey': '21::pricing_recommend::default_profit_v1', 'savedSource': 'pricing_recommend',
            'source': 'pricing_recommend', 'profileCode': 'default_profit_v1', 'selectedCanonicalSku': 'SKU-001',
            'explanation': {'summary': 'raise recommended price with guardrails'},
            'recommendationState': 'candidate_raise',
            'dominantRiskDriver': 'competition',
            'risks': [{'code': 'competition', 'message': 'competition pressure'}],
            'consistency': {
                'whyNotLower': [{'code': 'margin_guard', 'message': 'margin floor'}],
                'whyNotHigher': [{'code': 'competition_guard', 'message': 'competition pressure'}],
                'constraints': [{'code': 'floor_price_guard', 'active': False, 'value': 95.0}],
                'risks': [{'code': 'competition', 'message': 'competition pressure'}],
                'metrics': {'floorPrice': 95.0, 'targetPrice': 101.0, 'ceilingPrice': 105.0, 'recommendedPrice': 102.5, 'netMarginRate': 0.125},
            },
        },
    }

    monkeypatch.setattr(service, 'list_batch_profit_snapshots', lambda batch_ref, limit=20: listing)
    monkeypatch.setattr(service, 'get_batch_profit_snapshot_detail', lambda batch_ref, snapshot_id: details.get(int(snapshot_id)))
    monkeypatch.setattr(service, 'get_batch_profit_snapshot_explain', lambda batch_ref, snapshot_id, canonical_sku=None: explains.get(int(snapshot_id)))

    timeline = service.get_batch_profit_snapshot_timeline('21', canonical_sku='SKU-001')
    assert timeline is not None
    assert timeline['contractVersion'] == 'p4.profit_snapshot_timeline.v1'
    assert timeline['canonicalSku'] == 'SKU-001'
    assert [item['snapshotId'] for item in timeline['items']] == [900, 901]
    assert timeline['items'][1]['changeHints'] == ['recommendedPrice:up', 'avgMargin:up']

    review = service.get_batch_profit_snapshot_review_surface('21', 901, canonical_sku='SKU-001')
    assert review is not None
    assert review['contractVersion'] == 'p4.profit_snapshot_review_surface.v1'
    assert review['pricing']['recommendedPrice'] == 102.5
    assert review['reviewSurface']['decisionHints'] == ['candidate_raise', 'competition']
    assert review['reviewSurface']['riskFlags'] == ['competition']
