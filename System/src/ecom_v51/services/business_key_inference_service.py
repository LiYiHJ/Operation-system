from __future__ import annotations

from typing import Any, Dict, List


class BusinessKeyInferenceService:
    STRATEGIES = {
        'orders': [
            ('sku', ['sku']),
            ('seller_sku', ['seller_sku']),
            ('offer_id', ['offer_id']),
            ('platform_sku', ['platform_sku']),
            ('order_id+line_no', ['order_id', 'line_no']),
            ('surrogate(order_id,item_name,amount,date)', ['order_id', 'item_name', 'amount', 'date']),
        ],
        'ads': [
            ('sku', ['sku']),
            ('campaign_id+ad_group_id+date', ['campaign_id', 'ad_group_id', 'date']),
            ('campaign_id+keyword+date', ['campaign_id', 'keyword', 'date']),
            ('surrogate(campaign_name,spend,date)', ['campaign_name', 'spend', 'date']),
        ],
        'reviews': [
            ('sku', ['sku']),
            ('product_id', ['product_id']),
            ('review_id', ['review_id']),
            ('product_id+review_date+rating', ['product_id', 'review_date', 'rating']),
        ],
    }

    @staticmethod
    def _norm(value: Any) -> str:
        return str(value or '').strip().lower().replace('-', '_').replace(' ', '_')

    @classmethod
    def _mapped_fields(cls, payload: Dict[str, Any]) -> set[str]:
        names: set[str] = set()
        for item in list(payload.get('fieldMappings') or []):
            if not isinstance(item, dict):
                continue
            for key in ('targetField', 'standardField'):
                value = cls._norm(item.get(key))
                if value:
                    names.add(value)
        return names

    @classmethod
    def infer_candidates(cls, *, dataset_kind: str, payload: Dict[str, Any], limit: int = 4) -> List[Dict[str, Any]]:
        dataset_kind = cls._norm(dataset_kind or payload.get('datasetKind') or 'orders')
        field_names = cls._mapped_fields(payload)
        strategies = cls.STRATEGIES.get(dataset_kind) or [('sku', ['sku']), ('surrogate', ['date'])]
        items: List[Dict[str, Any]] = []
        quarantine_count = int((payload.get('batchSnapshot') or {}).get('quarantineCount') or payload.get('quarantineCount') or 0)
        for strategy_code, required_fields in strategies:
            required = [cls._norm(field) for field in required_fields if cls._norm(field)]
            matched = [field for field in required if field in field_names]
            missing = [field for field in required if field not in field_names]
            ratio = len(matched) / max(len(required), 1)
            surrogate_bonus = 0.12 if 'surrogate' in strategy_code and ratio >= 0.5 else 0.0
            score = max(0.0, min(1.0, 0.2 + ratio * 0.75 + surrogate_bonus - (0.12 if missing and len(matched) == 0 else 0.0)))
            unresolved_rows = 0 if ratio >= 1.0 else max(quarantine_count, 1 if missing else 0)
            surrogate_key_rate = 1.0 if 'surrogate' in strategy_code and score >= 0.45 else 0.0
            downstream_risk = round(max(0.0, 1.0 - score), 4)
            items.append({
                'strategyCode': strategy_code,
                'score': round(score, 4),
                'keyViabilityScore': round(score, 4),
                'unresolvedRows': unresolved_rows,
                'surrogateKeyRate': surrogate_key_rate,
                'downstreamLoadabilityRisk': downstream_risk,
                'reasonPayload': {
                    'matchedFields': matched,
                    'missingFields': missing,
                },
            })
        items.sort(key=lambda item: (item['score'], -item['unresolvedRows']), reverse=True)
        for index, item in enumerate(items, start=1):
            item['rank'] = index
            item['selected'] = index == 1
        return items[:max(limit, 1)]
