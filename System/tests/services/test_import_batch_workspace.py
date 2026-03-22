from pathlib import Path

from ecom_v51.services.import_batch_workspace import ImportBatchWorkspaceService


def test_workspace_event_timeline_roundtrip(tmp_path: Path):
    service = ImportBatchWorkspaceService(tmp_path)

    parse_result = {
        'sessionId': 7,
        'datasetKind': 'orders',
        'importProfile': 'ozon_orders_report',
        'fileName': 'demo.xlsx',
        'status': 'success',
        'finalStatus': 'passed',
        'mappedCount': 39,
        'unmappedCount': 8,
        'mappingCoverage': 0.83,
        'selectedSheet': 'sheet1',
        'batchSnapshot': {
            'contractVersion': 'p1.v1',
            'datasetKind': 'orders',
            'batchStatus': 'validated',
            'transportStatus': 'passed',
            'semanticStatus': 'passed',
            'importabilityStatus': 'risk',
            'quarantineCount': 0,
            'importedRows': 0,
            'mappingSummary': {'mappingCoverage': 0.83},
            'auditSummary': {},
        },
    }
    service.register_parse(session_id=7, parse_result=parse_result, shop_id=1, operator='tester', source_mode='server_file')

    confirm_result = {
        'status': 'success',
        'success': True,
        'datasetKind': 'orders',
        'importProfile': 'ozon_orders_report',
        'importedRows': 1372,
        'errorRows': 0,
        'quarantineCount': 0,
        'batchSnapshot': {
            'contractVersion': 'p1.v1',
            'datasetKind': 'orders',
            'batchStatus': 'imported',
            'transportStatus': 'passed',
            'semanticStatus': 'passed',
            'importabilityStatus': 'passed',
            'quarantineCount': 0,
            'importedRows': 1372,
            'mappingSummary': {'mappingCoverage': 0.83},
            'auditSummary': {},
        },
    }
    service.register_confirm(session_id=7, parse_result=parse_result, confirm_result=confirm_result, shop_id=1, operator='tester')

    detail = service.get_batch(7)
    assert detail is not None
    assert detail['finalSnapshot']['batchStatus'] == 'imported'
    assert len(detail['eventTimeline']) >= 2
    assert detail['eventTimeline'][-1]['eventType'] == 'confirm'
