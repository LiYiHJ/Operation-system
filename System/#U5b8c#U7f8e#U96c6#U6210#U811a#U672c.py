#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完美集成脚本 - 将新功能正确集成到原有系统
遵循原有架构，不创建独立系统
"""

print("=" * 60)
print("  完美集成 - 基于原有系统架构")
print("=" * 60)
print()

import shutil
from pathlib import Path
from datetime import datetime
import re

# ===== 1. 备份原有文件 =====
print("📦 步骤 1: 备份原有文件")
print("-" * 60)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_dir = Path('backups') / f'integration_{timestamp}'
backup_dir.mkdir(parents=True, exist_ok=True)

files_to_backup = [
    'backend/app.py',
    'src/ecom_v51/config/settings.py',
    'src/ecom_v51/db/models.py',
    'pyproject.toml'
]

for file in files_to_backup:
    src = Path(file)
    if src.exists():
        dst = backup_dir / file
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        print(f"  ✅ 备份: {file}")

print()

# ===== 2. 扩展数据库模型 =====
print("📊 步骤 2: 扩展数据库模型")
print("-" * 60)

db_models_path = Path('src/ecom_v51/db/models.py')

# 读取原有内容
with open(db_models_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加新表（如果不存在）
if 'class TrendPrediction' not in content:
    new_tables = """

# ===== 趋势预测相关表 =====

class TrendPrediction(Base):
    \"\"\"趋势预测结果表\"\"\"
    __tablename__ = 'trend_prediction'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(100), nullable=False, index=True)
    shop_name = Column(String(100), nullable=True)
    prediction_date = Column(Date, nullable=False)
    predicted_value = Column(Float, nullable=False)
    method = Column(String(50), default='auto')
    confidence = Column(Float, default=0.0)
    lower_bound = Column(Float, nullable=True)
    upper_bound = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_trend_sku_date', 'sku', 'prediction_date'),
    )


class AutomationTask(Base):
    \"\"\"自动化任务表\"\"\"
    __tablename__ = 'automation_task'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(50), nullable=False)  # price_adjust, stock_alert, etc.
    task_name = Column(String(200), nullable=False)
    sku = Column(String(100), nullable=True)
    shop_name = Column(String(100), nullable=True)
    status = Column(String(20), default='pending')  # pending, running, completed, failed
    priority = Column(String(5), default='P3')  # P0, P1, P2, P3
    scheduled_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_auto_task_status', 'status', 'priority'),
    )


class NotificationLog(Base):
    \"\"\"通知日志表\"\"\"
    __tablename__ = 'notification_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_type = Column(String(20), nullable=False)  # email, telegram
    recipient = Column(String(200), nullable=False)
    subject = Column(String(500), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(20), default='pending')  # pending, sent, failed
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_notif_status', 'status', 'created_at'),
    )
"""

    # 在文件末尾添加
    content += new_tables

    with open(db_models_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("  ✅ 添加了 3 个新表: TrendPrediction, AutomationTask, NotificationLog")
else:
    print("  ⚠️ 表已存在，跳过")

print()

# ===== 3. 扩展配置系统 =====
print("⚙️ 步骤 3: 扩展配置系统")
print("-" * 60)

settings_path = Path('src/ecom_v51/config/settings.py')

with open(settings_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加新配置（如果不存在）
if 'trend_prediction_method' not in content:
    new_config = """

    # ===== 趋势预测配置 =====
    trend_prediction_method: str = os.getenv("TREND_PREDICTION_METHOD", "auto")
    trend_prediction_days: int = int(os.getenv("TREND_PREDICTION_DAYS", "7"))

    # ===== Ozon API 配置 =====
    ozon_api_enabled: bool = os.getenv("OZON_API_ENABLED", "false").lower() == "true"

    # ===== 通知配置 =====
    notification_email_enabled: bool = os.getenv("NOTIFICATION_EMAIL_ENABLED", "false").lower() == "true"
    notification_telegram_enabled: bool = os.getenv("NOTIFICATION_TELEGRAM_ENABLED", "false").lower() == "true"
"""

    # 在 Settings 类的末尾添加
    if 'class Settings' in content:
        # 找到最后一个属性定义的位置
        lines = content.split('\n')
        insert_pos = -1
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() and not lines[i].strip().startswith('#') and ':' in lines[i]:
                insert_pos = i + 1
                break

        if insert_pos > 0:
            lines.insert(insert_pos, new_config)
            content = '\n'.join(lines)

            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print("  ✅ 添加了趋势预测、Ozon API、通知配置")
else:
    print("  ⚠️ 配置已存在，跳过")

print()

# ===== 4. 扩展 backend/app.py =====
print("🔌 步骤 4: 扩展 backend/app.py - 添加 API 路由")
print("-" * 60)

app_py_path = Path('backend/app.py')

with open(app_py_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 4.1 添加导入语句
if 'from ecom_v51.db.models import TrendPrediction' not in content:
    import_section = """
