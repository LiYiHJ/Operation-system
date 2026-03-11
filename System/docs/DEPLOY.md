# V5.1 跨境电商智能运营系统部署手册（详细版）

> 适用对象：开发、测试、运维。
>
> 目标：在 Linux 服务器上完成 V5.1 系统的可运行部署，包含 Python 服务、PostgreSQL、Redis、反向代理与进程托管。

---

## 1. 部署总览

当前仓库已经包含：

- 核心业务模块：`ingestion`、`profit_solver`、`war_room`、`strategy`
- 配置模块：`src/ecom_v51/config/*`
- SQLAlchemy 数据模型：`src/ecom_v51/db/models.py`
- CLI 入口：`v51-ops`

建议部署形态：

1. **开发环境**：本机 venv + 本机 PostgreSQL/Redis
2. **测试环境**：Docker Compose 拉起 PostgreSQL/Redis + Python 应用
3. **生产环境**：Nginx + Gunicorn + PostgreSQL + Redis（可选 Celery）

---

## 2. 环境要求

- OS: Ubuntu 22.04+（或兼容 Linux）
- Python: 3.11（建议）
- PostgreSQL: 14+
- Redis: 6+
- Nginx: 1.20+
- Gunicorn: 21+

建议硬件（初期）：

- 2 vCPU / 4GB RAM / 50GB SSD

---

## 3. 目录与用户规范（生产建议）

```bash
/opt/ecom_v51/
├── app/              # 代码目录
├── venv/             # Python 虚拟环境
├── logs/             # 应用日志
└── run/              # pid / sock 文件
```

建议创建专用系统用户：

```bash
sudo useradd -r -s /bin/bash ecom
sudo mkdir -p /opt/ecom_v51/{app,logs,run}
sudo chown -R ecom:ecom /opt/ecom_v51
```

---

## 4. 数据库部署（PostgreSQL）

### 4.1 创建数据库与账号

```sql
CREATE DATABASE ecom_v51;
CREATE USER ecom_user WITH PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE ecom_v51 TO ecom_user;
```

### 4.2 基础安全建议

- 仅允许内网访问 PostgreSQL 5432
- 禁止超级用户直连应用
- 开启定期备份（至少每日）

---

## 5. Redis 部署

安装后建议调整：

- `requirepass`（生产强制）
- `bind`（限制网段）
- `appendonly yes`

---

## 6. 代码部署步骤

以下以 `ecom` 用户执行：

```bash
cd /opt/ecom_v51/app
# 方式1：git clone 仓库
# 方式2：CI 产物同步

python3.11 -m venv /opt/ecom_v51/venv
source /opt/ecom_v51/venv/bin/activate
pip install -U pip
pip install -e .
```

> 若你们有内网私有镜像源，需将 `pip` 指向内部源进行安装。

---

## 7. 环境变量配置

建议在 `/opt/ecom_v51/app/.env` 或 systemd EnvironmentFile 中配置：

```bash
APP_ENV=production
APP_DEBUG=false
SECRET_KEY=replace_with_random_secret
TIMEZONE=Asia/Shanghai
DEFAULT_CURRENCY=RUB

DATABASE_URL=postgresql+psycopg://ecom_user:strong_password_here@127.0.0.1:5432/ecom_v51
REDIS_URL=redis://:redis_password@127.0.0.1:6379/0
CELERY_BROKER_URL=redis://:redis_password@127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://:redis_password@127.0.0.1:6379/2

SCHEDULER_HOURLY_ENABLED=true
SCHEDULER_DAILY_ENABLED=true
SCHEDULER_WEEKLY_ENABLED=true
```

配置字段来源见：`src/ecom_v51/config/settings.py`。

---

## 8. 初始化与自检

### 8.1 运行单元测试

```bash
cd /opt/ecom_v51/app
source /opt/ecom_v51/venv/bin/activate
pytest -q
```

### 8.2 CLI 冒烟

```bash
cat >/tmp/v51_input.json <<'JSON'
{
  "sku": "SKU-001",
  "impressions": 10000,
  "card_visits": 100,
  "add_to_cart": 5,
  "orders": 1,
  "ad_spend": 300,
  "ad_revenue": 200,
  "stock_total": 20,
  "days_of_supply": 5,
  "rating": 3.7,
  "return_rate": 0.2,
  "cancel_rate": 0.05,
  "sale_price": 100,
  "list_price": 120,
  "variable_rate_total": 0.35,
  "fixed_cost_total": 80
}
JSON

PYTHONPATH=src python -m ecom_v51.cli --input /tmp/v51_input.json --pretty
```

---

## 9. Gunicorn + systemd 部署（Web/API 服务）

> 当前仓库正逐步扩展 Flask 应用入口；本节给出标准托管模板，接入 `app` 对象后可直接启用。

