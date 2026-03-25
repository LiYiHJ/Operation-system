from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import actions as actions_module


def test_v1_action_approval_history_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        actions_module.action_entry_service,
        'get_action_approval_history',
        lambda request_id: {
            'contractVersion': 'p5.action_approval_history.v1',
            'actionRequestId': int(request_id),
            'approvalState': 'approved',
            'itemCount': 2,
            'items': [
                {
                    'actionRequestId': int(request_id),
                    'operation': 'submit',
                    'fromState': 'draft',
                    'toState': 'pending_review',
                    'actor': 'alice',
                    'note': '',
                    'occurredAt': '2026-03-24T18:41:00+00:00',
                },
                {
                    'actionRequestId': int(request_id),
                    'operation': 'approve',
                    'fromState': 'pending_review',
                    'toState': 'approved',
                    'actor': 'manager',
                    'note': 'approved',
                    'occurredAt': '2026-03-24T18:45:00+00:00',
                },
            ],
        },
    )

    resp = client.get('/api/v1/actions/requests/301/approval-history')
    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload['data']['contractVersion'] == 'p5.action_approval_history.v1'
    assert payload['data']['itemCount'] == 2
    assert payload['data']['items'][1]['operation'] == 'approve'
