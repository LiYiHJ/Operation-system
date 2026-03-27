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


def test_action_queue_round25_bulk_result_related_action_code_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _, job_a = _create_and_push(entry, approval, delivery, batch_ref="batch-r25", suffix="a")
    _, job_b = _create_and_push(entry, approval, delivery, batch_ref="batch-r25", suffix="b")
    _, job_c = _create_and_push(entry, approval, delivery, batch_ref="batch-r25", suffix="c")

    claimed = queue.claim_next_job(worker_id="worker-r25", operator="worker-r25", batch_ref="batch-r25")
    assert claimed["jobId"] == job_a

    parent = queue.execute_bulk_command(
        command="release-lease",
        job_ids=[job_a, job_b, job_c],
        operator="ops-r25",
        worker_id="worker-r25",
        reason="bulk_release_partial_r25",
    )
    child = queue.reexecute_bulk_command(
        parent["bulkCommandId"],
        selection="failed",
        command="dead-letter",
        operator="ops-r25",
        reason="rerun_failed_as_dead_letter_r25",
    )
    lineage = queue.reexecute_bulk_command_lineage(
        parent["bulkCommandId"],
        selection="failed",
        command="redrive",
        scope="entire_lineage",
        operator="ops-r25",
        reason="lineage_redrive_r25",
    )

    related = queue.get_bulk_command_related(parent["bulkCommandId"], limit=10)
    assert related["summary"]["totalResults"] == 3
    assert related["actionCodeSummary"]["price_update"] == 3
    latest = related["items"][0]
    assert latest["bulkCommandId"] == lineage["bulkCommandId"]
    assert latest["actionCode"] == "price_update"
    assert latest["actionCodes"] == ["price_update"]
    assert latest["linkedHistoryFilters"]["actionCode"] == "price_update"
    assert latest["linkedTimelineFilters"]["actionCode"] == "price_update"
    assert child["bulkCommandId"] in {item["bulkCommandId"] for item in related["items"]}
