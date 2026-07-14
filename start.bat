@echo off
chcp 65001 >nul 2>&1
title GridGo Launcher

echo.
echo  ========================================
echo        GridGo  -  大富翁游戏启动器
echo  ========================================
echo.

:: 项目路径
set "ROOT=%~dp0"
set "SERVER_DIR=%ROOT%gridgo-server"
set "WEB_DIR=%ROOT%gridgo-web"
set "VENV_DIR=%SERVER_DIR%\.venv"
set "BACKEND_PORT=8001"
set "FRONTEND_PORT=3000"

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [错误] 未找到 Python，请先安装 Python 3.12+
    pause
    exit /b 1
)

:: 检查 Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo  [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

:: 检查 pnpm
where pnpm >nul 2>&1
if %errorlevel% neq 0 (
    echo  [错误] 未找到 pnpm，请先运行: npm i -g pnpm
    pause
    exit /b 1
)

:: 检查 .env
if not exist "%SERVER_DIR%\.env" (
    echo  [配置] .env 不存在，从 .env.example 复制...
    copy "%SERVER_DIR%\.env.example" "%SERVER_DIR%\.env" >nul
    echo  [配置] 已创建 .env，请根据实际情况修改数据库密码等配置
    echo.
)

:: 检查虚拟环境
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo  [安装] 创建 Python 虚拟环境...
    python -m venv "%VENV_DIR%"
    echo  [安装] 安装后端依赖...
    call "%VENV_DIR%\Scripts\activate.bat"
    pip install -r "%SERVER_DIR%\requirements.txt" -q
    echo  [安装] 后端依赖安装完成
    echo.
) else (
    echo  [就绪] Python 虚拟环境已存在
)

:: 检查前端依赖
if not exist "%WEB_DIR%\node_modules" (
    echo  [安装] 安装前端依赖...
    cd /d "%WEB_DIR%"
    pnpm install
    echo  [安装] 前端依赖安装完成
    echo.
) else (
    echo  [就绪] 前端依赖已存在
)

echo.
echo  ----------------------------------------
echo  启动服务中...
echo  ----------------------------------------
echo.

:: 启动后端
echo  [启动] 后端服务 (FastAPI) - http://localhost:%BACKEND_PORT%
start "GridGo-Backend" cmd /k "cd /d %SERVER_DIR% && call %VENV_DIR%\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port %BACKEND_PORT%"

:: 等待后端启动
timeout /t 2 /nobreak >nul

:: 启动前端
echo  [启动] 前端服务 (Vite)    - http://localhost:%FRONTEND_PORT%
start "GridGo-Frontend" cmd /k "cd /d %WEB_DIR% && pnpm dev"

:: 等待前端启动
timeout /t 3 /nobreak >nul

echo.
echo  ========================================
echo  所有服务已启动！
echo.
echo  前端页面:  http://localhost:%FRONTEND_PORT%
echo  后端 API:  http://localhost:%BACKEND_PORT%
echo  API 文档:  http://localhost:%BACKEND_PORT%/docs
echo.
echo  关闭此窗口不会停止服务
echo  如需停止，请关闭后端/前端命令行窗口
echo  ========================================
echo.
pause
