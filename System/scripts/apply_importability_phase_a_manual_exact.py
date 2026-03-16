
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"

OLD_CONFIRM_BLOCK = """    def confirm_import(self, session_id: int, shop_id: int, manual_overrides: Optional[List[dict]] = None, operator: str = "frontend_user") -> dict:
        if session_id not in self._sessions:
            return {
                "sessionId": session_id,
                "batchId": 0,
                "importedRows": 0,
                "errorRows": 0,
                "status": "failed",
                "warnings": [],
                "errors": ["session not found"],
                "transportStatus": "failed",
                "semanticStatus": "failed",
                "finalStatus": "failed",
                "semanticGateReasons": ["session_not_found"],
                "riskOverrideReasons": [],
                "semanticAcceptanceReason": [],
                "recoverySummary": {},
            }

        session = self._sessions[session_id]
        result = session["result"]
        valid_df: pd.DataFrame = session["df"]
        row_errors: List[Dict[str, Any]] = session["rowErrors"]
        manual_overrides = manual_overrides or []

        if manual_overrides:
            # 仅记录，不在当前轻量版中二次重写 DataFrame。
            result = copy.deepcopy(result)
            result["fieldMappings"] = list(result.get("fieldMappings") or []) + [
                {
                    "originalField": str(item.get("originalField") or "manual_override"),
                    "normalizedField": str(item.get("normalizedField") or "manual_override"),
                    "standardField": item.get("standardField"),
                    "mappingSource": "manual_override",
                    "confidence": 1.0,
                    "sampleValues": [],
                    "isManual": True,
                    "reasons": ["manual_override_applied"],
                }
                for item in manual_overrides
            ]

        warnings: List[str] = []
        if session.get("duplicateCount"):
            warnings.append(f"发现并移除 {session['duplicateCount']} 条重复记录")
        if result.get("finalStatus") == "risk":
            warnings.append("当前样本处于 risk 状态，请结合语义门禁原因复核")

        response = {
            "sessionId": session_id,
            "batchId": session_id,
            "importedRows": int(len(valid_df)),
            "errorRows": int(len(row_errors)),
            "status": "success",
            "warnings": warnings,
            "errors": [str(item.get("error")) for item in row_errors[:50]],
            "rowErrorSummary": {
                "auto_fixed": 0,
                "ignorable": 0,
                "quarantined": int(len(row_errors)),
                "fatal": 0,
            },
            "quarantineCount": int(len(row_errors)),
            "stagingRows": int(len(valid_df)),
            "factLoadErrors": 0,
            "transportStatus": result.get("transportStatus"),
            "semanticStatus": result.get("semanticStatus"),
            "finalStatus": result.get("finalStatus"),
            "semanticGateReasons": list(result.get("semanticGateReasons") or []),
            "riskOverrideReasons": list(result.get("riskOverrideReasons") or []),
            "semanticAcceptanceReason": list(result.get("semanticAcceptanceReason") or []),
            "recoverySummary": {
                "headerRecoveryApplied": result.get("headerRecoveryApplied"),
                "preRecoveryStatus": result.get("preRecoveryStatus"),
                "postRecoveryStatus": result.get("postRecoveryStatus"),
                "recoveryAttempted": result.get("recoveryAttempted"),
                "recoveryImproved": result.get("recoveryImproved"),
                "semanticGateReasons": list(result.get("semanticGateReasons") or []),
                "riskOverrideReasons": list(result.get("riskOverrideReasons") or []),
                "recoveryDiff": copy.deepcopy(result.get("recoveryDiff") or {}),
            },
            "runtimeAudit": {
                "sessionId": session_id,
                "operator": operator,
                "shopId": shop_id,
                "confirmedAt": datetime.now().isoformat(),
                "sourceFile": session.get("fileName"),
                "finalStatus": result.get("finalStatus"),
                "transportStatus": result.get("transportStatus"),
                "semanticStatus": result.get("semanticStatus"),
                "quarantineCount": int(len(row_errors)),
                "factLoadErrors": 0,
                "recoverySummary": {
                    "headerRecoveryApplied": result.get("headerRecoveryApplied"),
                    "preRecoveryStatus": result.get("preRecoveryStatus"),
                    "postRecoveryStatus": result.get("postRecoveryStatus"),
                    "recoveryAttempted": result.get("recoveryAttempted"),
                    "recoveryImproved": result.get("recoveryImproved"),
                },
            },
        }
        return response
"""

