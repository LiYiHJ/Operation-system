from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"


def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_SERVICE}")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")
    backup = IMPORT_SERVICE.with_suffix(".py.bak_entity_key_df_scope_fix")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    old = "            df=df,\n"
    new = '            df=active_bundle["df"],\n'

    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[replace df scope] expected 1 match, got {count}")

    text = text.replace(old, new, 1)
    IMPORT_SERVICE.write_text(text, encoding="utf-8")

    print("Applied entity key df-scope fix")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
