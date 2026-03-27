from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.action_approval_service import ActionApprovalService
from ecom_v51.services.action_audit_service import ActionAuditService
from ecom_v51.services.action_callback_service import ActionCallbackService
from ecom_v51.services.action_compensation_service import ActionCompensationService
from ecom_v51.services.action_delivery_service import ActionDeliveryService
from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_store import reset_action_store


def test_action_audit_service_trace_and_workspace_views():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    delivery = ActionDeliveryService()
    callback = ActionCallbackService()
    compensation = ActionCompensationService()
    audit = ActionAuditService()

    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan'})
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')
    delivery.push(item['requestId'], operator='ops')
    callback.ingest_callback(item['requestId'], event_type='delivery_update', provider_status='failed', external_ref='ext-5')
    compensation.evaluate_compensation(item['requestId'], operator='ops')

    trace = audit.get_audit_trace(item['requestId'])
    assert trace['currentStage'] == 'compensation'
    assert any(event['stage'] == 'delivery' for event in trace['items'])

    summary = audit.get_workspace_summary()
    assert summary['totalRequests'] == 1
    assert summary['compensationFlaggedCount'] == 1

    items = audit.list_workspace_items(stage='compensation')
    assert items['total'] == 1
    assert items['items'][0]['requestId'] == item['requestId']
