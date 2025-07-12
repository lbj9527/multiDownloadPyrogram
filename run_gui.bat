@echo off
chcp 65001 > nul
title MultiDownloadPyrogram GUI启动器

echo.
echo MultiDownloadPyrogram GUI启动器
echo ===============================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请确保Python已安装并添加到PATH
    echo.
    echo 请从以下地址下载Python 3.8或更高版本:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM 显示Python版本
echo 检测到的Python版本:
python --version
echo.

REM 检查依赖
echo 正在检查依赖包...
pip show pyrogram >nul 2>&1
if %errorlevel% neq 0 (
    echo 警告: 未找到pyrogram包，可能需要安装依赖
    echo.
    echo 是否要安装依赖包？ (y/n)
    set /p install_deps=
    if /i "%install_deps%"=="y" (
        echo 正在安装依赖包...
        pip install -r requirements.txt
        if %errorlevel% neq 0 (
            echo 依赖安装失败，请手动执行: pip install -r requirements.txt
            pause
            exit /b 1
        )
    )
)

echo 正在启动GUI界面...
echo.
echo 提示: 
echo - 首次使用需要配置API ID和API Hash
echo - 建议使用代理以提高连接稳定性
echo - 可以在工具菜单中打开各种功能窗口
echo.
echo ===============================================
echo.

REM 启动GUI
python run_gui.py

if %errorlevel% neq 0 (
    echo.
    echo 启动失败，错误代码: %errorlevel%
    echo.
    pause
)

echo.
echo 程序已退出
pause 