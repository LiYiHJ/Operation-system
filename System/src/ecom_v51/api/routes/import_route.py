"""
数据导入API路由
"""

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from ecom_v51.ingest.orchestrator import IngestionOrchestrator
from ecom_v51.registry.dataset_registry import DatasetRegistryService
from ecom_v51.services.import_service import ImportService

import_bp = Blueprint('import', __name__)

ROOT_DIR = Path(__file__).resolve().parents[4]
UPLOAD_FOLDER = ROOT_DIR / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

import_service = ImportService()
dataset_registry = DatasetRegistryService(ROOT_DIR)
orchestrator = IngestionOrchestrator()


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


def _attach_parse_contract(parse_result: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(parse_result)
    enriched['datasetKind'] = contract.get('datasetKind') or 'orders'
    enriched['importProfile'] = contract.get('importProfile') or enriched['datasetKind']
    enriched['batchStatus'] = _derive_parse_batch_status(parse_result)
    snapshot = orchestrator.build_parse_snapshot(enriched, dataset_kind=enriched['datasetKind'])
    snapshot.batchStatus = enriched['batchStatus']
    if parse_result.get('finalStatus') == 'passed':
        snapshot.importabilityStatus = 'risk'
    elif parse_result.get('finalStatus') == 'risk':
        snapshot.importabilityStatus = 'risk'
    else:
        snapshot.importabilityStatus = 'failed'
    enriched['batchSnapshot'] = {
        'contractVersion': snapshot.contractVersion,
        'datasetKind': snapshot.datasetKind,
        'batchStatus': snapshot.batchStatus,
        'transportStatus': snapshot.transportStatus,
        'semanticStatus': snapshot.semanticStatus,
        'importabilityStatus': snapshot.importabilityStatus,
        'quarantineCount': snapshot.quarantineCount,
        'importedRows': snapshot.importedRows,
        'mappingSummary': snapshot.mappingSummary.__dict__,
        'auditSummary': snapshot.auditSummary,
    }
    return enriched


def _attach_confirm_contract(parse_result: Dict[str, Any], confirm_result: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(confirm_result)
    enriched['datasetKind'] = contract.get('datasetKind') or parse_result.get('datasetKind') or 'orders'
    enriched['importProfile'] = contract.get('importProfile') or parse_result.get('importProfile') or enriched['datasetKind']
    enriched['batchStatus'] = _derive_confirm_batch_status(confirm_result)
    snapshot = orchestrator.build_confirm_snapshot(parse_result, enriched)
    snapshot.batchStatus = enriched['batchStatus']
    enriched['batchSnapshot'] = {
        'contractVersion': snapshot.contractVersion,
        'datasetKind': snapshot.datasetKind,
        'batchStatus': snapshot.batchStatus,
        'transportStatus': snapshot.transportStatus,
        'semanticStatus': snapshot.semanticStatus,
        'importabilityStatus': snapshot.importabilityStatus,
        'quarantineCount': snapshot.quarantineCount,
        'importedRows': snapshot.importedRows,
        'mappingSummary': snapshot.mappingSummary.__dict__,
        'auditSummary': snapshot.auditSummary,
    }
    return enriched


@import_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    上传文件
    前端调用: importAPI.uploadFile(file)
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': '未找到文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400

        raw_filename = file.filename or ''
        filename = secure_filename(raw_filename)
        raw_suffix = Path(raw_filename).suffix
        if raw_suffix and '.' not in filename:
            filename = f"{filename}.{raw_suffix.lstrip('.')}" if filename else f"upload{raw_suffix}"
        if not filename:
            suffix = raw_suffix or '.xlsx'
            filename = f'upload{suffix}'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename_with_ts = f"{timestamp}_{filename}"
        filepath = UPLOAD_FOLDER / filename_with_ts
        file.save(filepath)

        shop_id = int(request.form.get('shop_id') or 1)
        operator = request.form.get('operator') or 'frontend_user'
        dataset_kind = str(request.form.get('dataset_kind') or '').strip() or None
        import_profile = str(request.form.get('import_profile') or '').strip() or None
        contract = _resolve_dataset_contract(dataset_kind, import_profile)

        result = import_service.parse_import_file(str(filepath), shop_id=shop_id, operator=operator)
        result = _attach_parse_contract(result, contract)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@import_bp.route('/confirm', methods=['POST'])
def confirm_import():
    """
    确认导入
    前端调用: importAPI.confirmImport(data)
    """
    try:
        data = request.get_json() or {}
        session_id = int(data.get('sessionId') or 0)
        parse_result = import_service.get_session_result(session_id) or {}
        dataset_kind = str(data.get('datasetKind') or parse_result.get('datasetKind') or '').strip() or None
        import_profile = str(data.get('importProfile') or parse_result.get('importProfile') or '').strip() or None
        contract = _resolve_dataset_contract(dataset_kind, import_profile)

        result = import_service.confirm_import(
            session_id=session_id,
            shop_id=int(data.get('shopId') or 1),
            manual_overrides=data.get('manualOverrides') or [],
            operator=data.get('operator') or 'frontend_user',
        )
        result['success'] = result.get('status') == 'success'
        result = _attach_confirm_contract(parse_result, result, contract)
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


@import_bp.route('/batches/<int:session_id>', methods=['GET'])
def get_batch_snapshot(session_id: int):
    """轻量批次快照：当前仍基于内存 session，用于前端工作台化过渡。"""
    try:
        parse_result = import_service.get_session_result(session_id)
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
