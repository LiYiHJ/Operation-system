from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
TARGET = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"

OLD_BLOCK = '''        rating_issue_samples = [
            {
                "row": item.get("row"),
                "rawValue": item.get("rawValue"),
                "error": item.get("error"),
            }
            for item in row_errors
            if str(item.get("field") or "") == "rating_value"
        ][:10]

        response = {
'''

NEW_BLOCK = '''        rating_source_column = None
        for mapping in session.get("stagingFieldMappings") or []:
            if str(mapping.get("standardField") or "") == "rating_value":
                rating_source_column = str(mapping.get("originalField") or "") or None
                break

        staging_df_for_audit = session.get("stagingDf")
        rating_issue_samples = []
        for item in row_errors:
            if str(item.get("field") or "") != "rating_value":
                continue

            row_no = item.get("row")
            rating_source_raw_value = None
            if (
                isinstance(row_no, int)
                and row_no >= 1
                and rating_source_column
                and hasattr(staging_df_for_audit, "columns")
                and rating_source_column in staging_df_for_audit.columns
                and row_no - 1 < len(staging_df_for_audit)
            ):
                raw = staging_df_for_audit.iloc[row_no - 1][rating_source_column]
                if raw is not None and str(raw).strip().lower() != "nan":
                    rating_source_raw_value = self._safe_scalar(raw)

            rating_issue_samples.append(
                {
                    "row": row_no,
                    "ratingValue": item.get("rawValue"),
                    "ratingSourceColumn": rating_source_column,
                    "ratingSourceRawValue": rating_source_raw_value,
                    "error": item.get("error"),
                }
            )

            if len(rating_issue_samples) >= 10:
                break

        response = {
'''

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"missing file: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    backup = TARGET.with_suffix(".py.bak_rating_source_audit_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_once(text, OLD_BLOCK, NEW_BLOCK, "replace rating issue audit block")
    TARGET.write_text(text, encoding="utf-8")

    print("Applied rating source audit patch v1")
    print(f"Patched: {TARGET}")
    print(f"Backup:  {backup}")

if __name__ == "__main__":
    main()
