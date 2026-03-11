"""
自动化任务调度器
支持定时执行分析、通知、自动执行策略等任务
"""
import schedule
import time
import threading
from typing import Callable, Dict, List, Optional
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    任务调度器
    
    基于 schedule 库实现定时任务
    """
    
    def __init__(self):
        """初始化调度器"""
        self.tasks: Dict[str, Dict] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def add_task(
        self,
        task_id: str,
        task_func: Callable,
        schedule_type: str,
        schedule_time: str = None,
        **kwargs
    ):
        """
        添加定时任务
        
        Args:
            task_id: 任务 ID
            task_func: 任务函数
            schedule_type: 调度类型
                - "daily": 每天
                - "hourly": 每小时
                - "interval": 间隔（分钟）
                - "monday/tuesday/...": 每周某天
            schedule_time: 执行时间（如 "08:00"）
            **kwargs: 其他参数
        """
        task_config = {
            "func": task_func,
            "type": schedule_type,
            "time": schedule_time,
            "kwargs": kwargs,
            "last_run": None,
            "next_run": None,
            "status": "active"
        }
        
        self.tasks[task_id] = task_config
        
        # 注册到 schedule
        self._register_task(task_id)
        
        logger.info(f"✅ 任务已添加: {task_id} ({schedule_type} at {schedule_time})")
    
    def _register_task(self, task_id: str):
        """注册任务到 schedule"""
        task = self.tasks[task_id]
        func = task["func"]
        kwargs = task["kwargs"]
        
        def task_wrapper():
            """任务包装器"""
            try:
                logger.info(f"🚀 开始执行任务: {task_id}")
                start_time = time.time()
                
                # 执行任务
                result = func(**kwargs)
                
                elapsed = time.time() - start_time
                logger.info(f"✅ 任务执行完成: {task_id} (耗时: {elapsed:.2f}秒)")
                
                # 更新任务状态
                self.tasks[task_id]["last_run"] = datetime.now().isoformat()
                
                return result
                
            except Exception as e:
                logger.error(f"❌ 任务执行失败: {task_id} - {e}")
                return None
        
        # 根据调度类型注册
        schedule_type = task["type"]
        schedule_time = task["time"]
        
        if schedule_type == "daily":
            schedule.every().day.at(schedule_time).do(task_wrapper)
        
        elif schedule_type == "hourly":
            schedule.every().hour.do(task_wrapper)
        
        elif schedule_type == "interval":
            minutes = int(schedule_time)
            schedule.every(minutes).minutes.do(task_wrapper)
        
        elif schedule_type == "monday":
            schedule.every().monday.at(schedule_time).do(task_wrapper)
        elif schedule_type == "tuesday":
            schedule.every().tuesday.at(schedule_time).do(task_wrapper)
        elif schedule_type == "wednesday":
            schedule.every().wednesday.at(schedule_time).do(task_wrapper)
        elif schedule_type == "thursday":
            schedule.every().thursday.at(schedule_time).do(task_wrapper)
        elif schedule_type == "friday":
            schedule.every().friday.at(schedule_time).do(task_wrapper)
        elif schedule_type == "saturday":
            schedule.every().saturday.at(schedule_time).do(task_wrapper)
        elif schedule_type == "sunday":
            schedule.every().sunday.at(schedule_time).do(task_wrapper)
        
        else:
            logger.warning(f"未知的调度类型: {schedule_type}")
    
    def remove_task(self, task_id: str):
        """
        移除任务
        
        Args:
            task_id: 任务 ID
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"🗑️ 任务已移除: {task_id}")
    
    def start(self, blocking: bool = True):
        """
        启动调度器
        
        Args:
            blocking: 是否阻塞主线程
        """
        if self.running:
            logger.warning("调度器已在运行")
            return
        
        self.running = True
        
        if blocking:
            self._run_loop()
        else:
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            logger.info("🚀 调度器已启动（后台模式）")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 调度器已停止")
    
    def _run_loop(self):
        """运行循环"""
        logger.info("🚀 调度器已启动")
        
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def list_tasks(self) -> List[Dict]:
        """
        列出所有任务
        
        Returns:
            任务列表
        """
        return [
            {
                "task_id": task_id,
                "type": task["type"],
                "time": task["time"],
                "last_run": task["last_run"],
                "status": task["status"]
            }
            for task_id, task in self.tasks.items()
        ]


