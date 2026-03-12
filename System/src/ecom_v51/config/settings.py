"""
配置管理
使用环境变量配置
"""

import os
from pathlib import Path


class Settings:
    """配置类"""
    
    # ========== 文件路径 ==========
    BASE_DIR = Path(__file__).parent.parent.parent.parent
    
    # ========== 应用配置 ==========
    app_env = os.getenv('APP_ENV', 'development')
    APP_ENV = app_env  # 别名
    
    debug = os.getenv('APP_DEBUG', 'true' if app_env != 'production' else 'false').lower() == 'true'
    DEBUG = debug  # 别名
    
    secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SECRET_KEY = secret_key  # 别名

    allow_seed_users = os.getenv('ALLOW_SEED_USERS', 'true' if app_env != 'production' else 'false').lower() == 'true'
    ALLOW_SEED_USERS = allow_seed_users
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    DATA_FOLDER = BASE_DIR / 'data'
    LOG_FOLDER = BASE_DIR / 'logs'
    
    # ========== 应用配置 ==========
    # （已在上方定义，这里删除重复）
    
    # ========== 时区和货币 ==========
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Shanghai')
    DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'RUB')
    
    # ========== 数据库配置 ==========
    # 优先使用环境变量，否则使用SQLite（开发环境）
    database_url = os.getenv(
        'DATABASE_URL',
        f'sqlite:///{BASE_DIR / "data" / "ecom_v51.db"}'  # SQLite开发环境
        # 'postgresql+psycopg://ecom_user:strong_password@127.0.0.1:5432/ecom_v51'  # 生产环境
    )
    
    # 兼容属性名（db/session.py 使用 database_url）
    DATABASE_URL = database_url
    database_url = database_url  # 别名
    
    # ========== Redis配置 ==========
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
    
    # ========== Celery配置 ==========
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/1')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/2')
    
    # 创建必要的目录
    def __init__(self):
        self.UPLOAD_FOLDER.mkdir(exist_ok=True)
        self.DATA_FOLDER.mkdir(exist_ok=True)
        self.LOG_FOLDER.mkdir(exist_ok=True)
    
    # ========== 配置文件路径 ==========
    FIELD_MAPPING_FILE = BASE_DIR / 'src' / 'ecom_v51' / 'config' / 'field_mapping.json'
    THRESHOLDS_FILE = BASE_DIR / 'src' / 'ecom_v51' / 'config' / 'thresholds.json'
    METRICS_FILE = BASE_DIR / 'src' / 'ecom_v51' / 'config' / 'metrics.json'
    
    # ========== API配置 ==========
    API_PREFIX = '/api'
    API_VERSION = 'v1'
    
    # ========== 分页配置 ==========
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # ========== 告警配置 ==========
    ALERT_EMAIL_RECIPIENTS = os.getenv('ALERT_EMAIL_RECIPIENTS', '').split(',')
    ALERT_WEBHOOK_URL = os.getenv('ALERT_WEBHOOK_URL')
    
    def __repr__(self):
        return f"<Settings(env={self.APP_ENV}, db={self.DATABASE_URL[:30]}...)>"


# 全局配置实例
settings = Settings()
