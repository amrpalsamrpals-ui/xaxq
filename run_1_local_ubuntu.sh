#!/usr/bin/env bash
set -u

cd /app

echo "======================================"
echo "       RAILWAY - 1 INSTANCE"
echo "======================================"

if [ ! -f "/app/1_rhel.py" ]; then
    echo "[ERROR] 1_rhel.py tidak ditemukan"
    exit 1
fi

echo "[CHECK] Python syntax..."
python3 -m py_compile /app/1_rhel.py || exit 1

echo "[OK] Python valid"
echo "[OK] Starting 1_rhel.py"
echo

exec python3 -u /app/1_rhel.py
