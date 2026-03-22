from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List


class ReasonClusteringService:
    REASON_PATTERNS = [
        ('MISSING_PRIMARY_KEY', ['sku', 'артикул', 'missing primary key', 'empty primary key', 'seller_sku', 'platform_sku']),
        ('BAD_DATE', ['date', '日期', 'дата', 'bad_date']),
        ('UNKNOWN_CURRENCY', ['currency', 'валют', 'currency code']),
        ('BAD_NUMERIC', ['numeric', 'number', 'price', 'amount', 'spend', 'float']),
        ('OUTLIER_PERCENTAGE', ['percentage', 'percent', '%', 'ctr']),
        ('CONFLICTING_ENTITY_KEY', ['duplicate', 'conflict', '冲突', 'дублик']),
        ('FACT_LOAD_BLOCKED', ['fact', 'loader', 'load blocked', 'target missing']),
        ('PROFILE_MISMATCH', ['profile mismatch', 'dataset drift', 'profile']),
    ]

    @classmethod
    def classify(cls, reason: str) -> str:
        lowered = str(reason or '').lower()
        for code, needles in cls.REASON_PATTERNS:
            if any(needle in lowered for needle in needles):
                return code
        return 'UNCLASSIFIED'

    @classmethod
    def cluster(cls, reasons: Iterable[str]) -> List[Dict]:
        buckets: Dict[str, Dict] = defaultdict(lambda: {'count': 0, 'examples': []})
        for reason in reasons:
            text = str(reason or '').strip()
            if not text:
                continue
            code = cls.classify(text)
            buckets[code]['count'] += 1
            if len(buckets[code]['examples']) < 3:
                buckets[code]['examples'].append(text)
        items: List[Dict] = []
        for code, payload in buckets.items():
            items.append({
                'reasonCode': code,
                'reasonClusterCode': code,
                'count': int(payload['count']),
                'examples': list(payload['examples']),
                'isAutoRecoverable': code in {'BAD_DATE', 'BAD_NUMERIC', 'OUTLIER_PERCENTAGE'},
            })
        items.sort(key=lambda item: (item['count'], item['reasonCode']), reverse=True)
        return items
