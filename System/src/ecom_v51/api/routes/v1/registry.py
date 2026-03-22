from __future__ import annotations

from pathlib import Path

from flask import Blueprint

from ecom_v51.registry.dataset_registry import DatasetRegistryService
from ecom_v51.services.batch_service import BatchService

from .common import fail, ok

registry_bp = Blueprint("api_v1_registry", __name__)
ROOT_DIR = Path(__file__).resolve().parents[5]
registry_service = DatasetRegistryService(ROOT_DIR)
batch_service = BatchService(ROOT_DIR)


@registry_bp.route('/datasets', methods=['GET'])
def list_datasets_v1():
    try:
        data = batch_service.list_registry_datasets()
        if not data.get('datasets'):
            data = registry_service.list_datasets()
        return ok(data)
    except Exception as exc:
        return fail('registry_list_failed', '读取数据集注册表失败', details={'reason': str(exc)}, status_code=500)
