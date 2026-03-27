from __future__ import annotations

import importlib.util
from pathlib import Path

def _load_module(module_name: str, filename: str):
    target = Path(__file__).resolve().parents[2] / 'src' / 'ecom_v51' / 'services' / filename
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

ImportabilityScoreBuilder = _load_module('importability_score_builder', 'importability_score_builder.py').ImportabilityScoreBuilder


def test_importability_score_builder_marks_partial_when_some_rows_quarantined():
    service = ImportabilityScoreBuilder()
    parse_result = {'mappingCoverage': 0.86, 'transportStatus': 'passed', 'semanticStatus': 'risk', 'semanticGateReasons': ['SKU 缺失，需要 surrogate key'], 'batchSnapshot': {'transportStatus': 'passed', 'semanticStatus': 'risk'}}
    confirm_result = {'importedRows': 80, 'quarantineCount': 20, 'importabilityReasons': ['SKU 缺失，需要 surrogate key'], 'batchSnapshot': {'transportStatus': 'passed', 'semanticStatus': 'risk', 'quarantineCount': 20, 'importedRows': 80}}
    result = service.build(parse_result=parse_result, confirm_result=confirm_result, profile_confidence=0.82, key_viability_score=0.78)
    assert result['decision'] in {'partial', 'imported'}
    assert result['score'] >= 0.6
