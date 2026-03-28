# FastAPI 首批真实工程文件（MVP）

本目录是当前新项目的 FastAPI 首批可落地工程骨架，服务边界遵循：

- BigQuery：只读分析查询
- PostgreSQL：规则、预警、任务、复盘主写
- FastAPI：统一应用服务层，承接页面、任务流转与查询聚合

## 当前已落地模块

- `app/main.py`：应用入口、路由注册、middleware、异常处理
- `app/api/health.py`：健康检查
- `app/api/dashboard.py`：老板首页 / 运营首页摘要
- `app/api/task.py`：任务创建、列表、详情、状态更新、转派、关闭
- `app/services/dashboard_service.py`：BigQuery 查询聚合
- `app/services/task_service.py`：任务状态机与业务校验
- `app/repositories/pg_task_repo.py`：PostgreSQL 读写
- `app/repositories/bq_queries/*.sql`：BigQuery 查询模板
- `app/utils/response.py`：统一返回结构
- `tools/smoke_test.py`：无需真正连库的冒烟脚本

## 环境约定

- Python：>= 3.11
- BigQuery 认证：默认使用 ADC（`gcloud auth application-default login`），不依赖本地 service-account keyfile
- BigQuery location：`US`
- PostgreSQL：沿用当前 `decision_system` 应用库

## 安装

```powershell
Set-Location "D:\AAA\Decision_System"
.\.venv\Scripts\Activate.ps1
Set-Location ".\app_service\fastapi_app"
python -m pip install -e ".[dev]"
```

## 启动

```powershell
Set-Location "D:\AAA\Decision_System"
.\.venv\Scripts\Activate.ps1
Set-Location ".\app_service\fastapi_app"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 冒烟验证

```powershell
Set-Location "D:\AAA\Decision_System"
.\.venv\Scripts\Activate.ps1
Set-Location ".\app_service\fastapi_app"
python ".\tools\smoke_test.py"
```

## 当前接口清单

- `GET /api/v1/health`
- `GET /api/v1/dashboard/ceo/summary`
- `GET /api/v1/dashboard/ops/summary`
- `POST /api/v1/tasks`
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `POST /api/v1/tasks/{task_id}/status`
- `POST /api/v1/tasks/{task_id}/reassign`
- `POST /api/v1/tasks/{task_id}/close`

## 下一步建议

1. 将 `dashboard` 查询与当前 dbt mart 字段逐条联调
2. 将 `task` / `alert` / `review` 三张应用表联动打通
3. 接入 `auth` / `metadata` / `rules` / `review` 模块
