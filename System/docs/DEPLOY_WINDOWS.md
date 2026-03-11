# V5.1 跨境电商智能运营系统 Windows 部署手册

> 目标：在 Windows 环境稳定运行 V5.1 后端（当前仓库阶段：核心引擎 + CLI + 数据模型 +文档）。

---

## 1. 支持范围与部署方式

Windows 推荐两种方式：

1. **本机原生部署（开发/测试）**
   - Python venv
   - PostgreSQL（Windows 安装包）
   - Redis（建议 Docker）
2. **Docker Desktop 部署（更推荐）**
   - 使用容器跑 PostgreSQL、Redis、Python 服务

> 生产长期建议 Linux；若必须 Windows 生产，建议至少使用 Docker + 反向代理并配合 NSSM/WinSW 做进程托管。

---

## 2. 先决条件

- Windows 10/11 或 Windows Server 2019+
- PowerShell 5+（建议 PowerShell 7）
- Python 3.11
- Git
- PostgreSQL 14+
- Docker Desktop（可选但推荐）

检查命令：

```powershell
python --version
git --version
docker --version
```

---

## 3. 本机原生部署（PowerShell）

## 3.1 获取代码并创建虚拟环境

```powershell
cd D:\workspace
git clone <your_repo_url> LiYiHJ
cd .\LiYiHJ

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e .
```

## 3.2 配置环境变量（当前会话）

```powershell
$env:APP_ENV = "production"
$env:APP_DEBUG = "false"
$env:SECRET_KEY = "replace_with_strong_secret"
$env:TIMEZONE = "Asia/Shanghai"
$env:DEFAULT_CURRENCY = "RUB"

$env:DATABASE_URL = "postgresql+psycopg://ecom_user:strong_password@127.0.0.1:5432/ecom_v51"
$env:REDIS_URL = "redis://127.0.0.1:6379/0"
$env:CELERY_BROKER_URL = "redis://127.0.0.1:6379/1"
$env:CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/2"
```

> 字段来源：`src/ecom_v51/config/settings.py`。

## 3.3 安装 PostgreSQL 并初始化

使用 PostgreSQL 官方安装器后，在 SQL Shell / pgAdmin 执行：

```sql
CREATE DATABASE ecom_v51;
CREATE USER ecom_user WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE ecom_v51 TO ecom_user;
```

---

## 4. Redis 在 Windows 的建议方案

Redis 官方不再维护 Windows 原生版本，建议：

### 方案 A（推荐）Docker 单独启动 Redis

```powershell
docker run -d --name ecom-redis -p 6379:6379 redis:7
```

### 方案 B WSL2 内运行 Redis

在 WSL Ubuntu 安装 Redis，并映射到 Windows 主机。

---

## 5. Docker Desktop 一体化部署（推荐）

虽然当前仓库未提交完整 `docker-compose.yml`，你可以先用如下模板在项目根目录创建 `docker-compose.windows.yml`：

```yaml
version: "3.9"
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ecom_v51
      POSTGRES_USER: ecom_user
      POSTGRES_PASSWORD: strong_password
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  pg_data:
```

启动：

```powershell
docker compose -f .\docker-compose.windows.yml up -d
```

---

## 6. 运行与验证

## 6.1 测试

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
```

## 6.2 CLI 冒烟

```powershell
@'
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
'@ | Set-Content -Encoding utf8 .\input.json

$env:PYTHONPATH = "src"
python -m ecom_v51.cli --input .\input.json --pretty
```

---

## 7. Windows 服务化建议

当前阶段（无完整 Flask Web 入口）建议先用 CLI / 任务脚本。
后续接入 Flask app 后：

- 用 **Waitress** 或 **Gunicorn in WSL** 托管 Web
- 用 **NSSM**（Non-Sucking Service Manager）把 Python 进程注册为 Windows Service

NSSM 示例：

```powershell
nssm install ecom-v51 "D:\workspace\LiYiHJ\.venv\Scripts\python.exe" "-m backend.app"
nssm start ecom-v51
```

---

## 8. 常见问题（Windows）

### 8.1 PowerShell 执行策略报错

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 8.2 `ModuleNotFoundError: ecom_v51`

- 确认已 `pip install -e .`
- 或设置 `PYTHONPATH=src`

### 8.3 PostgreSQL 连接失败

- 检查 `DATABASE_URL`
- 检查服务是否启动：`Get-Service *postgres*`
- 检查 5432 端口占用：`netstat -ano | findstr 5432`

### 8.4 Docker Desktop 启动慢或无法拉取镜像

- 检查代理
- 切换镜像源
- 确认 WSL2 正常

---

## 9. Windows 上线前检查清单

- [ ] Python 3.11、venv、依赖安装完成
- [ ] PostgreSQL 已建库与账号授权
- [ ] Redis 可连接（Docker/WSL）
- [ ] 环境变量配置正确
- [ ] `pytest -q` 通过
- [ ] CLI 冒烟通过
- [ ] 日志目录与备份策略已准备

---

## 10. 与现有文档关系

- Linux 部署：`docs/DEPLOY.md`
- Windows 部署（本手册）：`docs/DEPLOY_WINDOWS.md`
- 第一阶段架构：`docs/PHASE1_ARCHITECTURE.md`
- 
