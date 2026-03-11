from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .models import SkuSnapshot
from .war_room import WarRoomService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V5.1 跨境电商智能运营系统 - 单商品作战室CLI")
    parser.add_argument("--input", required=True, help="SKU快照JSON路径")
    parser.add_argument("--pretty", action="store_true", help="格式化输出")
    return parser


def load_snapshot(path: str) -> SkuSnapshot:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"input file not found: {path}")

    try:
        payload = json.loads(file_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON content in {path}: {exc}") from exc

    try:
        return SkuSnapshot(**payload)
    except TypeError as exc:
        raise ValueError(f"input fields mismatch for SkuSnapshot: {exc}") from exc


def main() -> None:
    args = build_parser().parse_args()

    try:
        snapshot = load_snapshot(args.input)
        report = WarRoomService().build_report(snapshot)
    except Exception as exc:  # noqa: BLE001
        print(f"[v51-ops] error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.pretty:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(asdict(report), ensure_ascii=False))


if __name__ == "__main__":
    main()
