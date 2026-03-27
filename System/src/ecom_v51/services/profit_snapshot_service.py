from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from ecom_v51.db.models import ReportSnapshot
from ecom_v51.db.session import get_session
from ecom_v51.services.economics_intake_service import EconomicsIntakeService


class ProfitSnapshotService:
    CONTRACT_VERSION = 'p4.profit_snapshot.v1'
    DETAIL_CONTRACT_VERSION = 'p4.profit_snapshot_detail.v1'
    EXPLAIN_CONTRACT_VERSION = 'p4.profit_snapshot_explain.v1'
    COMPARE_CONTRACT_VERSION = 'p4.profit_snapshot_compare.v1'
    EXPLAIN_DIFF_CONTRACT_VERSION = 'p4.profit_snapshot_explain_diff.v1'
    TIMELINE_CONTRACT_VERSION = 'p4.profit_snapshot_timeline.v1'
    REVIEW_CONTRACT_VERSION = 'p4.profit_snapshot_review_surface.v1'
    EXPLAIN_SCHEMA_VERSION = 'p4.6.explain.v1'
    REPORT_TYPE = 'economics_profit_snapshot_v1'
    ALLOWED_SOURCES = {'solve', 'pricing_recommend'}

    def __init__(self, root_dir: Path, *, economics_service: EconomicsIntakeService | None = None) -> None:
        self.root_dir = Path(root_dir)
        self.economics_service = economics_service or EconomicsIntakeService(self.root_dir)

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

    def _resolve_state(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        return self.economics_service._load_state(batch_ref)

    def _resolve_shop_id(self, state: Dict[str, Any], payload: Dict[str, Any]) -> int:
        detail = dict(state.get('detail') or {})
        if detail.get('shopId') is not None:
            return int(detail['shopId'])
        first_item = next(iter(payload.get('items') or []), {})
        if first_item.get('shopId') is not None:
            return int(first_item['shopId'])
        return 1

    def _build_source_payload(self, batch_ref: str, *, source: str, filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
        safe_filters = dict(filters or {})
        limit = max(min(int(safe_filters.get('limit') or 200), 500), 1)
        offset = max(int(safe_filters.get('offset') or 0), 0)
        view = self._clean_str(safe_filters.get('view'), 'all')
        if source == 'solve':
            return self.economics_service.get_batch_profit_solve(batch_ref, limit=limit, offset=offset, view=view) or {}
        if source == 'pricing_recommend':
            strategy_mode = self._clean_str(safe_filters.get('strategyMode'), 'balanced_profit')
            constraints = safe_filters.get('constraints') or {'minMargin': safe_filters.get('minMargin') or 0.08}
            return self.economics_service.get_batch_pricing_recommend(
                batch_ref,
                strategy_mode=strategy_mode,
                constraints=constraints,
                limit=limit,
                offset=offset,
                view=view,
            ) or {}
        raise ValueError('unsupported_snapshot_source')

    def _build_summary(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        items = list(payload.get('items') or [])
        sku_values = {self._clean_str(item.get('canonicalSku')) for item in items if self._clean_str(item.get('canonicalSku'))}
        margin_values = [
            self._safe_float(item.get('netMarginRate'))
            for item in items
            if item.get('netMarginRate') is not None
        ]
        avg_margin = round((sum(margin_values) / len(margin_values)) if margin_values else self._safe_float((payload.get('solveSummary') or {}).get('netMarginRate')), 4)
        loss_sku_count = sum(
            1
            for item in items
            if self._safe_float(item.get('riskAdjustedProfit')) < 0 or self._safe_float(item.get('netMarginRate')) < 0
        )
        first_item = next(iter(items), {})
        return {
            'skuCount': len(sku_values),
            'avgMargin': avg_margin,
            'lossSkuCount': loss_sku_count,
            'currency': first_item.get('currencyCode') or 'CNY',
            'itemCount': len(items),
        }

    def _build_snapshot_key(self, batch_ref: str, *, source: str, profile_code: str) -> str:
        return f'{self._clean_str(batch_ref)}::{self._clean_str(source)}::{self._clean_str(profile_code, "default_profit_v1")}'

    def _iter_matching_snapshot_rows(self, rows: Iterable[ReportSnapshot], batch_ref: str, snapshot_key: str) -> Iterable[ReportSnapshot]:
        for row in rows:
            content = dict(row.content_json or {})
            if str(content.get('batchRef') or '') != str(batch_ref):
                continue
            existing_source = self._clean_str(content.get('savedSource') or content.get('source'), 'solve')
            existing_profile = self._clean_str(content.get('profileCode'), 'default_profit_v1')
            existing_key = self._clean_str(content.get('snapshotKey')) or self._build_snapshot_key(batch_ref, source=existing_source, profile_code=existing_profile)
            if existing_key == snapshot_key:
                yield row

    def _allocate_snapshot_version(
        self,
        *,
        batch_ref: str,
        shop_id: int,
        snapshot_key: str,
    ) -> tuple[int, int | None]:
        with get_session() as session:
            rows = (
                session.query(ReportSnapshot)
                .filter(ReportSnapshot.report_type == self.REPORT_TYPE, ReportSnapshot.shop_id == shop_id)
                .order_by(ReportSnapshot.generated_at.desc(), ReportSnapshot.id.desc())
                .all()
            )
        max_version = 0
        derived_from_snapshot_id: int | None = None
        for row in self._iter_matching_snapshot_rows(rows, batch_ref, snapshot_key):
            content = dict(row.content_json or {})
            version = self._safe_int(content.get('snapshotVersion') or 1, 1)
            if version >= max_version:
                max_version = version
                derived_from_snapshot_id = int(row.id)
        return max_version + 1, derived_from_snapshot_id

    @staticmethod
    def _copy_item(item: Dict[str, Any]) -> Dict[str, Any]:
        copied = dict(item or {})
        explanation = copied.get('explanation')
        if isinstance(explanation, dict):
            copied['explanation'] = dict(explanation)
        risks = copied.get('risks')
        if isinstance(risks, list):
            copied['risks'] = list(risks)
        return copied

    def _normalize_reason_list(self, value: Any, *, fallback: str) -> list[Dict[str, Any]]:
        if isinstance(value, list):
            normalized = []
            for entry in value:
                if isinstance(entry, dict):
                    normalized.append({
                        'code': self._clean_str(entry.get('code'), 'free_text'),
                        'message': self._clean_str(entry.get('message') or entry.get('summary') or entry.get('reason'), fallback),
                    })
                else:
                    normalized.append({'code': 'free_text', 'message': self._clean_str(entry, fallback)})
            if normalized:
                return normalized
        if isinstance(value, dict):
            return [{
                'code': self._clean_str(value.get('code'), 'free_text'),
                'message': self._clean_str(value.get('message') or value.get('summary') or value.get('reason'), fallback),
            }]
        text = self._clean_str(value, fallback)
        return [{'code': 'free_text', 'message': text}]

    def _normalize_risks(self, value: Any) -> list[Dict[str, Any]]:
        risks = []
        for entry in list(value or []):
            if isinstance(entry, dict):
                risks.append({
                    'code': self._clean_str(entry.get('code') or entry.get('type'), 'risk'),
                    'message': self._clean_str(entry.get('message') or entry.get('summary') or entry.get('reason'), 'risk'),
                })
            else:
                risks.append({'code': 'risk', 'message': self._clean_str(entry, 'risk')})
        return risks

    def _build_constraints(self, *, floor_price: float, ceiling_price: float, recommended_price: float) -> list[Dict[str, Any]]:
        constraints: list[Dict[str, Any]] = []
        if floor_price > 0:
            constraints.append({
                'code': 'floor_price_guard',
                'active': recommended_price <= floor_price,
                'value': floor_price,
            })
        if ceiling_price > 0:
            constraints.append({
                'code': 'ceiling_price_guard',
                'active': recommended_price >= ceiling_price,
                'value': ceiling_price,
            })
        return constraints

    def _build_explain_consistency(self, selected: Dict[str, Any]) -> Dict[str, Any]:
        explanation = dict(selected.get('explanation') or {})
        risks = self._normalize_risks(selected.get('risks') or [])
        current_unit_price = round(self._safe_float(selected.get('currentUnitPrice')), 4)
        floor_price = round(self._safe_float(selected.get('floorPrice')), 4)
        target_price = round(self._safe_float(selected.get('targetPrice')), 4)
        ceiling_price = round(self._safe_float(selected.get('ceilingPrice')), 4)
        recommended_price = round(self._safe_float(selected.get('recommendedPrice')), 4)
        net_margin_rate = round(self._safe_float(selected.get('netMarginRate')), 4)
        risk_adjusted_profit = round(self._safe_float(selected.get('riskAdjustedProfit')), 4)
        profit_confidence = round(self._safe_float(selected.get('profitConfidence')), 4)

        why_not_lower = self._normalize_reason_list(
            explanation.get('whyNotLower'),
            fallback='缺少 whyNotLower 解释。',
        )
        why_not_higher = self._normalize_reason_list(
            explanation.get('whyNotHigher'),
            fallback='缺少 whyNotHigher 解释。',
        )
        return {
            'explainSchemaVersion': self.EXPLAIN_SCHEMA_VERSION,
            'whyNotLower': why_not_lower,
            'whyNotHigher': why_not_higher,
            'constraints': self._build_constraints(
                floor_price=floor_price,
                ceiling_price=ceiling_price,
                recommended_price=recommended_price,
            ),
            'risks': risks,
            'metrics': {
                'currentUnitPrice': current_unit_price,
                'floorPrice': floor_price,
                'targetPrice': target_price,
                'ceilingPrice': ceiling_price,
                'recommendedPrice': recommended_price,
                'netMarginRate': net_margin_rate,
                'riskAdjustedProfit': risk_adjusted_profit,
                'profitConfidence': profit_confidence,
            },
        }

    def save_batch_profit_snapshot(
        self,
        batch_ref: str,
        *,
        source: str = 'solve',
        operator: str = 'frontend_user',
        note: str | None = None,
        filters: Dict[str, Any] | None = None,
    ) -> Optional[Dict[str, Any]]:
        normalized_source = self._clean_str(source, 'solve')
        if normalized_source not in self.ALLOWED_SOURCES:
            raise ValueError('unsupported_snapshot_source')
        state = self._resolve_state(batch_ref)
        if not state:
            return None
        payload = self._build_source_payload(batch_ref, source=normalized_source, filters=filters)
        if not payload:
            return None
        batch_id = int(state['batchId'])
        shop_id = self._resolve_shop_id(state, payload)
        summary = self._build_summary(payload)
        profile_code = (
            self._clean_str((payload.get('configResolveSummary') or {}).get('defaultProfileCode'))
            or self._clean_str(next(iter(payload.get('items') or []), {}).get('resolvedProfileCode'))
            or 'default_profit_v1'
        )
        snapshot_key = self._build_snapshot_key(batch_ref, source=normalized_source, profile_code=profile_code)
        snapshot_version, derived_from_snapshot_id = self._allocate_snapshot_version(
            batch_ref=batch_ref,
            shop_id=shop_id,
            snapshot_key=snapshot_key,
        )
        generated_at = datetime.now(timezone.utc)
        content_json = {
            'contractVersion': self.CONTRACT_VERSION,
            'batchRef': str(batch_ref),
            'batchId': batch_id,
            'source': normalized_source,
            'savedSource': normalized_source,
            'profileCode': profile_code,
            'operator': self._clean_str(operator, 'frontend_user'),
            'note': self._clean_str(note),
            'filters': dict(filters or {}),
            'summary': summary,
            'payload': payload,
            'snapshotVersion': snapshot_version,
            'snapshotKey': snapshot_key,
            'derivedFromSnapshotId': derived_from_snapshot_id,
            'explainSchemaVersion': self.EXPLAIN_SCHEMA_VERSION,
        }
        with get_session() as session:
            row = ReportSnapshot(
                shop_id=shop_id,
                report_type=self.REPORT_TYPE,
                report_date=date.today(),
                content_md=self._clean_str(note) or f'batch_{batch_id}_{normalized_source}_snapshot_v{snapshot_version}',
                content_json=content_json,
                generated_at=generated_at,
            )
            session.add(row)
            session.flush()
            return {
                'batchRef': str(batch_ref),
                'batchId': batch_id,
                'contractVersion': self.CONTRACT_VERSION,
                'snapshotId': row.id,
                'snapshotVersion': snapshot_version,
                'snapshotKey': snapshot_key,
                'derivedFromSnapshotId': derived_from_snapshot_id,
                'savedSource': normalized_source,
                'explainSchemaVersion': self.EXPLAIN_SCHEMA_VERSION,
                'source': normalized_source,
                'profileCode': profile_code,
                'savedAt': generated_at.isoformat(),
                'itemCount': summary['itemCount'],
                'summary': {
                    'skuCount': summary['skuCount'],
                    'avgMargin': summary['avgMargin'],
                    'lossSkuCount': summary['lossSkuCount'],
                    'currency': summary['currency'],
                },
            }

    def _load_snapshot_row(self, batch_ref: str, snapshot_id: int):
        state = self._resolve_state(batch_ref)
        if not state:
            return None, None
        shop_id = int((state.get('detail') or {}).get('shopId') or 1)
        with get_session() as session:
            row = (
                session.query(ReportSnapshot)
                .filter(
                    ReportSnapshot.id == int(snapshot_id),
                    ReportSnapshot.report_type == self.REPORT_TYPE,
                    ReportSnapshot.shop_id == shop_id,
                )
                .one_or_none()
            )
        if row is None:
            return state, None
        content = dict(row.content_json or {})
        if str(content.get('batchRef') or '') != str(batch_ref):
            return state, None
        return state, row

    def get_batch_profit_snapshot_detail(self, batch_ref: str, snapshot_id: int) -> Optional[Dict[str, Any]]:
        state, row = self._load_snapshot_row(batch_ref, snapshot_id)
        if not state or row is None:
            return None
        batch_id = int(state['batchId'])
        content = dict(row.content_json or {})
        payload = dict(content.get('payload') or {})
        raw_items = list(payload.get('items') or [])
        items = [self._copy_item(item) for item in raw_items]
        summary = dict(content.get('summary') or {})
        readiness = {
            'itemCount': len(items),
            'recommendationReadyRowCount': sum(1 for item in items if item.get('recommendationReady') is True),
            'fallbackRowCount': sum(1 for item in items if self._clean_str(item.get('solveSourceMode')) == 'import_partial_fallback'),
            'configBoundRowCount': sum(1 for item in items if self._clean_str(item.get('solveSourceMode')) == 'config_resolve'),
        }
        snapshot_version = self._safe_int(content.get('snapshotVersion') or 1, 1)
        snapshot_key = self._clean_str(content.get('snapshotKey')) or self._build_snapshot_key(
            batch_ref,
            source=self._clean_str(content.get('savedSource') or content.get('source'), 'solve'),
            profile_code=self._clean_str(content.get('profileCode'), 'default_profit_v1'),
        )
        explain_schema_version = self._clean_str(content.get('explainSchemaVersion'), self.EXPLAIN_SCHEMA_VERSION)
        return {
            'batchRef': str(batch_ref),
            'batchId': int(content.get('batchId') or batch_id),
            'snapshotId': row.id,
            'snapshotVersion': snapshot_version,
            'snapshotKey': snapshot_key,
            'derivedFromSnapshotId': content.get('derivedFromSnapshotId'),
            'savedSource': self._clean_str(content.get('savedSource') or content.get('source'), 'solve'),
            'explainSchemaVersion': explain_schema_version,
            'contractVersion': self.DETAIL_CONTRACT_VERSION,
            'source': self._clean_str(content.get('source'), 'solve'),
            'profileCode': self._clean_str(content.get('profileCode'), 'default_profit_v1'),
            'savedAt': row.generated_at.isoformat() if row.generated_at else None,
            'operator': self._clean_str(content.get('operator'), 'frontend_user'),
            'note': self._clean_str(content.get('note')),
            'filters': dict(content.get('filters') or {}),
            'summary': {
                'skuCount': int(summary.get('skuCount') or 0),
                'avgMargin': round(self._safe_float(summary.get('avgMargin')), 4),
                'lossSkuCount': int(summary.get('lossSkuCount') or 0),
                'currency': self._clean_str(summary.get('currency'), 'CNY'),
                'itemCount': int(summary.get('itemCount') or len(items)),
            },
            'readiness': readiness,
            'items': items,
        }

    def get_batch_profit_snapshot_explain(
        self,
        batch_ref: str,
        snapshot_id: int,
        *,
        canonical_sku: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        detail = self.get_batch_profit_snapshot_detail(batch_ref, snapshot_id)
        if not detail:
            return None
        items = list(detail.get('items') or [])
        selected = None
        normalized_sku = self._clean_str(canonical_sku)
        if normalized_sku:
            selected = next((item for item in items if self._clean_str(item.get('canonicalSku')) == normalized_sku), None)
        if selected is None and items:
            selected = items[0]
        if selected is None:
            return {
                'batchRef': detail['batchRef'],
                'batchId': detail['batchId'],
                'snapshotId': detail['snapshotId'],
                'snapshotVersion': detail['snapshotVersion'],
                'snapshotKey': detail['snapshotKey'],
                'explainSchemaVersion': detail['explainSchemaVersion'],
                'contractVersion': self.EXPLAIN_CONTRACT_VERSION,
                'source': detail['source'],
                'profileCode': detail['profileCode'],
                'requestedCanonicalSku': normalized_sku or None,
                'selectedCanonicalSku': None,
                'explanationReady': False,
                'reason': 'snapshot_items_empty',
                'consistency': {
                    'explainSchemaVersion': detail['explainSchemaVersion'],
                    'whyNotLower': [],
                    'whyNotHigher': [],
                    'constraints': [],
                    'risks': [],
                    'metrics': {},
                },
            }
        consistency = self._build_explain_consistency(selected)
        explanation = dict(selected.get('explanation') or {})
        metrics = dict(consistency.get('metrics') or {})
        return {
            'batchRef': detail['batchRef'],
            'batchId': detail['batchId'],
            'snapshotId': detail['snapshotId'],
            'snapshotVersion': detail['snapshotVersion'],
            'snapshotKey': detail['snapshotKey'],
            'derivedFromSnapshotId': detail.get('derivedFromSnapshotId'),
            'explainSchemaVersion': detail['explainSchemaVersion'],
            'contractVersion': self.EXPLAIN_CONTRACT_VERSION,
            'source': detail['source'],
            'profileCode': detail['profileCode'],
            'requestedCanonicalSku': normalized_sku or None,
            'selectedCanonicalSku': self._clean_str(selected.get('canonicalSku')) or None,
            'explanationReady': True,
            'recommendationState': self._clean_str(selected.get('recommendationState')),
            'solveSourceMode': self._clean_str(selected.get('solveSourceMode')),
            'dominantRiskDriver': self._clean_str(selected.get('dominantRiskDriver')),
            'priceContext': {
                'currentUnitPrice': metrics.get('currentUnitPrice', 0.0),
                'floorPrice': metrics.get('floorPrice', 0.0),
                'targetPrice': metrics.get('targetPrice', 0.0),
                'ceilingPrice': metrics.get('ceilingPrice', 0.0),
                'recommendedPrice': metrics.get('recommendedPrice', 0.0),
            },
            'economicsContext': {
                'netMarginRate': metrics.get('netMarginRate', 0.0),
                'riskAdjustedProfit': metrics.get('riskAdjustedProfit', 0.0),
                'profitConfidence': metrics.get('profitConfidence', 0.0),
            },
            'explanation': {
                'summary': self._clean_str(explanation.get('summary')) or '当前快照未提供 explanation summary。',
                'whyNotLower': self._clean_str(explanation.get('whyNotLower')) or '缺少 whyNotLower 解释。',
                'whyNotHigher': self._clean_str(explanation.get('whyNotHigher')) or '缺少 whyNotHigher 解释。',
            },
            'risks': consistency['risks'],
            'consistency': consistency,
        }

    def _index_items_by_sku(self, items: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        indexed: Dict[str, Dict[str, Any]] = {}
        for item in list(items or []):
            canonical_sku = self._clean_str((item or {}).get('canonicalSku'))
            if canonical_sku and canonical_sku not in indexed:
                indexed[canonical_sku] = self._copy_item(item)
        return indexed

    def _select_compare_sku(
        self,
        *,
        requested: str | None,
        left_index: Dict[str, Dict[str, Any]],
        right_index: Dict[str, Dict[str, Any]],
    ) -> str | None:
        normalized_requested = self._clean_str(requested)
        if normalized_requested:
            return normalized_requested
        common = [sku for sku in right_index.keys() if sku in left_index]
        if common:
            return common[0]
        if right_index:
            return next(iter(right_index.keys()))
        if left_index:
            return next(iter(left_index.keys()))
        return None

    def _extract_item_metrics(self, item: Dict[str, Any] | None) -> Dict[str, Any]:
        if not item:
            return {}
        return {
            'currentUnitPrice': round(self._safe_float(item.get('currentUnitPrice')), 4),
            'floorPrice': round(self._safe_float(item.get('floorPrice')), 4),
            'targetPrice': round(self._safe_float(item.get('targetPrice')), 4),
            'ceilingPrice': round(self._safe_float(item.get('ceilingPrice')), 4),
            'recommendedPrice': round(self._safe_float(item.get('recommendedPrice')), 4),
            'netMarginRate': round(self._safe_float(item.get('netMarginRate')), 4),
            'riskAdjustedProfit': round(self._safe_float(item.get('riskAdjustedProfit')), 4),
            'profitConfidence': round(self._safe_float(item.get('profitConfidence')), 4),
        }

    def _diff_metric_maps(self, left_metrics: Dict[str, Any], right_metrics: Dict[str, Any]) -> Dict[str, Any]:
        keys = list(dict.fromkeys([*left_metrics.keys(), *right_metrics.keys()]))
        delta: Dict[str, Any] = {}
        for key in keys:
            left_value = self._safe_float(left_metrics.get(key))
            right_value = self._safe_float(right_metrics.get(key))
            delta[key] = round(right_value - left_value, 4)
        return delta

    def _normalize_text(self, value: Any) -> str:
        if isinstance(value, list):
            messages = []
            for entry in value:
                if isinstance(entry, dict):
                    message = self._clean_str(entry.get('message') or entry.get('summary') or entry.get('reason'))
                else:
                    message = self._clean_str(entry)
                if message:
                    messages.append(message)
            return ' | '.join(messages)
        if isinstance(value, dict):
            return self._clean_str(value.get('message') or value.get('summary') or value.get('reason'))
        return self._clean_str(value)

    def _normalize_reason_messages(self, value: Any) -> list[str]:
        normalized = []
        for entry in self._normalize_reason_list(value, fallback=''):
            message = self._clean_str(entry.get('message'))
            if message:
                normalized.append(message)
        return normalized

    def _normalize_risk_messages(self, value: Any) -> list[str]:
        normalized = []
        for entry in self._normalize_risks(value):
            message = self._clean_str(entry.get('message'))
            if message:
                normalized.append(message)
        return normalized

    def _build_snapshot_meta(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'snapshotId': payload.get('snapshotId'),
            'snapshotVersion': self._safe_int(payload.get('snapshotVersion') or 1, 1),
            'snapshotKey': self._clean_str(payload.get('snapshotKey')),
            'savedSource': self._clean_str(payload.get('savedSource') or payload.get('source'), 'solve'),
            'source': self._clean_str(payload.get('source'), 'solve'),
            'profileCode': self._clean_str(payload.get('profileCode'), 'default_profit_v1'),
            'savedAt': payload.get('savedAt'),
        }

    def get_batch_profit_snapshot_compare(
        self,
        batch_ref: str,
        left_snapshot_id: int,
        right_snapshot_id: int,
        *,
        canonical_sku: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        left_detail = self.get_batch_profit_snapshot_detail(batch_ref, left_snapshot_id)
        right_detail = self.get_batch_profit_snapshot_detail(batch_ref, right_snapshot_id)
        if not left_detail or not right_detail:
            return None
        left_index = self._index_items_by_sku(left_detail.get('items') or [])
        right_index = self._index_items_by_sku(right_detail.get('items') or [])
        selected_sku = self._select_compare_sku(requested=canonical_sku, left_index=left_index, right_index=right_index)
        left_item = left_index.get(selected_sku or '') if selected_sku else None
        right_item = right_index.get(selected_sku or '') if selected_sku else None
        left_metrics = self._extract_item_metrics(left_item)
        right_metrics = self._extract_item_metrics(right_item)
        left_summary = dict(left_detail.get('summary') or {})
        right_summary = dict(right_detail.get('summary') or {})
        sku_union = set(left_index.keys()) | set(right_index.keys())
        sku_added = sorted(set(right_index.keys()) - set(left_index.keys()))
        sku_removed = sorted(set(left_index.keys()) - set(right_index.keys()))
        changed_fields = []
        if left_summary.get('avgMargin') != right_summary.get('avgMargin'):
            changed_fields.append('summary.avgMargin')
        if left_summary.get('lossSkuCount') != right_summary.get('lossSkuCount'):
            changed_fields.append('summary.lossSkuCount')
        if left_metrics.get('recommendedPrice') != right_metrics.get('recommendedPrice'):
            changed_fields.append('selectedItem.recommendedPrice')
        if left_metrics.get('riskAdjustedProfit') != right_metrics.get('riskAdjustedProfit'):
            changed_fields.append('selectedItem.riskAdjustedProfit')
        return {
            'batchRef': str(batch_ref),
            'batchId': right_detail.get('batchId') or left_detail.get('batchId'),
            'contractVersion': self.COMPARE_CONTRACT_VERSION,
            'requestedCanonicalSku': self._clean_str(canonical_sku) or None,
            'selectedCanonicalSku': selected_sku,
            'leftSnapshot': self._build_snapshot_meta(left_detail),
            'rightSnapshot': self._build_snapshot_meta(right_detail),
            'summaryComparison': {
                'left': {
                    'skuCount': int(left_summary.get('skuCount') or 0),
                    'avgMargin': round(self._safe_float(left_summary.get('avgMargin')), 4),
                    'lossSkuCount': int(left_summary.get('lossSkuCount') or 0),
                    'currency': self._clean_str(left_summary.get('currency'), 'CNY'),
                    'itemCount': int(left_summary.get('itemCount') or 0),
                },
                'right': {
                    'skuCount': int(right_summary.get('skuCount') or 0),
                    'avgMargin': round(self._safe_float(right_summary.get('avgMargin')), 4),
                    'lossSkuCount': int(right_summary.get('lossSkuCount') or 0),
                    'currency': self._clean_str(right_summary.get('currency'), 'CNY'),
                    'itemCount': int(right_summary.get('itemCount') or 0),
                },
                'delta': {
                    'skuCount': int(right_summary.get('skuCount') or 0) - int(left_summary.get('skuCount') or 0),
                    'avgMargin': round(self._safe_float(right_summary.get('avgMargin')) - self._safe_float(left_summary.get('avgMargin')), 4),
                    'lossSkuCount': int(right_summary.get('lossSkuCount') or 0) - int(left_summary.get('lossSkuCount') or 0),
                    'itemCount': int(right_summary.get('itemCount') or 0) - int(left_summary.get('itemCount') or 0),
                },
            },
            'selection': {
                'leftPresent': left_item is not None,
                'rightPresent': right_item is not None,
                'sharedCanonicalSkuCount': len(set(left_index.keys()) & set(right_index.keys())),
                'skuAdded': sku_added,
                'skuRemoved': sku_removed,
                'skuUnionCount': len(sku_union),
            },
            'selectedItemComparison': {
                'left': left_metrics,
                'right': right_metrics,
                'delta': self._diff_metric_maps(left_metrics, right_metrics),
            },
            'changedFields': changed_fields,
        }

    def get_batch_profit_snapshot_explain_diff(
        self,
        batch_ref: str,
        left_snapshot_id: int,
        right_snapshot_id: int,
        *,
        canonical_sku: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        left_explain = self.get_batch_profit_snapshot_explain(batch_ref, left_snapshot_id, canonical_sku=canonical_sku)
        right_explain = self.get_batch_profit_snapshot_explain(batch_ref, right_snapshot_id, canonical_sku=canonical_sku)
        if not left_explain or not right_explain:
            return None
        left_consistency = dict(left_explain.get('consistency') or {})
        right_consistency = dict(right_explain.get('consistency') or {})
        left_why_not_lower = self._normalize_reason_messages((left_explain.get('explanation') or {}).get('whyNotLower') or left_consistency.get('whyNotLower'))
        right_why_not_lower = self._normalize_reason_messages((right_explain.get('explanation') or {}).get('whyNotLower') or right_consistency.get('whyNotLower'))
        left_why_not_higher = self._normalize_reason_messages((left_explain.get('explanation') or {}).get('whyNotHigher') or left_consistency.get('whyNotHigher'))
        right_why_not_higher = self._normalize_reason_messages((right_explain.get('explanation') or {}).get('whyNotHigher') or right_consistency.get('whyNotHigher'))
        left_risks = self._normalize_risk_messages(left_explain.get('risks') or left_consistency.get('risks'))
        right_risks = self._normalize_risk_messages(right_explain.get('risks') or right_consistency.get('risks'))
        left_metrics = dict(left_consistency.get('metrics') or {})
        right_metrics = dict(right_consistency.get('metrics') or {})
        return {
            'batchRef': str(batch_ref),
            'batchId': right_explain.get('batchId') or left_explain.get('batchId'),
            'contractVersion': self.EXPLAIN_DIFF_CONTRACT_VERSION,
            'selectedCanonicalSku': right_explain.get('selectedCanonicalSku') or left_explain.get('selectedCanonicalSku'),
            'leftSnapshot': self._build_snapshot_meta(left_explain),
            'rightSnapshot': self._build_snapshot_meta(right_explain),
            'explainSchemaVersion': self._clean_str(right_explain.get('explainSchemaVersion') or right_consistency.get('explainSchemaVersion'), self.EXPLAIN_SCHEMA_VERSION),
            'summary': {
                'left': self._normalize_text((left_explain.get('explanation') or {}).get('summary')),
                'right': self._normalize_text((right_explain.get('explanation') or {}).get('summary')),
                'changed': self._normalize_text((left_explain.get('explanation') or {}).get('summary')) != self._normalize_text((right_explain.get('explanation') or {}).get('summary')),
            },
            'whyNotLower': {
                'left': left_why_not_lower,
                'right': right_why_not_lower,
                'changed': left_why_not_lower != right_why_not_lower,
            },
            'whyNotHigher': {
                'left': left_why_not_higher,
                'right': right_why_not_higher,
                'changed': left_why_not_higher != right_why_not_higher,
            },
            'riskDiff': {
                'left': left_risks,
                'right': right_risks,
                'added': [risk for risk in right_risks if risk not in left_risks],
                'removed': [risk for risk in left_risks if risk not in right_risks],
            },
            'metricsDiff': {
                'left': left_metrics,
                'right': right_metrics,
                'delta': self._diff_metric_maps(left_metrics, right_metrics),
            },
        }

    def _extract_selected_item(self, detail: Dict[str, Any], canonical_sku: str | None = None) -> Dict[str, Any] | None:
        items = list((detail or {}).get('items') or [])
        normalized_sku = self._clean_str(canonical_sku)
        if normalized_sku:
            for item in items:
                if self._clean_str((item or {}).get('canonicalSku')) == normalized_sku:
                    return self._copy_item(item)
        if items:
            return self._copy_item(items[0])
        return None

    def get_batch_profit_snapshot_timeline(
        self,
        batch_ref: str,
        *,
        canonical_sku: str | None = None,
        limit: int = 50,
    ) -> Optional[Dict[str, Any]]:
        listed = self.list_batch_profit_snapshots(batch_ref, limit=max(min(int(limit or 50), 200), 1))
        if not listed:
            return None
        base_items = list(listed.get('items') or [])
        timeline_items = []
        previous_detail: Dict[str, Any] | None = None
        selected_canonical_sku = self._clean_str(canonical_sku) or None
        for base in reversed(base_items):
            detail = self.get_batch_profit_snapshot_detail(batch_ref, int(base.get('snapshotId') or 0))
            if not detail:
                continue
            selected_item = self._extract_selected_item(detail, canonical_sku=selected_canonical_sku)
            if selected_canonical_sku is None and selected_item is not None:
                selected_canonical_sku = self._clean_str(selected_item.get('canonicalSku')) or None
            summary = dict(detail.get('summary') or {})
            change_hints: list[str] = []
            if previous_detail is not None:
                prev_summary = dict(previous_detail.get('summary') or {})
                prev_item = self._extract_selected_item(previous_detail, canonical_sku=selected_canonical_sku)
                prev_price = self._safe_float((prev_item or {}).get('recommendedPrice'))
                curr_price = self._safe_float((selected_item or {}).get('recommendedPrice'))
                if round(curr_price - prev_price, 4) != 0:
                    direction = 'up' if curr_price > prev_price else 'down'
                    change_hints.append(f'recommendedPrice:{direction}')
                prev_margin = round(self._safe_float(prev_summary.get('avgMargin')), 4)
                curr_margin = round(self._safe_float(summary.get('avgMargin')), 4)
                if curr_margin != prev_margin:
                    direction = 'up' if curr_margin > prev_margin else 'down'
                    change_hints.append(f'avgMargin:{direction}')
                prev_loss = int(prev_summary.get('lossSkuCount') or 0)
                curr_loss = int(summary.get('lossSkuCount') or 0)
                if curr_loss != prev_loss:
                    direction = 'up' if curr_loss > prev_loss else 'down'
                    change_hints.append(f'lossSkuCount:{direction}')
            timeline_items.append({
                'snapshotId': int(detail.get('snapshotId') or 0),
                'snapshotVersion': self._safe_int(detail.get('snapshotVersion') or 1, 1),
                'snapshotKey': self._clean_str(detail.get('snapshotKey')),
                'savedSource': self._clean_str(detail.get('savedSource') or detail.get('source'), 'solve'),
                'derivedFromSnapshotId': detail.get('derivedFromSnapshotId'),
                'savedAt': detail.get('savedAt'),
                'profileCode': self._clean_str(detail.get('profileCode'), 'default_profit_v1'),
                'recommendedPrice': round(self._safe_float((selected_item or {}).get('recommendedPrice')), 4) if selected_item else 0.0,
                'avgMargin': round(self._safe_float(summary.get('avgMargin')), 4),
                'lossSkuCount': int(summary.get('lossSkuCount') or 0),
                'changeHints': change_hints,
            })
            previous_detail = detail
        return {
            'batchRef': str(batch_ref),
            'batchId': listed.get('batchId'),
            'contractVersion': self.TIMELINE_CONTRACT_VERSION,
            'canonicalSku': selected_canonical_sku,
            'items': timeline_items,
        }

    def get_batch_profit_snapshot_review_surface(
        self,
        batch_ref: str,
        snapshot_id: int,
        *,
        canonical_sku: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        detail = self.get_batch_profit_snapshot_detail(batch_ref, snapshot_id)
        explain = self.get_batch_profit_snapshot_explain(batch_ref, snapshot_id, canonical_sku=canonical_sku)
        if not detail or not explain:
            return None
        selected_item = self._extract_selected_item(detail, canonical_sku=explain.get('selectedCanonicalSku') or canonical_sku) or {}
        consistency = dict(explain.get('consistency') or {})
        metrics = dict(consistency.get('metrics') or {})
        risks = list(consistency.get('risks') or explain.get('risks') or [])
        constraints = list(consistency.get('constraints') or [])
        selected_canonical_sku = self._clean_str(explain.get('selectedCanonicalSku') or canonical_sku) or None
        risk_flags = [
            self._clean_str((entry or {}).get('code') or (entry or {}).get('message'))
            for entry in risks
            if self._clean_str((entry or {}).get('code') or (entry or {}).get('message'))
        ]
        return {
            'batchRef': str(batch_ref),
            'batchId': detail.get('batchId'),
            'snapshotId': detail.get('snapshotId'),
            'snapshotVersion': self._safe_int(detail.get('snapshotVersion') or 1, 1),
            'snapshotKey': self._clean_str(detail.get('snapshotKey')),
            'canonicalSku': selected_canonical_sku,
            'contractVersion': self.REVIEW_CONTRACT_VERSION,
            'savedSource': self._clean_str(detail.get('savedSource') or detail.get('source'), 'solve'),
            'pricing': {
                'floorPrice': round(self._safe_float(metrics.get('floorPrice') or selected_item.get('floorPrice')), 4),
                'targetPrice': round(self._safe_float(metrics.get('targetPrice') or selected_item.get('targetPrice')), 4),
                'ceilingPrice': round(self._safe_float(metrics.get('ceilingPrice') or selected_item.get('ceilingPrice')), 4),
                'recommendedPrice': round(self._safe_float(metrics.get('recommendedPrice') or selected_item.get('recommendedPrice')), 4),
            },
            'profit': {
                'grossMargin': round(self._safe_float(selected_item.get('grossMarginRate')), 4),
                'contributionMargin': round(self._safe_float(selected_item.get('contributionMarginRate')), 4),
                'netMargin': round(self._safe_float(metrics.get('netMarginRate') or selected_item.get('netMarginRate')), 4),
            },
            'explanation': {
                'whyNotLower': list(consistency.get('whyNotLower') or []),
                'whyNotHigher': list(consistency.get('whyNotHigher') or []),
                'constraints': constraints,
                'risks': risks,
                'metrics': metrics,
            },
            'reviewSurface': {
                'summary': self._clean_str(((explain.get('explanation') or {}).get('summary')), '当前快照未提供 review summary。'),
                'decisionHints': [
                    self._clean_str(explain.get('recommendationState')) or 'review_required',
                    self._clean_str(explain.get('dominantRiskDriver')) or 'risk_check',
                ],
                'riskFlags': risk_flags,
                'source': self._clean_str(detail.get('savedSource') or detail.get('source'), 'solve'),
            },
        }

    def list_batch_profit_snapshots(self, batch_ref: str, *, limit: int = 20) -> Optional[Dict[str, Any]]:
        state = self._resolve_state(batch_ref)
        if not state:
            return None
        batch_id = int(state['batchId'])
        safe_limit = max(min(int(limit or 20), 200), 1)
        shop_id = int((state.get('detail') or {}).get('shopId') or 1)
        with get_session() as session:
            rows = (
                session.query(ReportSnapshot)
                .filter(ReportSnapshot.report_type == self.REPORT_TYPE, ReportSnapshot.shop_id == shop_id)
                .order_by(ReportSnapshot.generated_at.desc(), ReportSnapshot.id.desc())
                .all()
            )
        filtered = [
            row for row in rows
            if str((row.content_json or {}).get('batchRef') or '') == str(batch_ref)
        ]
        items = []
        for row in filtered[:safe_limit]:
            content = dict(row.content_json or {})
            summary = dict(content.get('summary') or {})
            source = self._clean_str(content.get('savedSource') or content.get('source'), 'solve')
            profile_code = self._clean_str(content.get('profileCode'), 'default_profit_v1')
            items.append({
                'snapshotId': row.id,
                'snapshotVersion': self._safe_int(content.get('snapshotVersion') or 1, 1),
                'snapshotKey': self._clean_str(content.get('snapshotKey')) or self._build_snapshot_key(batch_ref, source=source, profile_code=profile_code),
                'savedSource': source,
                'explainSchemaVersion': self._clean_str(content.get('explainSchemaVersion'), self.EXPLAIN_SCHEMA_VERSION),
                'batchRef': str(batch_ref),
                'batchId': int(content.get('batchId') or batch_id),
                'source': self._clean_str(content.get('source'), 'solve'),
                'profileCode': profile_code,
                'savedAt': row.generated_at.isoformat() if row.generated_at else None,
                'itemCount': int(summary.get('itemCount') or 0),
                'summary': {
                    'skuCount': int(summary.get('skuCount') or 0),
                    'avgMargin': round(self._safe_float(summary.get('avgMargin')), 4),
                    'lossSkuCount': int(summary.get('lossSkuCount') or 0),
                    'currency': self._clean_str(summary.get('currency'), 'CNY'),
                },
            })
        return {
            'batchRef': str(batch_ref),
            'batchId': batch_id,
            'contractVersion': self.CONTRACT_VERSION,
            'pagination': {
                'limit': safe_limit,
                'returned': len(items),
                'total': len(filtered),
                'hasMore': len(filtered) > len(items),
            },
            'items': items,
        }
