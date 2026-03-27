from __future__ import annotations

import argparse
import json
import re
import subprocess
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_ROOT = Path(__file__).resolve().parents[1]

ROOT_GITIGNORE_REQUIRED = [
    'System/frontend/.venv/',
    'System/frontend/.pytest_cache/',
    'System/frontend/coverage/',
    'System/data/import_batch_workspace/*.json',
    'patch_bundle_20260322_*.zip',
]

SYSTEM_GITIGNORE_REQUIRED = [
    'frontend/.venv/',
    'frontend/.pytest_cache/',
    'frontend/coverage/',
    'coverage/',
    '*.log',
]

NOISE_TRACK_GLOBS = [
    'System/.venv/**',
    'System/frontend/.venv/**',
    'System/.pytest_cache/**',
    'System/frontend/.pytest_cache/**',
    'System/**/__pycache__/**',
    'System/frontend/dist/**',
    'System/data/import_batch_workspace/*.json',
    'System/p0a_round*_*.txt',
    'System/p0a_round*_*.json',
    'System/p0b_round*_*.txt',
    'System/p0b_round*_*.json',
]


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _contains_all(text: str, tokens: list[str]) -> list[str]:
    return [token for token in tokens if token not in text]


def _git_ls_files(root: Path) -> list[str]:
    proc = subprocess.run(['git', '-C', str(root), 'ls-files'], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _count_frontend_localhost_refs() -> list[str]:
    hits: list[str] = []
    for path in (SYSTEM_ROOT / 'frontend/src').rglob('*'):
        if path.suffix not in {'.ts', '.tsx', '.js', '.jsx'}:
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        if 'localhost:5000' in text or '127.0.0.1:5000' in text:
            hits.append(path.relative_to(ROOT).as_posix())
    return sorted(hits)


def _noise_summary() -> dict[str, int]:
    counts = {
        'system_venv_paths': 0,
        'frontend_venv_paths': 0,
        'pytest_cache_paths': 0,
        'pycache_paths': 0,
        'stage_output_paths': 0,
        'workspace_json_paths': 0,
        'frontend_dist_paths': 0,
    }
    for path in ROOT.rglob('*'):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith('System/.venv/') or rel == 'System/.venv':
            counts['system_venv_paths'] += 1
        if rel.startswith('System/frontend/.venv/') or rel == 'System/frontend/.venv':
            counts['frontend_venv_paths'] += 1
        if '/.pytest_cache/' in rel or rel.endswith('/.pytest_cache') or rel == 'System/.pytest_cache':
            counts['pytest_cache_paths'] += 1
        if '/__pycache__/' in rel or rel.endswith('/__pycache__'):
            counts['pycache_paths'] += 1
        if re.match(r'System/p0[ab]_round.*\.(txt|json|md)$', rel):
            counts['stage_output_paths'] += 1
        if re.fullmatch(r'System/data/import_batch_workspace/[^/]+\.json', rel):
            counts['workspace_json_paths'] += 1
        if rel.startswith('System/frontend/dist/') or rel == 'System/frontend/dist':
            counts['frontend_dist_paths'] += 1
    return counts


def build_report() -> dict:
    ingestion_service = _read(SYSTEM_ROOT / 'frontend/src/services/ingestion.ts')
    app_tsx = _read(SYSTEM_ROOT / 'frontend/src/App.tsx')
    app_py = _read(SYSTEM_ROOT / 'src/ecom_v51/api/app.py')
    import_route = _read(SYSTEM_ROOT / 'src/ecom_v51/api/routes/import_route.py')
    root_gitignore = _read(ROOT / '.gitignore')
    system_gitignore = _read(SYSTEM_ROOT / '.gitignore')

    tracked_files = _git_ls_files(ROOT)
    tracked_noise = sorted(path for path in tracked_files if any(fnmatch(path, pattern) for pattern in NOISE_TRACK_GLOBS))
    localhost_hits = _count_frontend_localhost_refs()

    frontend_checks = {
        'app_import_route_still_uses_data_workspace': "const DataImport = lazy(() => import('./pages/DataWorkspace'))" in app_tsx,
        'ingestion_service_prefers_v1_registry': '/api/v1/registry/datasets' in ingestion_service,
        'ingestion_service_prefers_v1_batch_list': '/api/v1/batches?' in ingestion_service,
        'ingestion_service_prefers_v1_batch_detail': '/api/v1/batches/${encodeURIComponent(String(sessionId))}' in ingestion_service,
        'ingestion_service_keeps_legacy_fallbacks': '/api/import/batches?' in ingestion_service and '/api/import/batches/${encodeURIComponent(String(sessionId))}' in ingestion_service,
        'frontend_has_no_localhost_5000_refs': not localhost_hits,
    }

    backend_checks = {
        'api_app_registers_v1_blueprint': '/api/v1' in app_py,
        'legacy_dataset_registry_route_still_exists': "@import_bp.route('/dataset-registry', methods=['GET'])" in import_route,
        'legacy_batch_list_route_still_exists': "@import_bp.route('/batches', methods=['GET'])" in import_route,
        'legacy_batch_detail_route_still_exists': "@import_bp.route('/batches/<int:session_id>', methods=['GET'])" in import_route,
    }

    gitignore_checks = {
        'root_missing_patterns': _contains_all(root_gitignore, ROOT_GITIGNORE_REQUIRED),
        'system_missing_patterns': _contains_all(system_gitignore, SYSTEM_GITIGNORE_REQUIRED),
    }

    report = {
        'status': 'passed',
        'frontendChecks': frontend_checks,
        'backendChecks': backend_checks,
        'gitignoreChecks': gitignore_checks,
        'trackedNoiseFiles': tracked_noise,
        'frontendLocalhostRefs': localhost_hits,
        'presentNoiseSummary': _noise_summary(),
        'recommendation': 'P0b round 2 fixes read-side boundary preference: frontend reads prefer /api/v1 and fallback to legacy compatibility only when needed.',
    }

    hard_fail = (
        not all(frontend_checks.values())
        or not all(backend_checks.values())
        or bool(gitignore_checks['root_missing_patterns'])
        or bool(gitignore_checks['system_missing_patterns'])
    )
    if hard_fail:
        report['status'] = 'failed'
    elif tracked_noise:
        report['status'] = 'warning'

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate P0b round 2 boundary report.')
    parser.add_argument('--output', default='p0b_round2_boundary_report.json')
    args = parser.parse_args()

    report = build_report()
    output = Path(args.output)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] != 'failed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
