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


def test_action_approval_service_transition_and_history(monkeypatch):
    base_service = ProfitSnapshotService(Path('.'))
    review_service = ProfitSnapshotReviewService(Path('.'), profit_snapshot_service=base_service)
    service = ActionEntryService(Path('.'), profit_snapshot_service=base_service, review_service=review_service)

    row = _FakeRow(301, {
        'contractVersion': 'p5.action_request.v1',
        'batchRef': '21',
        'batchId': 21,
        'snapshotId': 901,
        'snapshotVersion': 6,
        'canonicalSku': 'SKU-001',
        'actionType': 'price_change_review',
        'targetType': 'sku_price',
        'sourceEngine': 'economics_v1',
        'approvalState': 'pending_review',
        'executionState': 'not_started',
        'callbackState': 'not_applicable',
        'compensationState': 'not_required',
        'savedSource': 'pricing_recommend',
        'suggestedValue': 119.0,
        'operator': 'alice',
        'rationale': {'headline': {'recommendedPrice': 119.0}},
        'approvalHistory': [],
    })

    monkeypatch.setattr(service, '_load_action_request_row', lambda request_id: row if int(request_id) == 301 else None)

    def _persist_action_request_content(request_id: int, content_json: dict):
        row.content_json = dict(content_json)
        return row

    monkeypatch.setattr(service, '_persist_action_request_content', _persist_action_request_content)

    approved = service.transition_action_request(request_id=301, operation='approve', operator='manager', note='looks good')
    assert approved is not None
    assert approved['approvalContractVersion'] == 'p5.action_approval.v1'
    assert approved['approvalState'] == 'approved'
    assert approved['approvalEvent']['operation'] == 'approve'

    history = service.get_action_approval_history(301)
    assert history is not None
    assert history['contractVersion'] == 'p5.action_approval_history.v1'
    assert history['itemCount'] == 1
    assert history['items'][0]['actor'] == 'manager'
