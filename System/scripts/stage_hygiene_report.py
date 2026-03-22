from __future__ import annotations

import argparse
import json
import subprocess
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_ROOT = Path(__file__).resolve().parents[1]

ROOT_GITIGNORE_REQUIRED = [
    '.pytest_cache/',
    '**/__pycache__/',
    'smoke_workspace_latest/',
    'patch_bundle_*.zip',
    'p0a_round*_*.txt',
    'p0b_round*_*.txt',
]

SYSTEM_GITIGNORE_REQUIRED = [
    '.venv/',
    '.pytest_cache/',
    'frontend/dist/',
    'smoke_workspace_latest/',
    'p0a_round*_*.txt',
    'p0b_round*_*.txt',
    'data/import_batch_workspace/*.json',
]

GITATTRIBUTES_REQUIRED = [
    '*.py text eol=lf',
    '*.ts text eol=lf',
    '*.tsx text eol=lf',
    '*.md text eol=lf',
    '*.ps1 text eol=crlf',
]

NOISE_GLOBS = [
    '**/.pytest_cache',
    '**/__pycache__',
    '**/*.pyc',
    'smoke_workspace_latest',
    'System/frontend/dist',
    'System/.venv',
    'System/p0a_round*_*.txt',
    'System/p0a_round*_*.json',
    'System/p0b_round*_*.txt',
    'System/p0b_round*_*.json',
    'patch_bundle_*.zip',
]


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _contains_all(text: str, items: Iterable[str]) -> list[str]:
    return [item for item in items if item not in text]


def _git_ls_files(root: Path) -> list[str]:
    try:
        proc = subprocess.run(['git', '-C', str(root), 'ls-files'], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return []
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _find_noise_paths(root: Path) -> list[str]:
    results: set[str] = set()
    for path in root.rglob('*'):
        rel = path.relative_to(root).as_posix()
        if any(fnmatch(rel, pattern) for pattern in NOISE_GLOBS):
            results.add(rel)
    return sorted(results)


def build_report() -> dict:
    app_tsx = _read(SYSTEM_ROOT / 'frontend/src/App.tsx')
    data_import = _read(SYSTEM_ROOT / 'frontend/src/pages/DataImport.tsx').strip()
    data_import_index = _read(SYSTEM_ROOT / 'frontend/src/pages/DataImport/index.tsx').strip()
    dashboard_index = _read(SYSTEM_ROOT / 'frontend/src/pages/Dashboard/index.tsx').strip()
    system_settings = _read(SYSTEM_ROOT / 'frontend/src/pages/SystemSettings.tsx')
    data_workspace = _read(SYSTEM_ROOT / 'frontend/src/pages/DataWorkspace/index.tsx')
    root_gitignore = _read(ROOT / '.gitignore')
    system_gitignore = _read(SYSTEM_ROOT / '.gitignore')
    gitattributes = _read(ROOT / '.gitattributes')

    frontend_checks = {
        'app_import_uses_data_workspace': "const DataImport = lazy(() => import('./pages/DataWorkspace'))" in app_tsx,
        'legacy_data_import_shell': data_import == "export { default } from './DataWorkspace'",
        'legacy_data_import_index_shell': data_import_index == "export { default } from '../DataWorkspace'",
        'legacy_dashboard_index_shell': dashboard_index == "export { default } from '../Dashboard'",
        'system_settings_has_no_import_executor_component': 'DataImportV2' not in system_settings,
        'system_settings_keeps_only_config_tabs': all(token in system_settings for token in ['数据接入中心', '模板与规则', 'API 推送联调']),
        'workspace_tabs_are_present': all(token in data_workspace for token in ['工作台总览', '导入执行']),
    }

    gitignore_checks = {
        'root_missing_patterns': _contains_all(root_gitignore, ROOT_GITIGNORE_REQUIRED),
        'system_missing_patterns': _contains_all(system_gitignore, SYSTEM_GITIGNORE_REQUIRED),
        'gitattributes_missing_rules': _contains_all(gitattributes, GITATTRIBUTES_REQUIRED),
    }

    tracked_files = _git_ls_files(ROOT)
    tracked_noise = sorted(path for path in tracked_files if any(fnmatch(path, pattern) for pattern in NOISE_GLOBS))

    report = {
        'status': 'passed',
        'frontendChecks': frontend_checks,
        'gitignoreChecks': gitignore_checks,
        'trackedNoiseFiles': tracked_noise,
        'presentNoisePaths': _find_noise_paths(ROOT),
        'recommendation': 'P0b round 1 focuses on repo hygiene, legacy entry shells, and config-only settings page baseline.',
    }

    hard_fail = (
        not all(frontend_checks.values())
        or bool(gitignore_checks['root_missing_patterns'])
        or bool(gitignore_checks['system_missing_patterns'])
        or bool(gitignore_checks['gitattributes_missing_rules'])
    )
    if hard_fail:
        report['status'] = 'failed'
    elif tracked_noise:
        report['status'] = 'warning'

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate a P0b stage hygiene report.')
    parser.add_argument('--output', default='stage_hygiene_report.json', help='Path to output JSON report')
    args = parser.parse_args()

    report = build_report()
    output = Path(args.output)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] != 'failed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
