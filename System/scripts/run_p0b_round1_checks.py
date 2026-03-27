from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SYSTEM_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = SYSTEM_ROOT / 'frontend'


def run_step(name: str, command: list[str], cwd: Path) -> dict:
    proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {
        'name': name,
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
    }


def main() -> int:
    results = [
        run_step('stage_hygiene_report', [sys.executable, 'scripts/stage_hygiene_report.py', '--output', 'p0b_round1_stage_hygiene_report.json'], SYSTEM_ROOT),
        run_step('pytest_p0b_repo_hygiene', [sys.executable, '-m', 'pytest', 'tests/tools/test_p0b_repo_hygiene.py', '-q'], SYSTEM_ROOT),
        run_step('frontend_build', ['npm', 'run', 'build'], FRONTEND_ROOT),
    ]
    summary = {
        'status': 'passed' if all(item['returncode'] == 0 for item in results) else 'failed',
        'steps': results,
    }
    (SYSTEM_ROOT / 'p0b_round1_check_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': summary['status'], 'steps': [{'name': x['name'], 'returncode': x['returncode']} for x in results]}, ensure_ascii=False, indent=2))
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
