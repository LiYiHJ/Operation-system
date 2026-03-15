from __future__ import annotations

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

    backup = IMPORT_SERVICE.with_suffix(".py.bak_restore_baseline_init_fix")
    if not backup.exists():
        backup.write_text(IMPORT_SERVICE.read_text(encoding="utf-8"), encoding="utf-8")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")

    old = """    def __init__(self) -> None:\n        self._root_dir = Path(__file__).resolve().parents[3]\n        self._registry_cfg = self._load_json(self._root_dir / \"config\" / \"import_field_registry.json\", default={\"version\": \"v1\", \"fields\": []})\n        self._field_registry = self._registry_cfg.get(\"fields\") or []\n        self._alias_lookup = self._build_alias_lookup(self._field_registry)\n        self._fallback_mapping = FieldMapping()\n        self.diagnoser = _ImportDiagnoser() if _ImportDiagnoser is not None else _FallbackDiagnoser()\n"""
    new = """    def __init__(self) -> None:\n        self._root_dir = Path(__file__).resolve().parents[3]\n        self._registry_cfg = self._load_json(self._root_dir / \"config\" / \"import_field_registry.json\", default={\"version\": \"v1\", \"fields\": []})\n        self._field_registry = self._registry_cfg.get(\"fields\") or []\n        self._fallback_mapping = FieldMapping()\n        self._alias_lookup = self._build_alias_lookup(self._field_registry)\n        self.diagnoser = _ImportDiagnoser() if _ImportDiagnoser is not None else _FallbackDiagnoser()\n"""
    text = replace_once(text, old, new, "reorder fallback mapping init")

    IMPORT_SERVICE.write_text(text, encoding="utf-8")
    print("Applied restore-baseline init fix")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Backup:  {backup}")

if __name__ == "__main__":
    main()
