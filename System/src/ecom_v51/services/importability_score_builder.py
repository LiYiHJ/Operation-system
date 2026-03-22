from __future__ import annotations

from typing import Dict, List


class ImportabilityScoreBuilder:
    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    @classmethod
    def build(
        cls,
        *,
        parse_result: Dict,
        confirm_result: Dict | None = None,
        profile_confidence: float = 0.5,
        key_viability_score: float = 0.5,
    ) -> Dict:
        confirm_result = dict(confirm_result or {})
        snapshot = confirm_result.get('batchSnapshot') or parse_result.get('batchSnapshot') or {}
        transport_status = str(snapshot.get('transportStatus') or parse_result.get('transportStatus') or 'failed')
        semantic_status = str(snapshot.get('semanticStatus') or parse_result.get('semanticStatus') or 'failed')
        mapping_coverage = float(parse_result.get('mappingCoverage') or 0.0)
        transport_score = 1.0 if transport_status == 'passed' else 0.15
        semantic_score = cls._clamp(mapping_coverage * 0.7 + (0.3 if semantic_status in {'passed', 'risk'} else 0.05))

        imported_rows = int(confirm_result.get('importedRows') or snapshot.get('importedRows') or 0)
        quarantine_count = int(confirm_result.get('quarantineCount') or snapshot.get('quarantineCount') or 0)
        fact_loadability_score = cls._clamp(imported_rows / max(imported_rows + quarantine_count, 1)) if imported_rows > 0 else cls._clamp(mapping_coverage * 0.8)

        reasons: List[str] = list(confirm_result.get('importabilityReasons') or parse_result.get('semanticGateReasons') or [])
        risk_penalty = min(0.35, 0.05 * len(reasons))
        if semantic_status == 'risk':
            risk_penalty += 0.05
        if quarantine_count > imported_rows and quarantine_count > 0:
            risk_penalty += 0.08
        risk_penalty = cls._clamp(risk_penalty)

        score = (
            0.20 * transport_score
            + 0.25 * semantic_score
            + 0.25 * cls._clamp(float(key_viability_score))
            + 0.20 * fact_loadability_score
            + 0.10 * cls._clamp(float(profile_confidence))
            - risk_penalty
        )
        score = cls._clamp(score)
        if score >= 0.80:
            decision = 'imported'
        elif score >= 0.60:
            decision = 'partial'
        elif score >= 0.40:
            decision = 'blocked'
        else:
            decision = 'failed'
        return {
            'algorithmVersion': 'p1.v1',
            'transportScore': round(transport_score, 4),
            'semanticScore': round(semantic_score, 4),
            'keyViabilityScore': round(cls._clamp(float(key_viability_score)), 4),
            'factLoadabilityScore': round(fact_loadability_score, 4),
            'profileConfidence': round(cls._clamp(float(profile_confidence)), 4),
            'riskPenalty': round(risk_penalty, 4),
            'score': round(score, 4),
            'decision': decision,
            'reasonList': reasons,
        }
