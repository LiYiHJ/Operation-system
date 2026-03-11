# V5.1 跨境电商智能运营系统 - 启动脚本（PowerShell）
# 基于官方部署文档

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "V5.1 跨境电商智能运营系统 - 启动向导" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查Docker
Write-Host "步骤 1/6: 检查Docker服务..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    docker compose version | Out-Null
    Write-Host "  ✅ Docker已安装" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Docker未安装，请先安装Docker Desktop" -ForegroundColor Red
    exit 1
}

# 2. 启动基础服务
Write-Host ""
Write-Host "步骤 2/6: 启动PostgreSQL和Redis..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\docs"
docker compose -f .\docker-compose.windows.yml up -d
Start-Sleep -Seconds 5

# 检查容器状态
$containers = docker compose -f .\docker-compose.windows.yml ps
if ($containers -match "Up") {
    Write-Host "  ✅ 基础服务已启动" -ForegroundColor Green
} else {
    Write-Host "  ❌ 基础服务启动失败" -ForegroundColor Red
    exit 1
}

Set-Location $PSScriptRoot

# 3. 创建虚拟环境
Write-Host ""
Write-Host "步骤 3/6: 检查Python环境..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "  创建虚拟环境..." -ForegroundColor Gray
    python -m venv .venv
}
Write-Host "  ✅ 虚拟环境已就绪" -ForegroundColor Green

# 4. 激活虚拟环境
Write-Host ""
Write-Host "步骤 4/6: 激活虚拟环境..." -ForegroundColor Yellow
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& .\.venv\Scripts\Activate.ps1
Write-Host "  ✅ 虚拟环境已激活" -ForegroundColor Green

# 5. 安装依赖
Write-Host ""
Write-Host "步骤 5/6: 安装依赖..." -ForegroundColor Yellow
python -m pip install -U pip --quiet
pip install -e . --quiet
pip install flask sqlalchemy "psycopg[binary]" pytest --quiet
Write-Host "  ✅ 依赖已安装" -ForegroundColor Green

# 6. 设置环境变量
Write-Host ""
Write-Host "步骤 6/6: 配置环境变量..." -ForegroundColor Yellow
$env:APP_ENV = "production"
$env:APP_DEBUG = "false"
$env:SECRET_KEY = "replace_with_strong_secret"
$env:TIMEZONE = "Asia/Shanghai"
$env:DEFAULT_CURRENCY = "RUB"
$env:DATABASE_URL = "postgresql+psycopg://ecom_user:strong_password@127.0.0.1:5432/ecom_v51"
$env:REDIS_URL = "redis://127.0.0.1:6379/0"
$env:CELERY_BROKER_URL = "redis://127.0.0.1:6379/1"
$env:CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/2"
$env:PYTHONPATH = "src"
Write-Host "  ✅ 环境变量已设置" -ForegroundColor Green

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "系统启动完成！" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "后续操作:" -ForegroundColor Yellow
Write-Host "  1. 初始化数据库: python -m ecom_v51.init_db" -ForegroundColor Gray
Write-Host "  2. CLI测试:       python -m ecom_v51.cli --input input.json --pretty" -ForegroundColor Gray
Write-Host "  3. 启动Web:       python run_api.py" -ForegroundColor Gray
Write-Host "  4. 启动前端:      cd frontend && npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
