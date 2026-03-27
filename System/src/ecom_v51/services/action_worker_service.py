from __future__ import annotations

from typing import Any, Dict

from .action_store import ACTION_JOBS, utcnow_iso
from .action_queue_service import ActionQueueService


class ActionWorkerService:
    CONTRACT_VERSION = "p5.8.action_worker.v1"

    def __init__(self, queue_service: ActionQueueService | None = None) -> None:
        self.queue_service = queue_service or ActionQueueService()

    def mark_succeeded(self, job_id: str, *, operator: str = 'worker', external_ref: str | None = None) -> Dict[str, Any]:
        job = ACTION_JOBS.get(str(job_id))
        if not job:
            raise ValueError('job_not_found')
        now = utcnow_iso()
        job['jobStatus'] = 'succeeded'
        job['queueStatus'] = 'completed'
        job['finishedAt'] = now
        job['recoveryState'] = 'healthy'
        result = dict(job.get('result') or {})
        result.update({'accepted': True, 'queued': True, 'completed': True, 'externalRef': external_ref})
        job['result'] = result
        self.queue_service.append_job_event(str(job_id), event_type='job_succeeded', status='succeeded', actor=operator, message='action_push_job_succeeded', payload={'externalRef': external_ref})
        return dict(job)

    def mark_failed(self, job_id: str, *, operator: str = 'worker', reason: str) -> Dict[str, Any]:
        job = ACTION_JOBS.get(str(job_id))
        if not job:
            raise ValueError('job_not_found')
        now = utcnow_iso()
        job['jobStatus'] = 'failed'
        job['queueStatus'] = 'failed'
        job['finishedAt'] = now
        job['lastFailureReason'] = reason
        job['recoveryState'] = 'retryable'
        result = dict(job.get('result') or {})
        result.update({'accepted': True, 'queued': True, 'completed': True, 'failureReason': reason})
        job['result'] = result
        self.queue_service.append_job_event(str(job_id), event_type='job_failed', status='failed', actor=operator, message='action_push_job_failed', payload={'reason': reason})
        return dict(job)

    def mark_dead_letter(self, job_id: str, *, operator: str = 'worker', reason: str, note: str | None = None) -> Dict[str, Any]:
        return self.queue_service.mark_dead_letter(job_id, operator=operator, reason=reason, note=note)
