
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_ROUTE = REPO_ROOT / "src" / "ecom_v51" / "api" / "routes" / "import_route.py"
REMINDER_ROUTE = REPO_ROOT / "src" / "ecom_v51" / "api" / "routes" / "reminder.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def patch_import_route() -> None:
    text = IMPORT_ROUTE.read_text(encoding="utf-8")
    backup = IMPORT_ROUTE.with_suffix(".py.bak_root_fix_v2")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    if "import math" not in text:
        text = replace_once(
            text,
            "import ast\nimport json\n",
            "import ast\nimport json\nimport math\n",
            "add math import",
        )

    old_helper = """def _ensure_json_object(value, *, label: str):
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
    new_helper = """def _sanitize_for_json(value):
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
    if old_helper in text:
        text = replace_once(text, old_helper, new_helper, "replace ensure helper")

    IMPORT_ROUTE.write_text(text, encoding="utf-8")


def patch_reminder_route() -> None:
    text = REMINDER_ROUTE.read_text(encoding="utf-8")
    backup = REMINDER_ROUTE.with_suffix(".py.bak_root_fix_v2")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    if "from datetime import datetime, timezone" not in text:
        text = replace_once(
            text,
            "from datetime import datetime\n",
            "from datetime import datetime, timezone\n",
            "add timezone import",
        )

    if "def _to_utc_naive(" not in text:
        anchor = "reminder_bp = Blueprint('reminder', __name__, url_prefix='/api/reminders')\n\n\n"
        helper = """reminder_bp = Blueprint('reminder', __name__, url_prefix='/api/reminders')\n\n\ndef _to_utc_naive(dt: datetime | None) -> datetime | None:\n    if dt is None:\n        return None\n    if dt.tzinfo is None:\n        return dt\n    return dt.astimezone(timezone.utc).replace(tzinfo=None)\n\n\n"""
        text = replace_once(text, anchor, helper, "insert reminder datetime helper")

    old_line = "    unread_count = len([x for x in items if not read_at or (x.get('time') and datetime.fromisoformat(x['time']) > read_at)])\n"
    new_block = """    read_at_cmp = _to_utc_naive(read_at)\n    unread_count = len(\n        [\n            x\n            for x in items\n            if not read_at_cmp\n            or (\n                x.get('time')\n                and _to_utc_naive(datetime.fromisoformat(x['time']))\n                and _to_utc_naive(datetime.fromisoformat(x['time'])) > read_at_cmp\n            )\n        ]\n    )\n"""
    if old_line in text:
        text = replace_once(text, old_line, new_block, "replace unread_count compare")

    REMINDER_ROUTE.write_text(text, encoding="utf-8")


def main() -> None:
    if not IMPORT_ROUTE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_ROUTE}")
    if not REMINDER_ROUTE.exists():
        raise FileNotFoundError(f"missing file: {REMINDER_ROUTE}")

    patch_import_route()
    patch_reminder_route()

    print("Applied root fix patch v2")
    print(f"Patched: {IMPORT_ROUTE}")
    print(f"Patched: {REMINDER_ROUTE}")


if __name__ == "__main__":
    main()
