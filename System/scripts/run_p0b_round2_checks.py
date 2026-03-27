from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description='Run P0b round 2 boundary checks.')
    parser.add_argument('--output', default='p0b_round2_boundary_report.json')
    args = parser.parse_args()

    cmd = ['python', str(ROOT / 'scripts/p0b_round2_boundary_report.py'), '--output', args.output]
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    return proc.returncode


if __name__ == '__main__':
    raise SystemExit(main())
