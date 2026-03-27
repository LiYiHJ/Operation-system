from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ecom_v51.db.models import ReportSnapshot
from ecom_v51.db.session import get_session
from ecom_v51.services.action_store import (
    ACTION_APPROVAL_HISTORY,
    ACTION_REGISTRY,
    ACTION_REQUEST_ORDER,
    ACTION_REQUESTS,
    new_id,
    utcnow_iso,
)
from ecom_v51.services.profit_snapshot_review_service import ProfitSnapshotReviewService
from ecom_v51.services.profit_snapshot_service import ProfitSnapshotService


class ActionEntryService:
    REGISTRY_CONTRACT_VERSION = 'p5.action_registry.v1'
    REQUEST_CONTRACT_VERSION = 'p5.action_request.v1'
    REQUEST_LIST_CONTRACT_VERSION = 'p5.action_request_list.v1'
    APPROVAL_CONTRACT_VERSION = 'p5.action_approval.v1'
    APPROVAL_HISTORY_CONTRACT_VERSION = 'p5.action_approval_history.v1'
    REPORT_TYPE = 'action_request_v1'

    def __init__(
        self,
        root_dir: Path | str = '.',
        *,
        profit_snapshot_service: ProfitSnapshotService | None = None,
        review_service: ProfitSnapshotReviewService | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.profit_snapshot_service = profit_snapshot_service or ProfitSnapshotService(self.root_dir)
        self.review_service = review_service or ProfitSnapshotReviewService(
            self.root_dir,
            profit_snapshot_service=self.profit_snapshot_service,
        )

    @staticmethod
    def _clean_str(value: Any, default: str = '') -> str:
        text = str(value or '').strip()
        return text or default

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    # ---------- P5.0 store-backed entry API ----------
    def list_registry(self) -> Dict[str, Any]:
        return {
            'contractVersion': 'p5.0.action_entry.v1',
            'items': list(ACTION_REGISTRY),
            'total': len(ACTION_REGISTRY),
        }

    def list_action_registry(self) -> Dict[str, Any]:
        items = [
            {
                'actionType': 'price_change_review',
                'targetType': 'sku_price',
                'sourceEngine': 'economics_v1',
                'requiresApproval': True,
                'entryMode': 'manual_review',
                'supportedSavedSources': ['pricing_recommend', 'solve'],
                'guards': ['price_change_guard', 'duplicate_push_guard'],
                'states': {
                    'approval': 'pending_review',
                    'execution': 'not_started',
                    'callback': 'not_applicable',
                    'compensation': 'not_required',
                },
            },
            {
                'actionType': 'promo_price_review',
                'targetType': 'promotion_price',
                'sourceEngine': 'economics_v1',
                'requiresApproval': True,
                'entryMode': 'manual_review',
                'supportedSavedSources': ['pricing_recommend'],
                'guards': ['price_change_guard', 'shop_health_guard', 'duplicate_push_guard'],
                'states': {
                    'approval': 'pending_review',
                    'execution': 'not_started',
                    'callback': 'not_applicable',
                    'compensation': 'not_required',
                },
            },
        ]
        return {'contractVersion': self.REGISTRY_CONTRACT_VERSION, 'items': items}

    def create_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        action_code = self._clean_str(payload.get('actionCode'))
        if not action_code:
            raise ValueError('action_code_required')
        request_id = new_id('actreq')
        item = {
            'requestId': request_id,
            'actionCode': action_code,
            'status': 'draft',
            'batchRef': self._clean_str(payload.get('batchRef')) or None,
            'snapshotId': self._clean_str(payload.get('snapshotId')) or None,
            'canonicalSku': self._clean_str(payload.get('canonicalSku')) or None,
            'requestedBy': self._clean_str(payload.get('requestedBy') or payload.get('operator') or 'system', 'system'),
            'createdAt': utcnow_iso(),
            'payload': payload.get('payload') or {},
            'note': self._clean_str(payload.get('note')) or None,
        }
        ACTION_REQUESTS[request_id] = item
        ACTION_REQUEST_ORDER.insert(0, request_id)
        return item

    def list_requests(self, *, status: str | None = None, action_code: str | None = None, limit: int = 20) -> Dict[str, Any]:
        items = [ACTION_REQUESTS[rid] for rid in ACTION_REQUEST_ORDER if rid in ACTION_REQUESTS]
        if status:
            items = [item for item in items if str(item.get('status')) == status]
        if action_code:
            items = [item for item in items if str(item.get('actionCode')) == action_code]
        items = items[: max(limit, 0)]
        return {'contractVersion': 'p5.0.action_entry.v1', 'items': items, 'total': len(items)}

    def get_request(self, request_id: str) -> Dict[str, Any] | None:
        item = ACTION_REQUESTS.get(str(request_id))
        return dict(item) if item else None

    # ---------- P5.0/P5.1 row-backed compatibility API ----------
    def _get_registry_item(self, action_type: str) -> Optional[Dict[str, Any]]:
        normalized = self._clean_str(action_type)
        for item in self.list_action_registry().get('items', []):
            if self._clean_str(item.get('actionType')) == normalized:
                return dict(item)
        return None

    def _resolve_snapshot_row(self, batch_ref: str, snapshot_id: int):
        state, row = self.profit_snapshot_service._load_snapshot_row(batch_ref, snapshot_id)  # noqa: SLF001
        return state, row

    def _save_action_request_row(self, *, shop_id: int, content_json: Dict[str, Any], content_md: str | None = None) -> tuple[int, str]:
        generated_at = datetime.now(timezone.utc)
        with get_session() as session:
            row = ReportSnapshot(
                shop_id=shop_id,
                report_type=self.REPORT_TYPE,
                report_date=date.today(),
                content_md=self._clean_str(content_md) or f"action_request_{content_json.get('actionType')}_{content_json.get('snapshotId')}",
                content_json=dict(content_json),
                generated_at=generated_at,
            )
            session.add(row)
            session.flush()
            return int(row.id), generated_at.isoformat()

    def _load_action_request_rows(self) -> list[ReportSnapshot]:
        with get_session() as session:
            return (
                session.query(ReportSnapshot)
                .filter(ReportSnapshot.report_type == self.REPORT_TYPE)
                .order_by(ReportSnapshot.generated_at.desc(), ReportSnapshot.id.desc())
                .all()
            )

    def _load_action_request_row(self, request_id: int) -> Optional[ReportSnapshot]:
        with get_session() as session:
            return (
                session.query(ReportSnapshot)
                .filter(ReportSnapshot.report_type == self.REPORT_TYPE, ReportSnapshot.id == int(request_id))
                .one_or_none()
            )

    def _persist_action_request_content(self, request_id: int, content_json: Dict[str, Any]) -> Optional[ReportSnapshot]:
        with get_session() as session:
            row = (
                session.query(ReportSnapshot)
                .filter(ReportSnapshot.report_type == self.REPORT_TYPE, ReportSnapshot.id == int(request_id))
                .one_or_none()
            )
            if row is None:
                return None
            row.content_json = dict(content_json)
            session.flush()
            return row

    def _serialize_summary(self, row: ReportSnapshot) -> Dict[str, Any]:
        content = dict(row.content_json or {})
        return {
            'actionRequestId': int(row.id),
            'contractVersion': self.REQUEST_CONTRACT_VERSION,
            'actionType': self._clean_str(content.get('actionType')),
            'batchRef': self._clean_str(content.get('batchRef')),
            'batchId': self._safe_int(content.get('batchId')),
            'snapshotId': self._safe_int(content.get('snapshotId')),
            'snapshotVersion': self._safe_int(content.get('snapshotVersion') or 1, 1),
            'canonicalSku': self._clean_str(content.get('canonicalSku')),
            'approvalState': self._clean_str(content.get('approvalState'), 'pending_review'),
            'executionState': self._clean_str(content.get('executionState'), 'not_started'),
            'savedSource': self._clean_str(content.get('savedSource') or content.get('source'), 'pricing_recommend'),
            'suggestedValue': content.get('suggestedValue'),
            'operator': self._clean_str(content.get('operator'), 'frontend_user'),
            'createdAt': row.generated_at.isoformat() if row.generated_at else None,
        }

    def _approval_transition(self, state: str, operation: str) -> Optional[str]:
        normalized_state = self._clean_str(state, 'pending_review')
        normalized_operation = self._clean_str(operation)
        transitions = {
            ('draft', 'submit'): 'pending_review',
            ('pending_review', 'submit'): 'pending_review',
            ('pending_review', 'approve'): 'approved',
            ('submitted', 'approve'): 'approved',
            ('pending_review', 'reject'): 'rejected',
            ('submitted', 'reject'): 'rejected',
            ('draft', 'cancel'): 'cancelled',
            ('pending_review', 'cancel'): 'cancelled',
            ('submitted', 'cancel'): 'cancelled',
            ('approved', 'cancel'): 'cancelled',
            ('rejected', 'cancel'): 'cancelled',
        }
        return transitions.get((normalized_state, normalized_operation))

    def _build_approval_event(self, *, request_id: int, operation: str, actor: str, from_state: str, to_state: str, note: str | None) -> Dict[str, Any]:
        return {
            'actionRequestId': int(request_id),
            'operation': self._clean_str(operation),
            'fromState': self._clean_str(from_state),
            'toState': self._clean_str(to_state),
            'actor': self._clean_str(actor, 'frontend_user'),
            'note': self._clean_str(note),
            'occurredAt': datetime.now(timezone.utc).isoformat(),
        }

    def _serialize_approval_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'actionRequestId': self._safe_int(event.get('actionRequestId')),
            'operation': self._clean_str(event.get('operation')),
            'fromState': self._clean_str(event.get('fromState')),
            'toState': self._clean_str(event.get('toState')),
            'actor': self._clean_str(event.get('actor'), 'frontend_user'),
            'note': self._clean_str(event.get('note')),
            'occurredAt': event.get('occurredAt'),
        }

    def create_action_request(
        self,
        *,
        batch_ref: str,
        snapshot_id: int,
        action_type: str,
        operator: str,
        canonical_sku: str | None = None,
        note: str | None = None,
        idempotency_key: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        registry_item = self._get_registry_item(action_type)
        if not registry_item:
            raise ValueError('unsupported_action_type')
        detail = self.profit_snapshot_service.get_batch_profit_snapshot_detail(batch_ref, snapshot_id)
        decision = self.review_service.get_batch_profit_snapshot_decision_surface(batch_ref, snapshot_id, canonical_sku=canonical_sku)
        readiness = self.review_service.get_batch_profit_snapshot_readiness_gate(batch_ref, snapshot_id, canonical_sku=canonical_sku)
        if not detail or not decision or not readiness:
            return None
        if not readiness.get('isReady'):
            raise ValueError('action_request_not_ready')
        _, snapshot_row = self._resolve_snapshot_row(batch_ref, snapshot_id)
        if snapshot_row is None:
            return None
        selected_canonical_sku = self._clean_str(decision.get('canonicalSku') or canonical_sku)
        suggested_value = decision.get('headline', {}).get('recommendedPrice')
        content_json = {
            'contractVersion': self.REQUEST_CONTRACT_VERSION,
            'batchRef': self._clean_str(batch_ref),
            'batchId': self._safe_int(detail.get('batchId')),
            'snapshotId': int(snapshot_id),
            'snapshotVersion': self._safe_int(detail.get('snapshotVersion') or 1, 1),
            'snapshotKey': self._clean_str(detail.get('snapshotKey')),
            'derivedFromSnapshotId': detail.get('derivedFromSnapshotId'),
            'savedSource': self._clean_str(detail.get('savedSource') or detail.get('source'), 'pricing_recommend'),
            'canonicalSku': selected_canonical_sku,
            'actionType': self._clean_str(action_type),
            'targetType': self._clean_str(registry_item.get('targetType')),
            'sourceEngine': self._clean_str(registry_item.get('sourceEngine'), 'economics_v1'),
            'approvalState': 'pending_review',
            'executionState': 'not_started',
            'callbackState': 'not_applicable',
            'compensationState': 'not_required',
            'decisionHint': self._clean_str(decision.get('decisionHint'), 'ready_for_manual_decision'),
            'suggestedValue': suggested_value,
            'rationale': {
                'headline': dict(decision.get('headline') or {}),
                'metrics': dict(decision.get('metrics') or {}),
                'constraints': list(decision.get('constraints') or []),
                'risks': list(decision.get('risks') or []),
                'readiness': dict(readiness),
            },
            'operator': self._clean_str(operator, 'frontend_user'),
            'note': self._clean_str(note),
            'idempotencyKey': self._clean_str(idempotency_key) or f"action::{batch_ref}::{snapshot_id}::{selected_canonical_sku}::{self._clean_str(action_type)}",
            'approvalHistory': [],
        }
        request_id, created_at = self._save_action_request_row(
            shop_id=int(snapshot_row.shop_id),
            content_json=content_json,
            content_md=self._clean_str(note) or f"action_request_{batch_ref}_{snapshot_id}_{selected_canonical_sku}",
        )
        return {
            'actionRequestId': request_id,
            'contractVersion': self.REQUEST_CONTRACT_VERSION,
            'batchRef': self._clean_str(batch_ref),
            'batchId': self._safe_int(detail.get('batchId')),
            'snapshotId': int(snapshot_id),
            'snapshotVersion': self._safe_int(detail.get('snapshotVersion') or 1, 1),
            'actionType': self._clean_str(action_type),
            'canonicalSku': selected_canonical_sku,
            'savedSource': self._clean_str(detail.get('savedSource') or detail.get('source'), 'pricing_recommend'),
            'approvalState': 'pending_review',
            'executionState': 'not_started',
            'suggestedValue': suggested_value,
            'decisionHint': self._clean_str(decision.get('decisionHint'), 'ready_for_manual_decision'),
            'createdAt': created_at,
        }

    def list_action_requests(self, *, batch_ref: str | None = None, limit: int = 20) -> Dict[str, Any]:
        rows = list(self._load_action_request_rows())
        items = []
        normalized_batch_ref = self._clean_str(batch_ref)
        for row in rows:
            content = dict(row.content_json or {})
            if normalized_batch_ref and self._clean_str(content.get('batchRef')) != normalized_batch_ref:
                continue
            items.append(self._serialize_summary(row))
            if len(items) >= max(min(int(limit or 20), 100), 1):
                break
        return {
            'contractVersion': self.REQUEST_LIST_CONTRACT_VERSION,
            'batchRef': normalized_batch_ref or None,
            'items': items,
            'itemCount': len(items),
        }

    def get_action_request_detail(self, request_id: int | str) -> Optional[Dict[str, Any]]:
        row = self._load_action_request_row(int(request_id))
        if row is None:
            return None
        content = dict(row.content_json or {})
        detail = self._serialize_summary(row)
        detail.update({
            'targetType': self._clean_str(content.get('targetType')),
            'sourceEngine': self._clean_str(content.get('sourceEngine'), 'economics_v1'),
            'callbackState': self._clean_str(content.get('callbackState'), 'not_applicable'),
            'compensationState': self._clean_str(content.get('compensationState'), 'not_required'),
            'decisionHint': self._clean_str(content.get('decisionHint'), 'ready_for_manual_decision'),
            'rationale': dict(content.get('rationale') or {}),
            'note': self._clean_str(content.get('note')),
            'idempotencyKey': self._clean_str(content.get('idempotencyKey')),
            'approvalHistory': [self._serialize_approval_event(event) for event in list(content.get('approvalHistory') or [])],
        })
        return detail

    def transition_action_request(self, request_id: int | str, operation: str, operator: str, note: str | None = None) -> Optional[Dict[str, Any]]:
        # Row-backed compatibility path first.
        row = self._load_action_request_row(int(request_id)) if str(request_id).isdigit() else None
        if row is not None:
            content = dict(row.content_json or {})
            current_state = self._clean_str(content.get('approvalState'), 'pending_review')
            next_state = self._approval_transition(current_state, operation)
            if not next_state:
                raise ValueError('invalid_approval_transition')
            event = self._build_approval_event(
                request_id=int(request_id),
                operation=operation,
                actor=operator,
                from_state=current_state,
                to_state=next_state,
                note=note,
            )
            history = list(content.get('approvalHistory') or [])
            history.append(event)
            content['approvalState'] = next_state
            content['approvalHistory'] = history
            content['lastApprovalEvent'] = dict(event)
            persisted = self._persist_action_request_content(int(request_id), content)
            effective_row = persisted or row
            if hasattr(effective_row, 'content_json'):
                effective_row.content_json = dict(content)
            detail = self.get_action_request_detail(int(request_id))
            if detail is None:
                return None
            detail.update({
                'approvalContractVersion': self.APPROVAL_CONTRACT_VERSION,
                'operation': self._clean_str(operation),
                'approvalState': next_state,
                'approvalEvent': self._serialize_approval_event(event),
            })
            return detail

        # Store-backed P5.2 path.
        item = ACTION_REQUESTS.get(str(request_id))
        if not item:
            raise ValueError('request_not_found')
        current = self._clean_str(item.get('status'), 'draft')
        transitions = {
            ('draft', 'submit'): 'submitted',
            ('submitted', 'approve'): 'approved',
            ('submitted', 'reject'): 'rejected',
            ('draft', 'cancel'): 'cancelled',
            ('submitted', 'cancel'): 'cancelled',
            ('approved', 'cancel'): 'cancelled',
        }
        next_state = transitions.get((current, self._clean_str(operation)))
        if not next_state:
            raise ValueError('invalid_request_status')
        item['status'] = next_state
        event = {
            'actionRequestId': str(request_id),
            'operation': self._clean_str(operation),
            'fromState': current,
            'toState': next_state,
            'actor': self._clean_str(operator, 'system'),
            'note': self._clean_str(note),
            'occurredAt': utcnow_iso(),
        }
        ACTION_APPROVAL_HISTORY.setdefault(str(request_id), []).append(event)
        result = dict(item)
        result['approvalContractVersion'] = self.APPROVAL_CONTRACT_VERSION
        result['approvalState'] = next_state
        result['approvalEvent'] = event
        return result

    def get_action_approval_history(self, request_id: int | str) -> Optional[Dict[str, Any]]:
        row = self._load_action_request_row(int(request_id)) if str(request_id).isdigit() else None
        if row is not None:
            content = dict(row.content_json or {})
            history = [self._serialize_approval_event(event) for event in list(content.get('approvalHistory') or [])]
            return {
                'contractVersion': self.APPROVAL_HISTORY_CONTRACT_VERSION,
                'actionRequestId': int(request_id),
                'approvalState': self._clean_str(content.get('approvalState'), 'pending_review'),
                'itemCount': len(history),
                'items': history,
            }
        item = ACTION_REQUESTS.get(str(request_id))
        if not item:
            raise ValueError('request_not_found')
        history = list(ACTION_APPROVAL_HISTORY.get(str(request_id), []))
        return {
            'contractVersion': self.APPROVAL_HISTORY_CONTRACT_VERSION,
            'actionRequestId': str(request_id),
            'approvalState': self._clean_str(item.get('status'), 'draft'),
            'itemCount': len(history),
            'items': history,
        }
