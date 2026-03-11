#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统诊断脚本 - 全面检查系统状态
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

print("=" * 80)
print("🔍 V5.1 系统诊断")
print("=" * 80)

# 1. 检查 Python 版本
print(f"\n✅ Python 版本: {sys.version}")

# 2. 检查关键文件是否存在
key_files = [
    "src/ecom_v51/intelligent_field_mapper.py",
    "src/ecom_v51/import_service.py",
    "src/ecom_v51/web/app.py",
    "src/ecom_v51/web/routes/imports.py",
    "src/ecom_v51/templates/imports/index.html",
]

print("\n📁 关键文件检查:")
for file in key_files:
    file_path = Path(file)
    if file_path.exists():
        size = file_path.stat().st_size
        print(f"   ✅ {file} ({size} bytes)")
    else:
        print(f"   ❌ {file} 不存在")

# 3. 检查模块导入
print("\n📦 模块导入检查:")
try:
    from ecom_v51.intelligent_field_mapper import IntelligentFieldMapper
    print("   ✅ IntelligentFieldMapper 导入成功")
    
    # 测试映射器
    mapper = IntelligentFieldMapper()
    test_fields = ["Артикул", "Показы", "Заказы", "Сумма заказов"]
    
    print("\n🧪 字段映射测试:")
    for field in test_fields:
        standard_name, confidence, reasons = mapper.detect_field(field)
        status = "✅" if confidence >= 0.7 else "⚠️" if confidence >= 0.5 else "❌"
        print(f"   {status} {field:20s} → {standard_name or 'None':15s} (置信度: {confidence:.2f})")
        
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 检查配置文件
print("\n⚙️  配置文件检查:")
config_files = [
    "src/ecom_v51/config/settings.py",
    "src/ecom_v51/config/field_mapping.json",
]

for config in config_files:
    config_path = Path(config)
    if config_path.exists():
        print(f"   ✅ {config}")
    else:
        print(f"   ⚠️  {config} 不存在（将创建）")

# 5. 检查数据库连接（如果有）
print("\n💾 数据库检查:")
try:
    from ecom_v51.config.settings import settings
    print(f"   ✅ Settings 加载成功")
    print(f"      - App Env: {settings.app_env}")
    print(f"      - Debug: {settings.debug}")
except Exception as e:
    print(f"   ⚠️  Settings 加载失败: {e}")

print("\n" + "=" * 80)
print("✅ 诊断完成")
print("\n下一步：根据诊断结果优化系统")
print("=" * 80)
