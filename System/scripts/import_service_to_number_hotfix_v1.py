
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
TARGET = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"

ALIAS_BLOCK = """
    def _to_number(self, value: Any) -> Optional[float]:
        return self._to_number_like(value)

"""


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"missing file: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    backup = TARGET.with_suffix(".py.bak_to_number_hotfix_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    if "def _to_number(self, value: Any)" in text:
        print("Hotfix already present")
        print(f"Target: {TARGET}")
        return

    # Preferred: insert right after _to_number_like(...)
    pattern = (
        r"(    def _to_number_like\(self, value: Any\) -> Optional\[float\]:"
        r"[\s\S]*?^            return None\n)"
    )
    new_text, count = re.subn(pattern, r"\1\n" + ALIAS_BLOCK, text, count=1, flags=re.M)
    if count != 1:
        # Fallback: insert before _sample_quality_score(...)
        marker = "    def _sample_quality_score(self, canonical: Optional[str], value: Any) -> float:\n"
        idx = text.find(marker)
        if idx == -1:
            raise RuntimeError("could not find insertion point for _to_number hotfix")
        new_text = text[:idx] + ALIAS_BLOCK + text[idx:]

    TARGET.write_text(new_text, encoding="utf-8")
    print("Applied _to_number hotfix v1")
    print(f"Patched: {TARGET}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
