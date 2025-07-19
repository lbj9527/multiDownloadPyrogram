@echo off
chcp 65001 >nul
title Telegram多客户端消息下载器

echo ========================================
echo   Telegram多客户端消息下载器
echo ========================================
echo.

cd /d "D:\pythonproject\multiDownloadPyrogram"

echo 正在启动应用...
python start.py

if %errorlevel% neq 0 (
    echo.
    echo 启动失败！请检查错误信息
    echo.
    pause
) else (
    echo.
    echo 应用已关闭
)
