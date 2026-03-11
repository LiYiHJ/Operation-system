#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V5.1 系统诊断工具
自动检测所有模块运行状态和健康度
"""

import sys
import json
from pathlib import Path
from dataclasses import asdict
from typing import Dict, List, Tuple

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(title: str):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")


def print_status(module: str, status: str, message: str = ""):
    """打印状态"""
    status_colors = {
        "✅": Colors.GREEN,
        "⚠️": Colors.YELLOW,
        "❌": Colors.RED,
    }
    color = status_colors.get(status, "")
    print(f"{color}{status} {module:30s}{Colors.END} {message}")


def check_imports() -> Tuple[int, int]:
    """检查模块导入"""
    print_header("📦 模块导入检查")
    
    modules = [
        ("ecom_v51.models", "数据模型"),
        ("ecom_v51.profit_solver", "利润求解器"),
        ("ecom_v51.strategy", "策略引擎"),
        ("ecom_v51.war_room", "作战室服务"),
        ("ecom_v51.ingestion", "导入诊断器"),
        ("ecom_v51.intelligent_field_mapper", "智能字段映射器"),
        ("ecom_v51.cli", "CLI 入口"),
    ]
    
    success = 0
    total = len(modules)
    
    for module_name, desc in modules:
        try:
            __import__(module_name)
            print_status(desc, "✅", f"成功导入 {module_name}")
            success += 1
        except Exception as e:
            print_status(desc, "❌", f"导入失败: {str(e)[:50]}")
    
    return success, total


def test_profit_solver() -> bool:
    """测试利润求解器"""
    print_header("💰 利润求解器测试")
    
    try:
        from ecom_v51.profit_solver import ProfitSolver
        from ecom_v51.models import ProfitInput
        
        # 测试基础计算
        input_data = ProfitInput(
            sale_price=100,
            list_price=120,
            variable_rate_total=0.35,
            fixed_cost_total=80,
        )
        
        result = ProfitSolver.solve_current(input_data)
        
        # 验证结果
        expected_profit = -15.0  # 100 * (1 - 0.35) - 80 = -15
        if abs(result.net_profit - expected_profit) < 0.01:
            print_status("利润计算", "✅", f"净利润: {result.net_profit}")
            print_status("净利率", "✅", f"{result.net_margin:.2%}")
            print_status("保本价", "✅", f"{result.break_even_price:.2f} 元")
            return True
        else:
            print_status("利润计算", "❌", f"预期 {expected_profit}, 实际 {result.net_profit}")
            return False
            
    except Exception as e:
        print_status("利润求解器", "❌", f"运行错误: {str(e)}")
        return False


def test_strategy_engine() -> bool:
    """测试策略引擎"""
    print_header("🎯 策略引擎测试")
    
    try:
        from ecom_v51.strategy import StrategyEngine
        
        engine = StrategyEngine()
        
        # 测试亏损场景
        tasks = engine.generate_for_sku(
            ctr=0.01,
            add_to_cart_rate=0.04,
            order_rate=0.0,
            net_margin=-0.15,
            roas=0.0,
            days_of_supply=30,
            return_rate=0.25,
            rating=3.2,
        )
        
        # 验证生成的策略
        has_pricing = any(t.strategy_type == "pricing" for t in tasks)
        has_conversion = any(t.strategy_type == "conversion" for t in tasks)
        
        print_status("策略生成", "✅", f"生成了 {len(tasks)} 个策略任务")
        
        if has_pricing:
            print_status("定价策略", "✅", "检测到亏损并生成定价策略")
        
        if has_conversion:
            print_status("转化优化", "✅", "检测到低 CTR 并生成转化策略")
        
        return len(tasks) > 0
        
    except Exception as e:
        print_status("策略引擎", "❌", f"运行错误: {str(e)}")
        return False


def test_war_room() -> bool:
    """测试作战室服务"""
    print_header("🏠 作战室服务测试")
    
    try:
        from ecom_v51.war_room import WarRoomService
        from ecom_v51.models import SkuSnapshot
        
        service = WarRoomService()
        
        # 创建测试数据
        snapshot = SkuSnapshot(
            sku="TEST-001",
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
        report = service.build_report(snapshot)
        
        # 验证报告内容
        checks = [
            ("漏斗指标", "ctr" in report.funnel),
            ("利润指标", report.net_profit != 0),
            ("策略任务", len(report.strategy_tasks) > 0),
            ("折扣模拟", len(report.discount_simulations) == 3),
        ]
        
        all_passed = True
        for name, passed in checks:
            status = "✅" if passed else "❌"
            print_status(name, status)
            all_passed = all_passed and passed
        
        if all_passed:
            print_status("完整报告", "✅", f"SKU: {report.sku}")
        
        return all_passed
        
    except Exception as e:
        print_status("作战室服务", "❌", f"运行错误: {str(e)}")
        return False


def test_field_mapper() -> bool:
    """测试字段映射器"""
    print_header("🗺️ 智能字段映射器测试")
    
    try:
        from ecom_v51.intelligent_field_mapper import IntelligentFieldMapper
        
        mapper = IntelligentFieldMapper()
        
        # 测试不同字段识别
        test_cases = [
            ("Артикул товара", "sku"),
            ("Показы", "impressions"),
            ("Кол-во заказов", "orders"),
            ("Сумма продаж", "revenue"),
            ("Рейтинг", "rating"),
        ]
        
        success = 0
        for col_name, expected_field in test_cases:
            standard_name, confidence, reasons = mapper.detect_field(col_name)
            
            if standard_name == expected_field and confidence >= 0.5:
                print_status(f"识别 {col_name}", "✅", f"→ {standard_name} ({confidence:.2f})")
                success += 1
            else:
                print_status(f"识别 {col_name}", "❌", f"预期 {expected_field}, 实际 {standard_name}")
        
        return success == len(test_cases)
        
    except Exception as e:
        print_status("字段映射器", "❌", f"运行错误: {str(e)}")
        return False


def test_ingestion() -> bool:
    """测试导入诊断器"""
    print_header("📥 导入诊断器测试")
    
    try:
        from ecom_v51.ingestion import ImportDiagnoser
        
        diagnoser = ImportDiagnoser()
        
        # 测试 Ozon 平台识别
        diagnosis = diagnoser.diagnose(
            file_name="ozon_report.xlsx",
            preview_rows=[["Артикул", "Показы", "Заказы"]],
            headers=["Артикул", "Показы", "Заказы"],
            mapped_fields=3,
            unmapped_fields=[],
            row_error_count=0,
        )
        
        checks = [
            ("平台识别", diagnosis.platform == "ozon"),
            ("表头定位", diagnosis.detected_header_row == 0),
            ("主键识别", diagnosis.key_field is not None),
            ("状态判断", diagnosis.status == "success"),
        ]
        
        all_passed = True
        for name, passed in checks:
            status = "✅" if passed else "❌"
            print_status(name, status)
            all_passed = all_passed and passed
        
        return all_passed
        
    except Exception as e:
        print_status("导入诊断器", "❌", f"运行错误: {str(e)}")
        return False


def test_cli() -> bool:
    """测试 CLI"""
    print_header("🖥️ CLI 测试")
    
    try:
        import subprocess
        from pathlib import Path
        
        # 创建测试输入文件
        test_input = {
            "sku": "CLI-TEST-001",
            "impressions": 5000,
            "card_visits": 50,
            "add_to_cart": 2,
            "orders": 1,
            "ad_spend": 100,
            "ad_revenue": 150,
            "stock_total": 50,
            "days_of_supply": 10,
            "rating": 4.2,
            "return_rate": 0.1,
            "cancel_rate": 0.05,
            "sale_price": 80,
            "list_price": 100,
            "variable_rate_total": 0.3,
            "fixed_cost_total": 50,
        }
        
        input_path = Path("test_cli_input.json")
        input_path.write_text(json.dumps(test_input, indent=2), encoding='utf-8')
        
        # 运行 CLI
        result = subprocess.run(
            ["v51-ops", "--input", str(input_path), "--pretty"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        
        # 清理
        input_path.unlink()
        
        if result.returncode == 0:
            output = json.loads(result.stdout)
            print_status("CLI 执行", "✅", f"成功生成报告")
            print_status("输出格式", "✅", f"JSON 格式正确")
            return True
        else:
            print_status("CLI 执行", "❌", f"返回码: {result.returncode}")
            print(f"错误: {result.stderr}")
            return False
            
    except Exception as e:
        print_status("CLI 测试", "❌", f"运行错误: {str(e)}")
        return False


def generate_report(results: Dict[str, bool]) -> None:
    """生成诊断报告"""
    print_header("📊 诊断报告")
    
    total = len(results)
    success = sum(1 for v in results.values() if v)
    failed = total - success
    
    print(f"总测试模块: {total}")
    print(f"{Colors.GREEN}通过: {success}{Colors.END}")
    print(f"{Colors.RED}失败: {failed}{Colors.END}")
    
    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 所有模块运行正常！系统健康度 100%{Colors.END}\n")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  发现 {failed} 个模块需要修复{Colors.END}\n")
        
        # 列出失败的模块
        for module, passed in results.items():
            if not passed:
                print(f"  - {module}")


def main():
    """主诊断流程"""
    print(f"\n{Colors.BOLD}V5.1 跨境电商智能运营系统 - 诊断工具{Colors.END}")
    print(f"{Colors.BOLD}诊断时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}\n")
    
    # 运行所有测试
    results = {}
    
    # 1. 模块导入检查
    import_success, import_total = check_imports()
    results["模块导入"] = import_success == import_total
    
    # 2. 功能模块测试
    results["利润求解器"] = test_profit_solver()
    results["策略引擎"] = test_strategy_engine()
    results["作战室服务"] = test_war_room()
    results["字段映射器"] = test_field_mapper()
    results["导入诊断器"] = test_ingestion()
    results["CLI"] = test_cli()
    
    # 生成报告
    generate_report(results)
    
    # 返回退出码
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
