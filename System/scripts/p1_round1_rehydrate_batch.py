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


def _post_json(url: str, payload: dict[str, Any], timeout: int = 120) -> tuple[int, Any]:
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json; charset=utf-8'},
        method='POST',
    )
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


def _get_json(url: str, timeout: int = 60) -> tuple[int, Any]:
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


def _unwrap_api_payload(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {}
    data = body.get('data')
    if isinstance(data, dict) and body.get('success') is True:
        return data
    return body


def _candidate_files(base_dir: Path) -> list[Path]:
    return [
        base_dir / 'uploads' / 'analytics_report_2026-03-12_23_49.xlsx',
        base_dir / 'uploads' / '20260321_205439_analytics_report_2026-03-12_23_49.xlsx',
        base_dir / 'sample_data' / 'ozon_bad_header_or_missing_sku.xlsx',
        base_dir / 'sample_data' / 'p4_demo_import.csv',
        base_dir / 'sample_data' / 'p0_csv_scene_from_cn.csv',
        base_dir / 'data' / 'analytics_report_2026-03-12_23_49.xlsx',
    ]


def _pretty(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def _resolve_formal_batch_id(confirm_body: dict[str, Any], recent_items: list[dict[str, Any]], workspace_batch_id: str | None) -> int | None:
    for candidate in [
        confirm_body.get('formalBatchId'),
        confirm_body.get('batchId'),
        confirm_body.get('persistedBatchId'),
    ]:
        try:
            if candidate not in (None, ''):
                return int(candidate)
        except Exception:
            pass

    if workspace_batch_id:
        for item in recent_items:
            if str(item.get('workspaceBatchId') or '') == str(workspace_batch_id):
                try:
                    if item.get('batchId') not in (None, ''):
                        return int(item.get('batchId'))
                except Exception:
                    pass
    return None


def main() -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(description='Rehydrate one formalized batch for P1 by replaying upload/confirm.')
    parser.add_argument('--api-base', default='http://127.0.0.1:5000', help='API base URL, default http://127.0.0.1:5000')
    parser.add_argument('--base-dir', default=str(Path(__file__).resolve().parents[1]), help='System base dir')
    parser.add_argument('--json-out', default='', help='Optional JSON report output path')
    parser.add_argument('--dataset-kind', default='orders')
    parser.add_argument('--import-profile', default='ozon_orders_report')
    parser.add_argument('--shop-id', type=int, default=1)
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    api = args.api_base.rstrip('/')
    upload_url = f'{api}/api/import/upload-server-file'
    confirm_url = f'{api}/api/import/confirm'

    candidates = [p for p in _candidate_files(base_dir) if p.exists() and p.is_file()]
    report: dict[str, Any] = {
        'status': 'failed',
        'apiBase': api,
        'baseDir': str(base_dir),
        'candidateFiles': [str(p) for p in candidates],
        'selectedFile': None,
        'parse': None,
        'confirm': None,
        'formalBatchId': None,
        'workspaceBatchId': None,
        'recentBatches': None,
        'detail': None,
        'timeline': None,
        'quarantineSummary': None,
        'normalized': {},
        'errors': [],
    }

    def _finalize(exit_code: int) -> int:
        text = _pretty(report)
        if args.json_out:
            Path(args.json_out).write_text(text, encoding='utf-8')
        print(text)
        return exit_code

    if not candidates:
        report['errors'].append('no_candidate_fixture_found')
        return _finalize(1)

    selected = candidates[0]
    report['selectedFile'] = str(selected)

    parse_payload = {
        'filePath': str(selected),
        'datasetKind': args.dataset_kind,
        'importProfile': args.import_profile,
        'shop_id': args.shop_id,
        'operator': 'p1_rehydrate_script',
    }
    parse_status, parse_json = _post_json(upload_url, parse_payload)
    report['parse'] = {'httpStatus': parse_status, 'body': parse_json}
    parse_body = _unwrap_api_payload(parse_json)
    session_id = parse_body.get('sessionId') if isinstance(parse_body, dict) else None
    report['workspaceBatchId'] = parse_body.get('workspaceBatchId') if isinstance(parse_body, dict) else None
    if parse_status >= 400 or not session_id:
        report['errors'].append('parse_failed')
        return _finalize(1)

    confirm_payload = {
        'sessionId': int(session_id),
        'datasetKind': args.dataset_kind,
        'importProfile': args.import_profile,
        'shopId': args.shop_id,
        'operator': 'p1_rehydrate_script',
        'manualOverrides': [],
    }
    confirm_status, confirm_json = _post_json(confirm_url, confirm_payload)
    report['confirm'] = {'httpStatus': confirm_status, 'body': confirm_json}
    confirm_body = _unwrap_api_payload(confirm_json)

    if isinstance(confirm_body, dict) and confirm_body.get('workspaceBatchId'):
        report['workspaceBatchId'] = confirm_body.get('workspaceBatchId')
    if confirm_status >= 400:
        report['errors'].append('confirm_failed')
        return _finalize(1)

    recent_status, recent_json = _get_json(f'{api}/api/v1/batches?limit=20')
    report['recentBatches'] = {'httpStatus': recent_status, 'body': recent_json}
    recent_body = _unwrap_api_payload(recent_json)
    recent_items = list(recent_body.get('items') or []) if isinstance(recent_body, dict) else []

    batch_id = _resolve_formal_batch_id(confirm_body if isinstance(confirm_body, dict) else {}, recent_items, report.get('workspaceBatchId'))
    report['formalBatchId'] = batch_id
    if batch_id is None:
        report['errors'].append('missing_formal_batch_id')
        return _finalize(1)

    endpoints = {
        'detail': f'{api}/api/v1/batches/{batch_id}',
        'timeline': f'{api}/api/v1/batches/{batch_id}/timeline',
        'quarantineSummary': f'{api}/api/v1/batches/{batch_id}/quarantine-summary',
    }
    for key, url in endpoints.items():
        status, body = _get_json(url)
        report[key] = {'httpStatus': status, 'body': body}
        report['normalized'][key] = _unwrap_api_payload(body)

    report['normalized']['recentBatches'] = recent_body
    report['normalized']['parse'] = parse_body
    report['normalized']['confirm'] = confirm_body

    detail_body = report['normalized'].get('detail') or {}
    timeline_body = report['normalized'].get('timeline') or {}
    quarantine_body = report['normalized'].get('quarantineSummary') or {}
    detail_ok = recent_status == 200 and isinstance(detail_body, dict) and bool(detail_body) and detail_body.get('batchId') not in (None, '')
    timeline_ok = isinstance(timeline_body, dict) and len(timeline_body.get('eventTimeline') or timeline_body.get('events') or []) > 0
    quarantine_ok = isinstance(quarantine_body, dict) and 'reasonBuckets' in quarantine_body
    report['status'] = 'passed' if detail_ok and timeline_ok and quarantine_ok else 'failed'
    return _finalize(0 if report['status'] == 'passed' else 1)


if __name__ == '__main__':
    raise SystemExit(main())
