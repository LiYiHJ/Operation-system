#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V5.1 系统完整性检查 - 最终验证
确保 C:\Operation-system\System 所有模块能正常运行
"""

import sys
import os
from pathlib import Path
import subprocess

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

print("=" * 80)
print("🔍 V5.1 系统完整性检查 - 最终验证")
print("=" * 80)
print(f"项目根目录: {PROJECT_ROOT}")
print(f"Python 版本: {sys.version}")
print()

# 测试结果收集
test_results = {
    "passed": [],
    "warnings": [],
    "errors": []
}

# ==================== 1. 核心文件检查 ====================
print("📂 1. 核心文件检查")
print("-" * 80)

core_files = {
    "后端核心": [
        "src/ecom_v51/__init__.py",
        "src/ecom_v51/ingestion.py",
        "src/ecom_v51/intelligent_field_mapper.py",
        "src/ecom_v51/import_service.py",
        "src/ecom_v51/models.py",
    ],
    "配置文件": [
        "src/ecom_v51/config/settings.py",
        "src/ecom_v51/config/__init__.py",
    ],
    "Web 应用": [
        "src/ecom_v51/web/app.py",
        "src/ecom_v51/web/routes/__init__.py",
        "src/ecom_v51/web/routes/imports.py",
    ],
    "服务层": [
        "src/ecom_v51/services/__init__.py",
        "src/ecom_v51/services/import_service.py",
    ],
    "模板文件": [
        "src/ecom_v51/templates/base.html",
        "src/ecom_v51/templates/imports/index.html",
    ],
    "静态文件": [
        "src/ecom_v51/static/css/app.css",
        "src/ecom_v51/static/js/app.js",
    ],
}

for category, files in core_files.items():
    print(f"\n{category}:")
    for file in files:
        file_path = PROJECT_ROOT / file
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"  ✅ {file} ({size} bytes)")
            test_results["passed"].append(f"文件存在: {file}")
        else:
            print(f"  ❌ {file} 不存在")
            test_results["errors"].append(f"文件缺失: {file}")

# ==================== 2. 模块导入测试 ====================
print("\n\n📦 2. 模块导入测试")
print("-" * 80)

modules_to_test = [
    ("ecom_v51.ingestion", "导入诊断器"),
    ("ecom_v51.intelligent_field_mapper", "智能字段映射器"),
    ("ecom_v51.import_service", "导入服务"),
    ("ecom_v51.web.app", "Flask 应用"),
    ("ecom_v51.config.settings", "配置模块"),
    ("ecom_v51.services", "服务层"),
]

for module_name, description in modules_to_test:
    try:
        __import__(module_name)
        print(f"  ✅ {description} ({module_name})")
        test_results["passed"].append(f"模块导入: {module_name}")
    except Exception as e:
        print(f"  ❌ {description} ({module_name}): {e}")
        test_results["errors"].append(f"模块导入失败: {module_name} - {e}")

# ==================== 3. 智能映射器功能测试 ====================
print("\n\n🧠 3. 智能映射器功能测试")
print("-" * 80)

try:
    from ecom_v51.intelligent_field_mapper import IntelligentFieldMapper
    mapper = IntelligentFieldMapper()
    
    test_fields = [
        ("Артикул", "sku", 0.7),
        ("Показы", "impressions", 0.7),
        ("Заказы", "orders", 0.7),
        ("Сумма заказов", "revenue", 0.7),
        ("Рейтинг", "rating", 0.7),
    ]
    
    all_passed = True
    for field, expected_name, min_confidence in test_fields:
        standard_name, confidence, reasons = mapper.detect_field(field)
        
        if standard_name == expected_name and confidence >= min_confidence:
            status = "✅"
            test_results["passed"].append(f"字段映射: {field} → {standard_name}")
        else:
            status = "❌"
            all_passed = False
            test_results["errors"].append(f"字段映射失败: {field} (期望: {expected_name}, 实际: {standard_name}, 置信度: {confidence})")
        
        print(f"  {status} {field:20s} → {standard_name or 'None':15s} (置信度: {confidence:.2f})")
    
    if all_passed:
        print("\n  ✅ 智能映射器功能正常")
    else:
        print("\n  ❌ 智能映射器部分字段映射失败")
        
except Exception as e:
    print(f"  ❌ 智能映射器测试失败: {e}")
    test_results["errors"].append(f"智能映射器测试失败: {e}")

# ==================== 4. 导入诊断器测试 ====================
print("\n\n🔍 4. 导入诊断器测试")
print("-" * 80)

try:
    from ecom_v51.ingestion import ImportDiagnoser
    diagnoser = ImportDiagnoser()
    
    # 测试主键检测
    test_headers = [
        (["Артикул", "Показы"], "Артикул"),
        (["SKU", "Orders"], "SKU"),
        (["seller_sku", "Revenue"], "seller_sku"),
    ]
    
    all_passed = True
    for headers, expected_key in test_headers:
        key_field = diagnoser.detect_key_field(headers)
        if key_field == expected_key:
            status = "✅"
            test_results["passed"].append(f"主键检测: {headers} → {key_field}")
        else:
            status = "❌"
            all_passed = False
            test_results["errors"].append(f"主键检测失败: {headers} (期望: {expected_key}, 实际: {key_field})")
        
        print(f"  {status} {str(headers):40s} → {key_field or 'None'}")
    
    if all_passed:
        print("\n  ✅ 导入诊断器功能正常")
    else:
        print("\n  ❌ 导入诊断器部分功能失败")
        
except Exception as e:
    print(f"  ❌ 导入诊断器测试失败: {e}")
    test_results["errors"].append(f"导入诊断器测试失败: {e}")

# ==================== 5. Flask 应用测试 ====================
print("\n\n🌐 5. Flask 应用测试")
print("-" * 80)

try:
    from ecom_v51.web.app import create_app
    app = create_app()
    
    # 测试应用配置
    print(f"  ✅ Flask 应用创建成功")
    print(f"     - 调试模式: {app.debug}")
    print(f"     - 模板文件夹: {app.template_folder}")
    print(f"     - 静态文件夹: {app.static_folder}")
    
    # 测试路由
    with app.app_context():
        from flask import url_for
        try:
            # 测试导入页面路由
            with app.test_client() as client:
                response = client.get('/imports')
                if response.status_code == 200:
                    print(f"  ✅ 导入页面路由正常 (状态码: {response.status_code})")
                    test_results["passed"].append("Flask 路由: /imports")
                else:
                    print(f"  ⚠️  导入页面路由异常 (状态码: {response.status_code})")
                    test_results["warnings"].append(f"Flask 路由异常: /imports (状态码: {response.status_code})")
        except Exception as e:
            print(f"  ⚠️  路由测试失败: {e}")
            test_results["warnings"].append(f"路由测试失败: {e}")
    
    test_results["passed"].append("Flask 应用创建")
    
except Exception as e:
    print(f"  ❌ Flask 应用测试失败: {e}")
    test_results["errors"].append(f"Flask 应用测试失败: {e}")

# ==================== 6. 依赖包检查 ====================
print("\n\n📦 6. 依赖包检查")
print("-" * 80)

required_packages = [
    ("flask", "Flask"),
    ("pandas", "Pandas"),
    ("openpyxl", "OpenPyXL"),
    ("werkzeug", "Werkzeug"),
]

for package_name, description in required_packages:
    try:
        __import__(package_name)
        print(f"  ✅ {description} ({package_name})")
        test_results["passed"].append(f"依赖包: {package_name}")
    except ImportError:
        print(f"  ❌ {description} ({package_name}) 未安装")
        test_results["errors"].append(f"依赖包缺失: {package_name}")

# ==================== 7. 配置文件检查 ====================
print("\n\n⚙️  7. 配置文件检查")
print("-" * 80)

try:
    from ecom_v51.config.settings import settings
    
    print(f"  ✅ Settings 加载成功")
    print(f"     - App Env: {settings.app_env}")
    print(f"     - Debug: {settings.debug}")
    print(f"     - Secret Key: {'已配置' if settings.secret_key else '未配置'}")
    
    test_results["passed"].append("配置文件加载")
    
except Exception as e:
    print(f"  ❌ 配置文件加载失败: {e}")
    test_results["errors"].append(f"配置文件加载失败: {e}")

# ==================== 8. 数据导入服务测试 ====================
print("\n\n📊 8. 数据导入服务测试")
print("-" * 80)

try:
    from ecom_v51.services import ImportCenterService
    service = ImportCenterService()
    
    print(f"  ✅ ImportCenterService 创建成功")
    
    # 测试批次列表功能
    batches = service.list_batches()
    print(f"  ✅ 批次列表功能正常 (当前批次: {len(batches)})")
    
    test_results["passed"].append("数据导入服务")
    
except Exception as e:
    print(f"  ❌ 数据导入服务测试失败: {e}")
    test_results["errors"].append(f"数据导入服务测试失败: {e}")

# ==================== 最终总结 ====================
print("\n\n" + "=" * 80)
print("📋 最终测试总结")
print("=" * 80)

total_tests = len(test_results["passed"]) + len(test_results["warnings"]) + len(test_results["errors"])
pass_rate = (len(test_results["passed"]) / total_tests * 100) if total_tests > 0 else 0

print(f"\n总测试数: {total_tests}")
print(f"通过: {len(test_results['passed'])} ({len(test_results['passed'])/total_tests*100 if total_tests > 0 else 0:.1f}%)")
print(f"警告: {len(test_results['warnings'])}")
print(f"失败: {len(test_results['errors'])}")
print(f"通过率: {pass_rate:.1f}%")

if test_results["errors"]:
    print("\n❌ 失败项:")
    for i, error in enumerate(test_results["errors"][:10], 1):
        print(f"  {i}. {error}")

if test_results["warnings"]:
    print("\n⚠️  警告项:")
    for i, warning in enumerate(test_results["warnings"][:5], 1):
        print(f"  {i}. {warning}")

# 判断系统是否可用
if pass_rate >= 90 and len(test_results["errors"]) == 0:
    print("\n✅ 系统状态: 优秀 - 可以直接使用")
    print("\n下一步:")
    print("  1. 运行清理缓存: python clear_cache.py")
    print("  2. 启动 Flask: flask run")
    print("  3. 访问: http://127.0.0.1:5000/imports")
elif pass_rate >= 70:
    print("\n⚠️  系统状态: 良好 - 可以使用但需要修复部分问题")
else:
    print("\n❌ 系统状态: 需要修复 - 存在严重问题")

print("=" * 80)

# 返回退出码
sys.exit(0 if len(test_results["errors"]) == 0 else 1)
