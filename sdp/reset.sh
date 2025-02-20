#!/bin/bash

# 設定 Python 虛擬環境路徑（如果有的話）
VENV_PATH=".venv"

# 檢查虛擬環境是否存在
if [ -d "$VENV_PATH" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
fi

# 執行 Python 腳本
echo "Executing los_api/api.py..."
python ./los_api/api.py

# 如果使用了虛擬環境，則退出
if [ -d "$VENV_PATH" ]; then
    deactivate
fi