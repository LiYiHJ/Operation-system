#!/usr/bin/env python3
"""
前端项目验证脚本
检查所有必需文件是否存在，依赖是否安装
"""

import os
import sys
import json
from pathlib import Path

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(title):
    print(f"\n{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{title.center(80)}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.END}\n")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        print_success(f"{description}: {file_path} ({size} bytes)")
        return True
    else:
        print_error(f"{description}: {file_path} (不存在)")
        return False

def check_directory_exists(dir_path, description):
    """检查目录是否存在"""
    if os.path.exists(dir_path):
        print_success(f"{description}: {dir_path}")
        return True
    else:
        print_error(f"{description}: {dir_path} (不存在)")
        return False

def main():
    print_header("V5.1 前端项目验证")

    # 前端根目录
    frontend_root = r"C:\Operation-system\System\frontend"
    os.chdir(frontend_root)

    # 1. 检查核心配置文件
    print_header("1️⃣ 核心配置文件检查")
    checks = []
    checks.append(check_file_exists("package.json", "依赖配置"))
    checks.append(check_file_exists("vite.config.ts", "Vite配置"))
    checks.append(check_file_exists("tsconfig.json", "TypeScript配置"))
    checks.append(check_file_exists("index.html", "HTML入口"))
    
    # 2. 检查源代码文件
    print_header("2️⃣ 源代码文件检查")
    checks.append(check_file_exists("src/main.tsx", "React入口"))
    checks.append(check_file_exists("src/App.tsx", "路由配置"))
    checks.append(check_file_exists("src/App.css", "全局样式"))
    checks.append(check_file_exists("src/index.css", "基础样式"))
    
    # 3. 检查页面组件
    print_header("3️⃣ 页面组件检查")
    pages = [
        ("src/pages/Dashboard.tsx", "运营总览"),
        ("src/pages/DataImport.tsx", "数据导入"),
        ("src/pages/ABCAnalysis.tsx", "ABC分析"),
        ("src/pages/PriceCompetitiveness.tsx", "价格竞争力"),
        ("src/pages/FunnelAnalysis.tsx", "转化漏斗"),
        ("src/pages/InventoryAlert.tsx", "库存预警"),
        ("src/pages/AdsManagement.tsx", "广告管理"),
        ("src/pages/StrategyList.tsx", "策略清单"),
    ]
    
    for page_path, page_name in pages:
        checks.append(check_file_exists(page_path, page_name))
    
    # 4. 检查布局组件
    print_header("4️⃣ 布局组件检查")
    checks.append(check_file_exists("src/layout/Layout.tsx", "主布局"))
    
    # 5. 检查依赖安装
    print_header("5️⃣ 依赖检查")
    node_modules_exists = os.path.exists("node_modules")
    if node_modules_exists:
        print_success("node_modules 存在")
        
        # 检查关键依赖
        key_deps = [
            "node_modules/react",
            "node_modules/antd",
            "node_modules/echarts",
            "node_modules/@tanstack/react-query",
        ]
        for dep in key_deps:
            if os.path.exists(dep):
                print_success(f"  └─ {os.path.basename(dep)} 已安装")
            else:
                print_warning(f"  └─ {os.path.basename(dep)} 未安装")
    else:
        print_warning("node_modules 不存在，需要运行: npm install")
    
    # 6. 检查文档
    print_header("6️⃣ 文档检查")
    checks.append(check_file_exists("README_FRONTEND.md", "前端文档"))
    
    # 7. 统计代码量
    print_header("7️⃣ 代码统计")
    total_size = 0
    total_files = 0
    
    for page_path, _ in pages:
        if os.path.exists(page_path):
            size = os.path.getsize(page_path)
            total_size += size
            total_files += 1
    
    print_info(f"总文件数: {total_files}")
    print_info(f"总代码量: {total_size:,} bytes ({total_size/1024:.2f} KB)")
    
    # 8. 最终报告
    print_header("📊 验证报告")
    passed = sum(checks)
    total = len(checks)
    health_percent = (passed / total * 100) if total > 0 else 0
    
    print(f"\n总检查项: {total}")
    print(f"{Colors.GREEN}通过: {passed}{Colors.END}")
    print(f"{Colors.RED}失败: {total - passed}{Colors.END}")
    print(f"\n{Colors.BOLD}项目健康度: {health_percent:.0f}%{Colors.END}")
    
    if health_percent == 100:
        print(f"\n{Colors.GREEN}{'🎉 所有检查通过！项目可以运行！' ^ 80}{Colors.END}\n")
        print(f"{Colors.BOLD}启动命令:{Colors.END}")
        print(f"  cd C:\\Operation-system\\System\\frontend")
        if not node_modules_exists:
            print(f"  {Colors.YELLOW}npm install{Colors.END}  # 首次运行需要安装依赖")
        print(f"  {Colors.GREEN}npm run dev{Colors.END}")
        print(f"\n{Colors.BOLD}访问地址:{Colors.END}")
        print(f"  {Colors.BLUE}http://localhost:5173{Colors.END}\n")
    else:
        print(f"\n{Colors.RED}{'⚠️  存在缺失文件，请检查！' ^ 80}{Colors.END}\n")
    
    return health_percent == 100

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n{Colors.RED}验证失败: {e}{Colors.END}")
        sys.exit(1)
