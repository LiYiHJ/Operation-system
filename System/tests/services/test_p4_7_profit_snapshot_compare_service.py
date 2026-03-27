from __future__ import annotations

from pathlib import Path

from ecom_v51.services.profit_snapshot_service import ProfitSnapshotService


def test_profit_snapshot_compare_and_explain_diff_service(monkeypatch):
    service = ProfitSnapshotService(Path('.'))

    details = {
        900: {
            'batchRef': '21',
            'batchId': 21,
            'snapshotId': 900,
            'snapshotVersion': 1,
            'snapshotKey': '21::pricing_recommend::default_profit_v1',
            'savedSource': 'pricing_recommend',
            'explainSchemaVersion': 'p4.6.explain.v1',
            'source': 'pricing_recommend',
            'profileCode': 'default_profit_v1',
            'savedAt': '2026-03-24T10:00:00+00:00',
            'summary': {'skuCount': 2, 'avgMargin': 0.1125, 'lossSkuCount': 0, 'currency': 'CNY', 'itemCount': 2},
            'items': [
                {'canonicalSku': 'SKU-001', 'recommendedPrice': 99.75, 'riskAdjustedProfit': 7.0, 'netMarginRate': 0.1125},
                {'canonicalSku': 'SKU-002', 'recommendedPrice': 88.0, 'riskAdjustedProfit': 4.0, 'netMarginRate': 0.08},
            ],
        },
        901: {
            'batchRef': '21',
            'batchId': 21,
            'snapshotId': 901,
            'snapshotVersion': 2,
            'snapshotKey': '21::pricing_recommend::default_profit_v1',
            'savedSource': 'pricing_recommend',
            'explainSchemaVersion': 'p4.6.explain.v1',
            'source': 'pricing_recommend',
            'profileCode': 'default_profit_v1',
            'savedAt': '2026-03-24T11:00:00+00:00',
            'summary': {'skuCount': 2, 'avgMargin': 0.125, 'lossSkuCount': 0, 'currency': 'CNY', 'itemCount': 2},
            'items': [
                {'canonicalSku': 'SKU-001', 'recommendedPrice': 102.5, 'riskAdjustedProfit': 8.4, 'netMarginRate': 0.125},
                {'canonicalSku': 'SKU-002', 'recommendedPrice': 88.0, 'riskAdjustedProfit': 4.0, 'netMarginRate': 0.08},
            ],
        },
    }
    explains = {
        900: {
            'batchRef': '21', 'batchId': 21, 'snapshotId': 900, 'snapshotVersion': 1,
            'snapshotKey': '21::pricing_recommend::default_profit_v1', 'savedSource': 'pricing_recommend',
            'source': 'pricing_recommend', 'profileCode': 'default_profit_v1',
            'selectedCanonicalSku': 'SKU-001', 'explainSchemaVersion': 'p4.6.explain.v1',
            'explanation': {'summary': 'hold', 'whyNotLower': 'floor', 'whyNotHigher': 'ceiling'},
            'risks': [{'code': 'stable', 'message': 'stable'}],
            'consistency': {'explainSchemaVersion': 'p4.6.explain.v1', 'metrics': {'recommendedPrice': 99.75, 'riskAdjustedProfit': 7.0}},
        },
        901: {
            'batchRef': '21', 'batchId': 21, 'snapshotId': 901, 'snapshotVersion': 2,
            'snapshotKey': '21::pricing_recommend::default_profit_v1', 'savedSource': 'pricing_recommend',
            'source': 'pricing_recommend', 'profileCode': 'default_profit_v1',
            'selectedCanonicalSku': 'SKU-001', 'explainSchemaVersion': 'p4.6.explain.v1',
            'explanation': {'summary': 'raise', 'whyNotLower': 'margin', 'whyNotHigher': 'competition'},
            'risks': [{'code': 'competition', 'message': 'competition'}],
            'consistency': {'explainSchemaVersion': 'p4.6.explain.v1', 'metrics': {'recommendedPrice': 102.5, 'riskAdjustedProfit': 8.4}},
        },
    }

    monkeypatch.setattr(service, 'get_batch_profit_snapshot_detail', lambda batch_ref, snapshot_id: details.get(int(snapshot_id)))
    monkeypatch.setattr(service, 'get_batch_profit_snapshot_explain', lambda batch_ref, snapshot_id, canonical_sku=None: explains.get(int(snapshot_id)))

    compare = service.get_batch_profit_snapshot_compare('21', 900, 901, canonical_sku='SKU-001')
    assert compare is not None
    assert compare['contractVersion'] == 'p4.profit_snapshot_compare.v1'
    assert compare['selectedCanonicalSku'] == 'SKU-001'
    assert compare['summaryComparison']['delta']['avgMargin'] == 0.0125
    assert compare['selectedItemComparison']['delta']['recommendedPrice'] == 2.75

    explain_diff = service.get_batch_profit_snapshot_explain_diff('21', 900, 901, canonical_sku='SKU-001')
    assert explain_diff is not None
    assert explain_diff['contractVersion'] == 'p4.profit_snapshot_explain_diff.v1'
    assert explain_diff['summary']['changed'] is True
    assert explain_diff['whyNotLower']['changed'] is True
    assert explain_diff['riskDiff']['added'] == ['competition']
    assert explain_diff['metricsDiff']['delta']['recommendedPrice'] == 2.75
