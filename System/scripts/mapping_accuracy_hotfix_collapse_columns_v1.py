from pathlib import Path
import re
import sys

TARGET = Path("src/ecom_v51/services/import_service.py")

def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"未找到文件: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")

    pattern = re.compile(
        r"(?P<indent>^[ \t]*)(?P<decorator>@staticmethod\s*\n)?(?P=indent)def _collapse_duplicate_columns\((?P<params>[^)]*)\)\s*->\s*pd\.DataFrame:",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        raise RuntimeError("未找到 _collapse_duplicate_columns 定义")

    indent = match.group("indent")
    params = match.group("params").strip()

    replacement = (
        f"{indent}@staticmethod\n"
        f"{indent}def _collapse_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:"
    )

    text = text[: match.start()] + replacement + text[match.end() :]

    TARGET.write_text(text, encoding="utf-8")
    print("已修复 _collapse_duplicate_columns 为 @staticmethod 形式")

if __name__ == "__main__":
    main()
