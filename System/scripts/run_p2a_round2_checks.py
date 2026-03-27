from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def evaluate(report: Dict[str, Any]) -> Dict[str, Any]:
    checks = dict(report.get('checks') or {})
    status = 'passed' if checks and all(bool(v) for v in checks.values()) else 'failed'
    return {
        'status': status,
        'selectedBatchId': report.get('selectedBatchId'),
        'jobId': report.get('jobId'),
        **checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    report = json.loads(Path(args.input).read_text(encoding='utf-8'))
    payload = evaluate(report)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get('status') == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
