from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
TARGET = REPO_ROOT / "scripts" / "run_import_regression_v2.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"missing file: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    backup = TARGET.with_suffix(".py.bak_entity_key_capture")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    old = '''            "recoveryCandidatePreview": upload.get("recoveryCandidatePreview"),
            "entityKeyAudit": upload.get("entityKeyAudit"),
        }
'''
    new = '''            "recoveryCandidatePreview": upload.get("recoveryCandidatePreview"),
            "entityKeySuggestion": upload.get("entityKeySuggestion"),
            "entityKeyAudit": upload.get("entityKeyAudit"),
        }
'''
    text = replace_once(text, old, new, "capture entityKeySuggestion in upload block")
    TARGET.write_text(text, encoding="utf-8")

    print("Applied regression capture patch")
    print(f"Patched: {TARGET}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
