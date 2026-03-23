from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / 'scripts' / 'run_p2a_round2_checks.py'
spec = importlib.util.spec_from_file_location('run_p2a_round2_checks', SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_evaluate_passed():
    payload = module.evaluate({
        'selectedBatchId': 1,
        'jobId': 7,
        'checks': {
            'filteredBatchesHasItems': True,
            'rawRecordsFound': True,
            'jobFound': True,
            'jobCompleted': True,
            'jobEventsFound': True,
        },
    })
    assert payload['status'] == 'passed'
    assert payload['jobId'] == 7


def test_evaluate_failed():
    payload = module.evaluate({
        'checks': {
            'filteredBatchesHasItems': True,
            'rawRecordsFound': False,
            'jobFound': True,
            'jobCompleted': False,
            'jobEventsFound': False,
        },
    })
    assert payload['status'] == 'failed'
