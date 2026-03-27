from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sqlalchemy import inspect

from ecom_v51.config.settings import settings
from ecom_v51.db.session import get_engine
from ecom_v51.services.batch_service import BatchService

EXPECTED_TABLES = ['batch_profile_candidate', 'batch_business_key_candidate', 'batch_quarantine_row', 'mapping_feedback']


def _resolve_detail(batch_service: BatchService, requested_ref: str) -> tuple[str, dict]:
    requested_ref = str(requested_ref or '').strip()
    candidates: list[str] = []
    if requested_ref:
        candidates.append(requested_ref)

    recent_payload = batch_service.list_recent_batches(limit=20) or {}
    for item in list(recent_payload.get('items') or []):
        for ref in [item.get('batchId'), item.get('workspaceBatchId'), item.get('sessionId')]:
            text = str(ref or '').strip()
            if text and text not in candidates:
                candidates.append(text)

    for ref in candidates:
        detail = batch_service.get_batch_detail(ref) or {}
        if detail:
            return ref, detail
    return requested_ref, {}


def build_report(batch_ref: str) -> dict:
    inspector = inspect(get_engine())
    table_names = set(inspector.get_table_names())
    batch_service = BatchService(settings.BASE_DIR)
    resolved_ref, detail = _resolve_detail(batch_service, batch_ref)
    quarantine = batch_service.get_batch_quarantine_summary(resolved_ref) or {} if detail else {}
    report = {
        'status': 'passed',
        'requestedBatchRef': str(batch_ref),
        'resolvedBatchRef': str(resolved_ref or ''),
        'tables': {name: (name in table_names) for name in EXPECTED_TABLES},
        'detailFound': bool(detail),
        'detailHasProfileCandidates': bool(detail.get('profileCandidates')),
        'detailHasBusinessKeyCandidates': bool(detail.get('businessKeyCandidates')),
        'detailHasImportabilityEvaluation': bool(detail.get('importabilityEvaluation')),
        'quarantineHasReasonBuckets': bool(quarantine.get('reasonBuckets') or detail.get('reasonBuckets')),
        'topProfile': (detail.get('profileCandidates') or [{}])[0] if detail else {},
        'topBusinessKey': (detail.get('businessKeyCandidates') or [{}])[0] if detail else {},
        'importabilityEvaluation': detail.get('importabilityEvaluation') or {},
    }
    if (
        not all(report['tables'].values())
        or not report['detailFound']
        or not report['detailHasProfileCandidates']
        or not report['detailHasBusinessKeyCandidates']
        or not report['detailHasImportabilityEvaluation']
    ):
        report['status'] = 'failed'
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-ref', default='3')
    parser.add_argument('--json-out', default='')
    args = parser.parse_args()
    report = build_report(args.batch_ref)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
