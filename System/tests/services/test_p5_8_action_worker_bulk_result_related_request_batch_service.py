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


def test_action_queue_round27_bulk_result_related_request_batch_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    request_a, job_a = _create_and_push(entry, approval, delivery, batch_ref="batch-r27", suffix="a")
    request_b, job_b = _create_and_push(entry, approval, delivery, batch_ref="batch-r27", suffix="b")
    request_c, job_c = _create_and_push(entry, approval, delivery, batch_ref="batch-r27b", suffix="c")

    parent = queue.execute_bulk_command(
        command="release-lease",
        job_ids=[job_a, job_b, job_c],
        operator="ops-r27",
        reason="bulk_release_partial_r27",
    )
    queue.reexecute_bulk_command(
        parent["bulkCommandId"],
        selection="failed",
        command="dead-letter",
        operator="ops-r27",
        reason="rerun_failed_as_dead_letter_r27",
    )
    lineage = queue.reexecute_bulk_command_lineage(
        parent["bulkCommandId"],
        selection="failed",
        command="redrive",
        scope="entire_lineage",
        operator="ops-r27",
        reason="lineage_redrive_r27",
    )

    related = queue.get_bulk_command_related(parent["bulkCommandId"], limit=10)
    assert related["summary"]["totalResults"] == 3
    assert related["requestIdSummary"][request_a] == 1
    assert related["requestIdSummary"][request_b] == 1
    assert related["requestIdSummary"][request_c] == 1
    assert related["batchRefSummary"]["batch-r27"] == 2
    assert related["batchRefSummary"]["batch-r27b"] == 1
    latest = related["items"][0]
    assert latest["bulkCommandId"] == lineage["bulkCommandId"]
    assert set(latest["requestIds"]) == {request_a, request_b, request_c}
    assert set(latest["batchRefs"]) == {"batch-r27", "batch-r27b"}
