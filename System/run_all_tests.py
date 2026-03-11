#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键运行所有测试和诊断
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*80}")
    print(f"执行: {description}")
    print(f"{'='*80}\n")
    
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=Path(__file__).parent,
    )
    
    if result.returncode != 0:
        print(f"\n❌ {description} 失败")
        return False
    else:
        print(f"\n✅ {description} 成功")
        return True

def main():
    print(f"\n{'='*80}")
    print("V5.1 系统一键测试和诊断".center(80))
    print(f"{'='*80}\n")
    
    results = []
    
    # 1. 系统诊断
    results.append(run_command(
        "python src/ecom_v51/system_diagnostics.py",
        "系统诊断"
    ))
    
    # 2. 集成测试
    results.append(run_command(
        "pytest tests/test_integration.py -v",
        "集成测试"
    ))
    
    # 3. 生成示例报告
    results.append(run_command(
        "python quick_start.py",
        "生成示例报告"
    ))
    
    # 总结
    print(f"\n{'='*80}")
    print("测试总结".center(80))
    print(f"{'='*80}\n")
    
    total = len(results)
    success = sum(results)
    failed = total - success
    
    print(f"总测试: {total}")
    print(f"✅ 通过: {success}")
    print(f"❌ 失败: {failed}")
    
    if failed == 0:
        print(f"\n🎉 所有测试通过！系统健康度 100%\n")
        sys.exit(0)
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
