@echo off
REM 职业照小能手 Web 一键启动脚本
REM 双击此文件即可启动

cd /d "%~dp0"

set PYTHONPATH=C:\Users\YaoCa\.workbuddy\binaries\python\envs\skill_web_deps
set PYTHON=C:\Users\YaoCa\.workbuddy\binaries\python\versions\3.13.12\python.exe

echo ========================================
echo   职业照小能手 Web 系统启动中...
echo ========================================
echo.
echo   访问: http://localhost:8765
echo   按 Ctrl+C 停止服务
echo.

"%PYTHON%" server.py

pause
