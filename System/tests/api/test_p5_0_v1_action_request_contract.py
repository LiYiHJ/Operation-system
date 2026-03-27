from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import actions as actions_module


def test_v1_action_request_create_list_and_detail_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        actions_module.action_entry_service,
        'create_action_request',
        lambda **kwargs: {
            'actionRequestId': 301,
            'contractVersion': 'p5.action_request.v1',
            'batchRef': kwargs['batch_ref'],
            'batchId': 21,
            'snapshotId': kwargs['snapshot_id'],
            'snapshotVersion': 6,
            'actionType': kwargs['action_type'],
            'canonicalSku': kwargs.get('canonical_sku') or 'SKU-001',
            'savedSource': 'pricing_recommend',
            'approvalState': 'pending_review',
            'executionState': 'not_started',
            'suggestedValue': 119.0,
            'decisionHint': 'ready_for_manual_decision',
            'createdAt': '2026-03-24T18:40:00+00:00',
        },
    )
    monkeypatch.setattr(
        actions_module.action_entry_service,
        'list_action_requests',
        lambda batch_ref=None, limit=20: {
            'contractVersion': 'p5.action_request_list.v1',
            'batchRef': batch_ref,
            'itemCount': 1,
            'items': [
                {
                    'actionRequestId': 301,
                    'contractVersion': 'p5.action_request.v1',
                    'actionType': 'price_change_review',
                    'batchRef': batch_ref or '21',
                    'batchId': 21,
                    'snapshotId': 901,
                    'snapshotVersion': 6,
                    'canonicalSku': 'SKU-001',
                    'approvalState': 'pending_review',
                    'executionState': 'not_started',
                    'savedSource': 'pricing_recommend',
                    'suggestedValue': 119.0,
                    'operator': 'alice',
                    'createdAt': '2026-03-24T18:40:00+00:00',
                }
            ],
        },
    )
    monkeypatch.setattr(
        actions_module.action_entry_service,
        'get_action_request_detail',
        lambda request_id: {
            'actionRequestId': int(request_id),
            'contractVersion': 'p5.action_request.v1',
            'actionType': 'price_change_review',
            'batchRef': '21',
            'batchId': 21,
            'snapshotId': 901,
            'snapshotVersion': 6,
            'canonicalSku': 'SKU-001',
            'approvalState': 'pending_review',
            'executionState': 'not_started',
            'savedSource': 'pricing_recommend',
            'suggestedValue': 119.0,
            'operator': 'alice',
            'createdAt': '2026-03-24T18:40:00+00:00',
            'targetType': 'sku_price',
            'sourceEngine': 'economics_v1',
            'callbackState': 'not_applicable',
            'compensationState': 'not_required',
            'decisionHint': 'ready_for_manual_decision',
            'rationale': {'headline': {'recommendedPrice': 119.0}},
            'note': '',
            'idempotencyKey': 'action::21::901::SKU-001::price_change_review',
        },
    )

    create_resp = client.post('/api/v1/actions/requests', json={
        'batchRef': '21',
        'snapshotId': 901,
        'actionType': 'price_change_review',
        'canonicalSku': 'SKU-001',
        'operator': 'alice',
    })
    create_payload = create_resp.get_json()
    assert create_resp.status_code == 201
    assert create_payload['data']['contractVersion'] == 'p5.action_request.v1'
    assert create_payload['data']['actionRequestId'] == 301

    list_resp = client.get('/api/v1/actions/requests?batchRef=21')
    list_payload = list_resp.get_json()
    assert list_resp.status_code == 200
    assert list_payload['data']['contractVersion'] == 'p5.action_request_list.v1'
    assert list_payload['data']['items'][0]['actionRequestId'] == 301

    detail_resp = client.get('/api/v1/actions/requests/301')
    detail_payload = detail_resp.get_json()
    assert detail_resp.status_code == 200
    assert detail_payload['data']['contractVersion'] == 'p5.action_request.v1'
    assert detail_payload['data']['targetType'] == 'sku_price'
