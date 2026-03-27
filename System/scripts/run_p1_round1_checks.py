from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import os


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    out_path = project_root / 'p1_round1_algorithm_report_20260322.json'
    env = dict(os.environ)
    src_root = project_root / 'src'
    env['PYTHONPATH'] = str(src_root) + ((';' + env['PYTHONPATH']) if env.get('PYTHONPATH') else '')
    cmd = [
        sys.executable,
        str(project_root / 'scripts' / 'p1_round1_algorithm_report.py'),
        '--batch-ref',
        '3',
        '--json-out',
        str(out_path),
    ]
    completed = subprocess.run(cmd, cwd=project_root, check=False, env=env)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    payload = json.loads(out_path.read_text(encoding='utf-8'))
    if payload.get('status') != 'passed':
        raise SystemExit(1)
    print('P1 Round 1 checks: passed')


if __name__ == '__main__':
    main()
