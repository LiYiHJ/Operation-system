"""
数据导入API路由
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from ecom_v51.ingest.orchestrator import IngestionOrchestrator
from ecom_v51.registry.dataset_registry import DatasetRegistryService
from ecom_v51.services.import_batch_workspace import ImportBatchWorkspaceService
from ecom_v51.services.import_service import ImportService

import_bp = Blueprint('import', __name__)

ROOT_DIR = Path(__file__).resolve().parents[4]
UPLOAD_FOLDER = ROOT_DIR / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

import_service = ImportService()
dataset_registry = DatasetRegistryService(ROOT_DIR)
orchestrator = IngestionOrchestrator()
batch_workspace = ImportBatchWorkspaceService(ROOT_DIR)


def _build_safe_upload_filename(raw_filename: str | None) -> str:
    raw_filename = str(raw_filename or '').strip()
    fallback_name = f"upload-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
    candidate = secure_filename(raw_filename) if raw_filename else ''
    original_suffix = Path(raw_filename).suffix if raw_filename else ''

    if candidate:
        candidate_path = Path(candidate)
        if not candidate_path.suffix and original_suffix:
            return f"{candidate_path.name}{original_suffix}"
        return candidate

    if original_suffix:
        return f"{fallback_name}{original_suffix}"
    return fallback_name


def _resolve_dataset_contract(dataset_kind: str | None, import_profile: str | None) -> Dict[str, Any]:
    return dataset_registry.get_dataset(dataset_kind=dataset_kind, import_profile=import_profile)


def _derive_parse_batch_status(parse_result: Dict[str, Any]) -> str:
    final_status = str(parse_result.get('finalStatus') or 'failed')
    if str(parse_result.get('transportStatus') or 'failed') == 'failed':
        return 'failed'
    if final_status == 'passed':
        return 'validated'
    if final_status == 'risk':
        return 'mapped'
    return 'failed'


def _derive_confirm_batch_status(confirm_result: Dict[str, Any]) -> str:
    importability_status = str(confirm_result.get('importabilityStatus') or 'failed')
    imported_rows = int(confirm_result.get('importedRows') or 0)
    quarantine_count = int(confirm_result.get('quarantineCount') or 0)
    if importability_status == 'passed' and imported_rows > 0:
        return 'imported'
    if importability_status == 'risk' and imported_rows > 0:
        return 'partially_imported'
    if importability_status == 'risk' and quarantine_count > 0:
        return 'blocked'
    return 'failed'


def _snapshot_to_dict(snapshot: Any) -> Dict[str, Any]:
    if isinstance(snapshot, dict):
        return snapshot
    if snapshot is None:
        return {}
    mapping_summary = getattr(snapshot, 'mappingSummary', None)
    return {
        'contractVersion': getattr(snapshot, 'contractVersion', 'p1.v1'),
        'datasetKind': getattr(snapshot, 'datasetKind', 'orders'),
        'batchStatus': getattr(snapshot, 'batchStatus', 'failed'),
        'transportStatus': getattr(snapshot, 'transportStatus', 'failed'),
        'semanticStatus': getattr(snapshot, 'semanticStatus', 'failed'),
        'importabilityStatus': getattr(snapshot, 'importabilityStatus', 'failed'),
        'quarantineCount': getattr(snapshot, 'quarantineCount', 0),
        'importedRows': getattr(snapshot, 'importedRows', 0),
        'mappingSummary': mapping_summary.__dict__ if mapping_summary is not None else {},
        'auditSummary': getattr(snapshot, 'auditSummary', {}),
    }



def _build_confirm_snapshot_compat(parse_result: Dict[str, Any], confirm_result: Dict[str, Any], dataset_kind: str | None, import_profile: str | None):
    """兼容不同版本 orchestrator.build_confirm_snapshot 签名。"""
    parse_snapshot = parse_result.get('batchSnapshot') or parse_result or {}
    try:
        return orchestrator.build_confirm_snapshot(
            parse_snapshot,
            confirm_result,
            dataset_kind=dataset_kind,
            import_profile=import_profile,
        )
    except TypeError:
        return orchestrator.build_confirm_snapshot(parse_snapshot, confirm_result)


def _attach_parse_contract(parse_result: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(parse_result)
    enriched['datasetKind'] = contract.get('datasetKind') or enriched.get('datasetKind') or 'orders'
    enriched['importProfile'] = contract.get('importProfile') or enriched.get('importProfile') or enriched['datasetKind']
    enriched['batchStatus'] = _derive_parse_batch_status(parse_result)
    snapshot = orchestrator.build_parse_snapshot(enriched, dataset_kind=enriched['datasetKind'])
    snapshot.batchStatus = enriched['batchStatus']
    if parse_result.get('finalStatus') == 'passed':
        snapshot.importabilityStatus = 'risk'
    elif parse_result.get('finalStatus') == 'risk':
        snapshot.importabilityStatus = 'risk'
    else:
        snapshot.importabilityStatus = 'failed'
    enriched['batchSnapshot'] = _snapshot_to_dict(snapshot)
    return enriched


def _attach_confirm_contract(parse_result: Dict[str, Any], confirm_result: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(confirm_result)
    enriched['datasetKind'] = contract.get('datasetKind') or parse_result.get('datasetKind') or 'orders'
    enriched['importProfile'] = contract.get('importProfile') or parse_result.get('importProfile') or enriched['datasetKind']
    enriched['batchStatus'] = _derive_confirm_batch_status(confirm_result)
    parse_snapshot = parse_result.get('batchSnapshot') or {}
    snapshot = orchestrator.build_confirm_snapshot(
        parse_snapshot,
        enriched,
        dataset_kind=enriched['datasetKind'],
    )
    snapshot.batchStatus = enriched['batchStatus']
    snapshot.importabilityStatus = str(enriched.get('importabilityStatus') or snapshot.importabilityStatus)
    enriched['batchSnapshot'] = _snapshot_to_dict(snapshot)
    return enriched


def _get_session_result(session_id: int) -> Dict[str, Any]:
    getter = getattr(import_service, 'get_session_result', None)
    if callable(getter):
        result = getter(session_id)
        if isinstance(result, dict) and result:
            return result
    persisted = batch_workspace.get_batch(session_id)
    if not persisted:
        return {}
    parse_meta = persisted.get('parseResultMeta') or {}
    parse_snapshot = persisted.get('parseSnapshot') or persisted.get('finalSnapshot') or {}
    return {
        'sessionId': session_id,
        'fileName': persisted.get('fileName'),
        'datasetKind': persisted.get('datasetKind'),
        'importProfile': persisted.get('importProfile'),
        'sourceMode': persisted.get('sourceMode'),
        'status': parse_meta.get('status'),
        'finalStatus': parse_meta.get('finalStatus'),
        'mappedCount': parse_meta.get('mappedCount'),
        'unmappedCount': parse_meta.get('unmappedCount'),
        'mappingCoverage': parse_meta.get('mappingCoverage'),
        'mappedConfidence': parse_meta.get('mappedConfidence'),
        'selectedSheet': parse_meta.get('selectedSheet'),
        'topUnmappedHeaders': parse_meta.get('topUnmappedHeaders') or [],
        'importabilityReasons': parse_meta.get('importabilityReasons') or [],
        'semanticGateReasons': parse_meta.get('semanticGateReasons') or [],
        'riskOverrideReasons': parse_meta.get('riskOverrideReasons') or [],
        'batchSnapshot': parse_snapshot,
        'transportStatus': parse_snapshot.get('transportStatus'),
        'semanticStatus': parse_snapshot.get('semanticStatus'),
    }


@import_bp.route('/upload', methods=['POST'])
def upload_file():
    """上传并解析文件。"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '缺少文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400

        filename = _build_safe_upload_filename(file.filename)
        file_path = UPLOAD_FOLDER / filename
        file.save(file_path)

        shop_id = int(request.form.get('shop_id') or 1)
        operator = request.form.get('operator') or 'frontend_user'
        dataset_kind = str(request.form.get('dataset_kind') or '').strip() or None
        import_profile = str(request.form.get('import_profile') or '').strip() or None
        contract = _resolve_dataset_contract(dataset_kind, import_profile)

        result = import_service.parse_import_file(str(file_path), shop_id=shop_id, operator=operator)
        result['fileName'] = file.filename or filename
        result['sourceMode'] = 'upload'
        result = _attach_parse_contract(result, contract)
        persisted = batch_workspace.register_parse(
            session_id=int(result.get('sessionId') or 0),
            parse_result=result,
            shop_id=shop_id,
            operator=operator,
            source_mode='upload',
        )
        result['workspaceBatchId'] = persisted.get('workspaceBatchId')
        result['persistedBatchId'] = persisted.get('dbBatchId')
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500




