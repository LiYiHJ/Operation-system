from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict

BASE_URL = 'http://127.0.0.1:5000'


def _request_json(method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = None
    headers = {'Content-Type': 'application/json'}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}{path}', data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode('utf-8')
            return {'httpStatus': resp.getcode(), 'body': json.loads(body)}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {'raw': body}
        return {'httpStatus': exc.code, 'body': parsed}
    except Exception as exc:
        return {'httpStatus': None, 'body': {'error': str(exc)}}


def _unwrap(envelope: Dict[str, Any]) -> Dict[str, Any]:
    body = envelope.get('body') or {}
    if isinstance(body, dict) and 'data' in body:
        return body.get('data') or {}
    return body if isinstance(body, dict) else {}


def build_report() -> Dict[str, Any]:
    report: Dict[str, Any] = {'status': 'passed', 'steps': {}, 'errors': []}
    health = _request_json('GET', '/api/health')
    report['steps']['health'] = health
    if health.get('httpStatus') != 200:
        report['status'] = 'failed'
        report['errors'].append('health_failed')
        return report

    batch_list = _request_json('GET', '/api/v1/batches?limit=10&datasetKind=orders')
    report['steps']['filteredBatches'] = batch_list
    batch_list_data = _unwrap(batch_list)
    items = list(batch_list_data.get('items') or [])
    if not items:
        report['status'] = 'failed'
        report['errors'].append('no_batches_for_round2')
        return report

    batch_id = items[0].get('batchId')
    report['selectedBatchId'] = batch_id

    raw_records = _request_json('GET', f'/api/v1/batches/{batch_id}/raw-records?limit=20')
    report['steps']['rawRecords'] = raw_records

    replay = _request_json('POST', f'/api/v1/batches/{batch_id}/replay', {'notes': 'P2A round2 runtime check'})
    report['steps']['jobReplay'] = replay
    replay_data = _unwrap(replay)
    job_id = replay_data.get('jobId')
    report['jobId'] = job_id

    if job_id not in (None, ''):
        job_detail = _request_json('GET', f'/api/v1/jobs/{job_id}')
        job_events = _request_json('GET', f'/api/v1/jobs/{job_id}/events')
    else:
        job_detail = {'httpStatus': None, 'body': {'error': 'jobId_missing'}}
        job_events = {'httpStatus': None, 'body': {'error': 'jobId_missing'}}

    report['steps']['jobDetail'] = job_detail
    report['steps']['jobEvents'] = job_events

    raw_data = _unwrap(raw_records)
    job_data = _unwrap(job_detail)
    events_data = _unwrap(job_events)

    report['checks'] = {
        'filteredBatchesHasItems': bool(items),
        'rawRecordsFound': bool(raw_data.get('items')),
        'jobFound': bool(job_data.get('jobId')),
        'jobCompleted': str(job_data.get('status') or '').lower() == 'completed',
        'jobEventsFound': bool(events_data.get('events')),
    }
    if not all(report['checks'].values()):
        report['status'] = 'failed'
        report['errors'].extend([k for k, v in report['checks'].items() if not v])
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--json-out', required=True)
    args = parser.parse_args()
    report = build_report()
    out_path = Path(args.json_out)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get('status') == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
