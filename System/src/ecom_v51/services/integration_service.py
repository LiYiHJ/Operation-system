from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import json
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError
from sqlalchemy import inspect

from ecom_v51.db.models import ExternalDataSourceConfig, ImportBatch, PushDeliveryLog, SyncRunLog
from ecom_v51.db.session import get_engine, get_session
from ecom_v51.services.import_service import ImportService


class IntegrationService:
    def __init__(self, shop_id: int = 1):
        self.shop_id = shop_id
        self._ensure_tables()

    @staticmethod
    def _ensure_tables() -> None:
        engine = get_engine()
        existing = set(inspect(engine).get_table_names())
        to_create = []
        for m in [ExternalDataSourceConfig, SyncRunLog, PushDeliveryLog]:
            if m.__table__.name not in existing:
                to_create.append(m.__table__)
        if to_create:
            ExternalDataSourceConfig.metadata.create_all(bind=engine, tables=to_create)

    def get_data_source_config(self, provider: str = 'ozon') -> dict[str, Any]:
        with get_session() as session:
            row = session.query(ExternalDataSourceConfig).filter(
                ExternalDataSourceConfig.shop_id == self.shop_id,
                ExternalDataSourceConfig.provider == provider,
            ).order_by(ExternalDataSourceConfig.id.desc()).first()
            if not row:
                return {
                    'provider': provider,
                    'enabled': False,
                    'autoSyncEnabled': False,
                    'syncFrequency': 'manual',
                    'credentials': {},
                    'settings': {},
                    'lastSyncAt': None,
                    'lastSyncStatus': None,
                    'lastSyncError': None,
                }
            return {
                'provider': row.provider,
                'enabled': row.enabled,
                'autoSyncEnabled': row.auto_sync_enabled,
                'syncFrequency': row.sync_frequency,
                'credentials': row.credentials_json or {},
                'settings': row.settings_json or {},
                'lastSyncAt': row.last_sync_at.isoformat() if row.last_sync_at else None,
                'lastSyncStatus': row.last_sync_status,
                'lastSyncError': row.last_sync_error,
            }

    def save_data_source_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider = payload.get('provider', 'ozon')
        with get_session() as session:
            row = session.query(ExternalDataSourceConfig).filter(
                ExternalDataSourceConfig.shop_id == self.shop_id,
                ExternalDataSourceConfig.provider == provider,
            ).order_by(ExternalDataSourceConfig.id.desc()).first()
            if not row:
                row = ExternalDataSourceConfig(shop_id=self.shop_id, provider=provider)
                session.add(row)
            row.enabled = bool(payload.get('enabled', True))
            row.auto_sync_enabled = bool(payload.get('autoSyncEnabled', False))
            row.sync_frequency = str(payload.get('syncFrequency', 'manual'))
            row.credentials_json = payload.get('credentials') or {}
            row.settings_json = payload.get('settings') or {}
            session.flush()
        return self.get_data_source_config(provider=provider)

    @staticmethod
    def _latest_source_file() -> Path | None:
        candidates = []
        for folder in [Path('data'), Path('src/uploads')]:
            if folder.exists():
                candidates.extend(list(folder.glob('*.xlsx')))
                candidates.extend(list(folder.glob('*.xls')))
                candidates.extend(list(folder.glob('*.csv')))
        if not candidates:
            return None
        return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]

    def run_sync_once(self, provider: str = 'ozon', trigger_mode: str = 'manual') -> dict[str, Any]:
        source_file = self._latest_source_file()
        started = datetime.utcnow()

        with get_session() as session:
            run = SyncRunLog(
                shop_id=self.shop_id,
                provider=provider,
                trigger_mode=trigger_mode,
                status='running',
                started_at=started,
                message=f'准备同步: {source_file.name if source_file else "no_file"}',
            )
            session.add(run)
            session.flush()
            run_id = run.id

        try:
            if not source_file:
                raise ValueError('未找到可用于同步的数据文件（data 或 src/uploads）')

            svc = ImportService()
            parsed = svc.parse_import_file(str(source_file), shop_id=self.shop_id, operator=f'{provider}_sync')
            confirmed = svc.confirm_import(
                session_id=int(parsed['sessionId']),
                shop_id=self.shop_id,
                manual_overrides=[],
                operator=f'{provider}_sync',
            )

            with get_session() as session:
                run = session.query(SyncRunLog).filter(SyncRunLog.id == run_id).one()
                run.status = confirmed.get('status', 'success')
                run.finished_at = datetime.utcnow()
                run.imported_rows = int(confirmed.get('importedRows') or 0)
                run.batch_id = int(confirmed.get('batchId') or 0)
                run.message = f"session={parsed.get('sessionId')} imported={run.imported_rows}"

                cfg = session.query(ExternalDataSourceConfig).filter(
                    ExternalDataSourceConfig.shop_id == self.shop_id,
                    ExternalDataSourceConfig.provider == provider,
                ).order_by(ExternalDataSourceConfig.id.desc()).first()
                if cfg:
                    cfg.last_sync_at = datetime.utcnow()
                    cfg.last_sync_status = run.status
                    cfg.last_sync_error = None

            return {'status': 'success', 'provider': provider, 'runId': run_id, 'sourceFile': source_file.name, **confirmed}
        except Exception as ex:
            with get_session() as session:
                run = session.query(SyncRunLog).filter(SyncRunLog.id == run_id).one()
                run.status = 'failed'
                run.finished_at = datetime.utcnow()
                run.message = str(ex)
                cfg = session.query(ExternalDataSourceConfig).filter(
                    ExternalDataSourceConfig.shop_id == self.shop_id,
                    ExternalDataSourceConfig.provider == provider,
                ).order_by(ExternalDataSourceConfig.id.desc()).first()
                if cfg:
                    cfg.last_sync_at = datetime.utcnow()
                    cfg.last_sync_status = 'failed'
                    cfg.last_sync_error = str(ex)
            return {'status': 'failed', 'provider': provider, 'runId': run_id, 'error': str(ex)}

    def list_sync_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        with get_session() as session:
            rows = session.query(SyncRunLog).filter(SyncRunLog.shop_id == self.shop_id).order_by(SyncRunLog.id.desc()).limit(limit).all()
            return [{
                'id': r.id,
                'provider': r.provider,
                'triggerMode': r.trigger_mode,
                'status': r.status,
                'startedAt': r.started_at.isoformat() if r.started_at else None,
                'finishedAt': r.finished_at.isoformat() if r.finished_at else None,
                'importedRows': r.imported_rows,
                'batchId': r.batch_id,
                'message': r.message,
            } for r in rows]

    def list_import_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        with get_session() as session:
            rows = session.query(ImportBatch).order_by(ImportBatch.id.desc()).limit(limit).all()
            return [{
                'batchId': r.id,
                'sourceType': r.source_type,
                'platformCode': r.platform_code,
                'status': r.status,
                'successCount': r.success_count,
                'errorCount': r.error_count,
                'startedAt': r.started_at.isoformat() if r.started_at else None,
                'finishedAt': r.finished_at.isoformat() if r.finished_at else None,
                'message': r.message,
            } for r in rows]

    def push_to_sales_backend(self, payload: dict[str, Any], target_url: str | None = None, strategy_task_id: int | None = None, execution_log_id: int | None = None) -> dict[str, Any]:
        config = self.get_data_source_config('ozon')
        default_url = (config.get('settings') or {}).get('sales_push_url') or 'http://127.0.0.1:5000/api/integration/mock/sales-backend'
        url = target_url or default_url
        now = datetime.utcnow()

        status = 'failed'
        http_status = None
        response_json: dict[str, Any] = {}
        error_message = None

        try:
            req = urlrequest.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urlrequest.urlopen(req, timeout=8) as resp:
                http_status = resp.status
                raw = resp.read().decode('utf-8') if resp else ''
                try:
                    response_json = json.loads(raw) if raw else {}
                except Exception:
                    response_json = {'raw': raw[:500]}
                status = 'success' if 200 <= http_status < 300 else 'failed'
                if status != 'success':
                    error_message = f'HTTP {http_status}'
        except HTTPError as ex:
            http_status = ex.code
            error_message = f'HTTP {ex.code}'
            try:
                response_json = json.loads(ex.read().decode('utf-8'))
            except Exception:
                response_json = {'raw': str(ex)}
        except URLError as ex:
            error_message = str(ex)
        except Exception as ex:
            error_message = str(ex)

        with get_session() as session:
            log = PushDeliveryLog(
                strategy_task_id=strategy_task_id,
                execution_log_id=execution_log_id,
                target_system='sales_backend',
                payload_json=payload,
                response_json=response_json,
                status=status,
                http_status=http_status,
                error_message=error_message,
                pushed_at=now,
            )
            session.add(log)
            session.flush()
            log_id = log.id

        return {
            'pushId': log_id,
            'status': status,
            'httpStatus': http_status,
            'targetUrl': url,
            'response': response_json,
            'error': error_message,
            'pushedAt': now.isoformat(),
        }

    def list_push_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        with get_session() as session:
            rows = session.query(PushDeliveryLog).order_by(PushDeliveryLog.id.desc()).limit(limit).all()
            return [{
                'pushId': r.id,
                'strategyTaskId': r.strategy_task_id,
                'executionLogId': r.execution_log_id,
                'status': r.status,
                'httpStatus': r.http_status,
                'error': r.error_message,
                'pushedAt': r.pushed_at.isoformat() if r.pushed_at else None,
                'targetSystem': r.target_system,
                'response': r.response_json,
            } for r in rows]
