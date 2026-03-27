from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TEST_FILES = [
    "tests/services/test_p5_8_action_dashboard_service.py",
    "tests/api/test_p5_8_v1_action_job_dashboard_contract.py",
    "tests/services/test_p5_8_action_metrics_audit_service.py",
    "tests/api/test_p5_8_v1_action_job_metrics_contract.py",
    "tests/services/test_p5_8_action_queue_service.py",
    "tests/api/test_p5_8_v1_action_request_jobs_contract.py",
    "tests/services/test_p5_8_action_recovery_service.py",
    "tests/api/test_p5_8_v1_action_job_recovery_contract.py",
    "tests/services/test_p5_8_action_transition_guard_service.py",
    "tests/api/test_p5_8_v1_action_job_transition_contract.py",
    "tests/api/test_p5_8_v1_action_async_push_contract.py",
    "tests/services/test_p5_8_action_worker_audit_filter_service.py",
    "tests/api/test_p5_8_v1_action_worker_audit_filter_contract.py",
    "tests/services/test_p5_8_action_worker_bulk_command_service.py",
    "tests/api/test_p5_8_v1_action_worker_bulk_command_contract.py",
    "tests/services/test_p5_8_action_worker_bulk_result_history_service.py",
    "tests/api/test_p5_8_v1_action_worker_bulk_result_history_contract.py",
    "tests/services/test_p5_8_action_worker_bulk_result_lineage_command_service.py",
    "tests/api/test_p5_8_v1_action_worker_bulk_result_lineage_command_contract.py",
    "tests/services/test_p5_8_action_worker_bulk_result_lineage_service.py",
    "tests/api/test_p5_8_v1_action_worker_bulk_result_lineage_contract.py",
    "tests/services/test_p5_8_action_worker_bulk_result_lineage_summary_service.py",
    "tests/api/test_p5_8_v1_action_worker_bulk_result_lineage_summary_contract.py",
    "tests/services/test_p5_8_action_worker_bulk_result_linked_filter_service.py",
    "tests/api/test_p5_8_v1_action_worker_bulk_result_linked_filter_contract.py",
    "tests/services/test_p5_8_action_worker_bulk_result_reexecute_service.py",
    "tests/api/test_p5_8_v1_action_worker_bulk_result_reexecute_contract.py",
    "tests/services/test_p5_8_action_worker_bulk_result_timeline_service.py",
    "tests/api/test_p5_8_v1_action_worker_bulk_result_timeline_contract.py",
    "tests/services/test_p5_8_action_worker_lifecycle_service.py",
    "tests/api/test_p5_8_v1_action_worker_lifecycle_contract.py",
    "tests/services/test_p5_8_action_worker_recovery_command_service.py",
    "tests/api/test_p5_8_v1_action_worker_recovery_command_contract.py",
    "tests/services/test_p5_8_action_worker_stale_service.py",
    "tests/api/test_p5_8_v1_action_worker_stale_contract.py",
    "tests/services/test_p5_8_action_worker_store_service.py",
    "tests/api/test_p5_8_v1_action_worker_store_contract.py",
]


def build_pytest_command(system_root: Path) -> list[str]:
    return [sys.executable, "-m", "pytest", "-q", *[str(system_root / rel) for rel in TEST_FILES]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the explicit P5.8 targeted pytest suite.")
    parser.add_argument("--list", action="store_true", help="Print the explicit test file list and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved pytest command and exit.")
    args = parser.parse_args()

    system_root = Path(__file__).resolve().parents[1]
    missing = [rel for rel in TEST_FILES if not (system_root / rel).exists()]
    if missing:
        print("Missing test files:", file=sys.stderr)
        for rel in missing:
            print(rel, file=sys.stderr)
        return 2

    if args.list:
        for rel in TEST_FILES:
            print(rel)
        return 0

    cmd = build_pytest_command(system_root)
    if args.dry_run:
        print("Resolved system root:", system_root)
        print("Resolved pytest command:")
        print(" ".join(f'\"{part}\"' if " " in part else part for part in cmd))
        return 0

    print("Resolved system root:", system_root)
    print(f"Running explicit P5.8 targeted suite with {len(TEST_FILES)} files")
    return subprocess.run(cmd, cwd=str(system_root)).returncode


if __name__ == "__main__":
    raise SystemExit(main())
