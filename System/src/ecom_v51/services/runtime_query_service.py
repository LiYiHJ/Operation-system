from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import inspect, select

from ecom_v51.db.ingest_models import JobEvent, RawRecord, ReplayJob
from ecom_v51.db.session import get_engine, get_session
from ecom_v51.services.batch_service import BatchService


class RuntimeQueryService:
    CONTRACT_VERSION = 'p2a.v1'

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)
        self.batch_service = BatchService(self.root_dir)

    @staticmethod
    def _table_names() -> set[str]:
        try:
            return set(inspect(get_engine()).get_table_names())
        except Exception:
            return set()

    @staticmethod
    def _iso(value: Any) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        if value is None:
            return None
        return str(value)

    def _resolve_job(self, job_ref: str) -> Optional[ReplayJob]:
        if 'replay_job' not in self._table_names():
            return None
        job_ref = str(job_ref or '').strip()
        if not job_ref:
            return None
        with get_session() as session:
            if job_ref.isdigit():
                job = session.get(ReplayJob, int(job_ref))
                if job is not None:
                    return job
            return session.execute(select(ReplayJob).where(ReplayJob.job_code == job_ref)).scalar_one_or_none()

    def _load_job_events(self, job_id: int) -> list[dict[str, Any]]:
        if 'job_event' not in self._table_names():
            return []
        with get_session() as session:
            rows = session.execute(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.id.asc())).scalars().all()
            return [
                {
                    'jobEventId': row.id,
                    'createdAt': self._iso(row.created_at),
                    'eventType': row.event_type,
                    'payload': row.payload or {},
                }
                for row in rows
            ]

    def get_job_detail(self, job_ref: str) -> Optional[Dict[str, Any]]:
        job = self._resolve_job(job_ref)
        if job is None:
            return None
        events = self._load_job_events(job.id)
        return {
            'jobId': job.id,
            'jobCode': job.job_code,
            'batchId': job.batch_id,
            'jobType': job.job_type,
            'status': job.status,
            'traceId': job.trace_id,
            'idempotencyKey': job.idempotency_key,
            'operator': job.operator,
            'requestPayload': job.request_payload or {},
            'resultPayload': job.result_payload or {},
            'errorMessage': job.error_message,
            'startedAt': self._iso(job.started_at),
            'finishedAt': self._iso(job.finished_at),
            'timeline': events,
            'contractVersion': self.CONTRACT_VERSION,
        }

    def get_job_events(self, job_ref: str) -> Optional[Dict[str, Any]]:
        job = self._resolve_job(job_ref)
        if job is None:
            return None
        events = self._load_job_events(job.id)
        return {
            'jobId': job.id,
            'jobCode': job.job_code,
            'batchId': job.batch_id,
            'contractVersion': self.CONTRACT_VERSION,
            'events': events,
            'total': len(events),
        }

    def get_batch_raw_records(self, batch_ref: str, *, limit: int = 50) -> Optional[Dict[str, Any]]:
        detail = self.batch_service.get_batch_detail(str(batch_ref))
        if not detail:
            return None
        batch_id = detail.get('batchId')
        if batch_id in (None, '') or 'raw_record' not in self._table_names():
            return {
                'batchId': batch_id,
                'workspaceBatchId': detail.get('workspaceBatchId'),
                'contractVersion': detail.get('contractVersion') or self.CONTRACT_VERSION,
                'items': [],
                'total': 0,
            }
        with get_session() as session:
            rows = session.execute(
                select(RawRecord).where(RawRecord.batch_id == int(batch_id)).order_by(RawRecord.id.asc()).limit(max(limit, 1))
            ).scalars().all()
            items = [
                {
                    'rawRecordId': row.id,
                    'batchId': row.batch_id,
                    'rawStage': row.raw_stage,
                    'recordIndex': row.record_index,
                    'sourceName': row.source_name,
                    'sourceMode': row.source_mode,
                    'sourceHash': row.source_hash,
                    'sourceSignature': row.source_signature,
                    'previewText': row.preview_text,
                    'payload': row.payload or {},
                    'createdAt': self._iso(row.created_at),
                }
                for row in rows
            ]
        return {
            'batchId': batch_id,
            'workspaceBatchId': detail.get('workspaceBatchId'),
            'contractVersion': detail.get('contractVersion') or self.CONTRACT_VERSION,
            'items': items,
            'total': len(items),
        }
