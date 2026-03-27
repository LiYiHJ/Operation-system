from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _bool(v: Any) -> bool:
    return bool(v)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _pretty(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def _unwrap_api_payload(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {}
    data = body.get('data')
    if isinstance(data, dict) and body.get('success') is True:
        return data
    return body


def _find_default_input() -> Path:
    cwd = Path.cwd()
    candidates = sorted(cwd.glob('p1_round1_rehydrate_batch_*.json'), key=lambda p: p.name, reverse=True)
    if candidates:
        return candidates[0]
    return cwd / 'p1_round1_rehydrate_batch_20260322.json'


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate P1 rehydrate output before re-running P1 scripts.')
    parser.add_argument('--input', default='', help='Optional input report JSON path')
    parser.add_argument('--json-out', default='')
    args = parser.parse_args()

    input_path = Path(args.input) if args.input else _find_default_input()
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path

    if not input_path.exists():
        result = {
            'status': 'failed',
            'error': 'rehydrate_report_not_found',
            'input': str(input_path),
        }
        text = _pretty(result)
        print(text)
        if args.json_out:
            Path(args.json_out).write_text(text, encoding='utf-8')
        return 1

    data = _load_json(input_path)
    parse_body = _unwrap_api_payload(((data.get('parse') or {}).get('body') or {})) if isinstance(data, dict) else {}
    confirm_body = _unwrap_api_payload(((data.get('confirm') or {}).get('body') or {})) if isinstance(data, dict) else {}
    detail_body = _unwrap_api_payload(((data.get('detail') or {}).get('body') or {})) if isinstance(data, dict) else {}
    recent_body = _unwrap_api_payload(((data.get('recentBatches') or {}).get('body') or {})) if isinstance(data, dict) else {}
    timeline_body = _unwrap_api_payload(((data.get('timeline') or {}).get('body') or {})) if isinstance(data, dict) else {}
    quarantine_body = _unwrap_api_payload(((data.get('quarantineSummary') or {}).get('body') or {})) if isinstance(data, dict) else {}

    items = recent_body.get('items') or [] if isinstance(recent_body, dict) else []
    timeline = timeline_body.get('eventTimeline') or timeline_body.get('events') or [] if isinstance(timeline_body, dict) else []
    reason_buckets = quarantine_body.get('reasonBuckets')
    has_reason_bucket_field = isinstance(reason_buckets, list)
    detail_batch_id = detail_body.get('batchId') if isinstance(detail_body, dict) else None
    if detail_batch_id in (None, ''):
        detail_batch_id = data.get('formalBatchId')

    result = {
        'status': 'failed',
        'input': str(input_path),
        'selectedFileExists': _bool(data.get('selectedFile')),
        'parseSucceeded': (data.get('parse') or {}).get('httpStatus') == 200 and _bool(parse_body.get('sessionId')),
        'confirmSucceeded': (data.get('confirm') or {}).get('httpStatus') == 200 and _bool(data.get('formalBatchId')),
        'recentBatchesHasItems': len(items) > 0,
        'detailFound': (data.get('detail') or {}).get('httpStatus') == 200 and isinstance(detail_body, dict) and bool(detail_body),
        'detailBatchId': detail_batch_id,
        'detailImportabilityStatus': detail_body.get('importabilityStatus') if isinstance(detail_body, dict) else None,
        'timelineHasEvents': len(timeline) > 0,
        'quarantineSummaryPresent': (data.get('quarantineSummary') or {}).get('httpStatus') == 200 and isinstance(quarantine_body, dict),
        'quarantineHasReasonBuckets': has_reason_bucket_field,
        'formalBatchId': data.get('formalBatchId'),
        'workspaceBatchId': data.get('workspaceBatchId'),
    }

    critical = [
        result['selectedFileExists'],
        result['parseSucceeded'],
        result['confirmSucceeded'],
        result['recentBatchesHasItems'],
        result['detailFound'],
        result['detailBatchId'] not in (None, ''),
        result['timelineHasEvents'],
        result['quarantineSummaryPresent'],
        result['quarantineHasReasonBuckets'],
    ]
    result['status'] = 'passed' if all(critical) else 'failed'

    text = _pretty(result)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding='utf-8')
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
