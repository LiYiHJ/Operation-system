from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import actions as actions_module


def test_v1_action_registry_contract(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        actions_module.action_entry_service,
        'list_action_registry',
        lambda: {
            'contractVersion': 'p5.action_registry.v1',
            'items': [
                {
                    'actionType': 'price_change_review',
                    'targetType': 'sku_price',
                    'sourceEngine': 'economics_v1',
                    'requiresApproval': True,
                }
            ],
        },
    )

    response = client.get('/api/v1/actions/registry')
    payload = response.get_json()
    assert response.status_code == 200
    assert payload['data']['contractVersion'] == 'p5.action_registry.v1'
    assert payload['data']['items'][0]['actionType'] == 'price_change_review'