def _decorate_confirm_ui_result(result: dict) -> dict:
    payload = dict(result or {})
    imported_rows = int(payload.get('importedRows') or 0)
    quarantine_count = int(payload.get('quarantineCount') or 0)
    batch_status = str(payload.get('batchStatus') or '').lower()
    importability = str(payload.get('importabilityStatus') or '').lower()

    ui_outcome = 'failed'
    user_message = payload.get('errors', ['导入失败'])[0] if isinstance(payload.get('errors'), list) and payload.get('errors') else '导入失败'

    if batch_status == 'blocked' or (imported_rows == 0 and quarantine_count > 0):
        ui_outcome = 'blocked'
        user_message = f'本次 0 条入库，{quarantine_count} 条数据已隔离'
    elif imported_rows > 0 and quarantine_count > 0:
        ui_outcome = 'partial'
        user_message = f'导入完成：{imported_rows} 条入库，{quarantine_count} 条隔离'
    elif imported_rows > 0 and payload.get('status') == 'success':
        ui_outcome = 'imported'
        user_message = f'成功导入 {imported_rows} 条数据'
    elif payload.get('status') == 'success':
        ui_outcome = 'empty'
        user_message = '导入流程执行完成，但没有新增入库数据'

    payload['uiOutcome'] = ui_outcome
    payload['userMessage'] = user_message
    payload['success'] = payload.get('status') == 'success'
    payload['importabilityStatus'] = payload.get('importabilityStatus') or importability or 'failed'
    return payload