### 9.1 systemd 文件示例

`/etc/systemd/system/ecom-v51.service`

```ini
[Unit]
Description=Ecom V5.1 Gunicorn Service
After=network.target

[Service]
User=ecom
Group=ecom
WorkingDirectory=/opt/ecom_v51/app
EnvironmentFile=/opt/ecom_v51/app/.env
ExecStart=/opt/ecom_v51/venv/bin/gunicorn \
  --workers 3 \
  --bind unix:/opt/ecom_v51/run/ecom-v51.sock \
  --timeout 120 \
  "backend.wsgi:app"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启停命令：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ecom-v51
sudo systemctl start ecom-v51
sudo systemctl status ecom-v51
```

---

## 10. Nginx 反向代理

`/etc/nginx/conf.d/ecom-v51.conf`

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100m;

    location / {
        include proxy_params;
        proxy_pass http://unix:/opt/ecom_v51/run/ecom-v51.sock;
    }

    location /static/ {
        alias /opt/ecom_v51/app/backend/web/static/;
        expires 7d;
    }
}
```

校验并重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 11. Docker Compose 部署建议

若采用容器化，建议拆分服务：

- `web`: Flask + Gunicorn
- `worker`: Celery worker
- `scheduler`: Celery beat 或 APScheduler
- `db`: PostgreSQL
- `redis`: Redis
- `nginx`: 反向代理

关键点：

- `DATABASE_URL` 使用容器内主机名（如 `db`）
- `REDIS_URL` 使用容器内主机名（如 `redis`）
- 挂载 `logs` 与 `uploads/raw/reports` 数据卷
- 配置 `healthcheck`

---

## 12. 数据库迁移策略（推荐）

建议引入 Alembic（如未接入可在下一阶段完成）：

- `alembic revision --autogenerate -m "init schema"`
- `alembic upgrade head`

发布规范：

1. 先备份
2. 低峰执行迁移
3. 回滚预案（`alembic downgrade -1`）

---

## 13. 日志与监控

### 13.1 日志

建议三类日志：

- 应用日志（API/页面）
- 导入日志（每批次含 `batch_id`）
- 任务日志（调度/策略生成/报告生成）

### 13.2 监控指标

- API 响应耗时 / 错误率
- 导入成功率 / 失败分类分布
- 利润计算任务耗时
- PostgreSQL 连接数与慢查询
- Redis 内存与连接数

---

## 14. 备份与容灾

### 14.1 PostgreSQL

- 全量：每日 1 次
- 增量/WAL：按 RPO 要求
- 备份至少保留 7~30 天

### 14.2 文件目录

至少备份：

- 上传原始文件目录
- 报告快照目录
- 配置目录（field mapping / thresholds）

---

## 15. 升级发布流程（建议）

1. 拉取新版本代码
2. 安装依赖
3. 执行测试
4. 执行 DB 迁移
5. 滚动重启 Gunicorn/Celery
6. 执行冒烟（导入 + 利润求解 + 单商品作战室）

示例：

```bash
cd /opt/ecom_v51/app
git pull
source /opt/ecom_v51/venv/bin/activate
pip install -e .
pytest -q
# alembic upgrade head
sudo systemctl restart ecom-v51
```

---

## 16. 常见故障排查

### 16.1 `ModuleNotFoundError: sqlalchemy`
- 原因：运行环境未安装依赖
- 处理：`pip install -e .` 或检查私有源可用性

### 16.2 `NO_PRIMARY_KEY`
- 原因：导入文件缺少 SKU/Артикул/offer_id/seller_sku
- 处理：在映射页手动指定主键字段

### 16.3 保本价异常（极大/无穷）
- 原因：`V >= 1`
- 处理：检查费率配置总和（佣金、税费、广告费率、汇损）

### 16.4 Gunicorn 启动失败
- 检查 `WorkingDirectory`、`EnvironmentFile`、`backend.wsgi:app` 路径
- 查看 `journalctl -u ecom-v51 -n 200`

---

## 17. 验收清单（上线前）

- [ ] `pytest -q` 通过
- [ ] CLI 冒烟通过
- [ ] PostgreSQL 与 Redis 连通
- [ ] 环境变量齐全
- [ ] Nginx 反代正常
- [ ] 导入错误分类可输出
- [ ] 利润中心公式计算正确
- [ ] 备份任务已配置

---

## 18. 后续阶段衔接

本手册覆盖第一阶段“可部署基础”。
后续建议在第二阶段补齐：

- Flask Web 页面完整路由部署细节
- Celery/Beat 生产参数模板
- Docker Compose 实际文件与一键脚本
- CI/CD（GitHub Actions/GitLab CI）自动发布流程
