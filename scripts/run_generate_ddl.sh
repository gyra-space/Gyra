#!/bin/bash
# DDL 生成脚本 - 使用本地虚拟环境，无需网络

set -e

VENV_PYTHON=".venv/bin/python"

# 检查虚拟环境
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ 虚拟环境不存在，请先运行: uv sync"
    exit 1
fi

echo "✓ 使用 Python: $($VENV_PYTHON --version)"
echo "✓ 开始生成 DDL..."

# 直接运行，完全离线
exec "$VENV_PYTHON" scripts/generate_ddl.py "$@"