@import_bp.route('/confirm', methods=['POST'])
def confirm_import():
    """确认导入。"""
    try:
        data = request.get_json() or {}
        session_id = int(data.get('sessionId') or 0)
        parse_result = _get_session_result(session_id) or {}
        dataset_kind = str(data.get('datasetKind') or parse_result.get('datasetKind') or '').strip() or None
        import_profile = str(data.get('importProfile') or parse_result.get('importProfile') or '').strip() or None
        contract = _resolve_dataset_contract(dataset_kind, import_profile)

        parse_final_status = str(parse_result.get('finalStatus') or '').lower()
        parse_transport_status = str((parse_result.get('batchSnapshot') or {}).get('transportStatus') or parse_result.get('transportStatus') or '').lower()
        if not parse_result or parse_final_status == 'failed' or parse_transport_status == 'failed':
            return jsonify({
                'status': 'failed',
                'success': False,
                'errors': ['parse_not_confirmable'],
                'importabilityReasons': ['parse_not_confirmable'],
                'datasetKind': contract.get('datasetKind') or parse_result.get('datasetKind') or 'orders',
                'importProfile': contract.get('importProfile') or parse_result.get('importProfile') or 'orders',
                'batchStatus': 'failed',
            }), 400

        shop_id = int(data.get('shopId') or 1)
        operator = data.get('operator') or 'frontend_user'
        result = import_service.confirm_import(
            session_id=session_id,
            shop_id=shop_id,
            manual_overrides=data.get('manualOverrides') or [],
            operator=operator,
        )
        result = _attach_confirm_contract(parse_result, result, contract)
        result = _decorate_confirm_ui_result(result)
        persisted = batch_workspace.register_confirm(
            session_id=session_id,
            parse_result=parse_result,
            confirm_result=result,
            shop_id=shop_id,
            operator=operator,
        )
        result['workspaceBatchId'] = persisted.get('workspaceBatchId')
        if persisted.get('dbBatchId'):
            result['batchId'] = persisted.get('dbBatchId')
        result['persistedBatchId'] = persisted.get('dbBatchId')
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@import_bp.route('/field-registry', methods=['GET'])
def field_registry():
    """统一字段注册表（前后端同源）"""
    try:
        return jsonify(import_service.get_field_registry())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@import_bp.route('/dataset-registry', methods=['GET'])
