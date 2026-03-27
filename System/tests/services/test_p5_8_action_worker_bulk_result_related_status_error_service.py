from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.action_approval_service import ActionApprovalService
from ecom_v51.services.action_delivery_service import ActionDeliveryService
from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_queue_service import ActionQueueService
from ecom_v51.services.action_store import reset_action_store


def _create_and_push(entry, approval, delivery, *, batch_ref: str, suffix: str) -> tuple[str, str]:
    item = entry.create_request({
        "actionCode": "price_update",
        "requestedBy": "evan",
        "batchRef": batch_ref,
        "canonicalSku": f"SKU-{suffix}",
    })
    approval.submit(item["requestId"], operator="evan")
    approval.approve(item["requestId"], operator="lead")
    pushed = delivery.push(item["requestId"], operator="ops", channel="mock_push_adapter", trace_id=f"trc-{suffix}")
    return item["requestId"], pushed["jobId"]


def test_action_queue_round31_bulk_result_related_status_error_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _, job_a = _create_and_push(entry, approval, delivery, batch_ref="batch-r31", suffix="a")
    _, job_b = _create_and_push(entry, approval, delivery, batch_ref="batch-r31", suffix="b")
    _, job_c = _create_and_push(entry, approval, delivery, batch_ref="batch-r31", suffix="c")

    queue.claim_next_job(worker_id="worker-r31-a", operator="worker-r31-a", batch_ref="batch-r31")
    queue.claim_next_job(worker_id="worker-r31-c", operator="worker-r31-c", batch_ref="batch-r31")

    parent = queue.execute_bulk_command(
        command="mark-succeeded",
        job_ids=[job_a, job_b, job_c],
        operator="ops-r31",
        worker_id="worker-r31-a",
        external_ref="ext-parent-r31",
        note="parent-note-r31",
    )
    rerun = queue.reexecute_bulk_command(
        parent["bulkCommandId"],
        selection="failed",
        command="dead-letter",
        operator="ops-r31",
        reason="rerun_failed_dead_letter_r31",
        note="rerun-note-r31",
    )
    lineage = queue.reexecute_bulk_command_lineage(
        parent["bulkCommandId"],
        selection="failed",
        command="redrive",
        scope="entire_lineage",
        operator="ops-r31",
        reason="lineage_redrive_r31",
        note="lineage-note-r31",
    )

    related = queue.get_bulk_command_related(parent["bulkCommandId"], limit=10)
    assert related["summary"]["totalResults"] == 3
    assert related["itemStatusSummary"]["succeeded"] == 2
    assert related["itemStatusSummary"]["dead_letter"] == 1
    assert related["itemStatusSummary"]["queued"] == 1
    assert related["errorReasonSummary"]["job_not_completable"] == 1

    assert related["items"][0]["bulkCommandId"] == lineage["bulkCommandId"]
    assert related["items"][0]["itemStatusSummary"]["queued"] == 1
    assert related["items"][1]["bulkCommandId"] == rerun["bulkCommandId"]
    assert related["items"][1]["itemStatusSummary"]["dead_letter"] == 1
    assert related["items"][2]["bulkCommandId"] == parent["bulkCommandId"]
    assert related["items"][2]["itemStatusSummary"]["succeeded"] == 2
    assert related["items"][2]["errorReasonSummary"]["job_not_completable"] == 1
