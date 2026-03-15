
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests

REPO_ROOT = Path(r"C:\Operation-system\System")
BASE_URL = "http://127.0.0.1:5000"
SHOP_ID = 1
OPERATOR = "upload_transport_probe"
OUT_DIR = REPO_ROOT / "docs"

SAMPLES = [
    ("ru_real_xlsx", REPO_ROOT / "data" / "analytics_report_2026-03-12_23_49.xlsx"),
    ("cn_real_xlsx", REPO_ROOT / "data" / "销售数据分析.xlsx"),
    ("ru_bad_header_xlsx", REPO_ROOT / "sample_data" / "ozon_bad_header_or_missing_sku.xlsx"),
]

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"p0_upload_transport_probe_{ts}.json"
    rows = []

    for name, path in SAMPLES:
        item = {"sample": name, "path": str(path), "exists": path.exists()}
        if not path.exists():
            item["error"] = "file_missing"
            rows.append(item)
            continue

        with path.open("rb") as fh:
            files = {
                "file": (path.name, fh, "application/octet-stream"),
            }
            data = {
                "shop_id": str(SHOP_ID),
                "operator": OPERATOR,
            }
            try:
                resp = requests.post(f"{BASE_URL}/api/import/upload", files=files, data=data, timeout=180)
                item["status_code"] = resp.status_code
                item["content_type"] = resp.headers.get("content-type")
                item["body_text"] = resp.text[:10000]
                try:
                    item["body_json"] = resp.json()
                except Exception as exc:
                    item["body_json_error"] = f"{type(exc).__name__}: {exc}"
            except Exception as exc:
                item["request_error"] = f"{type(exc).__name__}: {exc}"
        rows.append(item)
        print(f"{name}: status={item.get('status_code')} request_error={item.get('request_error')}")

    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {out_path}")

if __name__ == "__main__":
    main()
