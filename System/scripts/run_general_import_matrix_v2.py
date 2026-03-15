from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
BASE_URL = "http://127.0.0.1:5000"
SHOP_ID = 1
OPERATOR = "general_import_matrix_v2"
OUT_DIR = REPO_ROOT / "docs"

SAMPLES = [
    ("ru_real_xlsx", REPO_ROOT / "data" / "analytics_report_2026-03-12_23_49.xlsx"),
    ("cn_real_xlsx", REPO_ROOT / "data" / "销售数据分析.xlsx"),
    ("ru_bad_header_xlsx", REPO_ROOT / "sample_data" / "ozon_bad_header_or_missing_sku.xlsx"),
]


def run_cmd(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stdout, proc.stderr


def post_upload(sample_path: Path) -> dict:
    code, out, err = run_cmd([
        "curl.exe", "-sS", "-i", "-X", "POST",
        "-F", f"file=@{sample_path}",
        "-F", f"shop_id={SHOP_ID}",
        "-F", f"operator={OPERATOR}",
        f"{BASE_URL}/api/import/upload",
    ])
    return parse_http_result(code, out, err)


def post_confirm(session_id: int) -> dict:
    payload = json.dumps({"sessionId": session_id, "shopId": SHOP_ID, "manualOverrides": []}, ensure_ascii=False)
    code, out, err = run_cmd([
        "curl.exe", "-sS", "-i", "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", payload,
        f"{BASE_URL}/api/import/confirm",
    ])
    return parse_http_result(code, out, err)


def parse_http_result(code: int, out: str, err: str) -> dict:
    out = out or ""
    raw = out.strip()
    if not raw:
        return {
            "processReturnCode": code,
            "stderr": err.strip(),
            "httpStatusLine": None,
            "headers": [],
            "rawBody": "",
            "json": None,
            "jsonError": "empty_response",
        }

    parts = raw.split("\r\n\r\n", 1)
    if len(parts) == 1:
        parts = raw.split("\n\n", 1)

    head = parts[0]
    body = parts[1] if len(parts) > 1 else ""
    lines = head.splitlines()
    status_line = lines[0] if lines else None
    headers = lines[1:] if len(lines) > 1 else []

    parsed = None
    json_error = None
    if body:
        try:
            parsed = json.loads(body)
        except Exception as exc:
            json_error = f"{type(exc).__name__}: {exc}"
    else:
        json_error = "empty_body"

    return {
        "processReturnCode": code,
        "stderr": err.strip(),
        "httpStatusLine": status_line,
        "headers": headers,
        "rawBody": body,
        "json": parsed,
        "jsonError": json_error,
    }


def summarize_upload(upload_json: dict | None) -> dict | None:
    if not upload_json:
        return None
    return {
        "sessionId": upload_json.get("sessionId"),
        "transportStatus": upload_json.get("transportStatus"),
        "semanticStatus": upload_json.get("semanticStatus"),
        "finalStatus": upload_json.get("finalStatus"),
        "semanticGateReasons": upload_json.get("semanticGateReasons"),
        "riskOverrideReasons": upload_json.get("riskOverrideReasons"),
        "semanticAcceptanceReason": upload_json.get("semanticAcceptanceReason"),
        "mappedCount": upload_json.get("mappedCount"),
        "unmappedCount": upload_json.get("unmappedCount"),
        "mappingCoverage": (upload_json.get("semanticMetrics") or {}).get("mappingCoverage"),
        "headerStructureScore": upload_json.get("headerStructureScore"),
        "headerStructureRiskSignals": upload_json.get("headerStructureRiskSignals"),
        "preRecoveryStatus": upload_json.get("preRecoveryStatus"),
        "postRecoveryStatus": upload_json.get("postRecoveryStatus"),
        "recoveryAttempted": upload_json.get("recoveryAttempted"),
        "headerRecoveryApplied": upload_json.get("headerRecoveryApplied"),
        "recoveryImproved": upload_json.get("recoveryImproved"),
        "recoveryDiff": upload_json.get("recoveryDiff"),
        "mappedCanonicalFields": upload_json.get("mappedCanonicalFields"),
        "topUnmappedHeaders": upload_json.get("topUnmappedHeaders"),
        "entityKeyAudit": upload_json.get("entityKeyAudit"),
        "dynamicMetricColumns": (upload_json.get("stats") or {}).get("dynamicMetricColumns"),
        "recoveryCandidatePreview": upload_json.get("recoveryCandidatePreview"),
    }


def summarize_confirm(confirm_json: dict | None) -> dict | None:
    if not confirm_json:
        return None
    return {
        "importedRows": confirm_json.get("importedRows"),
        "errorRows": confirm_json.get("errorRows"),
        "quarantineCount": confirm_json.get("quarantineCount"),
        "factLoadErrors": confirm_json.get("factLoadErrors"),
        "transportStatus": confirm_json.get("transportStatus"),
        "semanticStatus": confirm_json.get("semanticStatus"),
        "finalStatus": confirm_json.get("finalStatus"),
        "semanticGateReasons": confirm_json.get("semanticGateReasons"),
        "riskOverrideReasons": confirm_json.get("riskOverrideReasons"),
        "recoverySummary": confirm_json.get("recoverySummary"),
        "entityKeyAudit": confirm_json.get("entityKeyAudit"),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUT_DIR / f"p0_general_import_matrix_v2_{timestamp}.json"

    rows: list[dict] = []
    for sample_name, sample_path in SAMPLES:
        row: dict = {"sample": sample_name, "path": str(sample_path)}
        if not sample_path.exists():
            row["uploadProbe"] = {"error": "missing_file"}
            row["uploadSummary"] = None
            row["confirmProbe"] = None
            row["confirmSummary"] = None
            rows.append(row)
            continue

        print(f"Uploading {sample_name} -> {sample_path}")
        upload_probe = post_upload(sample_path)
        upload_json = upload_probe.get("json") if isinstance(upload_probe.get("json"), dict) else None
        row["uploadProbe"] = upload_probe
        row["uploadSummary"] = summarize_upload(upload_json)

        confirm_probe = None
        confirm_summary = None
        session_id = upload_json.get("sessionId") if upload_json else None
        if session_id:
            confirm_probe = post_confirm(int(session_id))
            confirm_json = confirm_probe.get("json") if isinstance(confirm_probe.get("json"), dict) else None
            confirm_summary = summarize_confirm(confirm_json)

        row["confirmProbe"] = confirm_probe
        row["confirmSummary"] = confirm_summary
        rows.append(row)

    out_file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved matrix report: {out_file}")


if __name__ == "__main__":
    main()
