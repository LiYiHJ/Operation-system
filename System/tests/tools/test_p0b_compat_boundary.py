from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_ingestion_service_prefers_v1_reads_with_legacy_fallback() -> None:
    content = _read('System/frontend/src/services/ingestion.ts')
    assert '/api/v1/registry/datasets' in content
    assert '/api/v1/batches?' in content
    assert '/api/v1/batches/${encodeURIComponent(String(sessionId))}' in content
    assert '/api/import/dataset-registry' in content
    assert '/api/import/batches?' in content
    assert '/api/import/batches/${encodeURIComponent(String(sessionId))}' in content


def test_frontend_has_no_hardcoded_localhost_5000() -> None:
    frontend_root = REPO_ROOT / 'System/frontend/src'
    offenders: list[str] = []
    for path in frontend_root.rglob('*'):
        if path.suffix not in {'.ts', '.tsx', '.js', '.jsx'}:
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        if 'localhost:5000' in text or '127.0.0.1:5000' in text:
            offenders.append(path.relative_to(REPO_ROOT).as_posix())
    assert offenders == []


def test_v1_and_legacy_boundary_routes_are_both_present() -> None:
    app_content = _read('System/src/ecom_v51/api/app.py')
    import_route_content = _read('System/src/ecom_v51/api/routes/import_route.py')
    assert '/api/v1' in app_content
    assert "@import_bp.route('/dataset-registry', methods=['GET'])" in import_route_content
    assert "@import_bp.route('/batches', methods=['GET'])" in import_route_content
    assert "@import_bp.route('/batches/<int:session_id>', methods=['GET'])" in import_route_content


def test_gitignore_boundary_rules_cover_frontend_runtime_noise() -> None:
    root_gitignore = _read('.gitignore')
    system_gitignore = _read('System/.gitignore')

    for token in ['System/frontend/.venv/', 'System/frontend/.pytest_cache/', 'System/frontend/coverage/', 'System/data/import_batch_workspace/*.json']:
        assert token in root_gitignore

    for token in ['frontend/.venv/', 'frontend/.pytest_cache/', 'frontend/coverage/', 'coverage/', '*.log']:
        assert token in system_gitignore


def test_boundary_report_script_is_present() -> None:
    content = _read('System/scripts/p0b_round2_boundary_report.py')
    assert 'frontendLocalhostRefs' in content
    assert 'presentNoiseSummary' in content
    assert 'ingestion_service_prefers_v1_registry' in content
