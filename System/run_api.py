#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V5.1 跨境电商智能运营系统 - 启动脚本
快速启动API服务
"""

import sys
from pathlib import Path

# 添加src到Python路径
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from ecom_v51.api.app import create_app

if __name__ == '__main__':
    # 创建应用
    app = create_app()  # 修复：移除参数
    
    # 启动信息
    print("\n" + "="*70)
    print("V5.1 跨境电商智能运营系统 - Flask API")
    print("="*70)
    print(f"环境: {app.config.get('ENV', 'development')}")
    print(f"数据库: {app.config.get('SQLALCHEMY_DATABASE_URI', 'N/A')}")
    print(f"API地址: http://localhost:5000")
    print(f"健康检查: http://localhost:5000/api/health")
    print("="*70)
    print("\n可用接口:")
    print("  Dashboard:")
    print("    GET /api/dashboard/metrics")
    print("    GET /api/dashboard/top-skus")
    print("    GET /api/dashboard/alerts")
    print("    GET /api/dashboard/trends")
    print("    GET /api/dashboard/shop-health")
    print("\n  Import:")
    print("    POST /api/import/upload")
    print("    POST /api/import/confirm")
    print("    GET  /api/import/template")
    print("\n  Analysis:")
    print("    GET  /api/analysis/sku/<sku>")
    print("    GET  /api/analysis/abc")
    print("    GET  /api/analysis/funnel")
    print("    GET  /api/analysis/price")
    print("    GET  /api/analysis/inventory")
    print("    POST /api/analysis/profit")
    print("\n  Strategy:")
    print("    GET  /api/strategy/list")
    print("    POST /api/strategy/generate/<sku>")
    print("    POST /api/strategy/batch")
    print("    POST /api/strategy/decision")
    print("    PUT  /api/strategy/task/<id>/status")
    print("="*70 + "\n")
    
    # 启动Flask开发服务器
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
    