NEW_CONFIRM_BLOCK = """    def confirm_import(self, session_id: int, shop_id: int, manual_overrides: Optional[List[dict]] = None, operator: str = "frontend_user") -> dict:
        if session_id not in self._sessions:
            return {
                "sessionId": session_id,
                "batchId": 0,
                "importedRows": 0,
                "errorRows": 0,
                "status": "failed",
                "warnings": [],
                "errors": ["session not found"],
                "transportStatus": "failed",
                "semanticStatus": "failed",
                "finalStatus": "failed",
                "importabilityStatus": "failed",
                "importabilityReasons": ["session_not_found"],
                "semanticGateReasons": ["session_not_found"],
                "riskOverrideReasons": [],
                "semanticAcceptanceReason": [],
                "recoverySummary": {},
            }

        session = self._sessions[session_id]
        result = session["result"]
        valid_df: pd.DataFrame = session["df"]
        row_errors: List[Dict[str, Any]] = session["rowErrors"]
        manual_overrides = manual_overrides or []

        if manual_overrides:
            # 仅记录，不在当前轻量版中二次重写 DataFrame。
            result = copy.deepcopy(result)
            result["fieldMappings"] = list(result.get("fieldMappings") or []) + [
                {
                    "originalField": str(item.get("originalField") or "manual_override"),
                    "normalizedField": str(item.get("normalizedField") or "manual_override"),
                    "standardField": item.get("standardField"),
                    "mappingSource": "manual_override",
                    "confidence": 1.0,
                    "sampleValues": [],
                    "isManual": True,
                    "reasons": ["manual_override_applied"],
                }
                for item in manual_overrides
            ]

        warnings: List[str] = []
        if session.get("duplicateCount"):
            warnings.append(f"发现并移除 {session['duplicateCount']} 条重复记录")
        if result.get("finalStatus") == "risk":
            warnings.append("当前样本处于 risk 状态，请结合语义门禁原因复核")

        imported_rows = int(len(valid_df))
        quarantine_count = int(len(row_errors))
        fact_load_errors = 0
        importability_reasons: List[str] = []
        if imported_rows == 0 and quarantine_count > 0 and fact_load_errors == 0:
            importability_status = "risk"
            importability_reasons.append("all_rows_quarantined")
        elif imported_rows > 0 and quarantine_count > 0:
            importability_status = "risk"
            importability_reasons.append("partial_quarantine")
        elif imported_rows > 0 and fact_load_errors == 0:
            importability_status = "passed"
        else:
            importability_status = "failed"

        response = {
            "sessionId": session_id,
            "batchId": session_id,
            "importedRows": imported_rows,
            "errorRows": quarantine_count,
            "status": "success",
            "warnings": warnings,
            "errors": [str(item.get("error")) for item in row_errors[:50]],
            "rowErrorSummary": {
                "auto_fixed": 0,
                "ignorable": 0,
                "quarantined": quarantine_count,
                "fatal": 0,
            },
            "quarantineCount": quarantine_count,
            "stagingRows": imported_rows,
            "factLoadErrors": fact_load_errors,
            "transportStatus": result.get("transportStatus"),
            "semanticStatus": result.get("semanticStatus"),
            "finalStatus": result.get("finalStatus"),
            "importabilityStatus": importability_status,
            "importabilityReasons": importability_reasons,
            "semanticGateReasons": list(result.get("semanticGateReasons") or []),
            "riskOverrideReasons": list(result.get("riskOverrideReasons") or []),
            "semanticAcceptanceReason": list(result.get("semanticAcceptanceReason") or []),
            "recoverySummary": {
                "headerRecoveryApplied": result.get("headerRecoveryApplied"),
                "preRecoveryStatus": result.get("preRecoveryStatus"),
                "postRecoveryStatus": result.get("postRecoveryStatus"),
                "recoveryAttempted": result.get("recoveryAttempted"),
                "recoveryImproved": result.get("recoveryImproved"),
                "semanticGateReasons": list(result.get("semanticGateReasons") or []),
                "riskOverrideReasons": list(result.get("riskOverrideReasons") or []),
                "recoveryDiff": copy.deepcopy(result.get("recoveryDiff") or {}),
            },
            "runtimeAudit": {
                "sessionId": session_id,
                "operator": operator,
                "shopId": shop_id,
                "confirmedAt": datetime.now().isoformat(),
                "sourceFile": session.get("fileName"),
                "finalStatus": result.get("finalStatus"),
                "transportStatus": result.get("transportStatus"),
                "semanticStatus": result.get("semanticStatus"),
                "importabilityStatus": importability_status,
                "importabilityReasons": importability_reasons,
                "quarantineCount": quarantine_count,
                "factLoadErrors": fact_load_errors,
                "recoverySummary": {
                    "headerRecoveryApplied": result.get("headerRecoveryApplied"),
                    "preRecoveryStatus": result.get("preRecoveryStatus"),
                    "postRecoveryStatus": result.get("postRecoveryStatus"),
                    "recoveryAttempted": result.get("recoveryAttempted"),
                    "recoveryImproved": result.get("recoveryImproved"),
                },
            },
        }
        return response
"""

def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_SERVICE}")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")
    backup = IMPORT_SERVICE.with_suffix(".py.bak_importability_phase_a_manual_exact")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    if NEW_CONFIRM_BLOCK in text:
        print("confirm_import already contains importability fields; no change needed")
        return

    count = text.count(OLD_CONFIRM_BLOCK)
    if count != 1:
        raise RuntimeError(f"expected exact confirm_import block once, got {count}")

    text = text.replace(OLD_CONFIRM_BLOCK, NEW_CONFIRM_BLOCK, 1)
    IMPORT_SERVICE.write_text(text, encoding="utf-8")

    print("Applied exact confirm_import importability patch")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
