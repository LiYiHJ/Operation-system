
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
TARGET = REPO_ROOT / "src" / "ecom_v51" / "api" / "routes" / "import_route.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


IMPORTS_OLD = """from flask import Blueprint, jsonify, request, send_file
import ast
import json
"""
IMPORTS_NEW = """from flask import Blueprint, jsonify, request, send_file
import ast
import json
import math
"""

HELPER_OLD = """def _ensure_json_object(value, *, label: str):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            try:
                value = ast.literal_eval(value)
            except Exception:
                return None, (jsonify({'error': f'{label} is string and cannot be parsed'}), 500)

    if not isinstance(value, dict):
        return None, (jsonify({'error': f'{label} must be dict, got {type(value).__name__}'}), 500)

    return value, None
"""

HELPER_NEW = """def _sanitize_for_json(value):
    try:
        import numpy as np  # type: ignore
    except Exception:
        np = None

    if np is not None:
        if isinstance(value, np.generic):
            value = value.item()
        elif isinstance(value, np.ndarray):
            value = value.tolist()

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_sanitize_for_json(v) for v in value]

    if hasattr(value, "isoformat") and not isinstance(value, (str, bytes)):
        try:
            return value.isoformat()
        except Exception:
            pass

    return value


def _ensure_json_object(value, *, label: str):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            try:
                value = ast.literal_eval(value)
            except Exception:
                return None, (jsonify({'error': f'{label} is string and cannot be parsed'}), 500)

    value = _sanitize_for_json(value)

    if not isinstance(value, dict):
        return None, (jsonify({'error': f'{label} must be dict, got {type(value).__name__}'}), 500)

    return value, None
"""


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"missing file: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    backup = TARGET.with_suffix(".py.bak_nan_json_fix_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_once(text, IMPORTS_OLD, IMPORTS_NEW, "add math import")
    text = replace_once(text, HELPER_OLD, HELPER_NEW, "replace helper with sanitize")

    TARGET.write_text(text, encoding="utf-8")
    print("Applied import_route NaN JSON fix v1")
    print(f"Patched: {TARGET}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
