from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_app_import_route_uses_data_workspace() -> None:
    content = _read('System/frontend/src/App.tsx')
    assert "const DataImport = lazy(() => import('./pages/DataWorkspace'))" in content
    assert 'path="import"' in content


def test_legacy_entry_shells_are_kept_as_wrappers() -> None:
    assert _read('System/frontend/src/pages/DataImport.tsx').strip() == "export { default } from './DataWorkspace'"
    assert _read('System/frontend/src/pages/DataImport/index.tsx').strip() == "export { default } from '../DataWorkspace'"
    assert _read('System/frontend/src/pages/Dashboard/index.tsx').strip() == "export { default } from '../Dashboard'"


def test_system_settings_is_config_only() -> None:
    content = _read('System/frontend/src/pages/SystemSettings.tsx')
    assert 'DataImportV2' not in content
    assert '数据接入中心' in content
    assert '模板与规则' in content
    assert 'API 推送联调' in content


def test_workspace_tabs_and_copy_remain_stable() -> None:
    content = _read('System/frontend/src/pages/DataWorkspace/index.tsx')
    assert '工作台总览' in content
    assert '导入执行' in content
    assert '数据工作台' in content


def test_git_hygiene_baseline_files_are_pinned() -> None:
    root_gitignore = _read('.gitignore')
    system_gitignore = _read('System/.gitignore')
    gitattributes = _read('.gitattributes')

    for token in ['smoke_workspace_latest/', 'patch_bundle_*.zip', 'p0a_round*_*.txt', 'p0b_round*_*.txt']:
        assert token in root_gitignore

    for token in ['.venv/', 'frontend/dist/', 'data/import_batch_workspace/*.json', 'p0b_round*_*.txt']:
        assert token in system_gitignore

    for token in ['*.py text eol=lf', '*.tsx text eol=lf', '*.ps1 text eol=crlf']:
        assert token in gitattributes
