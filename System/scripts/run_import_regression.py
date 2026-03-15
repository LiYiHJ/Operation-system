from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
BASE_URL = "http://127.0.0.1:5000"
OPERATOR = "import_gate_regression"
SHOP_ID = 1
OUT_DIR = REPO_ROOT / "docs"

SAMPLES = [
    ("ru_real_xlsx", REPO_ROOT / "data" / "analytics_report_2026-03-12_23_49.xlsx"),
    ("cn_real_xlsx", REPO_ROOT / "data" / "销售数据分析.xlsx"),
    ("ru_bad_header_xlsx", REPO_ROOT / "sample_data" / "ozon_bad_header_or_missing_sku.xlsx"),
]


def run_curl(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"curl failed: {' '.join(args)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc.stdout.strip()


def post_upload(sample_path: Path) -> dict:
    out = run_curl([
        "curl.exe", "-sS", "-X", "POST",
        "-F", f"file=@{sample_path}",
        "-F", f"shop_id={SHOP_ID}",
        "-F", f"operator={OPERATOR}",
        f"{BASE_URL}/api/import/upload",
    ])
    return json.loads(out)


def post_confirm(session_id: int) -> dict:
    payload = json.dumps({"sessionId": session_id, "shopId": SHOP_ID, "manualOverrides": []}, ensure_ascii=False)
    out = run_curl([
        "curl.exe", "-sS", "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", payload,
        f"{BASE_URL}/api/import/confirm",
    ])
    return json.loads(out)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUT_DIR / f"p0_import_gate_regression_{timestamp}.json"

    rows: list[dict] = []
    for sample_name, sample_path in SAMPLES:
        item: dict = {"sample": sample_name, "path": str(sample_path)}
        if not sample_path.exists():
            item["upload"] = {"status": "missing_file"}
            item["confirm"] = None
            rows.append(item)
            continue

        print(f"Uploading {sample_name} -> {sample_path}")
        upload = post_upload(sample_path)
        confirm = None
        if upload.get("sessionId"):
            confirm = post_confirm(int(upload["sessionId"]))

        item["upload"] = {
            "sessionId": upload.get("sessionId"),
            "transportStatus": upload.get("transportStatus"),
            "semanticStatus": upload.get("semanticStatus"),
            "finalStatus": upload.get("finalStatus"),
            "semanticGateReasons": upload.get("semanticGateReasons"),
            "riskOverrideReasons": upload.get("riskOverrideReasons"),
            "semanticAcceptanceReason": upload.get("semanticAcceptanceReason"),
            "mappedCount": upload.get("mappedCount"),
            "unmappedCount": upload.get("unmappedCount"),
            "mappingCoverage": (upload.get("semanticMetrics") or {}).get("mappingCoverage"),
            "headerStructureScore": upload.get("headerStructureScore"),
            "headerStructureRiskSignals": upload.get("headerStructureRiskSignals"),
            "preRecoveryStatus": upload.get("preRecoveryStatus"),
            "postRecoveryStatus": upload.get("postRecoveryStatus"),
            "recoveryAttempted": upload.get("recoveryAttempted"),
            "headerRecoveryApplied": upload.get("headerRecoveryApplied"),
            "recoveryImproved": upload.get("recoveryImproved"),
            "recoveryDiff": upload.get("recoveryDiff"),
            "mappedCanonicalFields": upload.get("mappedCanonicalFields"),
            "topUnmappedHeaders": upload.get("topUnmappedHeaders"),
            "dynamicMetricColumns": (upload.get("stats") or {}).get("dynamicMetricColumns"),
            "recoveryCandidatePreview": upload.get("recoveryCandidatePreview"),
        }
        item["confirm"] = None if not confirm else {
            "importedRows": confirm.get("importedRows"),
            "errorRows": confirm.get("errorRows"),
            "quarantineCount": confirm.get("quarantineCount"),
            "factLoadErrors": confirm.get("factLoadErrors"),
            "transportStatus": confirm.get("transportStatus"),
            "semanticStatus": confirm.get("semanticStatus"),
            "finalStatus": confirm.get("finalStatus"),
            "semanticGateReasons": confirm.get("semanticGateReasons"),
            "riskOverrideReasons": confirm.get("riskOverrideReasons"),
            "recoverySummary": confirm.get("recoverySummary"),
        }
        rows.append(item)

    out_file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved regression report: {out_file}")


if __name__ == "__main__":
    main()
