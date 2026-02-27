#!/bin/bash

# Dừng ngay nếu có lỗi
set -e

# Đường dẫn tới venv (chỉnh nếu khác)
VENV_DIR="venv"

echo "Kích hoạt virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Đang chạy script1.py..."
python script1.py

echo "Đang chạy script2.py..."
python script2.py

echo "Hoàn thành!"

# Thoát venv (không bắt buộc)
deactivate