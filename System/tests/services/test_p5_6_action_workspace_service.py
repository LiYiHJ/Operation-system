from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_store import reset_action_store
from ecom_v51.services.action_workspace_service import ActionWorkspaceService


def test_action_workspace_service_actions_preview_and_command():
    reset_action_store()
    entry = ActionEntryService()
    workspace = ActionWorkspaceService()

    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan'})

    actions = workspace.get_workspace_actions(item['requestId'])
    submit_item = next(action for action in actions['availableActions'] if action['code'] == 'submit')
    assert submit_item['enabled'] is True

    result = workspace.execute_command(item['requestId'], command='submit', operator='evan')
    assert result['accepted'] is True
    assert result['resultStatus'] == 'submitted'

    preview = workspace.get_workspace_preview(item['requestId'])
    assert preview['currentStage'] == 'approval'
    assert preview['currentStatus'] == 'submitted'
    assert any(action['code'] == 'approve' and action['enabled'] for action in preview['availableActions'])
