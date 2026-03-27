from __future__ import annotations

from pathlib import Path

from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.profit_snapshot_review_service import ProfitSnapshotReviewService
from ecom_v51.services.profit_snapshot_service import ProfitSnapshotService


class _FakeRow:
    def __init__(self, row_id: int, content_json: dict, generated_at: str = '2026-03-24T18:40:00+00:00') -> None:
        from datetime import datetime

        self.id = row_id
        self.shop_id = 1
        self.content_json = dict(content_json)
        self.generated_at = datetime.fromisoformat(generated_at)


def test_action_entry_service_create_list_and_detail(monkeypatch):
    base_service = ProfitSnapshotService(Path('.'))
    review_service = ProfitSnapshotReviewService(Path('.'), profit_snapshot_service=base_service)
    service = ActionEntryService(Path('.'), profit_snapshot_service=base_service, review_service=review_service)

    detail = {
        'batchRef': '21', 'batchId': 21, 'snapshotId': 901, 'snapshotVersion': 6,
        'snapshotKey': '21::pricing_recommend::default_profit_v1', 'savedSource': 'pricing_recommend',
        'source': 'pricing_recommend', 'profileCode': 'default_profit_v1', 'derivedFromSnapshotId': 900,
    }
    decision = {
        'batchRef': '21', 'batchId': 21, 'snapshotId': 901, 'snapshotVersion': 6,
        'canonicalSku': 'SKU-001', 'decisionHint': 'ready_for_manual_decision',
        'headline': {'recommendedPrice': 119.0},
        'metrics': {'recommendedPrice': 119.0, 'netMarginRate': 0.18},
        'constraints': [{'code': 'floor_price_guard', 'active': False, 'value': 110.0}],
        'risks': [{'code': 'competition', 'message': 'watch competition'}],
    }
    readiness = {
        'contractVersion': 'p4.9.review_readiness.v1',
        'isReady': True,
        'reviewLevel': 'normal',
        'confidence': 'medium',
        'blockingReasons': [],
        'requiredFields': [],
        'evidence': {'hasTimeline': True},
        'canonicalSku': 'SKU-001',
    }

    monkeypatch.setattr(base_service, 'get_batch_profit_snapshot_detail', lambda batch_ref, snapshot_id: detail)
    monkeypatch.setattr(review_service, 'get_batch_profit_snapshot_decision_surface', lambda batch_ref, snapshot_id, canonical_sku=None: decision)
    monkeypatch.setattr(review_service, 'get_batch_profit_snapshot_readiness_gate', lambda batch_ref, snapshot_id, canonical_sku=None: readiness)
    monkeypatch.setattr(service, '_resolve_snapshot_row', lambda batch_ref, snapshot_id: ({'detail': {'shopId': 1}}, type('Row', (), {'shop_id': 1})()))

    storage: list[_FakeRow] = []

    def _save_action_request_row(*, shop_id: int, content_json: dict, content_md: str | None = None):
        row = _FakeRow(301, content_json)
        storage.append(row)
        return row.id, row.generated_at.isoformat()

    monkeypatch.setattr(service, '_save_action_request_row', _save_action_request_row)
    monkeypatch.setattr(service, '_load_action_request_rows', lambda: list(storage))
    monkeypatch.setattr(service, '_load_action_request_row', lambda request_id: storage[0] if storage and int(request_id) == 301 else None)

    created = service.create_action_request(
        batch_ref='21',
        snapshot_id=901,
        action_type='price_change_review',
        canonical_sku='SKU-001',
        operator='alice',
        note='review first',
    )
    assert created is not None
    assert created['contractVersion'] == 'p5.action_request.v1'
    assert created['approvalState'] == 'pending_review'

    listed = service.list_action_requests(batch_ref='21', limit=20)
    assert listed['contractVersion'] == 'p5.action_request_list.v1'
    assert listed['itemCount'] == 1
    assert listed['items'][0]['actionRequestId'] == 301

    detail_view = service.get_action_request_detail(301)
    assert detail_view is not None
    assert detail_view['contractVersion'] == 'p5.action_request.v1'
    assert detail_view['targetType'] == 'sku_price'
    assert detail_view['rationale']['headline']['recommendedPrice'] == 119.0
