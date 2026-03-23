from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _unwrap(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {}
    if body.get('success') is True and isinstance(body.get('data'), dict):
        return body['data']
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate P2A runtime report.')
    parser.add_argument('--input', default=str(Path(__file__).resolve().parents[1] / 'p2a_round1_runtime_report_20260323.json'))
    args = parser.parse_args()
    path = Path(args.input)
    report = _load_json(path)

    recent = _unwrap((((report.get('batches') or {}).get('recent') or {}).get('body')))
    detail = _unwrap((((report.get('batches') or {}).get('detail') or {}).get('body')))
    timeline = _unwrap((((report.get('batches') or {}).get('timeline') or {}).get('body')))
    quarantine = _unwrap((((report.get('batches') or {}).get('quarantine') or {}).get('body')))
    job_upload = _unwrap((((report.get('jobs') or {}).get('upload') or {}).get('body')))
    job_confirm = _unwrap((((report.get('jobs') or {}).get('confirm') or {}).get('body')))
    job_replay = _unwrap((((report.get('jobs') or {}).get('replay') or {}).get('body')))

    result = {
        'status': 'failed',
        'reportStatusPassed': report.get('status') == 'passed',
        'recentBatchesHasItems': len(recent.get('items') or []) > 0,
        'detailFound': isinstance(detail, dict) and bool(detail),
        'detailBatchId': detail.get('batchId'),
        'detailHasRawRecords': 'rawRecords' in detail and isinstance(detail.get('rawRecords'), list),
        'timelineHasEvents': len(timeline.get('eventTimeline') or timeline.get('events') or []) > 0,
        'quarantineSummaryPresent': isinstance(quarantine, dict) and bool(quarantine),
        'quarantineHasReasonBuckets': 'reasonBuckets' in quarantine,
        'jobUploadCompleted': job_upload.get('status') == 'completed',
        'jobConfirmCompleted': job_confirm.get('status') == 'completed',
        'jobReplayCompleted': job_replay.get('status') == 'completed',
        'detailContractVersion': detail.get('contractVersion'),
        'jobReplayBatchId': job_replay.get('batchId'),
    }
    result['status'] = 'passed' if all([
        result['reportStatusPassed'],
        result['recentBatchesHasItems'],
        result['detailFound'],
        result['detailBatchId'] not in (None, ''),
        result['detailHasRawRecords'],
        result['timelineHasEvents'],
        result['quarantineSummaryPresent'],
        result['quarantineHasReasonBuckets'],
        result['jobUploadCompleted'],
        result['jobConfirmCompleted'],
        result['jobReplayCompleted'],
    ]) else 'failed'
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
