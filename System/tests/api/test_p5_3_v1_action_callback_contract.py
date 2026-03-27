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


def test_action_callback_contract_happy_path():
    client = _build_client()
    create_resp = client.post('/api/v1/actions/requests', json={'actionCode': 'price_update', 'batchRef': 'batch-1', 'canonicalSku': 'SKU-1', 'requestedBy': 'evan'})
    request_id = create_resp.get_json()['data']['requestId']
    client.post(f'/api/v1/actions/requests/{request_id}/submit', json={'operator': 'evan'})
    client.post(f'/api/v1/actions/requests/{request_id}/approve', json={'operator': 'lead'})
    client.post(f'/api/v1/actions/requests/{request_id}/push', json={'operator': 'ops'})

    callback_resp = client.post(
        f'/api/v1/actions/requests/{request_id}/callback',
        json={'eventType': 'delivery_update', 'providerStatus': 'delivered', 'externalRef': 'ext-1'},
    )
    assert callback_resp.status_code == 202
    payload = callback_resp.get_json()
    assert payload['success'] is True
    assert payload['data']['requestId'] == request_id
    assert payload['data']['latestCallbackState'] == 'delivered'