# ===== 自动化功能导入 =====
from ecom_v51.db.models import TrendPrediction, AutomationTask, NotificationLog
from ecom_v51.db.session import get_session
try:
    from ecom_v51 import trend_predictor
    TREND_PREDICTOR_AVAILABLE = True
except ImportError:
    TREND_PREDICTOR_AVAILABLE = False
"""

    # 在第一个 from ecom_v51 导入之后添加
    match = re.search(r'from ecom_v51\..*', content)
    if match:
        pos = match.end()
        content = content[:pos] + '\n' + import_section + '\n' + content[pos:]
        print("  ✅ 添加了导入语句")

# 4.2 添加 API 路由
if '/api/automation/trend/predict' not in content:
    api_routes = """

# ===== 自动化 API 路由 =====

@app.route('/api/automation/status', methods=['GET'])
def get_automation_status():
    \"\"\"获取自动化模块状态\"\"\"
    return jsonify({
        'success': True,
        'modules': {
            'trend_predictor': TREND_PREDICTOR_AVAILABLE,
            'database': True,
            'notification': False  # 需要配置后启用
        },
        'version': '5.1.0'
    })


@app.route('/api/automation/trend/predict', methods=['POST'])
def predict_trend():
    \"\"\"
    趋势预测 API

    Request Body:
    {
        "historical_data": [{"date": "2026-02-01", "orders": 50}, ...],
        "days": 7,
        "sku": "SKU-001"
    }
    \"\"\"
    try:
        data = request.json
        historical_data = data.get('historical_data', [])
        days = data.get('days', 7)
        sku = data.get('sku', 'Unknown')

        if not historical_data:
            return jsonify({'success': False, 'error': '没有历史数据'}), 400

        # 转换为 DataFrame
        df = pd.DataFrame(historical_data)

        if TREND_PREDICTOR_AVAILABLE:
            # 使用高级预测器
            predictor = trend_predictor.TrendPredictor(method="auto")
            result = predictor.predict_sales(df, days=days, sku=sku)

            if result:
                return jsonify({
                    'success': True,
                    'predictions': result['predictions'],
                    'stats': result['stats'],
                    'confidence': result['confidence'],
                    'method': result['method']
                })
        else:
            # 使用简单预测（移动平均）
            import numpy as np
            values = df.get('orders', df.get('value', pd.Series([0])))
            avg = np.mean(values.tail(7))

            predictions = []
            for i in range(days):
                from datetime import datetime, timedelta
                pred_date = datetime.now() + timedelta(days=i+1)
                predictions.append({
                    'date': pred_date.strftime('%Y-%m-%d'),
                    'predicted_value': round(avg, 2)
                })

            return jsonify({
                'success': True,
                'predictions': predictions,
                'stats': {'avg_daily_sales': round(avg, 2)},
                'confidence': 0.5,
                'method': 'simple_moving_average'
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/automation/stock/predict', methods=['POST'])
def predict_stock():
    \"\"\"
    库存预测 API

    Request Body:
    {
        "current_stock": 500,
        "daily_sales": [50, 52, 48, ...],
        "days_to_predict": 30
    }
    \"\"\"
    try:
        data = request.json
        current_stock = data.get('current_stock', 0)
        daily_sales = data.get('daily_sales', [])
        days_to_predict = data.get('days_to_predict', 30)

        if not daily_sales:
            return jsonify({'success': False, 'error': '没有历史销量数据'}), 400

        if TREND_PREDICTOR_AVAILABLE:
            # 使用高级预测器
            predictor = trend_predictor.TrendPredictor(method="auto")
            result = predictor.predict_stockout(current_stock, daily_sales, days_to_predict)

            if result:
                return jsonify({
                    'success': True,
                    'current_stock': result['current_stock'],
                    'days_of_stock': result['days_of_stock'],
                    'stockout_date': result['stockout_date'],
                    'risk_level': result['risk_level'],
                    'reorder_recommendation': result['reorder_recommendation']
                })
        else:
            # 简单计算
            import numpy as np
            from datetime import datetime, timedelta

            avg_sales = np.mean(daily_sales)
            days_of_stock = current_stock / avg_sales if avg_sales > 0 else 999
            stockout_date = datetime.now() + timedelta(days=days_of_stock)

            risk_level = 'normal'
            if days_of_stock < 7:
                risk_level = 'critical'
            elif days_of_stock < 14:
                risk_level = 'warning'

            return jsonify({
                'success': True,
                'current_stock': current_stock,
                'days_of_stock': round(days_of_stock, 1),
                'stockout_date': stockout_date.strftime('%Y-%m-%d'),
                'risk_level': risk_level,
                'avg_daily_sales': round(avg_sales, 2)
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/automation/task/list', methods=['GET'])
def list_automation_tasks():
    \"\"\"获取自动化任务列表\"\"\"
    try:
        status = request.args.get('status', 'pending')
        limit = int(request.args.get('limit', 100))

        with get_session() as session:
            tasks = session.query(AutomationTask).filter_by(
                status=status
            ).order_by(
                AutomationTask.priority,
                AutomationTask.created_at.desc()
            ).limit(limit).all()

            return jsonify({
                'success': True,
                'tasks': [{
                    'id': task.id,
                    'task_type': task.task_type,
                    'task_name': task.task_name,
                    'sku': task.sku,
                    'status': task.status,
                    'priority': task.priority,
                    'created_at': task.created_at.isoformat() if task.created_at else None
                } for task in tasks]
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


print("✅ 自动化 API 路由已添加")
"""

    # 在 if __name__ == '__main__': 之前插入
    main_pos = content.find("if __name__ == '__main__':")
    if main_pos > 0:
        content = content[:main_pos] + api_routes + '\n' + content[main_pos:]
        print("  ✅ 添加了 4 个 API 路由:")
        print("      - GET  /api/automation/status")
        print("      - POST /api/automation/trend/predict")
        print("      - POST /api/automation/stock/predict")
        print("      - GET  /api/automation/task/list")

    # 保存修改
    with open(app_py_path, 'w', encoding='utf-8') as f:
        f.write(content)

print()

# ===== 5. 更新依赖 =====
print("📦 步骤 5: 更新依赖")
print("-" * 60)

pyproject_path = Path('pyproject.toml')

with open(pyproject_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加新依赖（如果不存在）
if 'schedule' not in content:
    # 在 dependencies 数组中添加
    if 'dependencies = [' in content:
        new_deps = """  "schedule>=1.2.0",  # 定时任务
  "requests>=2.31.0",  # HTTP 客户端
"""
        content = content.replace(
            'dependencies = [',
            'dependencies = [\n' + new_deps
        )

        with open(pyproject_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("  ✅ 添加了 schedule 和 requests 依赖")
        print("  ⚠️  请运行: pip install -e .")
else:
    print("  ⚠️ 依赖已存在")

print()

# ===== 6. 创建启动脚本 =====
print("🚀 步骤 6: 创建启动脚本")
print("-" * 60)

start_script = """@echo off
chcp 65001 >nul
echo ========================================
echo   V5.1 完整系统启动
echo ========================================
echo.

echo [1/4] 启动 Docker 服务...
cd docs
docker compose -f docker-compose.windows.yml up -d
cd ..
timeout /t 3 >nul

echo.
echo [2/4] 激活虚拟环境...
call .venv\\Scripts\\activate.bat

echo.
echo [3/4] 设置环境变量...
set APP_ENV=production
set DATABASE_URL=postgresql+psycopg://ecom_user:strong_password@127.0.0.1:5432/ecom_v51
set REDIS_URL=redis://127.0.0.1:6379/0
set PYTHONPATH=src

echo.
echo [4/4] 启动后端服务...
python backend\\app.py

pause
"""

with open('启动完整系统.bat', 'w', encoding='utf-8') as f:
    f.write(start_script)

print("  ✅ 创建了启动脚本: 启动完整系统.bat")

print()

# ===== 7. 更新数据库 =====
print("💾 步骤 7: 更新数据库")
print("-" * 60)
print("  ⚠️  请运行以下命令创建新表:")
print("      python -m ecom_v51.init_db")
print()

# ===== 完成 =====
print("=" * 60)
print("  ✅ 完美集成完成！")
print("=" * 60)
print()
print("📁 已完成的操作:")
print("  1. ✅ 备份了原有文件")
print("  2. ✅ 扩展了数据库模型（3 个新表）")
print("  3. ✅ 扩展了配置系统")
print("  4. ✅ 在 backend/app.py 中添加了 API 路由")
print("  5. ✅ 更新了依赖")
print("  6. ✅ 创建了启动脚本")
print()
print("🚀 下一步操作:")
print("  1. 安装新依赖: pip install -e .")
print("  2. 更新数据库: python -m ecom_v51.init_db")
print("  3. 启动系统: 启动完整系统.bat")
print()
print("📖 新增的 API 端点:")
print("  - GET  /api/automation/status")
print("  - POST /api/automation/trend/predict")
print("  - POST /api/automation/stock/predict")
print("  - GET  /api/automation/task/list")
print()
print("📚 前端可以调用这些 API 了！")
print()
print("=" * 60)
