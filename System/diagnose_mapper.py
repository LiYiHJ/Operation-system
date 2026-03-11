#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速诊断：检查智能映射器是否工作"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

print("=" * 80)
print("🔍 诊断：智能映射器加载检查")
print("=" * 80)

# 1. 检查模块是否存在
mapper_file = project_root / "ecom_v51" / "intelligent_field_mapper.py"
if mapper_file.exists():
    print(f"✅ 文件存在：{mapper_file}")
    print(f"   大小：{mapper_file.stat().st_size} 字节")
else:
    print(f"❌ 文件不存在：{mapper_file}")
    sys.exit(1)

# 2. 尝试导入
try:
    from ecom_v51.intelligent_field_mapper import IntelligentFieldMapper
    print("✅ 模块导入成功")
except Exception as e:
    print(f"❌ 模块导入失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. 创建实例
try:
    mapper = IntelligentFieldMapper()
    print("✅ 实例化成功")
except Exception as e:
    print(f"❌ 实例化失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. 测试映射功能
print("\n" + "=" * 80)
print("🧪 测试字段映射功能")
print("=" * 80)

test_fields = [
    "Артикул",
    "Показы",
    "Заказы",
    "Сумма заказов",
    "Рейтинг",
    "Остатки",
    "seller_sku",
    "Product ID",
    "未知字段"
]

for field in test_fields:
    standard_name, confidence, reasons = mapper.detect_field(field)
    if standard_name:
        status = "✅" if confidence >= 0.7 else "⚠️"
        print(f"{status} {field:20s} → {standard_name:15s} (置信度: {confidence:.2f})")
    else:
        print(f"❌ {field:20s} → 无法识别")

print("\n" + "=" * 80)
print("✅ 诊断完成")
print("\n如果上述测试通过，说明智能映射器工作正常。")
print("如果 Web 界面仍然失败，可能是 Flask 未重启。")
print("=" * 80)
