from __future__ import annotations

from pathlib import Path

from flask import Blueprint, request

from ecom_v51.api.routes import import_route
from ecom_v51.services.batch_runtime_service import BatchRuntimeService

from .common import fail, get_trace_id, ok

import_bp_v1 = Blueprint('api_v1_import', __name__)
ROOT_DIR = Path(__file__).resolve().parents[5]


def _get_runtime_service() -> BatchRuntimeService:
    batch_service = import_route._get_batch_service()
    return BatchRuntimeService(
        root_dir=ROOT_DIR,
        import_service=import_route.import_service,
        workspace_service=import_route.batch_workspace,
        batch_service=batch_service,
    )


@import_bp_v1.route('/upload', methods=['POST'])
def upload_v1():
    trace_id = get_trace_id()
    idempotency_key = str(request.headers.get('Idempotency-Key') or request.headers.get('IdempotencyKey') or '').strip() or None
    runtime = _get_runtime_service()
    payload = request.get_json(silent=True) or {}
    try:
        shop_id = int((request.form.get('shopId') if request.form else None) or (request.form.get('shop_id') if request.form else None) or payload.get('shopId') or payload.get('shop_id') or 1)
    except Exception:
        shop_id = 1
    operator = str((request.form.get('operator') if request.form else None) or payload.get('operator') or 'frontend_user').strip() or 'frontend_user'
    dataset_kind = str((request.form.get('datasetKind') if request.form else None) or payload.get('datasetKind') or '').strip() or None
    import_profile = str((request.form.get('profileCode') if request.form else None) or (request.form.get('importProfile') if request.form else None) or payload.get('profileCode') or payload.get('importProfile') or '').strip() or None

    file_storage = request.files.get('file')
    file_path = None
    if file_storage is None:
        file_path = str(payload.get('filePath') or '').strip() or None
    if file_storage is None and not file_path:
        return fail('missing_file', '缺少 file 或 filePath', status_code=400, trace_id=trace_id)

    try:
        data = runtime.run_upload(
            file_storage=file_storage,
            file_path=file_path,
            shop_id=shop_id,
            operator=operator,
            dataset_kind=dataset_kind,
            import_profile=import_profile,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            source_mode='upload' if file_storage is not None else 'server_file',
        )
        return ok(data, trace_id=trace_id, status_code=202)
    except FileNotFoundError as exc:
        return fail('source_file_not_found', '源文件不存在', details={'reason': str(exc)}, status_code=404, trace_id=trace_id)
    except Exception as exc:
        return fail('upload_runtime_failed', '上传受理失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)
