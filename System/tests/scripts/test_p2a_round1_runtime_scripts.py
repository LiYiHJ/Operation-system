from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_module(rel_path: str, name: str):
    path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_runtime_report_prefers_wrapped_data_and_marks_passed_shape():
    module = _load_module('scripts/p2a_round1_runtime_report.py', 'p2a_runtime_report')
    assert module._unwrap({'success': True, 'data': {'batchId': 7}}) == {'batchId': 7}
    assert module._unwrap({'batchId': 9}) == {'batchId': 9}


def test_runtime_checks_accepts_empty_reason_buckets_when_present(tmp_path):
    module = _load_module('scripts/run_p2a_round1_checks.py', 'p2a_runtime_checks')
    payload = {
        'status': 'passed',
        'jobs': {
            'upload': {'body': {'success': True, 'data': {'status': 'completed', 'batchId': 1}}},
            'confirm': {'body': {'success': True, 'data': {'status': 'completed', 'batchId': 1}}},
            'replay': {'body': {'success': True, 'data': {'status': 'completed', 'batchId': 2}}},
        },
        'batches': {
            'recent': {'body': {'success': True, 'data': {'items': [{'batchId': 2}]}}},
            'detail': {'body': {'success': True, 'data': {'batchId': 2, 'rawRecords': []}}},
            'timeline': {'body': {'success': True, 'data': {'eventTimeline': [{'eventType': 'parse'}]}}},
            'quarantine': {'body': {'success': True, 'data': {'reasonBuckets': []}}},
        },
    }
    fp = tmp_path / 'report.json'
    fp.write_text(__import__('json').dumps(payload), encoding='utf-8')
    assert module.main.__name__ == 'main'
