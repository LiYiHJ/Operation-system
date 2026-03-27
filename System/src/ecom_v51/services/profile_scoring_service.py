from __future__ import annotations

from typing import Any, Dict, Iterable, List


class ProfileScoringService:
    """Explainable heuristic scorer used for P1 V1."""

    COMPONENT_WEIGHTS = {
        'header_match_score': 0.30,
        'structure_shape_score': 0.15,
        'numeric_pattern_score': 0.15,
        'key_recoverability_score': 0.15,
        'platform_trace_score': 0.10,
        'historical_success_prior': 0.10,
        'user_override_prior': 0.05,
    }

    @staticmethod
    def _norm_text(value: Any) -> str:
        return str(value or '').strip().lower().replace('-', '_').replace(' ', '_')

    @classmethod
    def _extract_field_names(cls, parse_result: Dict[str, Any]) -> List[str]:
        names: List[str] = []
        for item in list(parse_result.get('fieldMappings') or []):
            if not isinstance(item, dict):
                continue
            target = item.get('targetField') or item.get('standardField')
            source = item.get('sourceHeader') or item.get('originalField')
            if target:
                names.append(cls._norm_text(target))
            if source:
                names.append(cls._norm_text(source))
        return [name for name in names if name]

    @classmethod
    def _tokenize_dataset(cls, dataset: Dict[str, Any]) -> set[str]:
        tokens: set[str] = set()
        for key in [dataset.get('datasetKind'), dataset.get('importProfile'), dataset.get('label')]:
            norm = cls._norm_text(key)
            if norm:
                tokens.add(norm)
                tokens.update({part for part in norm.split('_') if part})
        for field in list(dataset.get('requiredCoreFields') or []) + list(dataset.get('optionalCommonFields') or []):
            norm = cls._norm_text(field)
            if norm:
                tokens.add(norm)
        return tokens

    @classmethod
    def _numeric_pattern_score(cls, dataset_kind: str, field_names: Iterable[str]) -> float:
        names = set(field_names)
        heuristics = {
            'orders': {'price', 'quantity', 'order_id', 'order_date', 'sku'},
            'ads': {'campaign_id', 'ad_group_id', 'spend', 'clicks', 'impressions', 'ctr', 'date'},
            'reviews': {'rating', 'review_id', 'review_date', 'product_id', 'comment'},
        }
        target = heuristics.get(dataset_kind, {dataset_kind})
        hit = len(target & names)
        return min(1.0, hit / max(len(target), 1))

    @classmethod
    def _key_recoverability_score(cls, dataset: Dict[str, Any], field_names: Iterable[str]) -> float:
        names = set(field_names)
        entity_key = cls._norm_text(dataset.get('entityKeyField') or 'sku')
        alternates = {
            'orders': {'sku', 'seller_sku', 'platform_sku', 'offer_id', 'order_id', 'line_no'},
            'ads': {'sku', 'campaign_id', 'ad_group_id', 'keyword', 'date'},
            'reviews': {'sku', 'product_id', 'review_id', 'review_date'},
        }
        dataset_kind = cls._norm_text(dataset.get('datasetKind') or '')
        pool = alternates.get(dataset_kind, {entity_key}) | {entity_key}
        hits = len(pool & names)
        return min(1.0, hits / max(len(pool), 1) * 2.0)

    @classmethod
    def _platform_trace_score(cls, dataset: Dict[str, Any], parse_result: Dict[str, Any]) -> float:
        source_text = ' '.join([
            str(parse_result.get('fileName') or ''),
            str(parse_result.get('importProfile') or ''),
            str(parse_result.get('datasetKind') or ''),
        ]).lower()
        score = 0.0
        for token in cls._tokenize_dataset(dataset):
            if token and token in source_text:
                score += 0.25
        return min(1.0, score)

    @classmethod
    def score_candidates(cls, *, registry_datasets: List[Dict[str, Any]], parse_result: Dict[str, Any], selected_profile: str | None = None, limit: int = 3) -> List[Dict[str, Any]]:
        field_names = cls._extract_field_names(parse_result)
        mapped_count = int(parse_result.get('mappedCount') or 0)
        unmapped_count = int(parse_result.get('unmappedCount') or 0)
        total_columns = max(mapped_count + unmapped_count, 1)
        mapping_coverage = float(parse_result.get('mappingCoverage') or (mapped_count / total_columns))
        current_dataset_kind = cls._norm_text(parse_result.get('datasetKind'))
        selected_profile = cls._norm_text(selected_profile or parse_result.get('importProfile'))

        payloads: List[Dict[str, Any]] = []
        for dataset in registry_datasets:
            dataset_kind = cls._norm_text(dataset.get('datasetKind'))
            profile_code = cls._norm_text(dataset.get('importProfile') or dataset_kind)
            dataset_tokens = cls._tokenize_dataset(dataset)
            overlap = len(dataset_tokens & set(field_names))
            header_match_score = min(1.0, overlap / max(len(dataset_tokens), 1) * 3.0)
            structure_shape_score = max(0.2, min(1.0, mapping_coverage))
            numeric_pattern_score = cls._numeric_pattern_score(dataset_kind, field_names)
            key_recoverability_score = cls._key_recoverability_score(dataset, field_names)
            platform_trace_score = cls._platform_trace_score(dataset, parse_result)
            historical_success_prior = 0.55
            user_override_prior = 0.8 if selected_profile and selected_profile == profile_code else 0.45
            drift_penalty = 0.12 if current_dataset_kind and current_dataset_kind != dataset_kind else 0.0
            component_scores = {
                'header_match_score': round(header_match_score, 4),
                'structure_shape_score': round(structure_shape_score, 4),
                'numeric_pattern_score': round(numeric_pattern_score, 4),
                'key_recoverability_score': round(key_recoverability_score, 4),
                'platform_trace_score': round(platform_trace_score, 4),
                'historical_success_prior': historical_success_prior,
                'user_override_prior': user_override_prior,
                'drift_penalty': round(drift_penalty, 4),
            }
            score = sum(component_scores[name] * weight for name, weight in cls.COMPONENT_WEIGHTS.items()) - drift_penalty
            score = max(0.0, min(1.0, score))
            confidence = int(round(score * 100))
            explain = []
            exclude = []
            if header_match_score >= 0.35:
                explain.append('header_overlap')
            else:
                exclude.append('low_header_overlap')
            if key_recoverability_score >= 0.35:
                explain.append('recoverable_business_key')
            else:
                exclude.append('weak_key_recoverability')
            if numeric_pattern_score >= 0.35:
                explain.append('numeric_shape_match')
            if drift_penalty > 0:
                exclude.append('dataset_drift_penalty')

            payloads.append({
                'datasetKind': dataset_kind or 'orders',
                'profileCode': profile_code or dataset_kind or 'orders',
                'score': round(score, 4),
                'confidence': confidence,
                'componentScores': component_scores,
                'reasonPayload': {
                    'selectionReasons': explain,
                    'exclusionReasons': exclude,
                    'currentDatasetKind': current_dataset_kind or None,
                },
            })

        payloads.sort(key=lambda item: (item['score'], item['confidence']), reverse=True)
        if not payloads:
            return []
        top_score = payloads[0]['score']
        second_score = payloads[1]['score'] if len(payloads) > 1 else 0.0
        gap = top_score - second_score
        for index, item in enumerate(payloads, start=1):
            item['rank'] = index
            item['selected'] = index == 1
            item['autoBindable'] = index == 1 and top_score >= 0.75 and gap >= 0.08
            item['requiresManualConfirm'] = not item['autoBindable']
        return payloads[:max(limit, 1)]
