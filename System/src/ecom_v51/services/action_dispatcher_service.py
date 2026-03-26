from __future__ import annotations

from typing import Any, Dict

from .action_store import ACTION_JOBS, utcnow_iso
from .action_queue_service import ActionQueueService


class ActionDispatcherService:
    CONTRACT_VERSION = "p5.8.action_dispatcher.v1"

    def __init__(self, queue_service: ActionQueueService | None = None) -> None:
        self.queue_service = queue_service or ActionQueueService()

    def dispatch(self, job_id: str, *, operator: str = 'dispatcher') -> Dict[str, Any]:
        job = ACTION_JOBS.get(str(job_id))
        if not job:
            raise ValueError('job_not_found')
        if str(job.get('jobStatus') or '') not in {'queued', 'accepted'}:
            raise ValueError('job_not_dispatchable')
        now = utcnow_iso()
        attempt_count = int(job.get('attemptCount') or 0) + 1
        job['jobStatus'] = 'running'
        job['queueStatus'] = 'dispatched'
        job['startedAt'] = now
        job['attemptCount'] = attempt_count
        job['recoveryState'] = 'in_progress'
        self.queue_service.append_job_event(
            str(job_id),
            event_type='job_dispatched',
            status='running',
            actor=operator,
            message='action_push_job_dispatched',
            payload={'attemptCount': attempt_count},
        )
        return dict(job)
