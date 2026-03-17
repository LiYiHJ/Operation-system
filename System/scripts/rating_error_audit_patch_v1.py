
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
TARGET = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


OLD_VALIDATE = """    def validate_data(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        errors: List[Dict[str, Any]] = []
        valid_rows: List[Dict[str, Any]] = []
        for idx, row in df.iterrows():
            row_dict = {k: self._safe_scalar(v) for k, v in row.to_dict().items()}
            is_valid, row_errors = self.validator.validate_row(row_dict, idx + 1)
            if is_valid:
                valid_rows.append(row_dict)
            else:
                for err in row_errors:
                    errors.append({"row": idx + 1, "error": err})
        valid_df = (
            pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)
        )
        return valid_df, errors
"""

NEW_VALIDATE = """    def validate_data(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        errors: List[Dict[str, Any]] = []
        valid_rows: List[Dict[str, Any]] = []
        for idx, row in df.iterrows():
            row_dict = {k: self._safe_scalar(v) for k, v in row.to_dict().items()}
            is_valid, row_errors = self.validator.validate_row(row_dict, idx + 1)
            if is_valid:
                valid_rows.append(row_dict)
            else:
                for err in row_errors:
                    detail: Dict[str, Any] = {"row": idx + 1, "error": err}
                    if "评分必须在0-5之间" in err:
                        detail["field"] = "rating_value"
                        detail["rawValue"] = row_dict.get("rating_value")
                    elif "SKU不能为空" in err:
                        detail["field"] = "sku"
                        detail["rawValue"] = row_dict.get("sku")
                    errors.append(detail)
        valid_df = (
            pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)
        )
        return valid_df, errors
"""

INJECT_BEFORE_RESPONSE_OLD = """        response = {
"""
INJECT_BEFORE_RESPONSE_NEW = """        rating_issue_samples = [
            {
                "row": item.get("row"),
                "rawValue": item.get("rawValue"),
                "error": item.get("error"),
            }
            for item in row_errors
            if str(item.get("field") or "") == "rating_value"
        ][:10]

        response = {
"""

ERRORS_BLOCK_OLD = """            "errors": [str(item.get("error")) for item in row_errors[:50]],
            "rowErrorSummary": {
"""
ERRORS_BLOCK_NEW = """            "errors": [str(item.get("error")) for item in row_errors[:50]],
            "ratingIssueSamples": rating_issue_samples,
            "rowErrorSummary": {
"""

RUNTIME_BLOCK_OLD = """                "quarantineCount": quarantine_count,
                "factLoadErrors": fact_load_errors,
                "recoverySummary": {
"""
RUNTIME_BLOCK_NEW = """                "quarantineCount": quarantine_count,
                "factLoadErrors": fact_load_errors,
                "ratingIssueCount": len(rating_issue_samples),
                "recoverySummary": {
"""


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"missing file: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    backup = TARGET.with_suffix(".py.bak_rating_error_audit_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_once(text, OLD_VALIDATE, NEW_VALIDATE, "replace validate_data")
    text = replace_once(text, INJECT_BEFORE_RESPONSE_OLD, INJECT_BEFORE_RESPONSE_NEW, "inject rating_issue_samples")
    text = replace_once(text, ERRORS_BLOCK_OLD, ERRORS_BLOCK_NEW, "add ratingIssueSamples to response")
    text = replace_once(text, RUNTIME_BLOCK_OLD, RUNTIME_BLOCK_NEW, "add ratingIssueCount to runtimeAudit")

    TARGET.write_text(text, encoding="utf-8")
    print("Applied rating error audit patch v1")
    print(f"Patched: {TARGET}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
