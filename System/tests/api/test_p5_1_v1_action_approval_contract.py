from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import actions as actions_module


def test_v1_action_approval_submit_approve_reject_cancel_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        actions_module.action_entry_service,
        'transition_action_request',
        lambda request_id, operation, operator, note=None: {
            'actionRequestId': int(request_id),
            'contractVersion': 'p5.action_request.v1',
            'approvalContractVersion': 'p5.action_approval.v1',
            'actionType': 'price_change_review',
            'batchRef': '21',
            'batchId': 21,
            'snapshotId': 901,
            'snapshotVersion': 6,
            'canonicalSku': 'SKU-001',
            'approvalState': {
                'submit': 'pending_review',
                'approve': 'approved',
                'reject': 'rejected',
                'cancel': 'cancelled',
            }[operation],
            'executionState': 'not_started',
            'savedSource': 'pricing_recommend',
            'suggestedValue': 119.0,
            'operator': 'alice',
            'createdAt': '2026-03-24T18:40:00+00:00',
            'approvalEvent': {
                'actionRequestId': int(request_id),
                'operation': operation,
                'fromState': 'pending_review',
                'toState': {
                    'submit': 'pending_review',
                    'approve': 'approved',
                    'reject': 'rejected',
                    'cancel': 'cancelled',
                }[operation],
                'actor': operator,
                'note': note or '',
                'occurredAt': '2026-03-24T18:50:00+00:00',
            },
        },
    )

    for operation, expected_state in [('submit', 'pending_review'), ('approve', 'approved'), ('reject', 'rejected'), ('cancel', 'cancelled')]:
        resp = client.post(f'/api/v1/actions/requests/301/{operation}', json={'operator': 'alice', 'note': operation})
        payload = resp.get_json()
        assert resp.status_code == 200
        assert payload['data']['approvalContractVersion'] == 'p5.action_approval.v1'
        assert payload['data']['approvalState'] == expected_state
        assert payload['data']['approvalEvent']['operation'] == operation
