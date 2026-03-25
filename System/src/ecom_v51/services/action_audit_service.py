from __future__ import annotations

from typing import Any, Dict, List

from .action_store import (
    ACTION_APPROVAL_HISTORY,
    ACTION_CALLBACK_HISTORY,
    ACTION_COMPENSATION_HISTORY,
    ACTION_DELIVERY_HISTORY,
    ACTION_REQUEST_ORDER,
    ACTION_REQUESTS,
)


class ActionAuditService:
    CONTRACT_VERSION = "p5.5.action_audit.v1"

    def _get_request(self, request_id: str) -> Dict[str, Any]:
        item = ACTION_REQUESTS.get(str(request_id))
        if not item:
            raise ValueError("request_not_found")
        return item

    @staticmethod
    def _latest(history: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        return history[-1] if history else None

    @staticmethod
    def _compensation_state(latest: Dict[str, Any] | None) -> str | None:
        if not latest:
            return None
        return "recommended" if latest.get("shouldCompensate") else "not_required"

    def _derive_stage_status(self, request_id: str, item: Dict[str, Any]) -> tuple[str, str]:
        latest_comp = self._latest(ACTION_COMPENSATION_HISTORY.get(str(request_id), []))
        if latest_comp:
            return "compensation", self._compensation_state(latest_comp) or "not_evaluated"
        latest_cb = self._latest(ACTION_CALLBACK_HISTORY.get(str(request_id), []))
        if latest_cb:
            return "callback", str(latest_cb.get("providerStatus") or "received")
        latest_delivery = self._latest(ACTION_DELIVERY_HISTORY.get(str(request_id), []))
        if latest_delivery:
            return "delivery", str(latest_delivery.get("deliveryStatus") or "accepted")
        latest_approval = self._latest(ACTION_APPROVAL_HISTORY.get(str(request_id), []))
        if latest_approval:
            return "approval", str(latest_approval.get("statusTo") or item.get("status") or "submitted")
        return "entry", str(item.get("status") or "draft")

    def get_audit_trace(self, request_id: str) -> Dict[str, Any]:
        item = self._get_request(request_id)
        items: List[Dict[str, Any]] = []
        items.append({
            "stage": "entry",
            "status": str(item.get("status") or "draft"),
            "timestamp": item.get("createdAt"),
            "actor": item.get("requestedBy"),
            "message": "action_request_created",
        })
        for ev in ACTION_APPROVAL_HISTORY.get(str(request_id), []):
            items.append({
                "stage": "approval",
                "status": ev.get("statusTo"),
                "timestamp": ev.get("eventAt"),
                "actor": ev.get("operator"),
                "message": ev.get("eventType"),
            })
        for ev in ACTION_DELIVERY_HISTORY.get(str(request_id), []):
            items.append({
                "stage": "delivery",
                "status": ev.get("deliveryStatus"),
                "timestamp": ev.get("pushedAt"),
                "actor": ev.get("operator"),
                "message": ev.get("resultMessage"),
            })
        for ev in ACTION_CALLBACK_HISTORY.get(str(request_id), []):
            items.append({
                "stage": "callback",
                "status": ev.get("providerStatus"),
                "timestamp": ev.get("receivedAt"),
                "actor": "provider",
                "message": ev.get("eventType"),
            })
        for ev in ACTION_COMPENSATION_HISTORY.get(str(request_id), []):
            items.append({
                "stage": "compensation",
                "status": "recommended" if ev.get("shouldCompensate") else "not_required",
                "timestamp": ev.get("evaluatedAt"),
                "actor": ev.get("operator"),
                "message": ev.get("recommendedAction"),
            })
        items = sorted(items, key=lambda x: str(x.get("timestamp") or ""))
        current_stage, current_status = self._derive_stage_status(request_id, item)
        return {
            "contractVersion": self.CONTRACT_VERSION,
            "requestId": str(request_id),
            "currentStage": current_stage,
            "currentStatus": current_status,
            "items": items,
        }

    def get_workspace_summary(self) -> Dict[str, Any]:
        total = 0
        pending_approval = 0
        approved = 0
        pushed = 0
        callbacked = 0
        compensation_flagged = 0
        closed = 0
        for request_id in ACTION_REQUEST_ORDER:
            item = ACTION_REQUESTS.get(request_id)
            if not item:
                continue
            total += 1
            status = str(item.get("status") or "draft")
            if status == "submitted":
                pending_approval += 1
            if status == "approved":
                approved += 1
            if ACTION_DELIVERY_HISTORY.get(request_id):
                pushed += 1
            if ACTION_CALLBACK_HISTORY.get(request_id):
                callbacked += 1
            latest_comp = self._latest(ACTION_COMPENSATION_HISTORY.get(request_id, []))
            if latest_comp and latest_comp.get("shouldCompensate"):
                compensation_flagged += 1
            if status in {"rejected", "cancelled"}:
                closed += 1
        return {
            "contractVersion": self.CONTRACT_VERSION,
            "totalRequests": total,
            "pendingApprovalCount": pending_approval,
            "approvedCount": approved,
            "pushedCount": pushed,
            "callbackedCount": callbacked,
            "compensationFlaggedCount": compensation_flagged,
            "closedCount": closed,
        }

    def list_workspace_items(self, *, stage: str | None = None, status: str | None = None) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        for request_id in ACTION_REQUEST_ORDER:
            item = ACTION_REQUESTS.get(request_id)
            if not item:
                continue
            current_stage, current_status = self._derive_stage_status(request_id, item)
            latest_delivery = self._latest(ACTION_DELIVERY_HISTORY.get(request_id, []))
            latest_callback = self._latest(ACTION_CALLBACK_HISTORY.get(request_id, []))
            latest_comp = self._latest(ACTION_COMPENSATION_HISTORY.get(request_id, []))
            row = {
                "requestId": request_id,
                "actionCode": item.get("actionCode"),
                "currentStage": current_stage,
                "currentStatus": current_status,
                "approvalStatus": item.get("status"),
                "deliveryStatus": (latest_delivery or {}).get("deliveryStatus"),
                "callbackState": (latest_callback or {}).get("providerStatus"),
                "compensationState": self._compensation_state(latest_comp) or "not_evaluated",
                "updatedAt": item.get("lastCompensationEvaluatedAt") or item.get("lastCallbackReceivedAt") or item.get("lastPushedAt") or item.get("lastApprovalEventAt") or item.get("createdAt"),
            }
            if stage and row["currentStage"] != stage:
                continue
            if status and row["currentStatus"] != status:
                continue
            items.append(row)
        return {
            "contractVersion": self.CONTRACT_VERSION,
            "items": items,
            "total": len(items),
        }
