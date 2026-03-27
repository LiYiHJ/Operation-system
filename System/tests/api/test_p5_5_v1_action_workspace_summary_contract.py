from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.api.app import create_app
from ecom_v51.services.action_store import reset_action_store


def _build_client():
    reset_action_store()
    app = create_app('development')
    return app.test_client()


def test_action_workspace_summary_contract():
    client = _build_client()
    req1 = client.post('/api/v1/actions/requests', json={'actionCode': 'price_update', 'requestedBy': 'evan'}).get_json()['data']['requestId']
    client.post(f'/api/v1/actions/requests/{req1}/submit', json={'operator': 'evan'})

    req2 = client.post('/api/v1/actions/requests', json={'actionCode': 'inventory_adjustment', 'requestedBy': 'ops'}).get_json()['data']['requestId']
    client.post(f'/api/v1/actions/requests/{req2}/submit', json={'operator': 'ops'})
    client.post(f'/api/v1/actions/requests/{req2}/approve', json={'operator': 'lead'})
    client.post(f'/api/v1/actions/requests/{req2}/push', json={'operator': 'ops'})
    client.post(f'/api/v1/actions/requests/{req2}/callback', json={'eventType': 'delivery_update', 'providerStatus': 'failed'})
    client.post(f'/api/v1/actions/requests/{req2}/compensation/evaluate', json={'operator': 'ops'})

    resp = client.get('/api/v1/actions/workspace/summary')
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['totalRequests'] == 2
    assert data['pendingApprovalCount'] == 1
    assert data['pushedCount'] == 1
    assert data['callbackedCount'] == 1
    assert data['compensationFlaggedCount'] == 1
