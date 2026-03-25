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


def test_action_workspace_items_contract_and_filter():
    client = _build_client()
    req1 = client.post('/api/v1/actions/requests', json={'actionCode': 'price_update', 'requestedBy': 'evan'}).get_json()['data']['requestId']
    client.post(f'/api/v1/actions/requests/{req1}/submit', json={'operator': 'evan'})

    req2 = client.post('/api/v1/actions/requests', json={'actionCode': 'inventory_adjustment', 'requestedBy': 'ops'}).get_json()['data']['requestId']

    items_resp = client.get('/api/v1/actions/workspace/items')
    assert items_resp.status_code == 200
    data = items_resp.get_json()['data']
    assert data['total'] == 2
    assert {'requestId', 'currentStage', 'currentStatus', 'updatedAt'}.issubset(data['items'][0].keys())

    filtered_resp = client.get('/api/v1/actions/workspace/items?status=submitted')
    assert filtered_resp.status_code == 200
    filtered = filtered_resp.get_json()['data']
    assert filtered['total'] == 1
    assert filtered['items'][0]['requestId'] == req1
