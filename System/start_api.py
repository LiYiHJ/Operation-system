#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V5.1 系统启动脚本（前后端分离版）
- 后端：Flask API（端口5000）
- 前端：React + Vite（端口5173）
"""

import subprocess
import sys
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / 'src'


def setup_environment():
    """设置环境变量"""
    os.environ['PYTHONPATH'] = str(SRC_DIR)
    os.environ['DATABASE_URL'] = os.getenv(
        'DATABASE_URL',
        f'sqlite:///{PROJECT_ROOT / "data" / "ecom_v51.db"}'
    )
    os.environ['APP_ENV'] = 'development'
    os.environ['APP_DEBUG'] = 'true'
    os.environ['SECRET_KEY'] = 'dev-secret-key-change-in-production'


def check_database():
    """检查数据库"""
    print("🔍 检查数据库...")
    
    db_file = PROJECT_ROOT / 'data' / 'ecom_v51.db'
    if not db_file.exists():
        print("  ⚠️  数据库不存在，正在创建...")
        subprocess.run(
            [sys.executable, '-m', 'ecom_v51.init_db'],
            cwd=PROJECT_ROOT,
            check=True
        )
        print("  ✅ 数据库创建成功")
    else:
        print("  ✅ 数据库已存在")


def start_api():
    """启动Flask API"""
    print("\n🚀 启动Flask API...")
    print("="*70)
    print("API地址: http://localhost:5000/api")
    print("健康检查: http://localhost:5000/api/health")
    print("前端地址: http://localhost:5173")
    print("="*70)
    print("\n按 Ctrl+C 停止服务\n")
    
    # 启动API
    subprocess.run(
        [sys.executable, '-m', 'ecom_v51.api.app'],
        cwd=PROJECT_ROOT
    )


def main():
    """主函数"""
    print("\n" + "="*70)
    print("V5.1 跨境电商智能运营系统（前后端分离版）")
    print("="*70 + "\n")
    
    # 1. 设置环境
    setup_environment()
    
    # 2. 检查数据库
    check_database()
    
    # 3. 启动API
    start_api()


if __name__ == '__main__':
    main()
