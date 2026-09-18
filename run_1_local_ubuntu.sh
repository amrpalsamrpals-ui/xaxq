#!/usr/bin/env bash
set -u

cd /app

echo "======================================"
echo "     RAILWAY - 1 INSTANCE"
echo "======================================"
echo "Starting 1_rhel.py..."
echo

if [ ! -f "/app/1_rhel.py" ]; then
    echo "[ERROR] 1_rhel.py tidak ditemukan."
    exit 1
fi

echo "[CHECK] Validasi Python..."

python3 -m py_compile /app/1_rhel.py

if [ $? -ne 0 ]; then
    echo "[ERROR] 1_rhel.py tidak valid."
    exit 1
fi

echo "[OK] Python valid."
echo "[OK] Menjalankan 1 instance..."
echo

exec python3 -u /app/1_rhel.py
