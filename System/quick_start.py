#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V5.1 快速启动脚本
自动诊断并运行示例
"""

import sys
import json
from pathlib import Path

print("=" * 80)
print("V5.1 跨境电商智能运营系统 - 快速启动".center(80))
print("=" * 80)

# 1. 运行系统诊断
print("\n📊 正在运行系统诊断...\n")
try:
    from ecom_v51.system_diagnostics import main as run_diagnostics
    run_diagnostics()
except Exception as e:
    print(f"❌ 诊断失败: {e}")
    sys.exit(1)

# 2. 生成示例报告
print("\n" + "=" * 80)
print("生成示例作战室报告".center(80))
print("=" * 80)

try:
    from ecom_v51.war_room import WarRoomService
    from ecom_v51.models import SkuSnapshot
    from dataclasses import asdict
    
    # 示例 SKU 数据
    sample_data = SkuSnapshot(
        sku="EXAMPLE-001",
        impressions=10000,
        card_visits=100,
        add_to_cart=5,
        orders=1,
        ad_spend=300,
        ad_revenue=200,
        stock_total=20,
        days_of_supply=5,
        rating=3.7,
        return_rate=0.2,
        cancel_rate=0.05,
        sale_price=100,
        list_price=120,
        variable_rate_total=0.35,
        fixed_cost_total=80,
    )
    
    # 生成报告
    service = WarRoomService()
    report = service.build_report(sample_data)
    
    # 保存报告
    output_file = Path("example_war_room_report.json")
    output_file.write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    print(f"\n✅ 示例报告已生成: {output_file}")
    print(f"\n📋 报告摘要:")
    print(f"  - SKU: {report.sku}")
    print(f"  - 净利润: {report.net_profit:.2f} 元")
    print(f"  - 净利率: {report.net_margin:.2%}")
    print(f"  - 保本价: {report.break_even_price:.2f} 元")
    print(f"  - CTR: {report.funnel['ctr']:.2%}")
    print(f"  - 策略任务: {len(report.strategy_tasks)} 个")
    
except Exception as e:
    print(f"❌ 报告生成失败: {e}")
    import traceback
    traceback.print_exc()

# 3. CLI 使用说明
print("\n" + "=" * 80)
print("CLI 使用说明".center(80))
print("=" * 80)
print("""
📖 命令行使用方法:

1. 生成 JSON 输入文件:
   {
     "sku": "SKU-001",
     "impressions": 10000,
     "card_visits": 100,
     "add_to_cart": 5,
     "orders": 1,
     "ad_spend": 300,
     "ad_revenue": 200,
     "stock_total": 20,
     "days_of_supply": 5,
     "rating": 3.7,
     "return_rate": 0.2,
     "cancel_rate": 0.05,
     "sale_price": 100,
     "list_price": 120,
     "variable_rate_total": 0.35,
     "fixed_cost_total": 80
   }

2. 运行 CLI:
   ./v51-ops --input input.json --pretty

3. 输出内容包括:
   ✅ 漏斗指标 (CTR, 加购率, 下单率)
   ✅ 利润分析 (净利润, 净利率, 保本价)
   ✅ 折扣模拟 (95折/9折/85折利润)
   ✅ 策略任务 (P0-P3 优先级建议)
""")

print("\n" + "=" * 80)
print("系统启动完成！".center(80))
print("=" * 80)
