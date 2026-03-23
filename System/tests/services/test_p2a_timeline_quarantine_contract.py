
from ecom_v51.services.batch_service import BatchService


def test_batch_timeline_contract_uses_detail_contract_version(monkeypatch):
    service = object.__new__(BatchService)
    monkeypatch.setattr(service, 'get_batch_detail', lambda batch_ref: {
        'batchId': 2,
        'workspaceBatchId': 'ws-000002',
        'sessionId': 2,
        'contractVersion': 'p2a.v1',
        'eventTimeline': [{'eventType': 'parse'}],
    })
    result = BatchService.get_batch_timeline(service, '2')
    assert result['contractVersion'] == 'p2a.v1'
    assert result['total'] == 1


def test_batch_quarantine_contract_uses_detail_contract_version(monkeypatch):
    service = object.__new__(BatchService)
    monkeypatch.setattr(service, 'get_batch_detail', lambda batch_ref: {
        'batchId': 2,
        'workspaceBatchId': 'ws-000002',
        'contractVersion': 'p2a.v1',
        'finalSnapshot': {'quarantineCount': 0, 'importabilityStatus': 'passed'},
        'reasonBuckets': [],
    })
    result = BatchService.get_batch_quarantine_summary(service, '2')
    assert result['contractVersion'] == 'p2a.v1'
    assert result['reasonBuckets'] == []
