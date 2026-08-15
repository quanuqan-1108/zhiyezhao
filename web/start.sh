#!/usr/bin/env bash
# 职业照小能手 Web 一键启动脚本（macOS / Linux）
set -e

cd "$(dirname "$0")"

# 自动检测 Python
if command -v python3 &> /dev/null; then
    PY=python3
elif command -v python &> /dev/null; then
    PY=python
else
    echo "[ERROR] 未找到 Python，请先安装 Python 3.8+"
    exit 1
fi

# 检查 ARK_API_KEY
if [ -z "$ARK_API_KEY" ]; then
    echo "[ERROR] 未设置 ARK_API_KEY 环境变量"
    echo "  请先执行: export ARK_API_KEY='ark-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx-NNNNN'"
    exit 1
fi

# 检查依赖
if ! $PY -c "import fastapi" 2>/dev/null; then
    echo "[INFO] 安装依赖中..."
    $PY -m pip install -r requirements.txt
fi

echo "========================================"
echo "  职业照小能手 Web 系统启动中..."
echo "========================================"
echo
echo "  访问: http://localhost:8765"
echo "  按 Ctrl+C 停止服务"
echo

exec $PY server.py
