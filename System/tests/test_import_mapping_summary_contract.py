from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.import_service import ImportService


def _make_service() -> ImportService:
    return ImportService()


def _patch_summary_helpers(monkeypatch):
    monkeypatch.setattr(
        ImportService,
        '_compute_header_structure_score',
        staticmethod(lambda header_block, flattened_headers, dropped_placeholder_columns: (0.91, ['stable_headers'])),
    )

    def fake_semantic_gate(
        self,
        mapped_targets,
        candidate_columns,
        mapped_count,
        wrongly_mapped_count,
        header_signals,
        header_structure_score,
    ):
        coverage = round(mapped_count / candidate_columns, 3) if candidate_columns else 0.0
        return (
            'passed',
            ['stable_gate'],
            [],
            ['core_safe'],
            {
                'mappingCoverage': coverage,
                'candidateColumns': candidate_columns,
                'mappedConfidence': 0.0,
                'wronglyMappedCount': wrongly_mapped_count,
                'mappedCount': mapped_count,
                'unmappedCount': max(candidate_columns - mapped_count, 0),
            },
        )

    monkeypatch.setattr(ImportService, '_semantic_gate', fake_semantic_gate)
    monkeypatch.setattr(
        ImportService,
        '_build_core_field_hit_summary',
        staticmethod(lambda mapped_targets: {'sku': 'sku' in mapped_targets}),
    )


def _sample_field_mappings():
    return [
        {
            'originalField': 'SKU',
            'standardField': 'sku',
            'confidence': 1.0,
            'dynamicCompanion': False,
            'excludeFromSemanticGate': False,
        },
        {
            'originalField': 'Dynamic Trend',
            'standardField': None,
            'confidence': 0.2,
            'dynamicCompanion': True,
            'excludeFromSemanticGate': True,
        },
        {
            'originalField': 'Unmapped Notes',
            'standardField': None,
            'confidence': 0.4,
            'dynamicCompanion': False,
            'excludeFromSemanticGate': False,
        },
    ]


def test_field_mapping_summary_excludes_dynamic_companion_and_semantic_excluded_fields(monkeypatch):
    _patch_summary_helpers(monkeypatch)
    service = _make_service()

    summary = service._build_field_mapping_summary(
        field_mappings=_sample_field_mappings(),
        header_block={'startRow': 0, 'endRow': 0},
        flattened_headers=['SKU', 'Dynamic Trend', 'Unmapped Notes'],
        dropped_placeholder_columns=[],
    )

    assert 'Dynamic Trend' not in summary['topUnmappedHeaders']
    assert summary['topUnmappedHeaders'] == ['Unmapped Notes']
    assert summary['mappedCount'] == 1
    assert summary['unmappedCount'] == 1
    assert 'mappingCoverage' in summary
    assert 'mappedConfidence' in summary
    assert 'semanticMetrics' in summary
    assert 'coreFieldHitSummary' in summary


def test_field_mapping_summary_surfaces_top_level_mapping_metrics(monkeypatch):
    _patch_summary_helpers(monkeypatch)
    service = _make_service()

    summary = service._build_field_mapping_summary(
        field_mappings=_sample_field_mappings(),
        header_block={'startRow': 0, 'endRow': 0},
        flattened_headers=['SKU', 'Dynamic Trend', 'Unmapped Notes'],
        dropped_placeholder_columns=[],
    )

    assert 'mappingCoverage' in summary
    assert 'mappedConfidence' in summary
    assert summary['semanticMetrics']['mappingCoverage'] == summary['mappingCoverage']
    assert summary['semanticMetrics']['mappedConfidence'] == summary['mappedConfidence']


def test_confirm_import_manual_override_keeps_top_level_mapping_metrics(monkeypatch):
    service = _make_service()
    staging_df = pd.DataFrame([{'SKU': 'A-1', 'Unmapped Notes': 'note'}])
    override_mappings = [
        {
            'originalField': 'SKU',
            'standardField': 'sku',
            'confidence': 1.0,
            'dynamicCompanion': False,
            'excludeFromSemanticGate': False,
            'isManual': True,
        }
    ]
    override_summary = {
        'mappedCanonicalFields': ['sku'],
        'topUnmappedHeaders': [],
        'mappedCount': 1,
        'unmappedCount': 0,
        'mappingCoverage': 1.0,
        'mappedConfidence': 1.0,
        'semanticMetrics': {'mappingCoverage': 1.0, 'mappedConfidence': 1.0},
        'coreFieldHitSummary': {'sku': True},
        'semanticStatus': 'passed',
        'semanticGateReasons': [],
        'riskOverrideReasons': [],
        'semanticAcceptanceReason': ['manual_override'],
    }

    monkeypatch.setattr(
        service,
        '_apply_manual_overrides_to_staging',
        lambda staging_df, field_mappings, manual_overrides: (staging_df.copy(), override_mappings),
    )
    monkeypatch.setattr(service, '_build_field_mapping_summary', lambda **kwargs: override_summary)
    monkeypatch.setattr(service, 'clean_data', lambda df: df)
    monkeypatch.setattr(service, 'validate_data', lambda df: (df, []))
    monkeypatch.setattr(service, 'remove_duplicates', lambda df: (df, 0))

    service._sessions[101] = {
        'result': {
            'transportStatus': 'passed',
            'semanticStatus': 'passed',
            'finalStatus': 'passed',
            'headerBlock': {'startRow': 0, 'endRow': 0},
            'flattenedHeaders': ['SKU', 'Unmapped Notes'],
            'droppedPlaceholderColumns': [],
            'semanticGateReasons': [],
            'riskOverrideReasons': [],
            'semanticAcceptanceReason': [],
            'headerRecoveryApplied': False,
            'preRecoveryStatus': 'passed',
            'postRecoveryStatus': 'passed',
            'recoveryAttempted': False,
            'recoveryImproved': False,
            'recoveryDiff': {},
            'confidence': 0.5,
        },
        'df': staging_df.copy(),
        'rowErrors': [],
        'duplicateCount': 0,
        'stagingDf': staging_df.copy(),
        'stagingFieldMappings': [
            {
                'originalField': 'SKU',
                'standardField': 'sku',
                'confidence': 0.5,
            }
        ],
        'fileName': 'contract.xlsx',
    }

    response = service.confirm_import(
        session_id=101,
        shop_id=1,
        manual_overrides=[{'originalField': 'SKU', 'standardField': 'sku'}],
        operator='pytest',
    )

    assert 'mappingCoverage' in response
    assert 'mappedConfidence' in response
    if 'confidence' in response:
        assert response['confidence'] == response['mappedConfidence']
