from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .action_store import (
    ACTION_APPROVAL_HISTORY,
    ACTION_CALLBACK_HISTORY,
    ACTION_COMPENSATION_HISTORY,
    ACTION_DELIVERY_HISTORY,
    ACTION_BULK_COMMAND_ORDER,
    ACTION_BULK_COMMANDS,
    ACTION_JOB_COMMAND_IDEMPOTENCY,
    ACTION_JOB_EVENTS,
    ACTION_JOB_IDEMPOTENCY,
    ACTION_JOBS,
    ACTION_REQUESTS,
    ACTION_REQUEST_JOB_INDEX,
    new_id,
    utcnow_iso,
)


class ActionQueueService:
    CONTRACT_VERSION = "p5.8.action_queue.v8"
    JOB_CONTRACT_VERSION = "p5.8.job.v8"
    QUEUE_LAG_SLA_SECONDS = 300
    RUN_DURATION_SLA_SECONDS = 900
    TURNAROUND_SLA_SECONDS = 1200
    DEFAULT_MAX_ATTEMPTS = 3
    LEASE_TTL_SECONDS = 300
    SUCCESS_CALLBACK_STATES = {'success', 'succeeded', 'completed', 'delivered', 'accepted'}
    FAILURE_CALLBACK_STATES = {'failed', 'rejected', 'cancelled', 'returned', 'error', 'timeout'}
    IN_PROGRESS_CALLBACK_STATES = {'processing', 'running', 'pending', 'delayed', 'queued'}

    def _get_request(self, request_id: str) -> Dict[str, Any]:
        item = ACTION_REQUESTS.get(str(request_id))
        if not item:
            raise ValueError('request_not_found')
        return item

    def _get_job(self, job_id: str) -> Dict[str, Any]:
        job = ACTION_JOBS.get(str(job_id))
        if not job:
            raise ValueError('job_not_found')
        return job

    @staticmethod
    def _idempotency_scope(request_id: str, idempotency_key: str | None) -> str | None:
        key = str(idempotency_key or '').strip()
        if not key:
            return None
        return f'action_push:{request_id}:{key}'

    @staticmethod
    def _command_scope(job_id: str, operation: str, idempotency_key: str | None) -> str | None:
        key = str(idempotency_key or '').strip()
        if not key:
            return None
        return f'action_job_command:{job_id}:{operation}:{key}'

    @staticmethod
    def _status(job: Dict[str, Any]) -> str:
        return str(job.get('jobStatus') or '')

    def _job_recommended_operation(self, job: Dict[str, Any]) -> str | None:
        status = self._status(job)
        attempt_count = int(job.get('attemptCount') or 0)
        max_attempts = int(job.get('maxAttempts') or self.DEFAULT_MAX_ATTEMPTS)
        if status == 'failed' and attempt_count < max_attempts:
            return 'retry'
        if status == 'failed' and attempt_count >= max_attempts:
            return 'dead_letter'
        if status == 'dead_letter':
            return 'redrive'
        return None

    def _available_commands(self, job: Dict[str, Any]) -> list[str]:
        status = self._status(job)
        recommended = self._job_recommended_operation(job)
        commands: list[str] = []
        if status == 'failed':
            if recommended == 'retry':
                commands.append('retry')
            commands.append('dead-letter')
        elif status == 'dead_letter':
            commands.append('redrive')
        elif status == 'queued':
            commands.append('dead-letter')
        elif status == 'running':
            commands.extend(['release-lease', 'mark-succeeded', 'mark-failed', 'dead-letter'])
        return commands

    def _build_job_payload(self, job: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(job)
        payload['recommendedOperation'] = self._job_recommended_operation(job)
        payload['availableCommands'] = self._available_commands(job)
        return payload


    @staticmethod
    def _next_queue_sequence() -> int:
        values: list[int] = []
        for item in ACTION_JOBS.values():
            try:
                values.append(int(item.get('queueSequence') or 0))
            except Exception:
                continue
        return (max(values) if values else 0) + 1

    @staticmethod
    def _parse_iso(value: Any) -> datetime | None:
        raw = str(value or '').strip()
        if not raw:
            return None
        try:
            if raw.endswith('Z'):
                raw = raw[:-1] + '+00:00'
            return datetime.fromisoformat(raw)
        except Exception:
            return None

    @staticmethod
    def _seconds_between(start: datetime | None, end: datetime | None) -> float | None:
        if not start or not end:
            return None
        return max((end - start).total_seconds(), 0.0)

    def _job_metrics_snapshot(self, job: Dict[str, Any], *, now_dt: datetime | None = None) -> Dict[str, Any]:
        now_dt = now_dt or datetime.now(timezone.utc)
        accepted_at = self._parse_iso(job.get('acceptedAt'))
        queued_at = self._parse_iso(job.get('queuedAt'))
        started_at = self._parse_iso(job.get('startedAt'))
        finished_at = self._parse_iso(job.get('finishedAt'))
        queue_lag = self._seconds_between(queued_at, started_at or now_dt)
        run_duration = self._seconds_between(started_at, finished_at or now_dt)
        turnaround = self._seconds_between(accepted_at, finished_at or now_dt)
        status = str(job.get('jobStatus') or '')
        return {
            'jobId': job.get('jobId'),
            'requestId': job.get('requestId'),
            'batchRef': job.get('batchRef') or job.get('batchId'),
            'actionCode': job.get('actionCode'),
            'jobStatus': status,
            'queueLagSeconds': queue_lag,
            'runDurationSeconds': run_duration,
            'turnaroundSeconds': turnaround,
            'queueLagSlaBreached': bool(queue_lag is not None and queue_lag > self.QUEUE_LAG_SLA_SECONDS),
            'runDurationSlaBreached': bool(run_duration is not None and run_duration > self.RUN_DURATION_SLA_SECONDS),
            'turnaroundSlaBreached': bool(turnaround is not None and turnaround > self.TURNAROUND_SLA_SECONDS),
        }

    @staticmethod
    def _summarize_metric(values: list[float]) -> Dict[str, Any]:
        if not values:
            return {'averageSeconds': 0.0, 'maxSeconds': 0.0, 'minSeconds': 0.0, 'samples': 0}
        ordered = sorted(values)
        return {
            'averageSeconds': round(sum(ordered) / len(ordered), 3),
            'maxSeconds': round(max(ordered), 3),
            'minSeconds': round(min(ordered), 3),
            'samples': len(ordered),
            'p95ApproxSeconds': round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 3),
        }

    @staticmethod
    def _reason_bucket(reason: str | None) -> str:
        normalized = str(reason or '').strip().lower()
        if not normalized:
            return 'unknown'
        if 'timeout' in normalized or 'lag' in normalized:
            return 'timeout'
        if 'reject' in normalized or 'invalid' in normalized or 'validation' in normalized:
            return 'validation_or_reject'
        if 'quota' in normalized or 'rate' in normalized or 'limit' in normalized:
            return 'quota_or_rate_limit'
        if 'manual' in normalized or 'operator' in normalized:
            return 'manual_intervention'
        if 'provider' in normalized or 'adapter' in normalized:
            return 'provider_error'
        return 'other'

    def append_job_event(
        self,
        job_id: str,
        *,
        event_type: str,
        status: str,
        actor: str,
        message: str,
        payload: Dict[str, Any] | None = None,
        event_at: str | None = None,
    ) -> Dict[str, Any]:
        event = {
            'eventId': new_id('jobevt'),
            'jobId': str(job_id),
            'eventType': event_type,
            'status': status,
            'eventAt': str(event_at or utcnow_iso()),
            'actor': actor,
            'message': message,
            'payload': dict(payload or {}),
        }
        ACTION_JOB_EVENTS.setdefault(str(job_id), []).append(event)
        return event

    def _touch_job(self, job_id: str, **fields: Any) -> Dict[str, Any] | None:
        job = ACTION_JOBS.get(str(job_id))
        if not job:
            return None
        for key, value in fields.items():
            if value is not None:
                job[key] = value
        return job

    def _complete_result(self, job: Dict[str, Any], **fields: Any) -> None:
        result = dict(job.get('result') or {})
        result.update(fields)
        job['result'] = result

    def enqueue_push(
        self,
        request_id: str,
        *,
        operator: str,
        channel: str | None = None,
        note: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Dict[str, Any]:
        item = self._get_request(request_id)
        current = str(item.get('status') or 'draft')
        if current != 'approved':
            raise ValueError('request_not_approved')

        scope = self._idempotency_scope(str(request_id), idempotency_key)
        if scope and scope in ACTION_JOB_IDEMPOTENCY:
            existing_id = ACTION_JOB_IDEMPOTENCY[scope]
            existing = ACTION_JOBS.get(existing_id)
            if existing:
                return self._build_job_payload(existing)

        accepted_at = utcnow_iso()
        job_id = new_id('job')
        batch_ref = str(item.get('batchRef') or '').strip() or None
        adapter = str(channel or 'mock_push_adapter')
        job = {
            'contractVersion': self.JOB_CONTRACT_VERSION,
            'jobId': job_id,
            'jobCode': 'action_push',
            'jobType': 'action_delivery',
            'jobStatus': 'queued',
            'queueStatus': 'queued',
            'executionMode': 'async_queue',
            'requestId': str(request_id),
            'batchId': batch_ref,
            'batchRef': batch_ref,
            'actionCode': item.get('actionCode'),
            'adapter': adapter,
            'traceId': trace_id,
            'idempotencyKey': str(idempotency_key).strip() if idempotency_key else None,
            'acceptedAt': accepted_at,
            'queuedAt': accepted_at,
            'queueSequence': self._next_queue_sequence(),
            'startedAt': None,
            'finishedAt': None,
            'lastCallbackAt': None,
            'lastCompensationAt': None,
            'operator': operator,
            'note': note,
            'attemptCount': 0,
            'retryCount': 0,
            'redriveCount': 0,
            'maxAttempts': self.DEFAULT_MAX_ATTEMPTS,
            'deadLettered': False,
            'workerState': 'unclaimed',
            'workerId': None,
            'leaseClaimedAt': None,
            'leaseHeartbeatAt': None,
            'leaseExpiresAt': None,
            'leaseGeneration': 0,
            'storeState': 'memory_queue',
            'deadLetteredAt': None,
            'deadLetterReason': None,
            'lastFailureReason': None,
            'lastRecoveryOperation': None,
            'lastRecoveryReason': None,
            'lastRecoveryAt': None,
            'callbackState': None,
            'compensationState': None,
            'recoveryState': 'healthy',
            'result': {
                'accepted': True,
                'queued': True,
                'message': 'accepted_into_async_queue',
            },
        }
        ACTION_JOBS[job_id] = job
        ACTION_REQUEST_JOB_INDEX.setdefault(str(request_id), []).append(job_id)
        if scope:
            ACTION_JOB_IDEMPOTENCY[scope] = job_id
        self.append_job_event(job_id, event_type='job_accepted', status='accepted', actor=operator, message='action_push_request_accepted', payload={'requestId': str(request_id), 'adapter': adapter})
        self.append_job_event(job_id, event_type='job_queued', status='queued', actor='queue', message='action_push_job_queued', payload={'requestId': str(request_id), 'adapter': adapter})
        return self._build_job_payload(job)


    @staticmethod
    def _sort_jobs(jobs: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        return sorted(
            list(jobs),
            key=lambda item: (
                int(item.get('queueSequence') or 0) if str(item.get('queueSequence') or '').strip() else 0,
                str(item.get('acceptedAt') or item.get('queuedAt') or ''),
                str(item.get('jobId') or ''),
            ),
            reverse=True,
        )

    def _list_jobs(
        self,
        *,
        request_id: str | None = None,
        batch_ref: str | None = None,
        action_code: str | None = None,
        status: str | None = None,
    ) -> list[Dict[str, Any]]:
        request_filter = str(request_id or '').strip() or None
        batch_filter = str(batch_ref or '').strip() or None
        action_filter = str(action_code or '').strip() or None
        status_filter = str(status or '').strip() or None
        jobs = []
        for job in ACTION_JOBS.values():
            if request_filter and str(job.get('requestId') or '') != request_filter:
                continue
            if batch_filter and str(job.get('batchRef') or job.get('batchId') or '') != batch_filter:
                continue
            if action_filter and str(job.get('actionCode') or '') != action_filter:
                continue
            if status_filter and str(job.get('jobStatus') or '') != status_filter:
                continue
            jobs.append(job)
        return self._sort_jobs(jobs)

    def _aggregate_jobs(self, jobs: list[Dict[str, Any]]) -> Dict[str, Any]:
        summary = {
            'totalJobs': len(jobs),
            'queuedJobs': 0,
            'runningJobs': 0,
            'succeededJobs': 0,
            'failedJobs': 0,
            'deadLetterJobs': 0,
            'retryableJobs': 0,
            'redriveableJobs': 0,
            'deadLetterableJobs': 0,
        }
        status_summary: dict[str, int] = {}
        recovery_state_summary: dict[str, int] = {}
        action_code_summary: dict[str, int] = {}
        batch_summary: dict[str, int] = {}
        request_ids: set[str] = set()
        for job in jobs:
            status = self._status(job)
            recovery_state = str(job.get('recoveryState') or 'healthy')
            action_code = str(job.get('actionCode') or 'unknown')
            batch_key = str(job.get('batchRef') or job.get('batchId') or 'unscoped')
            request_id = str(job.get('requestId') or '').strip()
            recommended_operation = self._job_recommended_operation(job)
            if request_id:
                request_ids.add(request_id)
            status_summary[status] = int(status_summary.get(status, 0)) + 1
            recovery_state_summary[recovery_state] = int(recovery_state_summary.get(recovery_state, 0)) + 1
            action_code_summary[action_code] = int(action_code_summary.get(action_code, 0)) + 1
            batch_summary[batch_key] = int(batch_summary.get(batch_key, 0)) + 1
            if status == 'queued':
                summary['queuedJobs'] += 1
            elif status == 'running':
                summary['runningJobs'] += 1
            elif status == 'succeeded':
                summary['succeededJobs'] += 1
            elif status == 'failed':
                summary['failedJobs'] += 1
            elif status == 'dead_letter':
                summary['deadLetterJobs'] += 1
            if recommended_operation == 'retry':
                summary['retryableJobs'] += 1
            elif recommended_operation == 'redrive':
                summary['redriveableJobs'] += 1
            elif recommended_operation == 'dead_letter':
                summary['deadLetterableJobs'] += 1
        summary['totalRequests'] = len(request_ids)
        summary['healthyJobs'] = max(
            summary['succeededJobs'] + summary['queuedJobs'] + summary['runningJobs'] - summary['failedJobs'] - summary['deadLetterJobs'],
            0,
        )
        return {
            'summary': summary,
            'statusSummary': status_summary,
            'recoveryStateSummary': recovery_state_summary,
            'actionCodeSummary': action_code_summary,
            'batchSummary': batch_summary,
        }

    def _recent_recovery_events(self, jobs: list[Dict[str, Any]], *, limit: int = 20) -> list[Dict[str, Any]]:
        tracked = {'job_retry_requested', 'job_redrive_requested', 'job_dead_lettered'}
        events: list[Dict[str, Any]] = []
        for job in jobs:
            request_id = str(job.get('requestId') or '')
            for event in ACTION_JOB_EVENTS.get(str(job.get('jobId')), []):
                if str(event.get('eventType') or '') not in tracked:
                    continue
                record = dict(event)
                record['requestId'] = request_id
                record['actionCode'] = job.get('actionCode')
                record['batchRef'] = job.get('batchRef') or job.get('batchId')
                events.append(record)
        events.sort(key=lambda item: (str(item.get('eventAt') or ''), str(item.get('eventId') or '')), reverse=True)
        return events[: max(int(limit or 0), 0)]

    def list_jobs_summary(
        self,
        *,
        request_id: str | None = None,
        batch_ref: str | None = None,
        action_code: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        jobs = self._list_jobs(request_id=request_id, batch_ref=batch_ref, action_code=action_code, status=status)
        aggregate = self._aggregate_jobs(jobs)
        items = []
        for job in jobs[: max(int(limit or 0), 0)]:
            payload = self._build_job_payload(job)
            payload['eventCount'] = len(ACTION_JOB_EVENTS.get(str(job.get('jobId')), []))
            items.append(payload)
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'filters': {
                'requestId': str(request_id or '').strip() or None,
                'batchRef': str(batch_ref or '').strip() or None,
                'actionCode': str(action_code or '').strip() or None,
                'status': str(status or '').strip() or None,
                'limit': max(int(limit or 0), 0),
            },
            **aggregate,
            'items': items,
            'total': len(jobs),
        }

    def get_jobs_dashboard(self, *, batch_ref: str | None = None, limit: int = 10) -> Dict[str, Any]:
        jobs = self._list_jobs(batch_ref=batch_ref)
        aggregate = self._aggregate_jobs(jobs)
        latest_jobs = []
        for job in jobs[: max(int(limit or 0), 0)]:
            payload = self._build_job_payload(job)
            payload['eventCount'] = len(ACTION_JOB_EVENTS.get(str(job.get('jobId')), []))
            latest_jobs.append(payload)
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'scope': {'batchRef': str(batch_ref or '').strip() or None},
            **aggregate,
            'latestJobs': latest_jobs,
            'latestJobsTotal': len(latest_jobs),
            'recentRecoveryEvents': self._recent_recovery_events(jobs, limit=20),
        }

    def get_batch_queue_health(self, batch_ref: str) -> Dict[str, Any]:
        normalized_batch = str(batch_ref or '').strip()
        if not normalized_batch:
            raise ValueError('batch_not_found')
        request_items = [
            item
            for item in ACTION_REQUESTS.values()
            if str(item.get('batchRef') or '').strip() == normalized_batch
        ]
        if not request_items:
            raise ValueError('batch_not_found')
        jobs = self._list_jobs(batch_ref=normalized_batch)
        aggregate = self._aggregate_jobs(jobs)
        request_summary = {
            'totalRequests': len(request_items),
            'draftRequests': 0,
            'pendingApprovalRequests': 0,
            'approvedRequests': 0,
            'pushedRequests': 0,
            'requestsWithFailures': 0,
            'requestsWithDeadLetter': 0,
            'requestsNeedingAttention': 0,
            'healthyRequests': 0,
        }
        request_status_summary: dict[str, int] = {}
        for item in request_items:
            status = str(item.get('status') or 'draft')
            request_status_summary[status] = int(request_status_summary.get(status, 0)) + 1
            if status == 'draft':
                request_summary['draftRequests'] += 1
            elif status == 'pending_review':
                request_summary['pendingApprovalRequests'] += 1
            elif status == 'approved':
                request_summary['approvedRequests'] += 1
            elif status == 'pushed':
                request_summary['pushedRequests'] += 1
            request_jobs = [job for job in jobs if str(job.get('requestId') or '') == str(item.get('requestId') or '')]
            has_dead_letter = any(str(job.get('jobStatus') or '') == 'dead_letter' for job in request_jobs)
            has_failed = any(str(job.get('jobStatus') or '') == 'failed' for job in request_jobs)
            if has_dead_letter:
                request_summary['requestsWithDeadLetter'] += 1
            if has_failed:
                request_summary['requestsWithFailures'] += 1
            if has_dead_letter or has_failed:
                request_summary['requestsNeedingAttention'] += 1
            if request_jobs and all(str(job.get('jobStatus') or '') in {'queued', 'running', 'succeeded'} for job in request_jobs):
                request_summary['healthyRequests'] += 1
        timeline: list[Dict[str, Any]] = []
        for job in jobs:
            for event in ACTION_JOB_EVENTS.get(str(job.get('jobId')), []):
                record = dict(event)
                record['requestId'] = job.get('requestId')
                record['actionCode'] = job.get('actionCode')
                timeline.append(record)
        timeline.sort(key=lambda item: (str(item.get('eventAt') or ''), str(item.get('eventId') or '')), reverse=True)
        latest_jobs = []
        for job in jobs[:10]:
            payload = self._build_job_payload(job)
            payload['eventCount'] = len(ACTION_JOB_EVENTS.get(str(job.get('jobId')), []))
            latest_jobs.append(payload)
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'batchRef': normalized_batch,
            'requestSummary': request_summary,
            'requestStatusSummary': request_status_summary,
            **aggregate,
            'latestJobs': latest_jobs,
            'latestJobsTotal': len(latest_jobs),
            'timeline': timeline[:50],
            'timelineTotal': len(timeline),
            'recentRecoveryEvents': self._recent_recovery_events(jobs, limit=20),
        }

    def get_jobs_metrics(
        self,
        *,
        request_id: str | None = None,
        batch_ref: str | None = None,
        action_code: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        jobs = self._list_jobs(request_id=request_id, batch_ref=batch_ref, action_code=action_code, status=status)
        now_dt = datetime.now(timezone.utc)
        snapshots = [self._job_metrics_snapshot(job, now_dt=now_dt) for job in jobs]
        queue_values = [float(item['queueLagSeconds']) for item in snapshots if item.get('queueLagSeconds') is not None]
        run_values = [float(item['runDurationSeconds']) for item in snapshots if item.get('runDurationSeconds') is not None]
        turnaround_values = [float(item['turnaroundSeconds']) for item in snapshots if item.get('turnaroundSeconds') is not None]
        lag_buckets = {'under60s': 0, '60to300s': 0, 'over300s': 0}
        sla = {'queueLagBreaches': 0, 'runDurationBreaches': 0, 'turnaroundBreaches': 0}
        for item in snapshots:
            queue_lag = item.get('queueLagSeconds')
            if queue_lag is not None:
                if queue_lag < 60:
                    lag_buckets['under60s'] += 1
                elif queue_lag <= 300:
                    lag_buckets['60to300s'] += 1
                else:
                    lag_buckets['over300s'] += 1
            if item.get('queueLagSlaBreached'):
                sla['queueLagBreaches'] += 1
            if item.get('runDurationSlaBreached'):
                sla['runDurationBreaches'] += 1
            if item.get('turnaroundSlaBreached'):
                sla['turnaroundBreaches'] += 1
        top_lagging_jobs = sorted(snapshots, key=lambda item: float(item.get('queueLagSeconds') or 0.0), reverse=True)[: max(int(limit or 0), 0)]
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'filters': {
                'requestId': str(request_id or '').strip() or None,
                'batchRef': str(batch_ref or '').strip() or None,
                'actionCode': str(action_code or '').strip() or None,
                'status': str(status or '').strip() or None,
                'limit': max(int(limit or 0), 0),
            },
            'summary': {
                'totalJobs': len(jobs),
                'activeJobs': sum(1 for job in jobs if str(job.get('jobStatus') or '') in {'queued', 'running'}),
                'finishedJobs': sum(1 for job in jobs if str(job.get('jobStatus') or '') in {'succeeded', 'failed', 'dead_letter'}),
            },
            'queueLagMetrics': self._summarize_metric(queue_values),
            'runDurationMetrics': self._summarize_metric(run_values),
            'turnaroundMetrics': self._summarize_metric(turnaround_values),
            'lagBuckets': lag_buckets,
            'sla': sla,
            'topLaggingJobs': top_lagging_jobs,
            'topLaggingJobsTotal': len(top_lagging_jobs),
        }

    def get_failure_buckets(
        self,
        *,
        request_id: str | None = None,
        batch_ref: str | None = None,
        action_code: str | None = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        jobs = [
            job for job in self._list_jobs(request_id=request_id, batch_ref=batch_ref, action_code=action_code)
            if str(job.get('jobStatus') or '') in {'failed', 'dead_letter'}
        ]
        reason_summary: dict[str, int] = {}
        reason_bucket_summary: dict[str, int] = {}
        recovery_state_summary: dict[str, int] = {}
        recommended_operation_summary: dict[str, int] = {}
        items = []
        for job in jobs:
            reason = str(job.get('deadLetterReason') or job.get('lastFailureReason') or (job.get('result') or {}).get('failureReason') or 'unknown')
            bucket = self._reason_bucket(reason)
            recovery_state = str(job.get('recoveryState') or 'unknown')
            recommended = self._job_recommended_operation(job) or 'none'
            reason_summary[reason] = int(reason_summary.get(reason, 0)) + 1
            reason_bucket_summary[bucket] = int(reason_bucket_summary.get(bucket, 0)) + 1
            recovery_state_summary[recovery_state] = int(recovery_state_summary.get(recovery_state, 0)) + 1
            recommended_operation_summary[recommended] = int(recommended_operation_summary.get(recommended, 0)) + 1
            payload = self._build_job_payload(job)
            payload['failureReason'] = reason
            payload['failureBucket'] = bucket
            items.append(payload)
        items = self._sort_jobs(items)[: max(int(limit or 0), 0)]
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'filters': {
                'requestId': str(request_id or '').strip() or None,
                'batchRef': str(batch_ref or '').strip() or None,
                'actionCode': str(action_code or '').strip() or None,
                'limit': max(int(limit or 0), 0),
            },
            'summary': {'totalFailedJobs': len(jobs), 'deadLetterJobs': sum(1 for job in jobs if str(job.get('jobStatus') or '') == 'dead_letter')},
            'reasonSummary': reason_summary,
            'reasonBucketSummary': reason_bucket_summary,
            'recoveryStateSummary': recovery_state_summary,
            'recommendedOperationSummary': recommended_operation_summary,
            'items': items,
            'total': len(jobs),
        }

    def get_job_audit(self, job_id: str) -> Dict[str, Any]:
        payload = self.get_job_detail(job_id)
        if not payload:
            raise ValueError('job_not_found')
        metrics = self._job_metrics_snapshot(payload)
        timeline = list(payload.get('timeline') or [])
        event_type_summary: dict[str, int] = {}
        for event in timeline:
            event_type = str(event.get('eventType') or 'unknown')
            event_type_summary[event_type] = int(event_type_summary.get(event_type, 0)) + 1
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'scope': 'job',
            'jobId': str(job_id),
            'requestId': payload.get('requestId'),
            'batchRef': payload.get('batchRef') or payload.get('batchId'),
            'actionCode': payload.get('actionCode'),
            'jobStatus': payload.get('jobStatus'),
            'queueStatus': payload.get('queueStatus'),
            'recoveryState': payload.get('recoveryState'),
            'recommendedOperation': payload.get('recommendedOperation'),
            'availableCommands': payload.get('availableCommands'),
            'failureReason': payload.get('deadLetterReason') or payload.get('lastFailureReason'),
            'metrics': metrics,
            'timeline': timeline,
            'timelineTotal': len(timeline),
            'eventTypeSummary': event_type_summary,
        }

    def get_request_audit(self, request_id: str) -> Dict[str, Any]:
        request_item = self._get_request(request_id)
        recovery = self.get_request_recovery(request_id)
        metrics = self.get_jobs_metrics(request_id=request_id, limit=10)
        failure = self.get_failure_buckets(request_id=request_id, limit=10)
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'scope': 'request',
            'requestId': str(request_id),
            'batchRef': request_item.get('batchRef'),
            'actionCode': request_item.get('actionCode'),
            'requestStatus': request_item.get('status'),
            'requestedBy': request_item.get('requestedBy'),
            'summary': recovery.get('summary'),
            'statusSummary': recovery.get('statusSummary'),
            'recoveryStateSummary': recovery.get('recoveryStateSummary'),
            'timeline': recovery.get('timeline'),
            'timelineTotal': recovery.get('timelineTotal'),
            'metrics': metrics,
            'failureBuckets': failure,
        }

    def get_batch_audit(self, batch_ref: str) -> Dict[str, Any]:
        health = self.get_batch_queue_health(batch_ref)
        metrics = self.get_jobs_metrics(batch_ref=batch_ref, limit=20)
        failure = self.get_failure_buckets(batch_ref=batch_ref, limit=20)
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'scope': 'batch',
            'batchRef': str(batch_ref),
            'requestSummary': health.get('requestSummary'),
            'requestStatusSummary': health.get('requestStatusSummary'),
            'summary': health.get('summary'),
            'statusSummary': health.get('statusSummary'),
            'recoveryStateSummary': health.get('recoveryStateSummary'),
            'timeline': health.get('timeline'),
            'timelineTotal': health.get('timelineTotal'),
            'metrics': metrics,
            'failureBuckets': failure,
            'recentRecoveryEvents': health.get('recentRecoveryEvents'),
        }

    def get_worker_overview(self, *, batch_ref: str | None = None, limit: int = 10) -> Dict[str, Any]:
        jobs = self._list_jobs(batch_ref=batch_ref)
        now_dt = datetime.now(timezone.utc)
        queued_jobs = [job for job in jobs if self._status(job) in {'queued', 'accepted'}]
        running_jobs = [job for job in jobs if self._status(job) == 'running']
        stalled_jobs = []
        active_leases = []
        for job in running_jobs:
            lease_expires_at = self._parse_iso(job.get('leaseExpiresAt'))
            if lease_expires_at and lease_expires_at < now_dt:
                stalled_jobs.append(self._build_job_payload(job))
            if job.get('workerId') or job.get('leaseClaimedAt'):
                active = self._build_job_payload(job)
                active['leaseExpired'] = bool(lease_expires_at and lease_expires_at < now_dt)
                active_leases.append(active)
        next_jobs = []
        queued_ordered = sorted(queued_jobs, key=lambda item: (str(item.get('queuedAt') or item.get('acceptedAt') or ''), str(item.get('jobId') or '')))
        for job in queued_ordered[: max(int(limit or 0), 0)]:
            payload = self._build_job_payload(job)
            payload['eventCount'] = len(ACTION_JOB_EVENTS.get(str(job.get('jobId')), []))
            next_jobs.append(payload)
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'scope': {'batchRef': str(batch_ref or '').strip() or None},
            'summary': {
                'totalJobs': len(jobs),
                'queuedJobs': len(queued_jobs),
                'runningJobs': len(running_jobs),
                'leasedJobs': len(active_leases),
                'stalledJobs': len(stalled_jobs),
                'finishedJobs': sum(1 for job in jobs if self._status(job) in {'succeeded', 'failed', 'dead_letter'}),
                'deadLetterJobs': sum(1 for job in jobs if self._status(job) == 'dead_letter'),
            },
            'nextJobs': next_jobs,
            'nextJobsTotal': len(next_jobs),
            'activeLeases': active_leases[: max(int(limit or 0), 0)],
            'activeLeasesTotal': len(active_leases),
            'stalledJobs': stalled_jobs[: max(int(limit or 0), 0)],
            'stalledJobsTotal': len(stalled_jobs),
        }


    def get_worker_stale_jobs(self, *, batch_ref: str | None = None, limit: int = 10) -> Dict[str, Any]:
        jobs = self._list_jobs(batch_ref=batch_ref)
        now_dt = datetime.now(timezone.utc)
        stale_items: list[Dict[str, Any]] = []
        for job in jobs:
            if self._status(job) != 'running':
                continue
            lease_expires_at = self._parse_iso(job.get('leaseExpiresAt'))
            lease_heartbeat_at = self._parse_iso(job.get('leaseHeartbeatAt'))
            if not lease_expires_at or lease_expires_at >= now_dt:
                continue
            stale_seconds = self._seconds_between(lease_expires_at, now_dt) or 0.0
            heartbeat_age_seconds = self._seconds_between(lease_heartbeat_at, now_dt)
            payload = self._build_job_payload(job)
            payload['staleSeconds'] = round(float(stale_seconds), 3)
            payload['heartbeatAgeSeconds'] = round(float(heartbeat_age_seconds or 0.0), 3)
            payload['staleCategory'] = 'lease_expired'
            stale_items.append(payload)
        stale_items = sorted(
            stale_items,
            key=lambda item: (float(item.get('staleSeconds') or 0.0), str(item.get('jobId') or '')),
            reverse=True,
        )
        oldest_stale = max((float(item.get('staleSeconds') or 0.0) for item in stale_items), default=0.0)
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'scope': {'batchRef': str(batch_ref or '').strip() or None},
            'summary': {
                'staleJobs': len(stale_items),
                'oldestStaleSeconds': round(oldest_stale, 3),
                'leaseTtlSeconds': self.LEASE_TTL_SECONDS,
            },
            'items': stale_items[: max(int(limit or 0), 0)],
            'total': len(stale_items),
        }

    def release_stale_jobs(
        self,
        *,
        batch_ref: str | None = None,
        worker_id: str | None = None,
        operator: str = 'system',
        limit: int = 20,
        reason: str | None = None,
        note: str | None = None,
    ) -> Dict[str, Any]:
        batch_filter = str(batch_ref or '').strip() or None
        worker_filter = str(worker_id or '').strip() or None
        stale_view = self.get_worker_stale_jobs(batch_ref=batch_filter, limit=max(int(limit or 0), 0) or 20)
        items: list[Dict[str, Any]] = []
        released = 0
        skipped = 0
        release_reason = str(reason or '').strip() or 'stale_lease_expired'
        for stale in list(stale_view.get('items') or []):
            job = ACTION_JOBS.get(str(stale.get('jobId') or ''))
            if not job or self._status(job) != 'running':
                skipped += 1
                continue
            existing_worker = str(job.get('workerId') or '').strip() or None
            if worker_filter and existing_worker != worker_filter:
                skipped += 1
                continue
            now = utcnow_iso()
            stale_seconds = float(stale.get('staleSeconds') or 0.0)
            job.update({
                'jobStatus': 'queued',
                'queueStatus': 'queued',
                'workerState': 'released_stale',
                'workerId': None,
                'leaseClaimedAt': None,
                'leaseHeartbeatAt': None,
                'leaseExpiresAt': None,
                'lastRecoveryOperation': 'stale_release',
                'lastRecoveryReason': release_reason,
                'lastRecoveryAt': now,
                'recoveryState': 'healthy',
                'queueSequence': self._next_queue_sequence(),
            })
            self._complete_result(job, accepted=True, queued=True, completed=False, message='stale_lease_released')
            if existing_worker:
                job['result']['releasedWorkerId'] = existing_worker
            if note:
                job['result']['releaseNote'] = note
            event = self.append_job_event(
                str(job.get('jobId')),
                event_type='job_stale_released',
                status='queued',
                actor=operator,
                message='action_push_job_stale_released',
                payload={'workerId': existing_worker, 'reason': release_reason, 'note': note, 'staleSeconds': round(stale_seconds, 3)},
                event_at=now,
            )
            payload = self._build_job_payload(job)
            payload['staleSeconds'] = round(stale_seconds, 3)
            payload['releaseEventId'] = event.get('eventId')
            items.append(payload)
            released += 1
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'scope': {'batchRef': batch_filter, 'workerId': worker_filter, 'limit': max(int(limit or 0), 0) or 20},
            'summary': {
                'staleMatched': int(stale_view.get('total') or 0),
                'releasedJobs': released,
                'skippedJobs': skipped,
            },
            'items': items,
            'total': len(items),
        }

    def claim_next_job(self, *, worker_id: str, operator: str = 'worker', batch_ref: str | None = None, note: str | None = None) -> Dict[str, Any]:
        normalized_worker = str(worker_id or '').strip()
        if not normalized_worker:
            raise ValueError('worker_id_required')
        candidates = [job for job in self._list_jobs(batch_ref=batch_ref) if self._status(job) in {'queued', 'accepted'}]
        if not candidates:
            raise ValueError('no_job_available')
        job = sorted(
            candidates,
            key=lambda item: (
                int(item.get('queueSequence') or 0) if str(item.get('queueSequence') or '').strip() else 0,
                str(item.get('queuedAt') or item.get('acceptedAt') or ''),
                str(item.get('jobId') or ''),
            ),
        )[0]
        now = utcnow_iso()
        attempt_count = int(job.get('attemptCount') or 0) + 1
        generation = int(job.get('leaseGeneration') or 0) + 1
        lease_expires = datetime.fromisoformat(now).astimezone(timezone.utc).timestamp() + float(self.LEASE_TTL_SECONDS)
        lease_expires_at = datetime.fromtimestamp(lease_expires, tz=timezone.utc).isoformat()
        job.update({
            'jobStatus': 'running',
            'queueStatus': 'claimed',
            'startedAt': job.get('startedAt') or now,
            'attemptCount': attempt_count,
            'workerState': 'claimed',
            'workerId': normalized_worker,
            'leaseClaimedAt': now,
            'leaseHeartbeatAt': now,
            'leaseExpiresAt': lease_expires_at,
            'leaseGeneration': generation,
            'recoveryState': 'in_progress',
        })
        if note:
            job['note'] = note
        self._complete_result(job, accepted=True, queued=True, completed=False, message='worker_claimed')
        self.append_job_event(str(job.get('jobId')), event_type='job_claimed', status='running', actor=operator, message='action_push_job_claimed', payload={'workerId': normalized_worker, 'leaseGeneration': generation, 'note': note}, event_at=now)
        return self._build_job_payload(job)

    def heartbeat_job(self, job_id: str, *, worker_id: str, operator: str = 'worker', note: str | None = None) -> Dict[str, Any]:
        job = self._get_job(job_id)
        normalized_worker = str(worker_id or '').strip()
        if not normalized_worker:
            raise ValueError('worker_id_required')
        if self._status(job) != 'running':
            raise ValueError('job_not_heartbeatable')
        existing_worker = str(job.get('workerId') or '').strip()
        if existing_worker and existing_worker != normalized_worker:
            raise ValueError('worker_mismatch')
        now = utcnow_iso()
        lease_expires = datetime.fromisoformat(now).astimezone(timezone.utc).timestamp() + float(self.LEASE_TTL_SECONDS)
        lease_expires_at = datetime.fromtimestamp(lease_expires, tz=timezone.utc).isoformat()
        job.update({
            'workerState': 'heartbeat',
            'workerId': normalized_worker,
            'leaseHeartbeatAt': now,
            'leaseExpiresAt': lease_expires_at,
        })
        self.append_job_event(str(job_id), event_type='job_heartbeat', status='running', actor=operator, message='action_push_job_heartbeat', payload={'workerId': normalized_worker, 'note': note}, event_at=now)
        return self._build_job_payload(job)

    def _validate_worker_control(self, job: Dict[str, Any], worker_id: str) -> str:
        normalized_worker = str(worker_id or '').strip()
        if not normalized_worker:
            raise ValueError('worker_id_required')
        existing_worker = str(job.get('workerId') or '').strip()
        if existing_worker and existing_worker != normalized_worker:
            raise ValueError('worker_mismatch')
        return normalized_worker

    def release_job_lease(self, job_id: str, *, worker_id: str, operator: str = 'worker', reason: str | None = None, note: str | None = None, idempotency_key: str | None = None) -> Dict[str, Any]:
        existing = self._idempotent_job_command(job_id, 'release_lease', idempotency_key)
        if existing:
            return existing
        job = self._get_job(job_id)
        if self._status(job) != 'running':
            raise ValueError('job_not_releasable')
        normalized_worker = self._validate_worker_control(job, worker_id)
        now = utcnow_iso()
        job.update({
            'jobStatus': 'queued',
            'queueStatus': 'queued',
            'workerState': 'released',
            'workerId': None,
            'lastLeaseWorkerId': normalized_worker,
            'leaseClaimedAt': None,
            'leaseHeartbeatAt': None,
            'leaseExpiresAt': None,
            'lastRecoveryOperation': 'lease_release',
            'lastRecoveryReason': reason,
            'lastRecoveryAt': now,
            'recoveryState': 'healthy',
        })
        self._complete_result(job, accepted=True, queued=True, completed=False, message='lease_released')
        if reason:
            job['result']['releaseReason'] = reason
        if note:
            job['result']['releaseNote'] = note
        self.append_job_event(str(job_id), event_type='job_lease_released', status='queued', actor=operator, message='action_push_job_lease_released', payload={'workerId': normalized_worker, 'reason': reason, 'note': note}, event_at=now)
        self._remember_job_command(job_id, 'release_lease', idempotency_key)
        return self._build_job_payload(job)

    def mark_job_succeeded(self, job_id: str, *, worker_id: str, operator: str = 'worker', external_ref: str | None = None, note: str | None = None, idempotency_key: str | None = None) -> Dict[str, Any]:
        existing = self._idempotent_job_command(job_id, 'mark_succeeded', idempotency_key)
        if existing:
            return existing
        job = self._get_job(job_id)
        normalized_worker = self._validate_worker_control(job, worker_id)
        current_status = self._status(job)
        released_worker = str(job.get('lastLeaseWorkerId') or '').strip() or None
        released_completion_allowed = current_status == 'queued' and str(job.get('workerState') or '').strip() == 'released' and released_worker == normalized_worker
        if current_status != 'running' and not released_completion_allowed:
            raise ValueError('job_not_completable')
        now = utcnow_iso()
        job.update({
            'jobStatus': 'succeeded',
            'queueStatus': 'completed',
            'finishedAt': now,
            'workerState': 'completed',
            'leaseHeartbeatAt': now,
            'leaseExpiresAt': None,
            'recoveryState': 'healthy',
            'lastFailureReason': None,
            'lastLeaseWorkerId': normalized_worker,
        })
        self._complete_result(job, accepted=True, queued=True, completed=True, externalRef=external_ref, message='worker_marked_succeeded')
        if note:
            job['result']['completionNote'] = note
        self.append_job_event(str(job_id), event_type='job_succeeded', status='succeeded', actor=operator, message='action_push_job_succeeded', payload={'externalRef': external_ref, 'workerId': normalized_worker, 'note': note, 'completionSource': 'worker_command'}, event_at=now)
        self._remember_job_command(job_id, 'mark_succeeded', idempotency_key)
        return self._build_job_payload(job)

    def mark_job_failed(self, job_id: str, *, worker_id: str, operator: str = 'worker', reason: str, note: str | None = None, idempotency_key: str | None = None) -> Dict[str, Any]:
        existing = self._idempotent_job_command(job_id, 'mark_failed', idempotency_key)
        if existing:
            return existing
        job = self._get_job(job_id)
        if self._status(job) != 'running':
            raise ValueError('job_not_failurable')
        normalized_worker = self._validate_worker_control(job, worker_id)
        now = utcnow_iso()
        attempt_count = int(job.get('attemptCount') or 0)
        max_attempts = int(job.get('maxAttempts') or self.DEFAULT_MAX_ATTEMPTS)
        recovery_state = 'retryable' if attempt_count < max_attempts else 'dead_letter_recommended'
        job.update({
            'jobStatus': 'failed',
            'queueStatus': 'failed',
            'finishedAt': now,
            'workerState': 'failed',
            'leaseHeartbeatAt': now,
            'leaseExpiresAt': None,
            'recoveryState': recovery_state,
            'lastFailureReason': reason,
        })
        self._complete_result(job, accepted=True, queued=True, completed=True, failureReason=reason, message='worker_marked_failed')
        if note:
            job['result']['failureNote'] = note
        self.append_job_event(str(job_id), event_type='job_failed', status='failed', actor=operator, message='action_push_job_failed', payload={'reason': reason, 'workerId': normalized_worker, 'note': note, 'failureSource': 'worker_command'}, event_at=now)
        self._remember_job_command(job_id, 'mark_failed', idempotency_key)
        return self._build_job_payload(job)

    def get_worker_lease_audit(
        self,
        *,
        batch_ref: str | None = None,
        worker_id: str | None = None,
        event_type: str | None = None,
        action_code: str | None = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        jobs = self._list_jobs(batch_ref=batch_ref)
        worker_filter = str(worker_id or '').strip() or None
        event_type_filter = str(event_type or '').strip() or None
        action_code_filter = str(action_code or '').strip() or None
        items: list[Dict[str, Any]] = []
        summary = {
            'totalEvents': 0,
            'claimEvents': 0,
            'heartbeatEvents': 0,
            'releaseEvents': 0,
            'succeededEvents': 0,
            'failedEvents': 0,
            'trackedWorkers': 0,
        }
        workers: set[str] = set()
        tracked_types = {'job_claimed', 'job_heartbeat', 'job_lease_released', 'job_succeeded', 'job_failed'}
        event_type_summary: dict[str, int] = {}
        action_code_summary: dict[str, int] = {}
        for job in jobs:
            job_id = str(job.get('jobId') or '')
            action_code_value = str(job.get('actionCode') or 'unknown')
            if action_code_filter and action_code_value != action_code_filter:
                continue
            for event in ACTION_JOB_EVENTS.get(job_id, []):
                event_type_value = str(event.get('eventType') or '')
                if event_type_value not in tracked_types:
                    continue
                if event_type_filter and event_type_value != event_type_filter:
                    continue
                payload = dict(event.get('payload') or {})
                event_worker = str(payload.get('workerId') or '').strip() or None
                if event_type_value in {'job_succeeded', 'job_failed'} and str(event.get('actor') or '') == 'provider' and not event_worker:
                    continue
                if worker_filter and event_worker != worker_filter:
                    continue
                if event_worker:
                    workers.add(event_worker)
                record = dict(event)
                record['requestId'] = job.get('requestId')
                record['batchRef'] = job.get('batchRef') or job.get('batchId')
                record['actionCode'] = job.get('actionCode')
                record['workerId'] = event_worker
                items.append(record)
                summary['totalEvents'] += 1
                event_type_summary[event_type_value] = int(event_type_summary.get(event_type_value, 0)) + 1
                action_code_summary[action_code_value] = int(action_code_summary.get(action_code_value, 0)) + 1
                if event_type_value == 'job_claimed':
                    summary['claimEvents'] += 1
                elif event_type_value == 'job_heartbeat':
                    summary['heartbeatEvents'] += 1
                elif event_type_value == 'job_lease_released':
                    summary['releaseEvents'] += 1
                elif event_type_value == 'job_succeeded':
                    summary['succeededEvents'] += 1
                elif event_type_value == 'job_failed':
                    summary['failedEvents'] += 1
        summary['trackedWorkers'] = len(workers)
        items.sort(key=lambda item: (str(item.get('eventAt') or ''), str(item.get('eventId') or '')), reverse=True)
        limited = items[: max(int(limit or 0), 0)]
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'scope': {
                'batchRef': str(batch_ref or '').strip() or None,
                'workerId': worker_filter,
                'eventType': event_type_filter,
                'actionCode': action_code_filter,
            },
            'summary': summary,
            'eventTypeSummary': event_type_summary,
            'actionCodeSummary': action_code_summary,
            'items': limited,
            'total': len(items),
        }

    def get_worker_command_audit(
        self,
        *,
        batch_ref: str | None = None,
        worker_id: str | None = None,
        event_type: str | None = None,
        action_code: str | None = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        jobs = self._list_jobs(batch_ref=batch_ref)
        worker_filter = str(worker_id or '').strip() or None
        event_type_filter = str(event_type or '').strip() or None
        action_code_filter = str(action_code or '').strip() or None
        items: list[Dict[str, Any]] = []
        summary = {
            'totalEvents': 0,
            'claimEvents': 0,
            'heartbeatEvents': 0,
            'releaseEvents': 0,
            'staleReleaseEvents': 0,
            'succeededEvents': 0,
            'failedEvents': 0,
            'retryEvents': 0,
            'redriveEvents': 0,
            'deadLetterEvents': 0,
            'trackedWorkers': 0,
        }
        workers: set[str] = set()
        tracked_types = {
            'job_claimed', 'job_heartbeat', 'job_lease_released', 'job_stale_released',
            'job_succeeded', 'job_failed', 'job_retry_requested', 'job_redrive_requested', 'job_dead_lettered'
        }
        command_type_summary: dict[str, int] = {}
        action_code_summary: dict[str, int] = {}
        for job in jobs:
            job_id = str(job.get('jobId') or '')
            action_code_value = str(job.get('actionCode') or 'unknown')
            if action_code_filter and action_code_value != action_code_filter:
                continue
            for event in ACTION_JOB_EVENTS.get(job_id, []):
                event_type_value = str(event.get('eventType') or '')
                if event_type_value not in tracked_types:
                    continue
                if event_type_filter and event_type_value != event_type_filter:
                    continue
                payload = dict(event.get('payload') or {})
                event_worker = str(payload.get('workerId') or '').strip() or None
                if event_type_value in {'job_succeeded', 'job_failed'} and str(event.get('actor') or '') == 'provider' and not event_worker:
                    continue
                if worker_filter and event_worker != worker_filter:
                    continue
                if event_worker:
                    workers.add(event_worker)
                record = dict(event)
                record['requestId'] = job.get('requestId')
                record['batchRef'] = job.get('batchRef') or job.get('batchId')
                record['actionCode'] = job.get('actionCode')
                record['workerId'] = event_worker
                items.append(record)
                summary['totalEvents'] += 1
                command_type_summary[event_type_value] = int(command_type_summary.get(event_type_value, 0)) + 1
                action_code_summary[action_code_value] = int(action_code_summary.get(action_code_value, 0)) + 1
                if event_type_value == 'job_claimed':
                    summary['claimEvents'] += 1
                elif event_type_value == 'job_heartbeat':
                    summary['heartbeatEvents'] += 1
                elif event_type_value == 'job_lease_released':
                    summary['releaseEvents'] += 1
                elif event_type_value == 'job_stale_released':
                    summary['staleReleaseEvents'] += 1
                elif event_type_value == 'job_succeeded':
                    summary['succeededEvents'] += 1
                elif event_type_value == 'job_failed':
                    summary['failedEvents'] += 1
                elif event_type_value == 'job_retry_requested':
                    summary['retryEvents'] += 1
                elif event_type_value == 'job_redrive_requested':
                    summary['redriveEvents'] += 1
                elif event_type_value == 'job_dead_lettered':
                    summary['deadLetterEvents'] += 1
        summary['trackedWorkers'] = len(workers)
        items.sort(key=lambda item: (str(item.get('eventAt') or ''), str(item.get('eventId') or '')), reverse=True)
        limited = items[: max(int(limit or 0), 0)]
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'scope': {
                'batchRef': str(batch_ref or '').strip() or None,
                'workerId': worker_filter,
                'eventType': event_type_filter,
                'actionCode': action_code_filter,
            },
            'summary': summary,
            'commandTypeSummary': command_type_summary,
            'actionCodeSummary': action_code_summary,
            'items': limited,
            'total': len(items),
        }

    def get_worker_command_audit_detail(self, event_id: str) -> Dict[str, Any]:
        normalized_event = str(event_id or '').strip()
        if not normalized_event:
            raise ValueError('command_audit_event_not_found')
        for job in ACTION_JOBS.values():
            job_id = str(job.get('jobId') or '')
            for event in ACTION_JOB_EVENTS.get(job_id, []):
                if str(event.get('eventId') or '') != normalized_event:
                    continue
                payload = dict(event.get('payload') or {})
                record = dict(event)
                record['requestId'] = job.get('requestId')
                record['batchRef'] = job.get('batchRef') or job.get('batchId')
                record['actionCode'] = job.get('actionCode')
                record['workerId'] = str(payload.get('workerId') or job.get('workerId') or '').strip() or None
                record['jobStatus'] = job.get('jobStatus')
                record['queueStatus'] = job.get('queueStatus')
                timeline = [dict(item) for item in ACTION_JOB_EVENTS.get(job_id, [])]
                timeline.sort(key=lambda item: (str(item.get('eventAt') or ''), str(item.get('eventId') or '')), reverse=True)
                return {
                    'contractVersion': self.CONTRACT_VERSION,
                    'eventId': normalized_event,
                    'commandAudit': record,
                    'job': self._build_job_payload(job),
                    'timeline': timeline[:20],
                    'timelineTotal': len(timeline),
                }
        raise ValueError('command_audit_event_not_found')


    def _bulk_command_scope(self, batch_ref: str | None, command: str | None) -> str:
        normalized_batch = str(batch_ref or '').strip() or 'all'
        normalized_command = str(command or '').strip() or 'all'
        return f'bulk:{normalized_batch}:{normalized_command}'

    def _record_bulk_command(
        self,
        *,
        command: str,
        operator: str,
        worker_id: str | None,
        reason: str | None,
        note: str | None,
        external_ref: str | None,
        items: list[Dict[str, Any]],
        errors: list[Dict[str, Any]],
        reexecute_of: str | None = None,
        selection: str | None = None,
        reexecute_command: str | None = None,
        lineage_scope: str | None = None,
        source_bulk_command_ids: list[str] | None = None,
    ) -> Dict[str, Any]:
        batch_refs = sorted({str(item.get('batchRef') or item.get('batchId') or 'unscoped') for item in items if item.get('batchRef') or item.get('batchId')})
        action_codes = sorted({str(item.get('actionCode') or 'unknown') for item in items if item.get('actionCode')})
        request_ids = sorted({str(item.get('requestId') or '') for item in items if item.get('requestId')})
        item_status_summary: dict[str, int] = {}
        error_reason_summary: dict[str, int] = {}
        for item in items:
            status_key = str(item.get('jobStatus') or item.get('queueStatus') or 'unknown')
            item_status_summary[status_key] = int(item_status_summary.get(status_key, 0)) + 1
        for error in errors:
            reason_key = str(error.get('reason') or 'unknown')
            error_reason_summary[reason_key] = int(error_reason_summary.get(reason_key, 0)) + 1
        bulk_id = new_id('bulkcmd')
        event_at = utcnow_iso()
        parent_id = str(reexecute_of or '').strip() or None
        parent_record = ACTION_BULK_COMMANDS.get(parent_id) if parent_id else None
        root_bulk_command_id = str((parent_record or {}).get('rootBulkCommandId') or parent_id or bulk_id)
        command_mode = 'lineage' if str(lineage_scope or '').strip() or (source_bulk_command_ids or []) else ('reexecute' if parent_id else 'direct')
        record = {
            'contractVersion': self.CONTRACT_VERSION,
            'bulkCommandId': bulk_id,
            'eventAt': event_at,
            'command': command,
            'commandMode': command_mode,
            'operator': operator,
            'workerId': worker_id,
            'reason': reason,
            'note': note,
            'externalRef': external_ref,
            'scope': {
                'batchRefs': batch_refs,
                'actionCodes': action_codes,
                'requestIds': request_ids,
            },
            'summary': {
                'requestedJobs': len(items) + len(errors),
                'succeededJobs': len(items),
                'failedJobs': len(errors),
            },
            'itemStatusSummary': item_status_summary,
            'errorReasonSummary': error_reason_summary,
            'items': [dict(item) for item in items],
            'errors': [dict(item) for item in errors],
            'total': len(items),
            'reexecuteOf': parent_id,
            'rootBulkCommandId': root_bulk_command_id,
            'selection': str(selection or '').strip() or None,
            'reexecuteCommand': str(reexecute_command or '').strip() or None,
            'lineageScope': str(lineage_scope or '').strip() or None,
            'sourceBulkCommandIds': [str(item) for item in (source_bulk_command_ids or []) if str(item).strip()],
            'childBulkCommandIds': [],
            'latestChildBulkCommandId': None,
            'latestChildEventAt': None,
        }
        ACTION_BULK_COMMANDS[bulk_id] = record
        ACTION_BULK_COMMAND_ORDER.append(bulk_id)
        if parent_record is not None:
            child_ids = [str(item) for item in parent_record.get('childBulkCommandIds') or [] if str(item).strip()]
            if bulk_id not in child_ids:
                child_ids.append(bulk_id)
            parent_record['childBulkCommandIds'] = child_ids
            parent_record['latestChildBulkCommandId'] = bulk_id
            parent_record['latestChildEventAt'] = event_at
        return record

    @staticmethod
    def _bulk_result_mode(record: Dict[str, Any]) -> str:
        summary = dict(record.get('summary') or {})
        succeeded = int(summary.get('succeededJobs') or 0)
        failed = int(summary.get('failedJobs') or 0)
        if succeeded and failed:
            return 'partial'
        if failed:
            return 'failed'
        return 'succeeded'


    def _bulk_related_records(self, bulk_command_id: str) -> list[Dict[str, Any]]:
        bulk_id = str(bulk_command_id or '').strip()
        record = ACTION_BULK_COMMANDS.get(bulk_id)
        if not record:
            return []
        root_id = str(record.get('rootBulkCommandId') or bulk_id)
        related: list[Dict[str, Any]] = []
        for candidate_id in ACTION_BULK_COMMAND_ORDER:
            candidate = ACTION_BULK_COMMANDS.get(candidate_id)
            if not candidate:
                continue
            candidate_root = str(candidate.get('rootBulkCommandId') or candidate.get('bulkCommandId') or '')
            if candidate_root == root_id:
                related.append(candidate)
        return related

    def _bulk_parent_chain(self, record: Dict[str, Any]) -> list[str]:
        chain: list[str] = []
        current_parent = str(record.get('reexecuteOf') or '').strip() or None
        visited: set[str] = set()
        while current_parent and current_parent not in visited:
            visited.add(current_parent)
            chain.append(current_parent)
            current_record = ACTION_BULK_COMMANDS.get(current_parent)
            current_parent = str((current_record or {}).get('reexecuteOf') or '').strip() or None
        return chain

    def _bulk_descendant_ids(self, bulk_command_id: str) -> list[str]:
        normalized_bulk_id = str(bulk_command_id or '').strip()
        if not normalized_bulk_id:
            return []
        descendants: list[str] = []
        for candidate_id in ACTION_BULK_COMMAND_ORDER:
            candidate = ACTION_BULK_COMMANDS.get(candidate_id)
            if not candidate:
                continue
            chain = self._bulk_parent_chain(candidate)
            if normalized_bulk_id in chain:
                descendants.append(str(candidate.get('bulkCommandId') or ''))
        return descendants

    def _bulk_lineage_payload(self, record: Dict[str, Any]) -> Dict[str, Any]:
        bulk_id = str(record.get('bulkCommandId') or '')
        child_ids = [str(item) for item in record.get('childBulkCommandIds') or [] if str(item).strip()]
        related_records = self._bulk_related_records(bulk_id)
        ancestor_ids = self._bulk_parent_chain(record)
        descendant_ids = self._bulk_descendant_ids(bulk_id)
        return {
            'bulkCommandId': bulk_id,
            'rootBulkCommandId': str(record.get('rootBulkCommandId') or bulk_id),
            'reexecuteOf': str(record.get('reexecuteOf') or '').strip() or None,
            'selection': str(record.get('selection') or '').strip() or None,
            'reexecuteCommand': str(record.get('reexecuteCommand') or '').strip() or None,
            'commandMode': str(record.get('commandMode') or '').strip() or 'direct',
            'lineageScope': str(record.get('lineageScope') or '').strip() or None,
            'sourceBulkCommandIds': [str(item) for item in record.get('sourceBulkCommandIds') or [] if str(item).strip()],
            'childBulkCommandIds': child_ids,
            'childCount': len(child_ids),
            'latestChildBulkCommandId': str(record.get('latestChildBulkCommandId') or '').strip() or None,
            'latestChildEventAt': str(record.get('latestChildEventAt') or '').strip() or None,
            'relatedResultCount': len(related_records),
            'lineageDepth': len(ancestor_ids),
            'ancestorBulkCommandIds': ancestor_ids,
            'descendantBulkCommandIds': descendant_ids,
            'descendantCount': len(descendant_ids),
        }

    @staticmethod
    def _bulk_source_ids(record: Dict[str, Any]) -> list[str]:
        return [str(item) for item in record.get('sourceBulkCommandIds') or [] if str(item).strip()]

    def _matches_source_bulk_filter(self, record: Dict[str, Any], source_bulk_command_id: str | None) -> bool:
        normalized = str(source_bulk_command_id or '').strip() or None
        if not normalized:
            return True
        if str(record.get('bulkCommandId') or '') == normalized:
            return True
        if str(record.get('reexecuteOf') or '') == normalized:
            return True
        if str(record.get('rootBulkCommandId') or record.get('bulkCommandId') or '') == normalized:
            return True
        return normalized in self._bulk_source_ids(record)

    def _bulk_linked_filters(self, record: Dict[str, Any]) -> Dict[str, Any]:
        bulk_id = str(record.get('bulkCommandId') or '')
        lineage = self._bulk_lineage_payload(record)
        root_id = str(lineage.get('rootBulkCommandId') or bulk_id)
        parent_id = str(lineage.get('reexecuteOf') or '').strip() or None
        return {
            'focusBulkCommandId': bulk_id,
            'rootBulkCommandId': root_id,
            'parentBulkCommandId': parent_id,
            'sourceBulkCommandId': bulk_id,
            'lineageDepth': int(lineage.get('lineageDepth') or 0),
            'commandMode': str(record.get('commandMode') or 'direct'),
            'selection': str(record.get('selection') or '').strip() or None,
            'reexecuteCommand': str(record.get('reexecuteCommand') or '').strip() or None,
            'actionCodes': [str(code) for code in (dict(record.get('scope') or {}).get('actionCodes') or []) if str(code).strip()],
        }

    def get_bulk_command_related(self, bulk_command_id: str, *, limit: int = 20) -> Dict[str, Any]:
        bulk_id = str(bulk_command_id or '').strip()
        record = ACTION_BULK_COMMANDS.get(bulk_id)
        if not record:
            raise ValueError('bulk_command_not_found')
        related_records = list(reversed(self._bulk_related_records(bulk_id)))
        normalized_limit = max(int(limit or 0), 0) or 20
        limited = related_records[:normalized_limit]
        command_summary: dict[str, int] = {}
        result_mode_summary: dict[str, int] = {}
        items: list[Dict[str, Any]] = []
        for item in limited:
            command_key = str(item.get('command') or 'unknown')
            result_mode = self._bulk_result_mode(item)
            command_summary[command_key] = int(command_summary.get(command_key, 0)) + 1
            result_mode_summary[result_mode] = int(result_mode_summary.get(result_mode, 0)) + 1
            items.append({
                'bulkCommandId': item.get('bulkCommandId'),
                'eventAt': item.get('eventAt'),
                'command': item.get('command'),
                'commandMode': item.get('commandMode'),
                'operator': item.get('operator'),
                'workerId': item.get('workerId'),
                'summary': dict(item.get('summary') or {}),
                'resultMode': result_mode,
                'lineage': self._bulk_lineage_payload(item),
                'isCurrent': str(item.get('bulkCommandId') or '') == bulk_id,
            })
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'bulkCommandId': bulk_id,
            'lineage': self._bulk_lineage_payload(record),
            'summary': {
                'totalResults': len(related_records),
                'returned': len(items),
            },
            'commandSummary': command_summary,
            'resultModeSummary': result_mode_summary,
            'items': items,
            'total': len(related_records),
        }

    def get_bulk_command_history(
        self,
        *,
        batch_ref: str | None = None,
        command: str | None = None,
        worker_id: str | None = None,
        action_code: str | None = None,
        result_mode: str | None = None,
        root_bulk_command_id: str | None = None,
        reexecute_of: str | None = None,
        parent_bulk_command_id: str | None = None,
        has_children: str | bool | None = None,
        lineage_depth: int | None = None,
        selection: str | None = None,
        reexecute_command: str | None = None,
        command_mode: str | None = None,
        source_bulk_command_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Dict[str, Any]:
        batch_filter = str(batch_ref or '').strip() or None
        command_filter = str(command or '').strip() or None
        worker_filter = str(worker_id or '').strip() or None
        action_filter = str(action_code or '').strip() or None
        result_filter = str(result_mode or '').strip() or None
        root_filter = str(root_bulk_command_id or '').strip() or None
        reexecute_filter = str(reexecute_of or '').strip() or None
        parent_filter = str(parent_bulk_command_id or '').strip() or None
        selection_filter = str(selection or '').strip() or None
        reexecute_command_filter = str(reexecute_command or '').strip() or None
        command_mode_filter = str(command_mode or '').strip() or None
        source_bulk_filter = str(source_bulk_command_id or '').strip() or None
        has_children_filter: bool | None = None
        if isinstance(has_children, bool):
            has_children_filter = has_children
        else:
            normalized_has_children = str(has_children or '').strip().lower()
            if normalized_has_children in {'true', '1', 'yes', 'y'}:
                has_children_filter = True
            elif normalized_has_children in {'false', '0', 'no', 'n'}:
                has_children_filter = False
        depth_filter = None if lineage_depth is None else int(lineage_depth)
        items: list[Dict[str, Any]] = []
        command_summary: dict[str, int] = {}
        result_mode_summary: dict[str, int] = {}
        action_code_summary: dict[str, int] = {}
        selection_summary: dict[str, int] = {}
        reexecute_command_summary: dict[str, int] = {}
        command_mode_summary: dict[str, int] = {}
        lineage_summary = {
            'rootResults': 0,
            'childResults': 0,
            'resultsWithChildren': 0,
            'maxDepth': 0,
        }
        status_summary = {
            'totalCommands': 0,
            'commandsWithFailures': 0,
            'commandsFullySucceeded': 0,
            'commandsPartial': 0,
        }
        for bulk_id in reversed(ACTION_BULK_COMMAND_ORDER):
            record = ACTION_BULK_COMMANDS.get(bulk_id)
            if not record:
                continue
            if command_filter and str(record.get('command') or '') != command_filter:
                continue
            if worker_filter and str(record.get('workerId') or '') != worker_filter:
                continue
            scope = dict(record.get('scope') or {})
            batch_refs = [str(item) for item in scope.get('batchRefs') or []]
            action_codes = [str(item) for item in scope.get('actionCodes') or []]
            if batch_filter and batch_filter not in batch_refs:
                continue
            if action_filter and action_filter not in action_codes:
                continue
            summary = dict(record.get('summary') or {})
            current_result_mode = self._bulk_result_mode(record)
            if result_filter and current_result_mode != result_filter:
                continue
            if root_filter and str(record.get('rootBulkCommandId') or record.get('bulkCommandId') or '') != root_filter:
                continue
            if reexecute_filter and str(record.get('reexecuteOf') or '') != reexecute_filter:
                continue
            if parent_filter and str(record.get('reexecuteOf') or '') != parent_filter:
                continue
            if selection_filter and str(record.get('selection') or '') != selection_filter:
                continue
            if reexecute_command_filter and str(record.get('reexecuteCommand') or '') != reexecute_command_filter:
                continue
            current_command_mode = str(record.get('commandMode') or 'direct')
            if command_mode_filter and current_command_mode != command_mode_filter:
                continue
            if not self._matches_source_bulk_filter(record, source_bulk_filter):
                continue
            lineage_payload = self._bulk_lineage_payload(record)
            child_count = int(lineage_payload.get('childCount') or 0)
            depth = int(lineage_payload.get('lineageDepth') or 0)
            if has_children_filter is True and child_count <= 0:
                continue
            if has_children_filter is False and child_count > 0:
                continue
            if depth_filter is not None and depth != depth_filter:
                continue
            failed_jobs = int(summary.get('failedJobs') or 0)
            succeeded_jobs = int(summary.get('succeededJobs') or 0)
            if failed_jobs > 0:
                status_summary['commandsWithFailures'] += 1
            if failed_jobs == 0:
                status_summary['commandsFullySucceeded'] += 1
            if failed_jobs > 0 and succeeded_jobs > 0:
                status_summary['commandsPartial'] += 1
            status_summary['totalCommands'] += 1
            if depth == 0:
                lineage_summary['rootResults'] += 1
            else:
                lineage_summary['childResults'] += 1
            if child_count > 0:
                lineage_summary['resultsWithChildren'] += 1
            lineage_summary['maxDepth'] = max(int(lineage_summary.get('maxDepth') or 0), depth)
            command_key = str(record.get('command') or 'unknown')
            command_summary[command_key] = int(command_summary.get(command_key, 0)) + 1
            result_mode_summary[current_result_mode] = int(result_mode_summary.get(current_result_mode, 0)) + 1
            selection_key = str(record.get('selection') or 'direct')
            selection_summary[selection_key] = int(selection_summary.get(selection_key, 0)) + 1
            reexecute_key = str(record.get('reexecuteCommand') or 'direct')
            reexecute_command_summary[reexecute_key] = int(reexecute_command_summary.get(reexecute_key, 0)) + 1
            command_mode_summary[current_command_mode] = int(command_mode_summary.get(current_command_mode, 0)) + 1
            for code in action_codes:
                action_code_summary[code] = int(action_code_summary.get(code, 0)) + 1
            items.append({
                'bulkCommandId': record.get('bulkCommandId'),
                'eventAt': record.get('eventAt'),
                'command': record.get('command'),
                'commandMode': current_command_mode,
                'operator': record.get('operator'),
                'workerId': record.get('workerId'),
                'scope': scope,
                'summary': summary,
                'resultMode': current_result_mode,
                'lineage': lineage_payload,
                'selection': record.get('selection'),
                'reexecuteCommand': record.get('reexecuteCommand'),
                'commandMode': current_command_mode,
                'lineageScope': record.get('lineageScope'),
                'sourceBulkCommandIds': [str(item) for item in record.get('sourceBulkCommandIds') or [] if str(item).strip()],
                'navigation': self._bulk_linked_filters(record),
                'itemStatusSummary': dict(record.get('itemStatusSummary') or {}),
                'errorReasonSummary': dict(record.get('errorReasonSummary') or {}),
                'total': record.get('total'),
            })
        normalized_offset = max(int(offset or 0), 0)
        normalized_limit = max(int(limit or 0), 0) or 20
        limited = items[normalized_offset: normalized_offset + normalized_limit]
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'scope': {
                'batchRef': batch_filter,
                'command': command_filter,
                'workerId': worker_filter,
                'actionCode': action_filter,
                'resultMode': result_filter,
                'rootBulkCommandId': root_filter,
                'reexecuteOf': reexecute_filter,
                'parentBulkCommandId': parent_filter,
                'hasChildren': has_children_filter,
                'lineageDepth': depth_filter,
                'selection': selection_filter,
                'reexecuteCommand': reexecute_command_filter,
                'commandMode': command_mode_filter,
                'sourceBulkCommandId': source_bulk_filter,
                'offset': normalized_offset,
                'limit': normalized_limit,
            },
            'summary': status_summary,
            'lineageSummary': lineage_summary,
            'commandSummary': command_summary,
            'resultModeSummary': result_mode_summary,
            'actionCodeSummary': action_code_summary,
            'selectionSummary': selection_summary,
            'reexecuteCommandSummary': reexecute_command_summary,
            'commandModeSummary': command_mode_summary,
            'linkedFilterSummary': {
                'rootBulkCommandId': 1 if root_filter else 0,
                'parentBulkCommandId': 1 if parent_filter else 0,
                'sourceBulkCommandId': 1 if source_bulk_filter else 0,
            },
            'pagination': {
                'offset': normalized_offset,
                'limit': normalized_limit,
                'returned': len(limited),
                'hasMore': normalized_offset + len(limited) < len(items),
            },
            'items': limited,
            'total': len(items),
        }

    def get_bulk_command_detail(self, bulk_command_id: str) -> Dict[str, Any]:
        bulk_id = str(bulk_command_id or '').strip()
        record = ACTION_BULK_COMMANDS.get(bulk_id)
        if not record:
            raise ValueError('bulk_command_not_found')
        errors = [dict(item) for item in record.get('errors') or []]
        failed_job_ids = [str(item.get('jobId') or '').strip() for item in errors if str(item.get('jobId') or '').strip()]
        rerunnable_commands = []
        if failed_job_ids:
            rerunnable_commands = ['retry', 'redrive', 'dead-letter', str(record.get('command') or '').strip() or None]
        rerunnable_commands = [item for item in rerunnable_commands if item]
        seen: set[str] = set()
        rerunnable_commands = [item for item in rerunnable_commands if not (item in seen or seen.add(item))]
        related_records = list(reversed(self._bulk_related_records(bulk_id)))
        related_items = [
            {
                'bulkCommandId': item.get('bulkCommandId'),
                'eventAt': item.get('eventAt'),
                'command': item.get('command'),
                'summary': dict(item.get('summary') or {}),
                'resultMode': self._bulk_result_mode(item),
                'lineage': self._bulk_lineage_payload(item),
                'isCurrent': str(item.get('bulkCommandId') or '') == bulk_id,
            }
            for item in related_records[:10]
        ]
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'bulkCommandId': bulk_id,
            'bulkCommand': dict(record),
            'failedJobIds': failed_job_ids,
            'lineage': self._bulk_lineage_payload(record),
            'navigationContext': self._bulk_linked_filters(record),
            'relatedResults': related_items,
            'secondaryActions': {
                'rerunnableCommands': rerunnable_commands,
                'failedJobCount': len(failed_job_ids),
            },
        }

    def get_bulk_command_timeline(
        self,
        bulk_command_id: str,
        *,
        result_mode: str | None = None,
        event_type: str | None = None,
        command: str | None = None,
        action_code: str | None = None,
        lineage_depth: int | None = None,
        command_mode: str | None = None,
        source_bulk_command_id: str | None = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        bulk_id = str(bulk_command_id or '').strip()
        record = ACTION_BULK_COMMANDS.get(bulk_id)
        if not record:
            raise ValueError('bulk_command_not_found')
        normalized_mode = str(result_mode or '').strip() or None
        normalized_event_type = str(event_type or '').strip() or None
        normalized_command = str(command or '').strip() or None
        normalized_action_code = str(action_code or '').strip() or None
        normalized_command_mode = str(command_mode or '').strip() or None
        normalized_source_bulk_command_id = str(source_bulk_command_id or '').strip() or None
        depth_filter = None if lineage_depth is None else int(lineage_depth)
        timeline_items: list[Dict[str, Any]] = []
        command_summary: dict[str, int] = {}
        result_mode_summary: dict[str, int] = {}
        event_type_summary: dict[str, int] = {}
        action_code_summary: dict[str, int] = {}
        command_mode_summary: dict[str, int] = {}
        lineage_summary = {'rootEvents': 0, 'childEvents': 0, 'maxDepth': 0}
        for item in self._bulk_related_records(bulk_id):
            if not self._matches_source_bulk_filter(item, normalized_source_bulk_command_id):
                continue
            current_mode = self._bulk_result_mode(item)
            if normalized_mode and current_mode != normalized_mode:
                continue
            lineage_payload = self._bulk_lineage_payload(item)
            depth = int(lineage_payload.get('lineageDepth') or 0)
            if depth_filter is not None and depth != depth_filter:
                continue
            event_type_value = 'bulk_result_created' if not lineage_payload.get('reexecuteOf') else 'bulk_result_reexecuted'
            if normalized_event_type and event_type_value != normalized_event_type:
                continue
            command_key = str(item.get('command') or 'unknown')
            if normalized_command and command_key != normalized_command:
                continue
            current_command_mode = str(item.get('commandMode') or 'direct')
            if normalized_command_mode and current_command_mode != normalized_command_mode:
                continue
            scope = dict(item.get('scope') or {})
            action_codes = [str(code) for code in scope.get('actionCodes') or [] if str(code).strip()]
            if normalized_action_code and normalized_action_code not in action_codes:
                continue
            command_summary[command_key] = int(command_summary.get(command_key, 0)) + 1
            result_mode_summary[current_mode] = int(result_mode_summary.get(current_mode, 0)) + 1
            event_type_summary[event_type_value] = int(event_type_summary.get(event_type_value, 0)) + 1
            command_mode_summary[current_command_mode] = int(command_mode_summary.get(current_command_mode, 0)) + 1
            if depth == 0:
                lineage_summary['rootEvents'] += 1
            else:
                lineage_summary['childEvents'] += 1
            lineage_summary['maxDepth'] = max(int(lineage_summary.get('maxDepth') or 0), depth)
            for code in action_codes or ['unknown']:
                action_code_summary[code] = int(action_code_summary.get(code, 0)) + 1
            timeline_items.append({
                'eventId': str(item.get('bulkCommandId') or ''),
                'bulkCommandId': item.get('bulkCommandId'),
                'eventType': event_type_value,
                'eventAt': item.get('eventAt'),
                'command': item.get('command'),
                'commandMode': current_command_mode,
                'operator': item.get('operator'),
                'workerId': item.get('workerId'),
                'resultMode': current_mode,
                'summary': dict(item.get('summary') or {}),
                'actionCodes': action_codes,
                'lineage': lineage_payload,
            })
        timeline_items.sort(key=lambda entry: str(entry.get('eventAt') or ''))
        normalized_limit = max(int(limit or 0), 0) or 20
        limited = timeline_items[:normalized_limit]
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'bulkCommandId': bulk_id,
            'scope': {
                'resultMode': normalized_mode,
                'eventType': normalized_event_type,
                'command': normalized_command,
                'actionCode': normalized_action_code,
                'lineageDepth': depth_filter,
                'commandMode': normalized_command_mode,
                'sourceBulkCommandId': normalized_source_bulk_command_id,
                'limit': normalized_limit,
            },
            'lineage': self._bulk_lineage_payload(record),
            'summary': {
                'totalEvents': len(timeline_items),
                'returned': len(limited),
            },
            'commandSummary': command_summary,
            'resultModeSummary': result_mode_summary,
            'eventTypeSummary': event_type_summary,
            'actionCodeSummary': action_code_summary,
            'commandModeSummary': command_mode_summary,
            'lineageSummary': lineage_summary,
            'items': limited,
            'total': len(timeline_items),
        }


    def get_bulk_command_lineage_summary(
        self,
        bulk_command_id: str,
        *,
        event_type: str | None = None,
        action_code: str | None = None,
        lineage_depth: int | None = None,
        command_mode: str | None = None,
        source_bulk_command_id: str | None = None,
        selection: str | None = None,
        reexecute_command: str | None = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        bulk_id = str(bulk_command_id or '').strip()
        record = ACTION_BULK_COMMANDS.get(bulk_id)
        if not record:
            raise ValueError('bulk_command_not_found')
        normalized_event_type = str(event_type or '').strip() or None
        normalized_action_code = str(action_code or '').strip() or None
        normalized_command_mode = str(command_mode or '').strip() or None
        normalized_source_bulk_command_id = str(source_bulk_command_id or '').strip() or None
        normalized_selection = str(selection or '').strip() or None
        normalized_reexecute_command = str(reexecute_command or '').strip() or None
        depth_filter = None if lineage_depth is None else int(lineage_depth)
        related_records: list[Dict[str, Any]] = []
        command_summary: dict[str, int] = {}
        result_mode_summary: dict[str, int] = {}
        action_code_summary: dict[str, int] = {}
        selection_summary: dict[str, int] = {}
        reexecute_command_summary: dict[str, int] = {}
        command_mode_summary: dict[str, int] = {}
        event_type_summary: dict[str, int] = {}
        lineage_summary = {
            'rootResults': 0,
            'childResults': 0,
            'resultsWithChildren': 0,
            'maxDepth': 0,
        }
        totals = {
            'totalResults': 0,
            'totalRequestedJobs': 0,
            'totalSucceededJobs': 0,
            'totalFailedJobs': 0,
            'totalSourceResults': 0,
        }
        source_ids: set[str] = set()
        for item in self._bulk_related_records(bulk_id):
            if not self._matches_source_bulk_filter(item, normalized_source_bulk_command_id):
                continue
            lineage_payload = self._bulk_lineage_payload(item)
            depth = int(lineage_payload.get('lineageDepth') or 0)
            if depth_filter is not None and depth != depth_filter:
                continue
            current_command_mode = str(item.get('commandMode') or 'direct')
            if normalized_command_mode and current_command_mode != normalized_command_mode:
                continue
            if normalized_selection and str(item.get('selection') or '').strip() != normalized_selection:
                continue
            if normalized_reexecute_command and str(item.get('reexecuteCommand') or '').strip() != normalized_reexecute_command:
                continue
            scope = dict(item.get('scope') or {})
            action_codes = [str(code) for code in scope.get('actionCodes') or [] if str(code).strip()]
            if normalized_action_code and normalized_action_code not in action_codes:
                continue
            event_type_value = 'bulk_result_created' if not lineage_payload.get('reexecuteOf') else 'bulk_result_reexecuted'
            if normalized_event_type and event_type_value != normalized_event_type:
                continue
            related_records.append(item)
            totals['totalResults'] += 1
            summary = dict(item.get('summary') or {})
            totals['totalRequestedJobs'] += int(summary.get('requestedJobs') or 0)
            totals['totalSucceededJobs'] += int(summary.get('succeededJobs') or 0)
            totals['totalFailedJobs'] += int(summary.get('failedJobs') or 0)
            source_ids.update([str(source_id) for source_id in item.get('sourceBulkCommandIds') or [] if str(source_id).strip()])
            command_key = str(item.get('command') or 'unknown')
            result_mode = self._bulk_result_mode(item)
            selection_key = str(item.get('selection') or 'direct')
            reexecute_key = str(item.get('reexecuteCommand') or 'direct')
            command_summary[command_key] = int(command_summary.get(command_key, 0)) + 1
            result_mode_summary[result_mode] = int(result_mode_summary.get(result_mode, 0)) + 1
            selection_summary[selection_key] = int(selection_summary.get(selection_key, 0)) + 1
            reexecute_command_summary[reexecute_key] = int(reexecute_command_summary.get(reexecute_key, 0)) + 1
            command_mode_summary[current_command_mode] = int(command_mode_summary.get(current_command_mode, 0)) + 1
            event_type_summary[event_type_value] = int(event_type_summary.get(event_type_value, 0)) + 1
            if depth == 0:
                lineage_summary['rootResults'] += 1
            else:
                lineage_summary['childResults'] += 1
            if int(lineage_payload.get('childCount') or 0) > 0:
                lineage_summary['resultsWithChildren'] += 1
            lineage_summary['maxDepth'] = max(int(lineage_summary.get('maxDepth') or 0), depth)
            for code in action_codes or ['unknown']:
                action_code_summary[code] = int(action_code_summary.get(code, 0)) + 1
        totals['totalSourceResults'] = len(source_ids)
        ordered_related = sorted(related_records, key=lambda item: str(item.get('eventAt') or ''), reverse=True)
        timeline = self.get_bulk_command_timeline(
            bulk_id,
            event_type=normalized_event_type,
            action_code=normalized_action_code,
            lineage_depth=depth_filter,
            command_mode=normalized_command_mode,
            source_bulk_command_id=normalized_source_bulk_command_id,
            limit=limit,
        )
        latest_results = [
            {
                'bulkCommandId': item.get('bulkCommandId'),
                'eventAt': item.get('eventAt'),
                'command': item.get('command'),
                'commandMode': item.get('commandMode'),
                'resultMode': self._bulk_result_mode(item),
                'summary': dict(item.get('summary') or {}),
                'lineage': self._bulk_lineage_payload(item),
            }
            for item in ordered_related[: min(max(int(limit or 0), 1), 10)]
        ]
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'bulkCommandId': bulk_id,
            'scope': {
                'eventType': normalized_event_type,
                'actionCode': normalized_action_code,
                'lineageDepth': depth_filter,
                'commandMode': normalized_command_mode,
                'sourceBulkCommandId': normalized_source_bulk_command_id,
                'selection': normalized_selection,
                'reexecuteCommand': normalized_reexecute_command,
                'limit': max(int(limit or 0), 0) or 20,
            },
            'lineage': self._bulk_lineage_payload(record),
            'summary': totals,
            'commandSummary': command_summary,
            'resultModeSummary': result_mode_summary,
            'actionCodeSummary': action_code_summary,
            'selectionSummary': selection_summary,
            'reexecuteCommandSummary': reexecute_command_summary,
            'commandModeSummary': command_mode_summary,
            'eventTypeSummary': event_type_summary,
            'lineageSummary': lineage_summary,
            'linkedHistoryFilters': self._bulk_linked_filters(record),
            'linkedTimelineFilters': {
                **self._bulk_linked_filters(record),
                'eventType': normalized_event_type,
                'actionCode': normalized_action_code,
                'commandMode': normalized_command_mode,
                'sourceBulkCommandId': normalized_source_bulk_command_id,
            },
            'latestResults': latest_results,
            'timeline': timeline.get('items', []),
            'timelineSummary': timeline.get('summary', {}),
            'timelineEventTypeSummary': timeline.get('eventTypeSummary', {}),
            'timelineCommandModeSummary': timeline.get('commandModeSummary', {}),
            'timelineTotal': timeline.get('total', 0),
        }

    def reexecute_bulk_command(
        self,
        bulk_command_id: str,
        *,
        selection: str = 'failed',
        command: str | None = None,
        operator: str = 'system',
        worker_id: str | None = None,
        reason: str | None = None,
        note: str | None = None,
        external_ref: str | None = None,
    ) -> Dict[str, Any]:
        bulk_id = str(bulk_command_id or '').strip()
        record = ACTION_BULK_COMMANDS.get(bulk_id)
        if not record:
            raise ValueError('bulk_command_not_found')
        normalized_selection = str(selection or 'failed').strip().lower() or 'failed'
        if normalized_selection not in {'failed', 'all', 'succeeded'}:
            raise ValueError('unsupported_bulk_selection')
        if normalized_selection == 'failed':
            job_ids = [str(item.get('jobId') or '').strip() for item in record.get('errors') or [] if str(item.get('jobId') or '').strip()]
        elif normalized_selection == 'succeeded':
            job_ids = [str(item.get('jobId') or '').strip() for item in record.get('items') or [] if str(item.get('jobId') or '').strip()]
        else:
            failed_ids = [str(item.get('jobId') or '').strip() for item in record.get('errors') or [] if str(item.get('jobId') or '').strip()]
            succeeded_ids = [str(item.get('jobId') or '').strip() for item in record.get('items') or [] if str(item.get('jobId') or '').strip()]
            job_ids = succeeded_ids + [item for item in failed_ids if item not in succeeded_ids]
        if not job_ids:
            raise ValueError('bulk_command_no_jobs_to_reexecute')
        effective_command = str(command or record.get('command') or '').strip().lower()
        if not effective_command:
            raise ValueError('unsupported_bulk_command')
        effective_reason = reason or f'reexecute_from_{bulk_id}'
        result = self.execute_bulk_command(
            command=effective_command,
            job_ids=job_ids,
            operator=operator,
            worker_id=worker_id,
            reason=effective_reason,
            note=note,
            external_ref=external_ref,
            reexecute_of=bulk_id,
            selection=normalized_selection,
            reexecute_command=effective_command,
        )
        result['reexecuteOf'] = bulk_id
        result['selection'] = normalized_selection
        result['reexecuteCommand'] = effective_command
        return result

    def reexecute_bulk_command_lineage(
        self,
        bulk_command_id: str,
        *,
        selection: str = 'failed',
        command: str | None = None,
        scope: str = 'entire_lineage',
        operator: str = 'system',
        worker_id: str | None = None,
        reason: str | None = None,
        note: str | None = None,
        external_ref: str | None = None,
    ) -> Dict[str, Any]:
        bulk_id = str(bulk_command_id or '').strip()
        record = ACTION_BULK_COMMANDS.get(bulk_id)
        if not record:
            raise ValueError('bulk_command_not_found')
        normalized_scope = str(scope or 'entire_lineage').strip().lower() or 'entire_lineage'
        if normalized_scope not in {'current', 'descendants', 'entire_lineage'}:
            raise ValueError('unsupported_lineage_scope')
        normalized_selection = str(selection or 'failed').strip().lower() or 'failed'
        if normalized_selection not in {'failed', 'all', 'succeeded'}:
            raise ValueError('unsupported_bulk_selection')
        effective_command = str(command or record.get('command') or '').strip().lower()
        if not effective_command:
            raise ValueError('unsupported_bulk_command')
        related_records = self._bulk_related_records(bulk_id)
        related_ids = []
        for item in related_records:
            item_id = str(item.get('bulkCommandId') or '')
            if normalized_scope == 'current' and item_id != bulk_id:
                continue
            if normalized_scope == 'descendants' and bulk_id not in self._bulk_parent_chain(item):
                continue
            related_ids.append(item_id)
        selected_job_ids: list[str] = []
        seen: set[str] = set()
        source_ids: list[str] = []
        for related_id in related_ids:
            current = ACTION_BULK_COMMANDS.get(related_id)
            if not current:
                continue
            candidate_job_ids: list[str]
            if normalized_selection == 'failed':
                candidate_job_ids = [str(item.get('jobId') or '').strip() for item in current.get('errors') or [] if str(item.get('jobId') or '').strip()]
            elif normalized_selection == 'succeeded':
                candidate_job_ids = [str(item.get('jobId') or '').strip() for item in current.get('items') or [] if str(item.get('jobId') or '').strip()]
            else:
                failed_ids = [str(item.get('jobId') or '').strip() for item in current.get('errors') or [] if str(item.get('jobId') or '').strip()]
                succeeded_ids = [str(item.get('jobId') or '').strip() for item in current.get('items') or [] if str(item.get('jobId') or '').strip()]
                candidate_job_ids = succeeded_ids + [item for item in failed_ids if item not in succeeded_ids]
            added = False
            for job_id in candidate_job_ids:
                if not job_id or job_id in seen:
                    continue
                seen.add(job_id)
                added = True
                selected_job_ids.append(job_id)
            if added:
                source_ids.append(related_id)
        if not selected_job_ids:
            raise ValueError('bulk_command_no_jobs_to_reexecute')
        effective_reason = reason or f'lineage_reexecute_from_{bulk_id}'
        result = self.execute_bulk_command(
            command=effective_command,
            job_ids=selected_job_ids,
            operator=operator,
            worker_id=worker_id,
            reason=effective_reason,
            note=note,
            external_ref=external_ref,
            reexecute_of=bulk_id,
            selection=normalized_selection,
            reexecute_command=effective_command,
            lineage_scope=normalized_scope,
            source_bulk_command_ids=source_ids,
        )
        result['reexecuteOf'] = bulk_id
        result['selection'] = normalized_selection
        result['reexecuteCommand'] = effective_command
        result['lineageScope'] = normalized_scope
        result['sourceBulkCommandIds'] = source_ids
        return result

    def execute_bulk_command(
        self,
        *,
        command: str,
        job_ids: list[str],
        operator: str = 'system',
        worker_id: str | None = None,
        reason: str | None = None,
        note: str | None = None,
        external_ref: str | None = None,
        reexecute_of: str | None = None,
        selection: str | None = None,
        reexecute_command: str | None = None,
        lineage_scope: str | None = None,
        source_bulk_command_ids: list[str] | None = None,
    ) -> Dict[str, Any]:
        normalized_command = str(command or '').strip().lower()
        if normalized_command not in {'release-lease', 'mark-succeeded', 'mark-failed', 'retry', 'redrive', 'dead-letter'}:
            raise ValueError('unsupported_bulk_command')
        normalized_job_ids: list[str] = []
        seen: set[str] = set()
        for item in job_ids or []:
            key = str(item or '').strip()
            if not key or key in seen:
                continue
            seen.add(key)
            normalized_job_ids.append(key)
        if not normalized_job_ids:
            raise ValueError('job_ids_required')

        results: list[Dict[str, Any]] = []
        errors: list[Dict[str, Any]] = []
        for job_id in normalized_job_ids:
            try:
                job = self._get_job(job_id)
                effective_worker = worker_id
                if normalized_command in {'release-lease', 'mark-succeeded', 'mark-failed'}:
                    effective_worker = str(worker_id or job.get('workerId') or '').strip() or None
                if normalized_command == 'release-lease':
                    payload = self.release_job_lease(job_id, worker_id=str(effective_worker or ''), operator=operator, reason=reason, note=note)
                elif normalized_command == 'mark-succeeded':
                    payload = self.mark_job_succeeded(job_id, worker_id=str(effective_worker or ''), operator=operator, external_ref=external_ref, note=note)
                elif normalized_command == 'mark-failed':
                    payload = self.mark_job_failed(job_id, worker_id=str(effective_worker or ''), operator=operator, reason=reason or 'bulk_mark_failed', note=note)
                elif normalized_command == 'retry':
                    payload = self.retry_job(job_id, operator=operator, reason=reason, note=note)
                elif normalized_command == 'redrive':
                    payload = self.redrive_job(job_id, operator=operator, reason=reason, note=note)
                else:
                    payload = self.mark_dead_letter(job_id, operator=operator, reason=reason or 'bulk_dead_letter', note=note)
                results.append(payload)
            except Exception as exc:
                errors.append({'jobId': job_id, 'reason': str(exc)})
        record = self._record_bulk_command(
            command=normalized_command,
            operator=operator,
            worker_id=worker_id,
            reason=reason,
            note=note,
            external_ref=external_ref,
            items=results,
            errors=errors,
            reexecute_of=reexecute_of,
            selection=selection,
            reexecute_command=reexecute_command,
            lineage_scope=lineage_scope,
            source_bulk_command_ids=source_bulk_command_ids,
        )
        return dict(record)

    def get_store_overview(self, *, batch_ref: str | None = None, limit: int = 10) -> Dict[str, Any]:
        normalized_batch = str(batch_ref or '').strip() or None
        requests = [item for item in ACTION_REQUESTS.values() if not normalized_batch or str(item.get('batchRef') or '').strip() == normalized_batch]
        request_ids = {str(item.get('requestId') or '') for item in requests}
        jobs = [job for job in ACTION_JOBS.values() if not normalized_batch or str(job.get('batchRef') or job.get('batchId') or '') == normalized_batch]
        indexed_job_ids = []
        for request_id, job_ids in ACTION_REQUEST_JOB_INDEX.items():
            if request_ids and request_id not in request_ids and normalized_batch:
                continue
            indexed_job_ids.extend(job_ids)
        recent_jobs = self._sort_jobs(jobs)[: max(int(limit or 0), 0)]
        if normalized_batch is None:
            total_deliveries = sum(len(items) for items in ACTION_DELIVERY_HISTORY.values())
            total_callbacks = sum(len(items) for items in ACTION_CALLBACK_HISTORY.values())
            total_compensations = sum(len(items) for items in ACTION_COMPENSATION_HISTORY.values())
            total_approval_events = sum(len(items) for items in ACTION_APPROVAL_HISTORY.values())
        elif request_ids:
            total_deliveries = sum(len(ACTION_DELIVERY_HISTORY.get(str(request_id), [])) for request_id in request_ids)
            total_callbacks = sum(len(ACTION_CALLBACK_HISTORY.get(str(request_id), [])) for request_id in request_ids)
            total_compensations = sum(len(ACTION_COMPENSATION_HISTORY.get(str(request_id), [])) for request_id in request_ids)
            total_approval_events = sum(len(ACTION_APPROVAL_HISTORY.get(str(request_id), [])) for request_id in request_ids)
        else:
            total_deliveries = 0
            total_callbacks = 0
            total_compensations = 0
            total_approval_events = 0
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'scope': {'batchRef': normalized_batch},
            'summary': {
                'totalRequests': len(requests),
                'totalJobs': len(jobs),
                'totalJobEvents': sum(len(ACTION_JOB_EVENTS.get(str(job.get('jobId')), [])) for job in jobs),
                'totalDeliveries': total_deliveries,
                'totalCallbacks': total_callbacks,
                'totalCompensations': total_compensations,
                'totalApprovalEvents': total_approval_events,
                'requestJobIndexEntries': len(indexed_job_ids),
                'pushIdempotencyEntries': len(ACTION_JOB_IDEMPOTENCY),
                'commandIdempotencyEntries': len(ACTION_JOB_COMMAND_IDEMPOTENCY),
            },
            'batchRefs': sorted({str(job.get('batchRef') or job.get('batchId') or 'unscoped') for job in jobs}),
            'latestJobs': [self._build_job_payload(job) for job in recent_jobs],
            'latestJobsTotal': len(recent_jobs),
        }

    def list_request_jobs(self, request_id: str) -> Dict[str, Any]:
        self._get_request(request_id)
        items = [self._build_job_payload(ACTION_JOBS[job_id]) for job_id in ACTION_REQUEST_JOB_INDEX.get(str(request_id), []) if job_id in ACTION_JOBS]
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'items': items,
            'total': len(items),
        }

    def _collect_request_timeline(self, request_id: str) -> list[dict[str, Any]]:
        timeline: list[dict[str, Any]] = []
        for job_id in ACTION_REQUEST_JOB_INDEX.get(str(request_id), []):
            for event in ACTION_JOB_EVENTS.get(str(job_id), []):
                record = dict(event)
                record['requestId'] = str(request_id)
                timeline.append(record)
        timeline.sort(key=lambda item: (str(item.get('eventAt') or ''), str(item.get('eventId') or '')))
        return timeline

    def get_request_recovery(self, request_id: str) -> Dict[str, Any]:
        self._get_request(request_id)
        jobs = [ACTION_JOBS[job_id] for job_id in ACTION_REQUEST_JOB_INDEX.get(str(request_id), []) if job_id in ACTION_JOBS]
        items = []
        summary = {
            'totalJobs': len(jobs),
            'queuedJobs': 0,
            'runningJobs': 0,
            'succeededJobs': 0,
            'failedJobs': 0,
            'deadLetterJobs': 0,
            'retryableJobs': 0,
            'redriveableJobs': 0,
            'deadLetterableJobs': 0,
        }
        state_summary: dict[str, int] = {}
        status_summary: dict[str, int] = {}
        for job in jobs:
            status = self._status(job)
            recovery_state = str(job.get('recoveryState') or 'healthy')
            recommended_operation = self._job_recommended_operation(job)
            status_summary[status] = int(status_summary.get(status, 0)) + 1
            state_summary[recovery_state] = int(state_summary.get(recovery_state, 0)) + 1
            if status == 'queued':
                summary['queuedJobs'] += 1
            elif status == 'running':
                summary['runningJobs'] += 1
            elif status == 'succeeded':
                summary['succeededJobs'] += 1
            elif status == 'failed':
                summary['failedJobs'] += 1
            elif status == 'dead_letter':
                summary['deadLetterJobs'] += 1
            if recommended_operation == 'retry':
                summary['retryableJobs'] += 1
            elif recommended_operation == 'redrive':
                summary['redriveableJobs'] += 1
            elif recommended_operation == 'dead_letter':
                summary['deadLetterableJobs'] += 1
            item = self._build_job_payload(job)
            item['eventCount'] = len(ACTION_JOB_EVENTS.get(str(job.get('jobId')), []))
            items.append(item)
        timeline = self._collect_request_timeline(request_id)
        latest = items[-1] if items else None
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'summary': summary,
            'statusSummary': status_summary,
            'recoveryStateSummary': state_summary,
            'items': items,
            'total': len(items),
            'timeline': timeline,
            'timelineTotal': len(timeline),
            'latestJobId': (latest or {}).get('jobId'),
            'latestJobStatus': (latest or {}).get('jobStatus'),
            'latestRecoveryOperation': (latest or {}).get('lastRecoveryOperation'),
        }

    def get_latest_request_job(self, request_id: str) -> Dict[str, Any] | None:
        ids = ACTION_REQUEST_JOB_INDEX.get(str(request_id), [])
        if not ids:
            return None
        job = ACTION_JOBS.get(ids[-1])
        return self._build_job_payload(job) if job else None

    def _idempotent_job_command(self, job_id: str, operation: str, idempotency_key: str | None) -> Dict[str, Any] | None:
        scope = self._command_scope(job_id, operation, idempotency_key)
        if not scope:
            return None
        if scope in ACTION_JOB_COMMAND_IDEMPOTENCY:
            existing_id = ACTION_JOB_COMMAND_IDEMPOTENCY[scope]
            existing = ACTION_JOBS.get(existing_id)
            if existing:
                return self._build_job_payload(existing)
        return None

    def _remember_job_command(self, job_id: str, operation: str, idempotency_key: str | None) -> None:
        scope = self._command_scope(job_id, operation, idempotency_key)
        if scope:
            ACTION_JOB_COMMAND_IDEMPOTENCY[scope] = str(job_id)

    def retry_job(self, job_id: str, *, operator: str, reason: str | None = None, note: str | None = None, idempotency_key: str | None = None) -> Dict[str, Any]:
        existing = self._idempotent_job_command(job_id, 'retry', idempotency_key)
        if existing:
            return existing
        job = self._get_job(job_id)
        if self._status(job) != 'failed':
            raise ValueError('job_not_retryable')
        attempt_count = int(job.get('attemptCount') or 0)
        max_attempts = int(job.get('maxAttempts') or self.DEFAULT_MAX_ATTEMPTS)
        if attempt_count >= max_attempts:
            raise ValueError('job_not_retryable')
        now = utcnow_iso()
        retry_count = int(job.get('retryCount') or 0) + 1
        job.update(
            {
                'jobStatus': 'queued',
                'queueStatus': 'queued',
                'finishedAt': None,
                'queuedAt': now,
                'queueSequence': self._next_queue_sequence(),
                'retryCount': retry_count,
                'lastRecoveryOperation': 'retry',
                'lastRecoveryReason': reason,
                'lastRecoveryAt': now,
                'recoveryState': 'retry_scheduled',
                'deadLettered': False,
            }
        )
        self._complete_result(job, queued=True, completed=False, message='retry_scheduled')
        if reason:
            job['result']['retryReason'] = reason
        if note:
            job['result']['retryNote'] = note
        self.append_job_event(str(job_id), event_type='job_retry_requested', status='retry_requested', actor=operator, message='action_push_job_retry_requested', payload={'reason': reason, 'note': note, 'retryCount': retry_count}, event_at=now)
        self.append_job_event(str(job_id), event_type='job_requeued', status='queued', actor='queue', message='action_push_job_requeued', payload={'retryCount': retry_count}, event_at=now)
        self._remember_job_command(job_id, 'retry', idempotency_key)
        return self._build_job_payload(job)

    def redrive_job(self, job_id: str, *, operator: str, reason: str | None = None, note: str | None = None, idempotency_key: str | None = None) -> Dict[str, Any]:
        existing = self._idempotent_job_command(job_id, 'redrive', idempotency_key)
        if existing:
            return existing
        job = self._get_job(job_id)
        if self._status(job) != 'dead_letter':
            raise ValueError('job_not_redriveable')
        now = utcnow_iso()
        redrive_count = int(job.get('redriveCount') or 0) + 1
        job.update(
            {
                'jobStatus': 'queued',
                'queueStatus': 'queued',
                'finishedAt': None,
                'queuedAt': now,
                'queueSequence': self._next_queue_sequence(),
                'deadLettered': False,
                'redriveCount': redrive_count,
                'lastRecoveryOperation': 'redrive',
                'lastRecoveryReason': reason,
                'lastRecoveryAt': now,
                'recoveryState': 'redrive_scheduled',
            }
        )
        self._complete_result(job, queued=True, completed=False, message='redrive_scheduled')
        if reason:
            job['result']['redriveReason'] = reason
        if note:
            job['result']['redriveNote'] = note
        self.append_job_event(str(job_id), event_type='job_redrive_requested', status='redrive_requested', actor=operator, message='action_push_job_redrive_requested', payload={'reason': reason, 'note': note, 'redriveCount': redrive_count}, event_at=now)
        self.append_job_event(str(job_id), event_type='job_redriven', status='queued', actor='queue', message='action_push_job_redriven', payload={'redriveCount': redrive_count}, event_at=now)
        self._remember_job_command(job_id, 'redrive', idempotency_key)
        return self._build_job_payload(job)

    def mark_dead_letter(self, job_id: str, *, operator: str, reason: str, note: str | None = None, idempotency_key: str | None = None) -> Dict[str, Any]:
        existing = self._idempotent_job_command(job_id, 'dead_letter', idempotency_key)
        if existing:
            return existing
        job = self._get_job(job_id)
        status = self._status(job)
        if status in {'succeeded', 'dead_letter'}:
            raise ValueError('job_not_dead_letterable')
        if status not in {'queued', 'running', 'failed', 'accepted'}:
            raise ValueError('job_not_dead_letterable')
        now = utcnow_iso()
        job.update(
            {
                'jobStatus': 'dead_letter',
                'queueStatus': 'dead_letter',
                'finishedAt': now,
                'deadLettered': True,
                'deadLetteredAt': now,
                'deadLetterReason': reason,
                'lastFailureReason': reason,
                'lastRecoveryOperation': 'dead_letter',
                'lastRecoveryReason': reason,
                'lastRecoveryAt': now,
                'recoveryState': 'dead_letter',
            }
        )
        self._complete_result(job, completed=True, deadLettered=True, deadLetterReason=reason, message='job_dead_lettered')
        if note:
            job['result']['deadLetterNote'] = note
        self.append_job_event(str(job_id), event_type='job_dead_lettered', status='dead_letter', actor=operator, message='action_push_job_dead_lettered', payload={'reason': reason, 'note': note}, event_at=now)
        self._remember_job_command(job_id, 'dead_letter', idempotency_key)
        return self._build_job_payload(job)

    def apply_callback_state(
        self,
        job_id: str,
        *,
        provider_status: str,
        callback_event_id: str,
        received_at: str,
        external_ref: str | None = None,
    ) -> Dict[str, Any] | None:
        job = ACTION_JOBS.get(str(job_id))
        if not job:
            return None
        normalized = str(provider_status or '').strip().lower() or 'unknown'
        self._touch_job(
            str(job_id),
            lastCallbackAt=received_at,
            callbackState=provider_status,
            lastCallbackEventId=callback_event_id,
        )
        if normalized in self.SUCCESS_CALLBACK_STATES:
            job.update(
                {
                    'jobStatus': 'succeeded',
                    'queueStatus': 'completed',
                    'finishedAt': received_at,
                    'recoveryState': 'healthy',
                    'lastFailureReason': None,
                }
            )
            self._complete_result(job, accepted=True, queued=True, completed=True, externalRef=external_ref, message='callback_succeeded')
            self.append_job_event(str(job_id), event_type='job_succeeded', status='succeeded', actor='provider', message='action_push_job_succeeded', payload={'callbackEventId': callback_event_id, 'externalRef': external_ref, 'providerStatus': provider_status}, event_at=received_at)
        elif normalized in self.FAILURE_CALLBACK_STATES:
            attempt_count = int(job.get('attemptCount') or 0)
            max_attempts = int(job.get('maxAttempts') or self.DEFAULT_MAX_ATTEMPTS)
            recovery_state = 'retryable' if attempt_count < max_attempts else 'dead_letter_recommended'
            job.update(
                {
                    'jobStatus': 'failed',
                    'queueStatus': 'failed',
                    'finishedAt': received_at,
                    'lastFailureReason': normalized,
                    'recoveryState': recovery_state,
                }
            )
            self._complete_result(job, accepted=True, queued=True, completed=True, failureReason=normalized, message='callback_failed')
            self.append_job_event(str(job_id), event_type='job_failed', status='failed', actor='provider', message='action_push_job_failed', payload={'callbackEventId': callback_event_id, 'providerStatus': provider_status}, event_at=received_at)
        elif normalized in self.IN_PROGRESS_CALLBACK_STATES:
            job.update(
                {
                    'jobStatus': 'running',
                    'queueStatus': 'callback_pending',
                    'startedAt': job.get('startedAt') or received_at,
                    'recoveryState': 'in_progress',
                }
            )
            self._complete_result(job, accepted=True, queued=True, completed=False, message='callback_pending')
            self.append_job_event(str(job_id), event_type='job_callback_pending', status='running', actor='provider', message='action_push_job_callback_pending', payload={'callbackEventId': callback_event_id, 'providerStatus': provider_status}, event_at=received_at)
        return self._build_job_payload(job)

    def get_job_detail(self, job_id: str) -> Dict[str, Any] | None:
        job = ACTION_JOBS.get(str(job_id))
        if not job:
            return None
        events = list(ACTION_JOB_EVENTS.get(str(job_id), []))
        job.update(self._build_job_payload(job))
        job['timeline'] = events
        job['eventCount'] = len(events)
        return job

    def get_job_events(self, job_id: str) -> Dict[str, Any] | None:
        job = ACTION_JOBS.get(str(job_id))
        if not job:
            return None
        events = list(ACTION_JOB_EVENTS.get(str(job_id), []))
        return {
            'contractVersion': self.JOB_CONTRACT_VERSION,
            'jobId': str(job_id),
            'jobCode': job.get('jobCode'),
            'requestId': job.get('requestId'),
            'batchId': job.get('batchId'),
            'events': events,
            'total': len(events),
            'currentStatus': job.get('jobStatus'),
            'queueStatus': job.get('queueStatus'),
            'recommendedOperation': self._job_recommended_operation(job),
            'availableCommands': self._available_commands(job),
        }
