"""
数据导入API路由
"""

import ast
import json
from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
from pathlib import Path
import math

from ecom_v51.services.import_service import ImportService
from ecom_v51.registry.dataset_registry import DatasetRegistryService

import_bp = Blueprint('import', __name__)

# 上传目录
UPLOAD_FOLDER = Path(__file__).parent.parent.parent.parent / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)
import_service = ImportService()

DATASET_CONTRACT_VERSION = "p0.v2"


def _get_dataset_registry_payload():
    try:
        if hasattr(import_service, "get_dataset_registry"):
            payload = import_service.get_dataset_registry()
            if isinstance(payload, dict):
                return _sanitize_for_json(payload)
    except Exception:
        pass
    try:
        root_dir = Path(__file__).resolve().parents[4]
        payload = DatasetRegistryService(root_dir).list_datasets()
        if isinstance(payload, dict):
            return _sanitize_for_json(payload)
    except Exception as exc:
        return {"contractVersion": DATASET_CONTRACT_VERSION, "datasets": [], "error": str(exc)}
    return {"contractVersion": DATASET_CONTRACT_VERSION, "datasets": []}


def _ensure_batch_contract_defaults(payload, *, stage: str):
    if not isinstance(payload, dict):
        return payload
    payload.setdefault("ingestionContractVersion", DATASET_CONTRACT_VERSION)
    payload.setdefault("contractVersion", DATASET_CONTRACT_VERSION)
    payload.setdefault("datasetKind", "orders")
    if stage == "upload":
        payload.setdefault("batchStatus", "parsed")
    elif stage == "confirm":
        payload.setdefault("batchStatus", "imported" if payload.get("status") == "success" else "failed")
    return payload



def _sanitize_for_json(value):
    try:
        import numpy as np  # type: ignore
    except Exception:
        np = None

    if np is not None:
        if isinstance(value, np.generic):
            value = value.item()
        elif isinstance(value, np.ndarray):
            value = value.tolist()

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_sanitize_for_json(v) for v in value]

    if hasattr(value, "isoformat") and not isinstance(value, (str, bytes)):
        try:
            return value.isoformat()
        except Exception:
            pass

    return value


def _ensure_json_object(value, *, label: str):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            try:
                value = ast.literal_eval(value)
            except Exception:
                return None, (jsonify({'error': f'{label} is string and cannot be parsed'}), 500)

    value = _sanitize_for_json(value)

    if not isinstance(value, dict):
        return None, (jsonify({'error': f'{label} must be dict, got {type(value).__name__}'}), 500)

    return value, None


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
        
        # 保存文件
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
        dataset_kind = request.form.get('dataset_kind') or request.form.get('datasetKind') or 'orders'
        import_profile = request.form.get('import_profile') or request.form.get('importProfile') or None
        result = import_service.parse_import_file(
            str(filepath),
            shop_id=shop_id,
            operator=operator,
            dataset_kind=dataset_kind,
            import_profile=import_profile,
        )
        result = _sanitize_for_json(result)
        result = _ensure_batch_contract_defaults(result, stage='upload')
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
        result = import_service.confirm_import(
            session_id=int(data.get('sessionId') or 0),
            shop_id=int(data.get('shopId') or 1),
            manual_overrides=data.get('manualOverrides') or [],
            operator=data.get('operator') or 'frontend_user',
            dataset_kind=data.get('datasetKind') or 'orders',
            import_profile=data.get('importProfile'),
        )
        result = _sanitize_for_json(result)
        result = _ensure_batch_contract_defaults(result, stage='confirm')
        result['success'] = result.get('status') == 'success'
        
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
def dataset_registry():
    """Dataset registry for dataset_kind/sourceType/grain/loaderTarget/gatePolicy."""
    try:
        return jsonify(_get_dataset_registry_payload())
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
        result = import_service.parse_import_file(file_path, shop_id=shop_id, operator=operator)
        result['sourceMode'] = 'server_file'
        result = _sanitize_for_json(result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@import_bp.route('/test-fixture/<name>', methods=['GET'])
def test_fixture(name: str):
    """测试辅助：向浏览器提供受控真实样本文件，便于走正式 /upload 链路。"""
    fixtures = {
        'analytics_xlsx': Path(__file__).resolve().parents[4] / 'data' / 'analytics_report_2026-03-12_23_49.xlsx',
        'cn_xlsx': Path(__file__).resolve().parents[4] / 'data' / '销售数据分析.xlsx',
        'ru_bad_header_xlsx': Path(__file__).resolve().parents[4] / 'sample_data' / 'ozon_bad_header_or_missing_sku.xlsx',
        'cn_csv': Path(__file__).resolve().parents[4] / 'sample_data' / 'p0_csv_scene_from_cn.csv',
    }
    fp = fixtures.get(name)
    if not fp or not fp.exists():
        return jsonify({'error': 'fixture not found'}), 404
    return send_file(fp, as_attachment=True, download_name=fp.name)