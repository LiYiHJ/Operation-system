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
from ecom_v51.services.action_compensation_service import ActionCompensationService
from ecom_v51.services.action_delivery_service import ActionDeliveryService
from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_store import reset_action_store


def test_action_compensation_service_requires_callback():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    delivery = ActionDeliveryService()
    compensation = ActionCompensationService()
    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan'})
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')
    delivery.push(item['requestId'], operator='ops')

    with pytest.raises(ValueError) as excinfo:
        compensation.evaluate_compensation(item['requestId'], operator='ops')
    assert str(excinfo.value) == 'callback_not_found'


def test_action_compensation_service_evaluate_and_state():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    delivery = ActionDeliveryService()
    callback = ActionCallbackService()
    compensation = ActionCompensationService()

    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan', 'batchRef': 'batch-3'})
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')
    delivery.push(item['requestId'], operator='ops')
    callback.ingest_callback(item['requestId'], event_type='delivery_update', provider_status='failed', external_ref='ext-3')

    evaluated = compensation.evaluate_compensation(item['requestId'], operator='ops')
    assert evaluated['policyResult']['shouldCompensate'] is True

    state = compensation.get_compensation_state(item['requestId'])
    assert state['latestRecommendedAction'] == 'manual_compensation_review'

    history = compensation.get_compensation_history(item['requestId'])
    assert history['total'] == 1
    assert history['items'][0]['reason'] == 'provider_status_failed'
