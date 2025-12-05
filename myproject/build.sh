#!/usr/bin/env bash
# exit on error
set -o errexit

# Cài đặt các thư viện
pip install -r requirements.txt

# Gom file tĩnh (CSS, Ảnh) vào thư mục staticfiles
python manage.py collectstatic --no-input

# Cập nhật Database
python manage.py migrate