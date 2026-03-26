from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

ACTION_REGISTRY: List[Dict[str, Any]] = [
    {
        'actionCode': 'price_update',
        'actionName': '价格调整',
        'requiresApproval': True,
        'defaultAdapter': 'mock_push_adapter',
        'entityType': 'sku',
    },
    {
        'actionCode': 'inventory_adjustment',
        'actionName': '库存调整',
        'requiresApproval': True,
        'defaultAdapter': 'mock_push_adapter',
        'entityType': 'sku',
    },
    {
        'actionCode': 'ad_budget_update',
        'actionName': '广告预算调整',
        'requiresApproval': True,
        'defaultAdapter': 'mock_push_adapter',
        'entityType': 'campaign',
    },
]

ACTION_REQUESTS: Dict[str, Dict[str, Any]] = {}
ACTION_REQUEST_ORDER: List[str] = []
ACTION_APPROVAL_HISTORY: Dict[str, List[Dict[str, Any]]] = {}
ACTION_DELIVERY_HISTORY: Dict[str, List[Dict[str, Any]]] = {}
ACTION_CALLBACK_HISTORY: Dict[str, List[Dict[str, Any]]] = {}
ACTION_COMPENSATION_HISTORY: Dict[str, List[Dict[str, Any]]] = {}
ACTION_JOBS: Dict[str, Dict[str, Any]] = {}
ACTION_JOB_EVENTS: Dict[str, List[Dict[str, Any]]] = {}
ACTION_REQUEST_JOB_INDEX: Dict[str, List[str]] = {}
ACTION_JOB_IDEMPOTENCY: Dict[str, str] = {}
ACTION_JOB_COMMAND_IDEMPOTENCY: Dict[str, str] = {}
ACTION_BULK_COMMANDS: Dict[str, Dict[str, Any]] = {}
ACTION_BULK_COMMAND_ORDER: List[str] = []


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f'{prefix}_{uuid4().hex[:12]}'


def reset_action_store() -> None:
    ACTION_REQUESTS.clear()
    ACTION_REQUEST_ORDER.clear()
    ACTION_APPROVAL_HISTORY.clear()
    ACTION_DELIVERY_HISTORY.clear()
    ACTION_CALLBACK_HISTORY.clear()
    ACTION_COMPENSATION_HISTORY.clear()
    ACTION_JOBS.clear()
    ACTION_JOB_EVENTS.clear()
    ACTION_REQUEST_JOB_INDEX.clear()
    ACTION_JOB_IDEMPOTENCY.clear()
    ACTION_JOB_COMMAND_IDEMPOTENCY.clear()
    ACTION_BULK_COMMANDS.clear()
    ACTION_BULK_COMMAND_ORDER.clear()