class OzonAutomationTasks:
    """
    Ozon 自动化任务集合
    """
    
    def __init__(
        self,
        data_dir: str = None,
        notification_config: Dict = None
    ):
        """
        初始化自动化任务
        
        Args:
            data_dir: 数据目录
            notification_config: 通知配置
        """
        self.data_dir = Path(data_dir) if data_dir else Path("C:/Operation-system/System/data")
        self.notification_config = notification_config or {}
        
        # 导入依赖
        from .batch_decision_engine import BatchDecisionEngine
        from .notification_service import EmailService, TelegramService
        
        self.decision_engine = BatchDecisionEngine()
        self.email_service = None
        self.telegram_service = None
        
        # 初始化通知服务
        if notification_config:
            if notification_config.get("email", {}).get("enabled"):
                self.email_service = EmailService(**notification_config["email"])
            
            if notification_config.get("telegram", {}).get("enabled"):
                self.telegram_service = TelegramService(**notification_config["telegram"])
    
    def task_morning_check(self):
        """
        任务：晨间巡检（08:00）
        
        检查项：
        1. 读取最新数据
        2. 检查订单量
        3. 检查库存
        4. 检查退货
        5. 发送报告
        """
        logger.info("🌅 执行晨间巡检...")
        
        try:
            # 1. 读取最新数据
            latest_data = self._load_latest_data()
            
            if not latest_data:
                logger.warning("未找到最新数据")
                return
            
            # 2. 分析数据
            report = self.decision_engine.analyze_skus(
                df=latest_data,
                shop_name="YunElite"
            )
            
            # 3. 生成晨间简报
            morning_report = {
                "health_score": self._calculate_health_score(report),
                "total_orders": latest_data.get("orders", {}).get("total", 0),
                "fbo_orders": latest_data.get("orders", {}).get("fbo", 0),
                "fbs_orders": latest_data.get("orders", {}).get("fbs", 0),
                "total_revenue": latest_data.get("revenue", 0),
                "p0_count": report.summary.get("P0", 0),
                "p1_count": report.summary.get("P1", 0),
                "p2_count": report.summary.get("P2", 0),
                "alerts": report.urgent_actions[:3]  # 只发送前 3 个紧急问题
            }
            
            # 4. 发送通知
            if report.summary.get("P0", 0) > 0:
                # 有 P0 问题，发送紧急告警
                self._send_p0_alert(report.urgent_actions)
            
            # 5. 发送日报
            self._send_daily_report(morning_report)
            
            logger.info("✅ 晨间巡检完成")
            
        except Exception as e:
            logger.error(f"❌ 晨间巡检失败: {e}")
    
    def task_noon_check(self):
        """
        任务：午间巡检（12:00）
        
        检查项：
        1. 对比上午订单量
        2. 检查库存消耗速度
        3. 检查退货
        4. 发送午间简报
        """
        logger.info("☀️ 执行午间巡检...")
        
        try:
            # 实现类似晨间巡检的逻辑
            # ...
            
            logger.info("✅ 午间巡检完成")
            
        except Exception as e:
            logger.error(f"❌ 午间巡检失败: {e}")
    
    def task_evening_check(self):
        """
        任务：日终巡检（16:00）
        
        检查项：
        1. 汇总全天数据
        2. 生成日终报告
        3. 识别畅销/滞销 SKU
        4. 发送给 CEO
        """
        logger.info("🌆 执行日终巡检...")
        
        try:
            # 实现类似逻辑
            # ...
            
            logger.info("✅ 日终巡检完成")
            
        except Exception as e:
            logger.error(f"❌ 日终巡检失败: {e}")
    
    def task_auto_execute_p0(self):
        """
        任务：自动执行 P0 策略
        
        自动执行可执行的 P0 策略（如自动调价、暂停广告）
        """
        logger.info("🤖 自动执行 P0 策略...")
        
        try:
            # 1. 读取最新数据
            latest_data = self._load_latest_data()
            
            # 2. 分析策略
            report = self.decision_engine.analyze_skus(latest_data, "YunElite")
            
            # 3. 筛选可自动执行的 P0 策略
            auto_executable_tasks = [
                task for task in report.tasks
                if task.get("priority") == "P0" and task.get("auto_executable")
            ]
            
            # 4. 执行策略
            executed_count = 0
            for task in auto_executable_tasks:
                result = self._execute_task(task)
                if result:
                    executed_count += 1
            
            logger.info(f"✅ 自动执行完成: {executed_count}/{len(auto_executable_tasks)}")
            
        except Exception as e:
            logger.error(f"❌ 自动执行失败: {e}")
    
    def task_data_sync(self):
        """
        任务：数据同步
        
        从 Ozon API 拉取最新数据
        """
        logger.info("🔄 同步数据...")
        
        try:
            # 导入 Ozon API 客户端
            from .ozon_api_client import get_ozon_client
            
            client = get_ozon_client("YunElite")
            
            if not client:
                logger.warning("Ozon API 未配置，跳过数据同步")
                return
            
            # 拉取数据
            products = client.get_products()
            orders = client.get_orders()
            analytics = client.get_analytics(["day", "sku"])
            
            # 保存数据
            self._save_data(products, orders, analytics)
            
            logger.info("✅ 数据同步完成")
            
        except Exception as e:
            logger.error(f"❌ 数据同步失败: {e}")
    
    # ===== 辅助方法 =====
    
    def _load_latest_data(self):
        """加载最新数据"""
        import pandas as pd
        
        # 模拟数据（实际应从文件读取）
        latest_file = self.data_dir / "processed" / "latest.json"
        
        if latest_file.exists():
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def _calculate_health_score(self, report) -> int:
        """计算健康度评分"""
        total = report.total_skus
        p0 = report.summary.get("P0", 0)
        p1 = report.summary.get("P1", 0)
        p2 = report.summary.get("P2", 0)
        p3 = report.summary.get("P3", 0)
        
        score = 100 - (p0 * 10 + p1 * 5 + p2 * 2 + p3 * 1)
        return max(0, score)
    
    def _send_p0_alert(self, alerts: List[str]):
        """发送 P0 告警"""
        if self.telegram_service:
            self.telegram_service.send_alert_message("P0", [
                {"title": alert, "issue": alert}
                for alert in alerts
            ])
        
        if self.email_service:
            recipients = self.notification_config.get("email", {}).get("recipients", [])
            for recipient in recipients:
                self.email_service.send_alert_email(
                    to=recipient,
                    alert_type="P0",
                    alerts=[{"title": alert} for alert in alerts]
                )
    
    def _send_daily_report(self, report_data: Dict):
        """发送日报"""
        if self.telegram_service:
            self.telegram_service.send_daily_report(report_data)
    
    def _execute_task(self, task: Dict) -> bool:
        """执行单个任务"""
        # 实现具体的执行逻辑
        # 如：调价、暂停广告、发送补货邮件等
        pass
    
    def _save_data(self, products, orders, analytics):
        """保存数据"""
        # 实现数据保存逻辑
        pass


