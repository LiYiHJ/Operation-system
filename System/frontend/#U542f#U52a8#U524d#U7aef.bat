@echo off
chcp 65001 > nul
title V5.1 前端启动器

echo ========================================
echo   V5.1 跨境电商智能运营系统
echo   前端启动器
echo ========================================
echo.

cd /d C:\Operation-system\System\frontend

echo [1/3] 检查项目完整性...
python verify_project.py
if errorlevel 1 (
    echo.
    echo ❌ 项目验证失败！
    echo 请检查缺失的文件。
    pause
    exit /b 1
)

echo.
echo [2/3] 检查依赖安装...
if not exist "node_modules" (
    echo ⚠️  未检测到 node_modules
    echo 正在安装依赖...
    npm install
    if errorlevel 1 (
        echo ❌ 依赖安装失败！
        pause
        exit /b 1
    )
) else (
    echo ✅ 依赖已安装
)

echo.
echo [3/3] 启动开发服务器...
echo.
echo ========================================
echo   系统启动中...
echo   请稍候...
echo ========================================
echo.

npm run dev

pause
