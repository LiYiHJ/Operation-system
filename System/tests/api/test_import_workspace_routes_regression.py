from ecom_v51.ingest.orchestrator import IngestionOrchestrator


def test_build_confirm_snapshot_accepts_dataset_kind_and_import_profile():
    orchestrator = IngestionOrchestrator()
    parse_result = {
        "datasetKind": "orders",
        "importProfile": "ozon_orders_report",
        "mappedCount": 10,
        "unmappedCount": 2,
        "mappingCoverage": 0.83,
        "transportStatus": "passed",
        "semanticStatus": "passed",
        "batchStatus": "validated",
    }
    confirm_result = {
        "status": "success",
        "datasetKind": "orders",
        "importProfile": "ozon_orders_report",
        "batchStatus": "imported",
        "transportStatus": "passed",
        "semanticStatus": "passed",
        "importabilityStatus": "passed",
        "importedRows": 100,
        "quarantineCount": 0,
        "success": True,
    }
    snapshot = orchestrator.build_confirm_snapshot(
        parse_result,
        confirm_result,
        dataset_kind="orders",
        import_profile="ozon_orders_report",
    )
    assert snapshot.datasetKind == "orders"
    assert snapshot.auditSummary["importProfile"] == "ozon_orders_report"
    assert snapshot.importedRows == 100
