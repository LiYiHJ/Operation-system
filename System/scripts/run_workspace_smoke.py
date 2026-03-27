#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Tuple


def request_json(url: str, *, method: str = 'GET', body: Dict[str, Any] | None = None) -> Tuple[int, Dict[str, Any]]:
    data = None
    headers = {'Accept': 'application/json'}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
            payload = json.loads(raw) if raw.strip() else {}
            return resp.status, payload
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', errors='replace')
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except Exception:
            payload = {'error': raw}
        payload.setdefault('_httpStatus', e.code)
        return e.code, payload
    except Exception as e:
        return 0, {'error': str(e), '_exceptionType': type(e).__name__}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def add_section(lines: list[str], title: str, payload_path: Path) -> None:
    lines.append('')
    lines.append('=' * 20)
    lines.append(title)
    lines.append('=' * 20)
    if payload_path.exists():
        lines.append(payload_path.read_text(encoding='utf-8', errors='replace').rstrip())
    else:
        lines.append(f'[missing] {payload_path.name}')
    lines.append('')




def resolve_server_file(repo_root: Path, server_file_arg: str) -> Path:
    raw = Path(server_file_arg)
    if raw.is_absolute():
        return raw

    candidates = [
        repo_root / raw,
        repo_root / 'System' / raw,
        repo_root / 'data' / raw.name,
        repo_root / 'System' / 'data' / raw.name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-root', required=True)
    parser.add_argument('--base-url', default='http://127.0.0.1:5000')
    parser.add_argument('--output-dir', default='smoke_workspace_latest')
    parser.add_argument('--dataset-kind', default='orders')
    parser.add_argument('--import-profile', default='ozon_orders_report')
    parser.add_argument('--server-file', default='analytics_report_2026-03-12_23_49.xlsx')
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    server_file = resolve_server_file(repo_root, args.server_file)

    results: dict[str, Path] = {}

    steps = [
        ('01_health.json', 'GET', '/api/health', None),
        ('02_import_dataset_registry.json', 'GET', '/api/import/dataset-registry', None),
        ('03_ingestion_dataset_registry.json', 'GET', '/api/ingestion/dataset-registry', None),
        ('04_batch_contract_template.json', 'GET', '/api/ingestion/batch-contract-template', None),
    ]

    for filename, method, route, body in steps:
        status, payload = request_json(args.base_url + route, method=method, body=body)
        payload.setdefault('_httpStatus', status)
        path = out_dir / filename
        write_json(path, payload)
        results[filename] = path

    parse_body = {
        'filePath': str(server_file),
        'shop_id': 1,
        'operator': 'workspace_smoke',
        'datasetKind': args.dataset_kind,
        'importProfile': args.import_profile,
    }
    status, parse_payload = request_json(args.base_url + '/api/import/upload-server-file', method='POST', body=parse_body)
    parse_payload.setdefault('_httpStatus', status)
    parse_path = out_dir / '05_parse.json'
    write_json(parse_path, parse_payload)
    results['05_parse.json'] = parse_path

    session_id = parse_payload.get('sessionId')

    batch_path = out_dir / '06_batch_snapshot.json'
    if session_id:
        status, batch_payload = request_json(args.base_url + f'/api/import/batches/{session_id}', method='GET')
        batch_payload.setdefault('_httpStatus', status)
        write_json(batch_path, batch_payload)
    else:
        write_json(batch_path, {'error': 'sessionId missing from parse', '_httpStatus': 0})
    results['06_batch_snapshot.json'] = batch_path

    confirm_path = out_dir / '07_confirm.json'
    if session_id:
        confirm_body = {
            'sessionId': session_id,
            'shopId': 1,
            'operator': 'workspace_smoke',
            'datasetKind': args.dataset_kind,
            'importProfile': args.import_profile,
            'manualOverrides': [],
        }
        status, confirm_payload = request_json(args.base_url + '/api/import/confirm', method='POST', body=confirm_body)
        confirm_payload.setdefault('_httpStatus', status)
        write_json(confirm_path, confirm_payload)
    else:
        write_json(confirm_path, {'error': 'sessionId missing from parse', '_httpStatus': 0})
    results['07_confirm.json'] = confirm_path

    profit_body = {
        'salePrice': 120,
        'listPrice': 150,
        'variableRateTotal': 0.23,
        'fixedCostTotal': 58,
        'algorithmProfile': 'ozon_daily_profit',
        'discountRatios': [1.0, 0.95, 0.9, 0.85],
        'scenarios': [
            {
                'name': 'promo_5',
                'layered_params': {
                    'sale_price': 114,
                    'list_price': 150,
                    'variable_rate_total': 0.23,
                    'fixed_cost_total': 58,
                },
            },
            {
                'name': 'promo_10',
                'layered_params': {
                    'sale_price': 108,
                    'list_price': 150,
                    'variable_rate_total': 0.23,
                    'fixed_cost_total': 58,
                },
            },
        ],
    }
    status, profit_payload = request_json(args.base_url + '/api/profit/simulate', method='POST', body=profit_body)
    profit_payload.setdefault('_httpStatus', status)
    profit_path = out_dir / '08_profit_simulate.json'
    write_json(profit_path, profit_payload)
    results['08_profit_simulate.json'] = profit_path

    status, recent_batches_payload = request_json(args.base_url + '/api/import/batches?limit=10', method='GET')
    recent_batches_payload.setdefault('_httpStatus', status)
    recent_batches_path = out_dir / '09_recent_batches.json'
    write_json(recent_batches_path, recent_batches_payload)
    results['09_recent_batches.json'] = recent_batches_path

    summary_lines = [
        f'repo_root: {repo_root}',
        f'output_dir: {out_dir}',
        f'base_url: {args.base_url}',
        f'dataset_kind: {args.dataset_kind}',
        f'import_profile: {args.import_profile}',
        f'server_file: {server_file}',
        '',
        'quick verdict',
        '-------------',
        f"health_status: {json.loads(results['01_health.json'].read_text(encoding='utf-8')).get('status')}",
        f"parse_status: {parse_payload.get('status')}",
        f"parse_final_status: {parse_payload.get('finalStatus')}",
        f"parse_mapping_coverage: {parse_payload.get('mappingCoverage')}",
        f"confirm_status: {json.loads(confirm_path.read_text(encoding='utf-8')).get('status')}",
        f"confirm_success: {json.loads(confirm_path.read_text(encoding='utf-8')).get('success')}",
    ]

    for name in ['01_health.json','02_import_dataset_registry.json','03_ingestion_dataset_registry.json','04_batch_contract_template.json','05_parse.json','06_batch_snapshot.json','07_confirm.json','08_profit_simulate.json','09_recent_batches.json']:
        add_section(summary_lines, name, results[name])

    summary_path = out_dir / 'smoke_workspace_summary.txt'
    summary_path.write_text('\n'.join(summary_lines).rstrip() + '\n', encoding='utf-8')
    print(summary_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
