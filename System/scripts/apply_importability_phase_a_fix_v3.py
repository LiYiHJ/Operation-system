
from __future__ import annotations

import textwrap
from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_SERVICE}")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")
    backup = IMPORT_SERVICE.with_suffix(".py.bak_importability_phase_a_fix_v3")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    # 1) session_not_found response
    old_not_found = textwrap.dedent("""\
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
""")
    new_not_found = textwrap.dedent("""\
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
""")
    text = replace_once(text, old_not_found, new_not_found, "session_not_found response")

    # 2) inject importability calculation before response dict
    anchor = textwrap.dedent("""\
        if result.get("finalStatus") == "risk":
            warnings.append("当前样本处于 risk 状态，请结合语义门禁原因复核")

        response = {
""")
    inject = textwrap.dedent("""\
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
""")
    text = replace_once(text, anchor, inject, "inject importability calculation")

    # 3) replace hard-coded counters
    text = replace_once(text, '"importedRows": int(len(valid_df)),', '"importedRows": imported_rows,', "importedRows")
    text = replace_once(text, '"errorRows": int(len(row_errors)),', '"errorRows": quarantine_count,', "errorRows")
    text = replace_once(text, '"quarantineCount": int(len(row_errors)),', '"quarantineCount": quarantine_count,', "quarantineCount")
    text = replace_once(text, '"stagingRows": int(len(valid_df)),', '"stagingRows": imported_rows,', "stagingRows")
    text = replace_once(text, '"factLoadErrors": 0,', '"factLoadErrors": fact_load_errors,', "factLoadErrors")

    # 4) add importability fields to main response
    old_status_block = textwrap.dedent("""\
            "transportStatus": result.get("transportStatus"),
            "semanticStatus": result.get("semanticStatus"),
            "finalStatus": result.get("finalStatus"),
            "semanticGateReasons": list(result.get("semanticGateReasons") or []),
""")
    new_status_block = textwrap.dedent("""\
            "transportStatus": result.get("transportStatus"),
            "semanticStatus": result.get("semanticStatus"),
            "finalStatus": result.get("finalStatus"),
            "importabilityStatus": importability_status,
            "importabilityReasons": importability_reasons,
            "semanticGateReasons": list(result.get("semanticGateReasons") or []),
""")
    text = replace_once(text, old_status_block, new_status_block, "main response statuses")

    # 5) add importability to runtimeAudit
    old_runtime = textwrap.dedent("""\
                "sourceFile": session.get("fileName"),
                "finalStatus": result.get("finalStatus"),
                "transportStatus": result.get("transportStatus"),
                "semanticStatus": result.get("semanticStatus"),
                "quarantineCount": int(len(row_errors)),
                "factLoadErrors": 0,
""")
    new_runtime = textwrap.dedent("""\
                "sourceFile": session.get("fileName"),
                "finalStatus": result.get("finalStatus"),
                "transportStatus": result.get("transportStatus"),
                "semanticStatus": result.get("semanticStatus"),
                "importabilityStatus": importability_status,
                "importabilityReasons": importability_reasons,
                "quarantineCount": quarantine_count,
                "factLoadErrors": fact_load_errors,
""")
    text = replace_once(text, old_runtime, new_runtime, "runtimeAudit importability")

    IMPORT_SERVICE.write_text(text, encoding="utf-8")
    print("Applied importability Phase A fix v3")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
