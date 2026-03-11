"""
V5.1 数据库模型 - SQLAlchemy ORM
对应 models.py 的 dataclass，提供数据持久化
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# ========== 维表 ==========

class DimPlatform(Base):
    """平台维度表"""
    __tablename__ = 'dim_platform'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)  # ozon, amazon, ebay
    name = Column(String(100))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DimShop(Base):
    """店铺维度表"""
    __tablename__ = 'dim_shop'
    
    id = Column(Integer, primary_key=True)
    shop_code = Column(String(50), unique=True, nullable=False)  # YunElite, ALORA, YunYi
    shop_name = Column(String(100))
    platform_id = Column(Integer, ForeignKey('dim_platform.id'))
    client_id = Column(String(50))
    api_key = Column(String(200))  # 加密存储
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    platform = relationship("DimPlatform")
    

class DimCategory(Base):
    """类目维度表"""
    __tablename__ = 'dim_category'
    
    id = Column(Integer, primary_key=True)
    category_code = Column(String(100), unique=True)
    category_name = Column(String(200))
    parent_id = Column(Integer, ForeignKey('dim_category.id'), nullable=True)
    level = Column(Integer)  # 1, 2, 3级类目
    platform_id = Column(Integer, ForeignKey('dim_platform.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    parent = relationship("DimCategory", remote_side=[id])


class DimProduct(Base):
    """产品维度表"""
    __tablename__ = 'dim_product'
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    product_name = Column(String(500))
    category_id = Column(Integer, ForeignKey('dim_category.id'))
    shop_id = Column(Integer, ForeignKey('dim_shop.id'))
    brand = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    category = relationship("DimCategory")
    shop = relationship("DimShop")


# ========== 事实表 ==========

class FactSkuDaily(Base):
    """SKU每日事实表"""
    __tablename__ = 'fact_sku_daily'
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(100), nullable=False, index=True)
    shop_id = Column(Integer, ForeignKey('dim_shop.id'))
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    
    # 流量数据
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    card_visits = Column(Integer, default=0)  # 商品页访问
    
    # 转化数据
    add_to_cart = Column(Integer, default=0)
    orders = Column(Integer, default=0)
    ordered_units = Column(Integer, default=0)  # 订单商品数
    
    # 销售数据
    revenue = Column(Float, default=0.0)  # 销售额
    order_amount = Column(Float, default=0.0)  # 订单金额
    
    # 价格数据
    sale_price = Column(Float)
    list_price = Column(Float)
    market_price = Column(Float)
    price_index = Column(Float)
    discount = Column(Float)
    
    # 库存数据
    stock_total = Column(Integer, default=0)
    stock_fbo = Column(Integer, default=0)
    stock_fbs = Column(Integer, default=0)
    days_of_supply = Column(Float)
    
    # 评价数据
    rating = Column(Float)
    reviews_count = Column(Integer, default=0)
    return_rate = Column(Float)
    cancel_rate = Column(Float)
    
    # 成本数据
    cost_price = Column(Float)
    commission_rate = Column(Float)
    logistics_cost = Column(Float)
    variable_rate_total = Column(Float)  # 总变动费率
    fixed_cost_total = Column(Float)  # 总固定成本
    
    # 利润数据（由 profit_solver 计算）
    net_profit = Column(Float)
    net_margin = Column(Float)
    break_even_price = Column(Float)
    
    # 元数据
    batch_id = Column(String(50), index=True)  # 批次ID
    data_source = Column(String(20))  # api, excel
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_sku_date', 'sku', 'date'),
        Index('idx_shop_date', 'shop_id', 'date'),
    )
    
    shop = relationship("DimShop")


class FactAdsDaily(Base):
    """广告每日事实表"""
    __tablename__ = 'fact_ads_daily'
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(100), nullable=False, index=True)
    shop_id = Column(Integer, ForeignKey('dim_shop.id'))
    date = Column(String(10), nullable=False, index=True)
    
    # 广告数据
    campaign_id = Column(String(50))
    campaign_name = Column(String(200))
    ad_group_id = Column(String(50))
    
    # 广告指标
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    ctr = Column(Float)  # 点击率
    cpc = Column(Float)  # 单次点击成本
    cpm = Column(Float)  # 千次展示成本
    
    # 广告花费和收入
    ad_spend = Column(Float, default=0.0)
    ad_revenue = Column(Float, default=0.0)
    roas = Column(Float)  # ROAS = ad_revenue / ad_spend
    
    # 转化数据
    ad_orders = Column(Integer, default=0)
    ad_units = Column(Integer, default=0)
    conversion_rate = Column(Float)
    
    # 元数据
    batch_id = Column(String(50), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_sku_date_ads', 'sku', 'date'),
    )
    
    shop = relationship("DimShop")


# ========== 系统表 ==========

class ImportBatch(Base):
    """导入批次表"""
    __tablename__ = 'import_batch'
    
    id = Column(Integer, primary_key=True)
    batch_id = Column(String(50), unique=True, nullable=False)
    shop_id = Column(Integer, ForeignKey('dim_shop.id'))
    
    # 文件信息
    file_name = Column(String(200))
    file_size = Column(Integer)
    file_path = Column(String(500))
    
    # 导入诊断
    platform = Column(String(50))
    header_row = Column(Integer)
    total_rows = Column(Integer)
    total_columns = Column(Integer)
    
    # 字段映射
    mapped_fields = Column(Integer)
    unmapped_fields = Column(Integer)
    field_mappings = Column(Text)  # JSON存储字段映射
    
    # 导入结果
    status = Column(String(20))  # success, partial, failed
    success_rows = Column(Integer)
    error_rows = Column(Integer)
    diagnosis = Column(Text)  # JSON存储诊断结果
    
    # 元数据
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    shop = relationship("DimShop")


class StrategyTask(Base):
    """策略任务表"""
    __tablename__ = 'strategy_task'
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(100), nullable=False, index=True)
    shop_id = Column(Integer, ForeignKey('dim_shop.id'))
    date = Column(String(10), index=True)
    
    # 策略信息
    strategy_type = Column(String(50))  # pricing, ads, inventory, conversion, risk_control
    level = Column(String(20))  # shop, category, sku
    priority = Column(String(5))  # P0, P1, P2, P3
    issue_summary = Column(Text)
    recommended_action = Column(Text)
    observation_metrics = Column(Text)  # JSON存储观察指标
    
    # 状态
    status = Column(String(20), default='pending')  # pending, in_progress, completed, cancelled
    assigned_to = Column(String(100))
    
    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    shop = relationship("DimShop")


class AlertEvent(Base):
    """告警事件表"""
    __tablename__ = 'alert_event'
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(100), index=True)
    shop_id = Column(Integer, ForeignKey('dim_shop.id'))
    
    # 告警信息
    alert_type = Column(String(50))  # inventory_critical, price_high, rating_low, etc.
    priority = Column(String(5))  # P0, P1, P2
    title = Column(String(200))
    message = Column(Text)
    
    # 状态
    status = Column(String(20), default='active')  # active, acknowledged, resolved
    acknowledged_by = Column(String(100))
    resolved_by = Column(String(100))
    
    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    shop = relationship("DimShop")


# ========== 配置表 ==========

class ProfitAssumptionProfile(Base):
    """利润假设配置表"""
    __tablename__ = 'profit_assumption_profile'
    
    id = Column(Integer, primary_key=True)
    profile_name = Column(String(100), unique=True, nullable=False)
    
    # 利润参数
    variable_rate_total = Column(Float, nullable=False)  # 总变动费率
    fixed_cost_total = Column(Float, nullable=False)  # 总固定成本
    commission_rate = Column(Float)  # 佣金率
    logistics_cost = Column(Float)  # 物流成本
    other_costs = Column(Float)  # 其他成本
    
    # 元数据
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ========== 辅助函数 ==========

def init_db(engine):
    """初始化数据库（创建所有表）"""
    Base.metadata.create_all(engine)


def drop_db(engine):
    """删除所有表（仅用于开发/测试）"""
    Base.metadata.drop_all(engine)
