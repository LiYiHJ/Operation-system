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


def test_action_automation_boundary_contract_happy_path():
    client = _build_client()
    create_resp = client.post('/api/v1/actions/requests', json={'actionCode': 'price_update', 'requestedBy': 'evan'})
    request_id = create_resp.get_json()['data']['requestId']

    resp = client.get(f'/api/v1/actions/requests/{request_id}/automation-boundary')
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['requestId'] == request_id
    assert 'automationBoundary' in data
    assert 'availableAutomationActions' in data