# ===== 创建默认调度器 =====

def create_default_scheduler(
    data_dir: str = None,
    notification_config: Dict = None
) -> TaskScheduler:
    """
    创建默认调度器
    
    Args:
        data_dir: 数据目录
        notification_config: 通知配置
    
    Returns:
        配置好的调度器
    """
    scheduler = TaskScheduler()
    automation = OzonAutomationTasks(data_dir, notification_config)
    
    # 添加定时任务
    scheduler.add_task(
        task_id="morning_check",
        task_func=automation.task_morning_check,
        schedule_type="daily",
        schedule_time="08:00"
    )
    
    scheduler.add_task(
        task_id="noon_check",
        task_func=automation.task_noon_check,
        schedule_type="daily",
        schedule_time="12:00"
    )
    
    scheduler.add_task(
        task_id="evening_check",
        task_func=automation.task_evening_check,
        schedule_type="daily",
        schedule_time="16:00"
    )
    
    scheduler.add_task(
        task_id="auto_execute_p0",
        task_func=automation.task_auto_execute_p0,
        schedule_type="interval",
        schedule_time="30"  # 每 30 分钟检查一次
    )
    
    scheduler.add_task(
        task_id="data_sync",
        task_func=automation.task_data_sync,
        schedule_type="interval",
        schedule_time="60"  # 每小时同步一次
    )
    
    return scheduler


# ===== 示例用法 =====

if __name__ == "__main__":
    # 创建调度器
    scheduler = create_default_scheduler()
    
    # 查看所有任务
    print("📋 已注册的任务:")
    for task in scheduler.list_tasks():
        print(f"  - {task['task_id']}: {task['type']} at {task['time']}")
    
    # 启动调度器（阻塞模式）
    print("\n🚀 启动调度器...")
    scheduler.start(blocking=True)
