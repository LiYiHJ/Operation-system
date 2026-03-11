from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import AnalysisEngine
from .models import ProductProfile, ProductScores


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="高 CRT 产品分析系统")
    parser.add_argument("--input", required=True, help="输入 JSON 文件路径")
    parser.add_argument("--pretty", action="store_true", help="格式化输出")
    return parser


def load_profile(path: str) -> ProductProfile:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return ProductProfile(
        name=payload["name"],
        category=payload.get("category", "未分类"),
        target_users=payload.get("target_users", "未指定"),
        notes=payload.get("notes", []),
        scores=ProductScores(
            conversion=payload["scores"]["conversion"],
            retention=payload["scores"]["retention"],
            traction=payload["scores"]["traction"],
        ),
    )


def main() -> None:
    args = build_parser().parse_args()
    profile = load_profile(args.input)
    engine = AnalysisEngine()
    result = engine.analyze(profile)

    if args.pretty:
        print(json.dumps(engine.to_dict(result), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(engine.to_dict(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
