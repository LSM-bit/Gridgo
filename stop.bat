@echo off
chcp 65001 >nul 2>&1
title GridGo Stopper

echo.
echo  ========================================
echo        GridGo  -  停止所有服务
echo  ========================================
echo.

:: 停止后端 (uvicorn)
echo  [停止] 正在停止后端服务 (uvicorn)...
taskkill /f /fi "WINDOWTITLE eq GridGo-Backend*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

:: 停止前端 (vite/node)
echo  [停止] 正在停止前端服务 (vite)...
taskkill /f /fi "WINDOWTITLE eq GridGo-Frontend*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo  [完成] 所有服务已停止
echo.
pause