def get_dataset_registry():
    """导入数据集注册表（兼容入口）"""
    try:
        return jsonify(dataset_registry.list_datasets())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@import_bp.route('/batches', methods=['GET'])
def list_batches():
    """工作台批次列表：优先返回持久化 workspace store。"""
    try:
        limit = int(request.args.get('limit') or 20)
        return jsonify(batch_workspace.list_batches(limit=limit))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@import_bp.route('/batches/<int:session_id>', methods=['GET'])
def get_batch_snapshot(session_id: int):
    """批次详情：优先读持久化 workspace store，找不到再回退到内存 session。"""
    try:
        persisted = batch_workspace.get_batch(session_id)
        if persisted:
            return jsonify(persisted)
        parse_result = _get_session_result(session_id)
        if not parse_result:
            return jsonify({'error': 'batch not found'}), 404
        contract = _resolve_dataset_contract(
            str(parse_result.get('datasetKind') or '').strip() or None,
            str(parse_result.get('importProfile') or '').strip() or None,
        )
        payload = _attach_parse_contract(parse_result, contract)
        return jsonify(payload)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@import_bp.route('/batches/workspace/<workspace_batch_id>', methods=['GET'])
def get_batch_by_workspace_id(workspace_batch_id: str):
    """按 workspaceBatchId 读取批次详情。"""
    try:
        persisted = batch_workspace.get_batch_by_workspace_id(workspace_batch_id)
        if not persisted:
            return jsonify({'error': 'batch not found'}), 404
        return jsonify(persisted)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@import_bp.route('/batches/<int:session_id>/audit', methods=['GET'])
def get_batch_audit(session_id: int):
    """批次审计时间线。"""
    try:
        persisted = batch_workspace.get_batch(session_id)
        if not persisted:
            return jsonify({'error': 'batch not found'}), 404
        return jsonify({
            'workspaceBatchId': persisted.get('workspaceBatchId'),
            'sessionId': persisted.get('sessionId'),
            'eventTimeline': persisted.get('eventTimeline') or [],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@import_bp.route('/upload-server-file', methods=['POST'])
def upload_server_file():
    """浏览器环境无法直传本地真实文件时，使用服务器侧已有文件做同链路解析。"""
    try:
        data = request.get_json() or {}
        file_path = str(data.get('filePath') or '').strip()
        if not file_path:
            return jsonify({'error': 'filePath is required'}), 400
        shop_id = int(data.get('shop_id') or 1)
        operator = data.get('operator') or 'frontend_user'
        dataset_kind = str(data.get('datasetKind') or '').strip() or None
        import_profile = str(data.get('importProfile') or '').strip() or None
        contract = _resolve_dataset_contract(dataset_kind, import_profile)
        result = import_service.parse_import_file(file_path, shop_id=shop_id, operator=operator)
        result['sourceMode'] = 'server_file'
        result = _attach_parse_contract(result, contract)
        persisted = batch_workspace.register_parse(
            session_id=int(result.get('sessionId') or 0),
            parse_result=result,
            shop_id=shop_id,
            operator=operator,
            source_mode='server_file',
        )
        result['workspaceBatchId'] = persisted.get('workspaceBatchId')
        result['persistedBatchId'] = persisted.get('dbBatchId')
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@import_bp.route('/test-fixture/<name>', methods=['GET'])
def test_fixture(name: str):
    """测试辅助：向浏览器提供受控真实样本文件，便于走正式 /upload 链路。"""
    fixtures = {
        'analytics_xlsx': ROOT_DIR / 'data' / 'analytics_report_2026-03-12_23_49.xlsx',
        'cn_xlsx': ROOT_DIR / 'data' / '销售数据分析.xlsx',
        'ru_bad_header_xlsx': ROOT_DIR / 'sample_data' / 'ozon_bad_header_or_missing_sku.xlsx',
        'cn_csv': ROOT_DIR / 'sample_data' / 'p0_csv_scene_from_cn.csv',
    }
    fp = fixtures.get(name)
    if not fp or not fp.exists():
        return jsonify({'error': 'fixture not found'}), 404
    return send_file(fp, as_attachment=True, download_name=fp.name)
