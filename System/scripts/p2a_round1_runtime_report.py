from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def _post_json(url: str, payload: dict[str, Any], timeout: int = 180) -> tuple[int, Any]:
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, {'error': body}


def _get_json(url: str, timeout: int = 120) -> tuple[int, Any]:
    req = urllib.request.Request(url, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, {'error': body}


def _unwrap(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {}
    if body.get('success') is True and isinstance(body.get('data'), dict):
        return body['data']
    return body


def _pretty(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def _candidate_files(base_dir: Path) -> list[Path]:
    return [
        base_dir / 'uploads' / 'analytics_report_2026-03-12_23_49.xlsx',
        base_dir / 'sample_data' / 'p4_demo_import.csv',
        base_dir / 'sample_data' / 'p0_csv_scene_from_cn.csv',
        base_dir / 'sample_data' / 'ozon_bad_header_or_missing_sku.xlsx',
        base_dir / 'data' / 'analytics_report_2026-03-12_23_49.xlsx',
    ]


def main() -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(description='P2A round1 runtime report: upload -> confirm -> replay -> jobs')
    parser.add_argument('--api-base', default='http://127.0.0.1:5000')
    parser.add_argument('--base-dir', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--json-out', default='')
    parser.add_argument('--shop-id', type=int, default=1)
    parser.add_argument('--dataset-kind', default='orders')
    parser.add_argument('--profile-code', default='ozon_orders_report')
    args = parser.parse_args()

    api = args.api_base.rstrip('/')
    base_dir = Path(args.base_dir).resolve()
    report: dict[str, Any] = {
        'status': 'failed',
        'apiBase': api,
        'baseDir': str(base_dir),
        'selectedFile': None,
        'upload': None,
        'confirm': None,
        'replay': None,
        'jobs': {},
        'batches': {},
        'errors': [],
    }

    candidates = [p for p in _candidate_files(base_dir) if p.exists() and p.is_file()]
    if not candidates:
        report['errors'].append('no_candidate_fixture_found')
        text = _pretty(report)
        if args.json_out:
            Path(args.json_out).write_text(text, encoding='utf-8')
        print(text)
        return 1
    selected = candidates[0]
    report['selectedFile'] = str(selected)

    upload_status, upload_body = _post_json(f'{api}/api/v1/import/upload', {
        'filePath': str(selected),
        'shopId': args.shop_id,
        'datasetKind': args.dataset_kind,
        'profileCode': args.profile_code,
        'operator': 'p2a_runtime_report',
    })
    report['upload'] = {'httpStatus': upload_status, 'body': upload_body}
    upload_data = _unwrap(upload_body)
    batch_id = upload_data.get('batchId')
    upload_job_id = upload_data.get('jobId')
    if upload_job_id:
        status, body = _get_json(f'{api}/api/v1/jobs/{upload_job_id}')
        report['jobs']['upload'] = {'httpStatus': status, 'body': body}
    if upload_status >= 400 or batch_id in (None, ''):
        report['errors'].append('upload_failed')
        text = _pretty(report)
        if args.json_out:
            Path(args.json_out).write_text(text, encoding='utf-8')
        print(text)
        return 1

    confirm_status, confirm_body = _post_json(f'{api}/api/v1/batches/{batch_id}/confirm', {
        'operator': 'p2a_runtime_report',
        'gateMode': 'manual_continue',
        'notes': 'P2A confirm runtime check',
        'manualOverrides': [],
    })
    report['confirm'] = {'httpStatus': confirm_status, 'body': confirm_body}
    confirm_data = _unwrap(confirm_body)
    confirm_job_id = confirm_data.get('jobId')
    if confirm_job_id:
        status, body = _get_json(f'{api}/api/v1/jobs/{confirm_job_id}')
        report['jobs']['confirm'] = {'httpStatus': status, 'body': body}
    runtime_batch_id = confirm_data.get('batchId') or batch_id

    replay_status, replay_body = _post_json(f'{api}/api/v1/batches/{runtime_batch_id}/replay', {
        'operator': 'p2a_runtime_report',
        'notes': 'P2A replay runtime check',
    })
    report['replay'] = {'httpStatus': replay_status, 'body': replay_body}
    replay_data = _unwrap(replay_body)
    replay_job_id = replay_data.get('jobId')
    replay_batch_id = replay_data.get('batchId')
    if replay_job_id:
        status, body = _get_json(f'{api}/api/v1/jobs/{replay_job_id}')
        report['jobs']['replay'] = {'httpStatus': status, 'body': body}

    target_batch_id = replay_batch_id or runtime_batch_id
    for label, suffix in {
        'recent': '/api/v1/batches?limit=20',
        'detail': f'/api/v1/batches/{target_batch_id}',
        'timeline': f'/api/v1/batches/{target_batch_id}/timeline',
        'quarantine': f'/api/v1/batches/{target_batch_id}/quarantine-summary',
        'jobUpload': f'/api/v1/jobs/{upload_job_id}' if upload_job_id else '',
        'jobConfirm': f'/api/v1/jobs/{confirm_job_id}' if confirm_job_id else '',
        'jobReplay': f'/api/v1/jobs/{replay_job_id}' if replay_job_id else '',
    }.items():
        if not suffix:
            continue
        status, body = _get_json(f'{api}{suffix}')
        report['batches'][label] = {'httpStatus': status, 'body': body}

    recent_data = _unwrap(report['batches'].get('recent', {}).get('body'))
    detail_data = _unwrap(report['batches'].get('detail', {}).get('body'))
    timeline_data = _unwrap(report['batches'].get('timeline', {}).get('body'))
    quarantine_data = _unwrap(report['batches'].get('quarantine', {}).get('body'))
    jobs_ok = all(_unwrap(v.get('body')).get('status') == 'completed' for v in report['jobs'].values() if isinstance(v, dict))
    report['status'] = 'passed' if (
        isinstance(recent_data, dict) and len(recent_data.get('items') or []) > 0
        and isinstance(detail_data, dict) and detail_data.get('batchId') not in (None, '')
        and isinstance(timeline_data, dict) and len(timeline_data.get('eventTimeline') or timeline_data.get('events') or []) > 0
        and isinstance(quarantine_data, dict) and 'reasonBuckets' in quarantine_data
        and jobs_ok
    ) else 'failed'

    text = _pretty(report)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding='utf-8')
    print(text)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
