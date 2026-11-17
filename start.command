#!/bin/bash
set -e
trap 'echo "启动未完成。请检查 Python 3.10+ 是否安装，以及依赖下载时网络是否可用。"' ERR
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c "import requests, bs4, selenium" 2>/dev/null; then
  .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python server.py --open "$@"
