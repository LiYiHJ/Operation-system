
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ecom_v51.services.profit_snapshot_service import ProfitSnapshotService


class ProfitSnapshotReviewService:
    DECISION_CONTRACT_VERSION = 'p4.9.review_decision_surface.v1'
    READINESS_CONTRACT_VERSION = 'p4.9.review_readiness.v1'

    def __init__(self, root_dir: Path, *, profit_snapshot_service: ProfitSnapshotService | None = None) -> None:
        self.root_dir = Path(root_dir)
        self.profit_snapshot_service = profit_snapshot_service or ProfitSnapshotService(self.root_dir)

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

    def _extract_selected_item(self, detail: Dict[str, Any], canonical_sku: str | None = None) -> Dict[str, Any]:
        normalized = self._clean_str(canonical_sku)
        items = list((detail or {}).get('items') or [])
        if normalized:
            for item in items:
                if self._clean_str((item or {}).get('canonicalSku')) == normalized:
                    return dict(item or {})
        if items:
            return dict(items[0] or {})
        return {}

    def _resolve_core_views(
        self,
        batch_ref: str,
        snapshot_id: int,
        *,
        canonical_sku: str | None = None,
    ) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        detail = self.profit_snapshot_service.get_batch_profit_snapshot_detail(batch_ref, snapshot_id)
        explain = self.profit_snapshot_service.get_batch_profit_snapshot_explain(batch_ref, snapshot_id, canonical_sku=canonical_sku)
        timeline = self.profit_snapshot_service.get_batch_profit_snapshot_timeline(batch_ref, canonical_sku=canonical_sku, limit=50)
        if not detail or not explain or not timeline:
            return None, None, None
        return detail, explain, timeline

    def get_batch_profit_snapshot_readiness_gate(
        self,
        batch_ref: str,
        snapshot_id: int,
        *,
        canonical_sku: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        detail, explain, timeline = self._resolve_core_views(batch_ref, snapshot_id, canonical_sku=canonical_sku)
        if not detail or not explain or not timeline:
            return None
        selected_canonical_sku = self._clean_str(explain.get('selectedCanonicalSku') or canonical_sku) or None
        selected_item = self._extract_selected_item(detail, canonical_sku=selected_canonical_sku)
        consistency = dict(explain.get('consistency') or {})
        metrics = dict(consistency.get('metrics') or {})
        constraints = list(consistency.get('constraints') or [])
        risks = list(consistency.get('risks') or explain.get('risks') or [])
        timeline_items = list(timeline.get('items') or [])

        evidence = {
            'hasExplain': bool(explain.get('explanation')),
            'hasMetrics': bool(metrics),
            'hasConstraints': bool(constraints),
            'hasRisks': bool(risks),
            'hasVersioning': self._safe_int(detail.get('snapshotVersion') or 0, 0) > 0,
            'hasTimeline': bool(timeline_items),
        }
        blocking_reasons: list[str] = []
        required_fields: list[str] = []
        if not selected_canonical_sku:
            blocking_reasons.append('canonical_sku_missing')
            required_fields.append('canonicalSku')
        if not evidence['hasExplain']:
            blocking_reasons.append('explain_missing')
        if not evidence['hasMetrics']:
            blocking_reasons.append('metrics_missing')
        recommended_price = self._safe_float(metrics.get('recommendedPrice') or selected_item.get('recommendedPrice'))
        if recommended_price <= 0:
            blocking_reasons.append('recommended_price_missing')
            required_fields.append('recommendedPrice')
        if not evidence['hasVersioning']:
            blocking_reasons.append('snapshot_version_missing')
        if not evidence['hasTimeline']:
            blocking_reasons.append('timeline_missing')
        net_margin = self._safe_float(metrics.get('netMarginRate') or selected_item.get('netMarginRate'))
        profit_confidence = self._safe_float(metrics.get('profitConfidence') or selected_item.get('profitConfidence'))
        review_level = 'high_attention' if risks or net_margin < 0.05 else 'normal'
        confidence = 'high' if profit_confidence >= 0.8 else 'medium' if profit_confidence >= 0.5 else 'low'
        return {
            'batchRef': str(batch_ref),
            'batchId': detail.get('batchId') or explain.get('batchId'),
            'snapshotId': int(detail.get('snapshotId') or snapshot_id),
            'snapshotVersion': self._safe_int(detail.get('snapshotVersion') or 1, 1),
            'canonicalSku': selected_canonical_sku,
            'savedSource': self._clean_str(detail.get('savedSource') or detail.get('source'), 'solve'),
            'contractVersion': self.READINESS_CONTRACT_VERSION,
            'isReady': not blocking_reasons,
            'reviewLevel': review_level,
            'confidence': confidence,
            'blockingReasons': blocking_reasons,
            'requiredFields': sorted(set(required_fields)),
            'evidence': evidence,
        }

    def get_batch_profit_snapshot_decision_surface(
        self,
        batch_ref: str,
        snapshot_id: int,
        *,
        canonical_sku: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        detail, explain, timeline = self._resolve_core_views(batch_ref, snapshot_id, canonical_sku=canonical_sku)
        readiness = self.get_batch_profit_snapshot_readiness_gate(batch_ref, snapshot_id, canonical_sku=canonical_sku)
        if not detail or not explain or not timeline or not readiness:
            return None
        selected_canonical_sku = self._clean_str(explain.get('selectedCanonicalSku') or canonical_sku) or None
        selected_item = self._extract_selected_item(detail, canonical_sku=selected_canonical_sku)
        consistency = dict(explain.get('consistency') or {})
        metrics = dict(consistency.get('metrics') or {})
        constraints = list(consistency.get('constraints') or [])
        risks = list(consistency.get('risks') or explain.get('risks') or [])
        timeline_items = list(timeline.get('items') or [])
        current_entry = next((item for item in timeline_items if int(item.get('snapshotId') or 0) == int(snapshot_id)), {})
        previous_entry = next((item for item in reversed(timeline_items) if int(item.get('snapshotId') or 0) < int(snapshot_id)), None)
        current_margin = self._safe_float(metrics.get('netMarginRate') or selected_item.get('netMarginRate'))
        target_margin = self._safe_float(metrics.get('targetMarginRate') or selected_item.get('targetMarginRate') or current_margin)
        decision_hint = 'ready_for_manual_decision' if readiness.get('isReady') else 'review_only'
        return {
            'batchRef': str(batch_ref),
            'batchId': detail.get('batchId') or explain.get('batchId'),
            'snapshotId': int(detail.get('snapshotId') or snapshot_id),
            'snapshotVersion': self._safe_int(detail.get('snapshotVersion') or 1, 1),
            'savedSource': self._clean_str(detail.get('savedSource') or detail.get('source'), 'solve'),
            'canonicalSku': selected_canonical_sku,
            'contractVersion': self.DECISION_CONTRACT_VERSION,
            'decisionHint': decision_hint,
            'headline': {
                'recommendedPrice': round(self._safe_float(metrics.get('recommendedPrice') or selected_item.get('recommendedPrice')), 4),
                'targetMargin': round(target_margin, 4),
                'currentMargin': round(current_margin, 4),
                'deltaToTarget': round(target_margin - current_margin, 4),
            },
            'readiness': {
                'isReady': bool(readiness.get('isReady')),
                'reviewLevel': self._clean_str(readiness.get('reviewLevel'), 'normal'),
                'confidence': self._clean_str(readiness.get('confidence'), 'low'),
                'blockingReasons': list(readiness.get('blockingReasons') or []),
                'requiredFields': list(readiness.get('requiredFields') or []),
            },
            'constraints': constraints,
            'risks': risks,
            'metrics': metrics,
            'timelineSummary': {
                'available': bool(timeline_items),
                'currentSnapshotId': int(detail.get('snapshotId') or snapshot_id),
                'latestPreviousSnapshotId': previous_entry.get('snapshotId') if previous_entry else None,
                'changeHints': list(current_entry.get('changeHints') or []),
            },
            'compareEntry': {
                'available': previous_entry is not None,
                'latestPreviousSnapshotId': previous_entry.get('snapshotId') if previous_entry else None,
            },
        }
