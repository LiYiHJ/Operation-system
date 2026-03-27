from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.action_approval_service import ActionApprovalService
from ecom_v51.services.action_callback_service import ActionCallbackService
from ecom_v51.services.action_delivery_service import ActionDeliveryService
from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_store import reset_action_store


def test_action_callback_service_requires_delivery():
    reset_action_store()
    entry = ActionEntryService()
    callback = ActionCallbackService()
    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan'})

    with pytest.raises(ValueError) as excinfo:
        callback.ingest_callback(item['requestId'], event_type='delivery_update', provider_status='accepted')
    assert str(excinfo.value) == 'delivery_not_found'


def test_action_callback_service_ingest_and_state():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    delivery = ActionDeliveryService()
    callback = ActionCallbackService()

    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan', 'batchRef': 'batch-3'})
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')
    delivery.push(item['requestId'], operator='ops')

    ingested = callback.ingest_callback(item['requestId'], event_type='delivery_update', provider_status='delivered', external_ref='ext-3')
    assert ingested['latestCallbackState'] == 'delivered'

    state = callback.get_callback_state(item['requestId'])
    assert state['latestCallbackState'] == 'delivered'

    events = callback.get_callback_events(item['requestId'])
    assert events['total'] == 1
    assert events['items'][0]['externalRef'] == 'ext-3'
