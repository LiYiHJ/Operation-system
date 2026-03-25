from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.action_automation_service import ActionAutomationService
from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_store import reset_action_store


def test_action_automation_service_boundary_preview_and_command():
    reset_action_store()
    entry = ActionEntryService()
    service = ActionAutomationService()

    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan'})

    boundary = service.get_automation_boundary(item['requestId'])
    assert boundary['requestId'] == item['requestId']
    assert 'automationBoundary' in boundary

    preview = service.get_handoff_preview(item['requestId'])
    assert preview['handoffTarget'] == 'review_queue'

    item['status'] = 'submitted'
    command = service.execute_handoff_command(item['requestId'], command='route_next', operator='evan')
    assert command['accepted'] is True
    assert command['handoffTarget'] == 'approver'
