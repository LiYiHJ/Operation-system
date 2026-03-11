# V5.1 第一阶段架构设计

## 1. 项目目录结构

```text
ecom_v51/
├── docs/
│   └── PHASE1_ARCHITECTURE.md
├── src/
│   └── ecom_v51/
│       ├── __init__.py
│       ├── cli.py
│       ├── ingestion.py
│       ├── models.py
│       ├── profit_solver.py
│       ├── strategy.py
│       ├── war_room.py
│       ├── config/
│       │   ├── settings.py
│       │   ├── field_mapping.json
│       │   ├── thresholds.json
│       │   ├── metrics.json
│       │   └── pipeline_rules.json
│       └── db/
│           ├── __init__.py
│           ├── base.py
│           └── models.py
├── tests/
│   ├── test_engine.py
│   └── test_v51_system.py
├── README.md
└── pyproject.toml
```

## 2. 模块职责说明

### 2.1 导入中心（Ingestion）
- 负责文件识别、平台识别、表头定位、字段映射、清洗、主键识别、导入校验、诊断输出。
- 核心目标：优先解决 Ozon 俄语字段、表头不固定、数字清洗与主键缺失提示。

### 2.2 利润中心（Profit Center）
- 使用统一变量费率 `V` 与固定成本 `F`。
- 统一求解 `真净利润 = 售价 × (1 - V) - F`。
- 支持保本价、目标净利润反推、目标净利率反推、目标 ROI 反推、折扣模拟。

### 2.3 商品中心与单商品作战室（War Room）
- 输出漏斗指标、利润状态、风险与策略组合。
- 结果可直接下沉到策略任务中心。

### 2.4 数据仓库（Warehouse）
- 使用 SQLAlchemy 定义维表/事实表/域表/系统表。
- 所有导入与事实写入要求带 `batch_id`，支持追溯。

### 2.5 配置中心（Config）
- 字段映射、阈值、指标定义、导入流水线规则独立配置。
- 通过 `settings.py` 统一管理数据库、Redis、调度、部署环境变量。

## 3. 数据库模型设计（SQLAlchemy）

### 3.1 维表
- `dim_platform`
- `dim_shop`
- `dim_category`
- `dim_product`
- `dim_sku`
- `dim_campaign`
- `dim_date`
- `fx_rate_daily`

### 3.2 事实表
- `fact_sku_daily`
- `fact_ads_daily`
- `fact_inventory_daily`
- `fact_orders_daily`
- `fact_reviews_daily`
- `fact_profit_snapshot`

### 3.3 价格利润域表
- `sku_price_master`
- `sku_cost_master`
- `price_change_log`
- `competitor_price_snapshot`
- `promotion_event`
- `profit_assumption_profile`
- `profit_allocation_rule`

### 3.4 系统表
- `import_batch`
- `import_batch_file`
- `import_error_log`
- `mapping_feedback`
- `strategy_task`
- `alert_event`
- `report_snapshot`

## 4. 配置文件设计

### 4.1 settings.py
- 环境：`APP_ENV`、`APP_DEBUG`。
- 数据库：`DATABASE_URL`（PostgreSQL）。
- Redis/Celery：`REDIS_URL`、`CELERY_BROKER_URL`、`CELERY_RESULT_BACKEND`。
- 调度：每小时/每日/每周任务开关。
- Web：`SECRET_KEY`、`TIMEZONE`、`DEFAULT_CURRENCY`。

### 4.2 field_mapping.json
- 原始字段 -> 标准字段映射。
- 覆盖俄语/中文/英文字段。

### 4.3 thresholds.json
- 风险、转化、库存、广告、评分阈值。

### 4.4 metrics.json
- 指标公式、展示口径与维度级别（店铺/类目/SKU）。

### 4.5 pipeline_rules.json
- 导入管道规则：扫描前20行、多级表头、主键优先级、错误分类。
