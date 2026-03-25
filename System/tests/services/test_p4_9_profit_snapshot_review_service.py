
from __future__ import annotations

from pathlib import Path

from ecom_v51.services.profit_snapshot_review_service import ProfitSnapshotReviewService
from ecom_v51.services.profit_snapshot_service import ProfitSnapshotService


def test_profit_snapshot_review_service_builds_decision_and_readiness(monkeypatch):
    base_service = ProfitSnapshotService(Path('.'))
    service = ProfitSnapshotReviewService(Path('.'), profit_snapshot_service=base_service)

    detail = {
        'batchRef': '21', 'batchId': 21, 'snapshotId': 901, 'snapshotVersion': 3,
        'snapshotKey': '21::pricing_recommend::default_profit_v1', 'savedSource': 'pricing_recommend',
        'source': 'pricing_recommend', 'profileCode': 'default_profit_v1', 'savedAt': '2026-03-24T11:00:00+00:00',
        'summary': {'skuCount': 2, 'avgMargin': 0.18, 'lossSkuCount': 0, 'currency': 'CNY', 'itemCount': 2},
        'items': [
            {'canonicalSku': 'SKU-001', 'recommendedPrice': 119.0, 'targetMarginRate': 0.23, 'netMarginRate': 0.18, 'profitConfidence': 0.72},
        ],
    }
    explain = {
        'batchRef': '21', 'batchId': 21, 'snapshotId': 901, 'snapshotVersion': 3,
        'snapshotKey': '21::pricing_recommend::default_profit_v1', 'savedSource': 'pricing_recommend',
        'source': 'pricing_recommend', 'profileCode': 'default_profit_v1', 'selectedCanonicalSku': 'SKU-001',
        'explanation': {'summary': 'raise price with normal review'},
        'risks': [{'code': 'competition', 'message': 'watch competition'}],
        'consistency': {
            'constraints': [{'code': 'floor_price_guard', 'active': False, 'value': 110.0}],
            'risks': [{'code': 'competition', 'message': 'watch competition'}],
            'metrics': {'recommendedPrice': 119.0, 'netMarginRate': 0.18, 'targetMarginRate': 0.23, 'profitConfidence': 0.72},
        },
    }
    timeline = {
        'batchRef': '21', 'batchId': 21, 'contractVersion': 'p4.profit_snapshot_timeline.v1', 'canonicalSku': 'SKU-001',
        'items': [
            {'snapshotId': 900, 'snapshotVersion': 2, 'changeHints': ['recommendedPrice:up']},
            {'snapshotId': 901, 'snapshotVersion': 3, 'changeHints': ['recommendedPrice:up', 'avgMargin:up']},
        ],
    }

    monkeypatch.setattr(base_service, 'get_batch_profit_snapshot_detail', lambda batch_ref, snapshot_id: detail)
    monkeypatch.setattr(base_service, 'get_batch_profit_snapshot_explain', lambda batch_ref, snapshot_id, canonical_sku=None: explain)
    monkeypatch.setattr(base_service, 'get_batch_profit_snapshot_timeline', lambda batch_ref, canonical_sku=None, limit=50: timeline)

    readiness = service.get_batch_profit_snapshot_readiness_gate('21', 901, canonical_sku='SKU-001')
    assert readiness is not None
    assert readiness['contractVersion'] == 'p4.9.review_readiness.v1'
    assert readiness['isReady'] is True
    assert readiness['reviewLevel'] == 'high_attention'
    assert readiness['evidence']['hasTimeline'] is True

    decision = service.get_batch_profit_snapshot_decision_surface('21', 901, canonical_sku='SKU-001')
    assert decision is not None
    assert decision['contractVersion'] == 'p4.9.review_decision_surface.v1'
    assert decision['decisionHint'] == 'ready_for_manual_decision'
    assert decision['headline']['deltaToTarget'] == 0.05
    assert decision['compareEntry']['latestPreviousSnapshotId'] == 900
