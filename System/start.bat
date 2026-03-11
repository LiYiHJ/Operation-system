@echo off
REM V5.1 系统启动脚本（Windows）
REM 前后端分离架构

echo ========================================================================
echo V5.1 跨境电商智能运营系统
echo ========================================================================
echo.

cd /d "%~dp0"

REM 检查虚拟环境
if not exist ".venv" (
    echo 创建虚拟环境...
    python -m venv .venv
)

REM 激活虚拟环境
echo 激活虚拟环境...
call .venv\Scripts\activate.bat

REM 安装依赖
echo 安装依赖...
python -m pip install -q --upgrade pip
pip install -q -e .
pip install -q flask flask-cors

echo.
echo ========================================================================
echo 启动说明
echo ========================================================================
echo.
echo 后端API:
echo   python start_api.py
echo   访问: http://localhost:5000/api
echo.
echo 前端React:
echo   cd frontend
echo   npm install
echo   npm run dev
echo   访问: http://localhost:5173
echo.
echo ========================================================================
echo.

REM 询问启动哪个
set /p choice="启动后端API吗？(y/n): "
if /i "%choice%"=="y" (
    python start_api.py
) else (
    echo.
    echo 请手动启动：
    echo   后端: python start_api.py
    echo   前端: cd frontend ^&^& npm run dev
)

pause
