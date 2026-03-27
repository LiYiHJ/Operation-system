from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.action_approval_service import ActionApprovalService
from ecom_v51.services.action_delivery_service import ActionDeliveryService
from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_store import reset_action_store


def test_action_delivery_service_requires_approved_request():
    reset_action_store()
    entry = ActionEntryService()
    delivery = ActionDeliveryService()
    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan'})

    with pytest.raises(ValueError) as excinfo:
        delivery.push(item['requestId'], operator='ops')
    assert str(excinfo.value) == 'request_not_approved'


def test_action_delivery_service_push_and_history():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    delivery = ActionDeliveryService()

    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan', 'batchRef': 'batch-3'})
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')

    pushed = delivery.push(item['requestId'], operator='ops', channel='mock_push_adapter')
    assert pushed['deliveryStatus'] == 'accepted'
    assert pushed['result']['accepted'] is True

    detail = delivery.get_delivery(item['requestId'])
    assert detail['latestDelivery']['deliveryStatus'] == 'accepted'

    history = delivery.get_delivery_history(item['requestId'])
    assert history['total'] == 1
    assert history['items'][0]['adapter'] == 'mock_push_adapter'
