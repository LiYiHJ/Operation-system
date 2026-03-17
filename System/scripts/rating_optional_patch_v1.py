
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
TARGET = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"


NEW_VALIDATE = """    def validate_data(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        errors: List[Dict[str, Any]] = []
        valid_rows: List[Dict[str, Any]] = []
        for idx, row in df.iterrows():
            row_dict = {k: self._safe_scalar(v) for k, v in row.to_dict().items()}
            is_valid, row_errors = self.validator.validate_row(row_dict, idx + 1)

            filtered_row_errors: List[str] = []
            for err in row_errors:
                if "评分必须在0-5之间" in err:
                    rating_value = row_dict.get("rating_value")
                    if rating_value is None or (
                        isinstance(rating_value, float) and pd.isna(rating_value)
                    ):
                        # rating_value 改为“可空但若存在必须合法”
                        continue
                filtered_row_errors.append(err)

            if not filtered_row_errors:
                valid_rows.append(row_dict)
            else:
                for err in filtered_row_errors:
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
INJECT_BEFORE_RESPONSE_NEW = """        missing_rating_count = 0
        if isinstance(valid_df, pd.DataFrame) and "rating_value" in valid_df.columns:
            missing_rating_count = int(valid_df["rating_value"].isna().sum())

        response = {
"""

RESPONSE_FACT_OLD = """            "factLoadErrors": fact_load_errors,
            "transportStatus": result.get("transportStatus"),
"""
RESPONSE_FACT_NEW = """            "factLoadErrors": fact_load_errors,
            "missingRatingCount": missing_rating_count,
            "transportStatus": result.get("transportStatus"),
"""

RUNTIME_FACT_OLD = """                "factLoadErrors": fact_load_errors,
                "ratingIssueCount": len(rating_issue_samples),
                "recoverySummary": {
"""
RUNTIME_FACT_NEW = """                "factLoadErrors": fact_load_errors,
                "missingRatingCount": missing_rating_count,
                "ratingIssueCount": len(rating_issue_samples),
                "recoverySummary": {
"""


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def replace_function(text: str, func_name: str, replacement: str, next_anchor: str) -> str:
    start = text.find(f"    def {func_name}(")
    if start == -1:
        raise RuntimeError(f"[{func_name}] start not found")
    end = text.find(next_anchor, start)
    if end == -1:
        raise RuntimeError(f"[{func_name}] end anchor not found")
    return text[:start] + replacement + "\n\n" + text[end:]


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"missing file: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    backup = TARGET.with_suffix(".py.bak_rating_optional_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_function(
        text,
        "validate_data",
        NEW_VALIDATE,
        "    def remove_duplicates(",
    )
    text = replace_once(text, INJECT_BEFORE_RESPONSE_OLD, INJECT_BEFORE_RESPONSE_NEW, "inject missing_rating_count")
    text = replace_once(text, RESPONSE_FACT_OLD, RESPONSE_FACT_NEW, "response missingRatingCount")
    text = replace_once(text, RUNTIME_FACT_OLD, RUNTIME_FACT_NEW, "runtimeAudit missingRatingCount")

    TARGET.write_text(text, encoding="utf-8")
    print("Applied rating optional patch v1")
    print(f"Patched: {TARGET}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
