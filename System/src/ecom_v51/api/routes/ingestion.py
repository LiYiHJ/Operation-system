"""统一 ingestion 入口（P1 过渡层）"""

from flask import Blueprint, jsonify
from pathlib import Path

from ecom_v51.ingest.contracts import MappingSummary
from ecom_v51.registry.dataset_registry import DatasetRegistryService

ROOT_DIR = Path(__file__).resolve().parents[4]
registry_service = DatasetRegistryService(ROOT_DIR)

ingestion_bp = Blueprint('ingestion', __name__)


@ingestion_bp.route('/dataset-registry', methods=['GET'])
def dataset_registry():
    return jsonify(registry_service.list_datasets())


@ingestion_bp.route('/batch-contract-template', methods=['GET'])
def batch_contract_template():
    return jsonify({
        'contractVersion': 'p1.v1',
        'datasetKind': 'orders',
        'batchStatus': 'validated',
        'transportStatus': 'passed',
        'semanticStatus': 'risk',
        'importabilityStatus': 'risk',
        'quarantineCount': 0,
        'importedRows': 0,
        'mappingSummary': MappingSummary().__dict__,
        'auditSummary': {
            'note': 'template_only',
            'purpose': 'frontend and connector contract alignment',
        },
    })
