from __future__ import annotations

import json
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from urllib import request, error

REPO_ROOT = Path(r"C:\Operation-system\System")
BASE_URL = "http://127.0.0.1:5000/api/import/upload"
SHOP_ID = "1"
OPERATOR = "transport_probe"
OUT_DIR = REPO_ROOT / "docs"

SAMPLES = [
    ("ru_real_xlsx", REPO_ROOT / "data" / "analytics_report_2026-03-12_23_49.xlsx"),
    ("cn_real_xlsx", REPO_ROOT / "data" / "销售数据分析.xlsx"),
    ("ru_bad_header_xlsx", REPO_ROOT / "sample_data" / "ozon_bad_header_or_missing_sku.xlsx"),
]


def encode_multipart(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    def add_line(line: str) -> None:
        chunks.append(line.encode("utf-8"))
        chunks.append(b"\r\n")

    for name, value in fields.items():
        add_line(f"--{boundary}")
        add_line(f'Content-Disposition: form-data; name="{name}"')
        add_line("")
        add_line(str(value))

    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    add_line(f"--{boundary}")
    add_line(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"'
    )
    add_line(f"Content-Type: {mime_type}")
    add_line("")
    chunks.append(file_path.read_bytes())
    chunks.append(b"\r\n")
    add_line(f"--{boundary}--")
    body = b"".join(chunks)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def post_upload(sample_path: Path) -> dict:
    fields = {"shop_id": SHOP_ID, "operator": OPERATOR}
    body, content_type = encode_multipart(fields, "file", sample_path)
    req = request.Request(
        BASE_URL,
        data=body,
        method="POST",
        headers={"Content-Type": content_type, "Content-Length": str(len(body))},
    )

    try:
        with request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            status_code = resp.getcode()
            headers = dict(resp.headers.items())
    except error.HTTPError as exc:
        raw = exc.read()
        status_code = exc.code
        headers = dict(exc.headers.items())
    except Exception as exc:  # noqa: BLE001
        return {
            "requestError": f"{type(exc).__name__}: {exc}",
            "httpStatus": None,
            "contentType": None,
            "rawBody": None,
            "json": None,
        }

    body_text = raw.decode("utf-8", errors="replace")
    parsed = None
    json_error = None
    try:
        parsed = json.loads(body_text)
    except Exception as exc:  # noqa: BLE001
        json_error = f"{type(exc).__name__}: {exc}"

    return {
        "httpStatus": status_code,
        "contentType": headers.get("Content-Type"),
        "rawBody": body_text,
        "json": parsed,
        "jsonError": json_error,
    }



def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUT_DIR / f"p0_upload_transport_probe_{timestamp}.json"

    rows: list[dict] = []
    for name, sample_path in SAMPLES:
        item = {"sample": name, "path": str(sample_path)}
        if not sample_path.exists():
            item["result"] = {"missingFile": True}
        else:
            print(f"Probing upload for {name}: {sample_path}")
            item["result"] = post_upload(sample_path)
        rows.append(item)

    out_file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved transport probe: {out_file}")


if __name__ == "__main__":
    main()
