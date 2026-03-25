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


def test_action_callback_state_and_events_contract():
    client = _build_client()
    create_resp = client.post('/api/v1/actions/requests', json={'actionCode': 'inventory_adjustment', 'batchRef': 'batch-2', 'canonicalSku': 'SKU-2', 'requestedBy': 'evan'})
    request_id = create_resp.get_json()['data']['requestId']
    client.post(f'/api/v1/actions/requests/{request_id}/submit', json={'operator': 'evan'})
    client.post(f'/api/v1/actions/requests/{request_id}/approve', json={'operator': 'lead'})
    client.post(f'/api/v1/actions/requests/{request_id}/push', json={'operator': 'ops'})
    client.post(f'/api/v1/actions/requests/{request_id}/callback', json={'eventType': 'delivery_update', 'providerStatus': 'in_transit', 'externalRef': 'ext-2'})

    state_resp = client.get(f'/api/v1/actions/requests/{request_id}/callback-state')
    assert state_resp.status_code == 200
    state_payload = state_resp.get_json()
    assert state_payload['data']['requestId'] == request_id
    assert state_payload['data']['latestCallbackState'] == 'in_transit'

    events_resp = client.get(f'/api/v1/actions/requests/{request_id}/callback-events')
    assert events_resp.status_code == 200
    events_payload = events_resp.get_json()
    assert events_payload['data']['requestId'] == request_id
    assert events_payload['data']['total'] == 1
    assert events_payload['data']['items'][0]['providerStatus'] == 'in_transit'
