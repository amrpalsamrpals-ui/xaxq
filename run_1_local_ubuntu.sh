#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# LOCAL UBUNTU - RUN 1_rhel.py ONLY
# Tidak memakai Sprite/Fly.io dan tidak menjalankan 100 instance.
# ============================================================

PYTHON_NAME="1_rhel.py"
MEDIAFIRE_PAGE="https://www.mediafire.com/file/m920u0yd8z5xq7f/1_rhel.py"

TMUX_SESSION="python1"
BASE_DIR="$HOME/1_rhel_local"
PY="$BASE_DIR/$PYTHON_NAME"
PYLOG="$BASE_DIR/python.log"
WATCHDOG="$BASE_DIR/python_watchdog.sh"
PAGE_FILE="$BASE_DIR/mediafire_page.html"
TMP_FILE="$BASE_DIR/${PYTHON_NAME}.download"

DOWNLOAD_TIMEOUT=60
DOWNLOAD_RETRY=3

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

die() {
    echo "[ERROR] $*" >&2
    exit 1
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Command tidak ditemukan: $1"
}

mkdir -p "$BASE_DIR"

echo
echo "============================================================"
echo "              LOCAL UBUNTU - 1 INSTANCE"
echo "============================================================"
echo "Folder   : $BASE_DIR"
echo "Python   : $PY"
echo "tmux     : $TMUX_SESSION"
echo "Mode     : 1 proses Python saja"
echo "============================================================"
echo

# ------------------------------------------------------------
# CHECK DEPENDENCIES
# ------------------------------------------------------------
require_cmd python3
require_cmd wget
require_cmd grep
require_cmd head
require_cmd file

if ! command -v tmux >/dev/null 2>&1; then
    echo "[INFO] tmux belum terpasang. Menginstall tmux..."
    sudo apt-get update
    sudo apt-get install -y tmux
fi

# ------------------------------------------------------------
# DOWNLOAD 1_rhel.py
# Jika file sudah ada dan valid, tidak download ulang.
# ------------------------------------------------------------
if [[ -s "$PY" ]] && python3 -m py_compile "$PY" >/dev/null 2>&1; then
    log "File $PYTHON_NAME sudah ada dan valid."
else
    log "Mengambil halaman MediaFire..."
    rm -f "$PAGE_FILE" "$TMP_FILE"

    wget \
        --max-redirect=10 \
        --tries="$DOWNLOAD_RETRY" \
        --timeout="$DOWNLOAD_TIMEOUT" \
        --user-agent="Mozilla/5.0" \
        -q -O "$PAGE_FILE" \
        "$MEDIAFIRE_PAGE" || die "Gagal mengambil halaman MediaFire."

    [[ -s "$PAGE_FILE" ]] || die "Halaman MediaFire kosong."

    # Cari direct download URL dari halaman MediaFire.
    DIRECT_URL="$(
        grep -oE 'https://download[0-9]+\.mediafire\.com/[^"<>[:space:]]+' \
        "$PAGE_FILE" |
        grep '/m920u0yd8z5xq7f/' |
        head -1 || true
    )"

    # Fallback: ambil URL download pertama yang tersedia.
    if [[ -z "$DIRECT_URL" ]]; then
        DIRECT_URL="$(
            grep -oE 'https://download[0-9]+\.mediafire\.com/[^"<>[:space:]]+' \
            "$PAGE_FILE" |
            head -1 || true
        )"
    fi

    [[ -n "$DIRECT_URL" ]] || {
        echo
        echo "[ERROR] Direct download URL MediaFire tidak ditemukan."
        echo "[INFO] Gunakan file lokal dengan cara:"
        echo "       cp /path/1_rhel.py $PY"
        echo "       lalu jalankan script ini lagi."
        exit 1
    }

    log "Direct URL ditemukan."
    log "Download $PYTHON_NAME..."

    wget \
        --max-redirect=10 \
        --tries="$DOWNLOAD_RETRY" \
        --timeout="$DOWNLOAD_TIMEOUT" \
        --user-agent="Mozilla/5.0" \
        -q -O "$TMP_FILE" \
        "$DIRECT_URL" || die "Download $PYTHON_NAME gagal."

    [[ -s "$TMP_FILE" ]] || die "File hasil download kosong."

    echo
    echo "===== FILE TYPE ====="
    file "$TMP_FILE"

    echo
    echo "===== VALIDASI PYTHON ====="
    if ! python3 -m py_compile "$TMP_FILE"; then
        echo "[ERROR] Hasil download bukan Python valid."
        echo
        echo "===== HEAD FILE ====="
        head -30 "$TMP_FILE" || true
        die "Validasi Python gagal."
    fi

    mv "$TMP_FILE" "$PY"
    chmod 644 "$PY"
    log "Python valid: $PY"
fi

echo
echo "===== SHA256 ====="
sha256sum "$PY"

# ------------------------------------------------------------
# STOP INSTANCE LAMA
# Hanya menghentikan session lokal python1 milik script ini.
# ------------------------------------------------------------
if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log "Menghentikan instance lama: $TMUX_SESSION"
    tmux kill-session -t "$TMUX_SESSION" || true
    sleep 1
fi

# ------------------------------------------------------------
# BUAT WATCHDOG
# Watchdog menjaga SATU proses 1_rhel.py tetap hidup.
# Jika Python berhenti/crash, Python dijalankan kembali.
# ------------------------------------------------------------
cat > "$WATCHDOG" <<'WATCHDOG_EOF'
#!/usr/bin/env bash
set -u

BASE_DIR="$HOME/1_rhel_local"
PY="$BASE_DIR/1_rhel.py"
PYLOG="$BASE_DIR/python.log"

exec >> "$PYLOG" 2>&1

echo
echo "============================================================"
echo "WATCHDOG START: $(date)"
echo "PID: $$"
echo "============================================================"

while true; do
    echo
    echo "============================================================"
    echo "START PYTHON: $(date)"
    echo "============================================================"

    if [[ ! -s "$PY" ]]; then
        echo "[ERROR] $PY tidak ditemukan."
        sleep 10
        continue
    fi

    if ! python3 -m py_compile "$PY" >/dev/null 2>&1; then
        echo "[ERROR] File Python tidak valid."
        sleep 10
        continue
    fi

    echo "[WATCHDOG] Menjalankan SATU instance: $PY"
    python3 -u "$PY"
    EXIT_CODE=$?

    echo
    echo "============================================================"
    echo "PYTHON EXITED: $(date)"
    echo "EXIT CODE: $EXIT_CODE"
    echo "RESTART IN 5 SECONDS"
    echo "============================================================"

    sleep 5
done
WATCHDOG_EOF

chmod 700 "$WATCHDOG"

# ------------------------------------------------------------
# START 1 INSTANCE SAJA
# ------------------------------------------------------------
log "Menjalankan satu instance Python di tmux..."

tmux new-session -d \
    -s "$TMUX_SESSION" \
    "cd '$BASE_DIR' && exec '$WATCHDOG'" \
    </dev/null >/dev/null 2>&1

sleep 2

if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo
    echo "[ERROR] tmux gagal dibuat."
    tail -30 "$PYLOG" 2>/dev/null || true
    exit 1
fi

echo
echo "============================================================"
echo "                    BERHASIL"
echo "============================================================"
echo "Hanya 1 instance yang dijalankan."
echo
echo "Session : $TMUX_SESSION"
echo "Python  : $PY"
echo "Log     : $PYLOG"
echo
echo "Cek status:"
echo "  tmux ls"
echo "  pgrep -af 'python3.*1_rhel.py'"
echo
echo "Lihat log:"
echo "  tail -f '$PYLOG'"
echo
echo "Masuk ke terminal Python:"
echo "  tmux attach -t $TMUX_SESSION"
echo
echo "Keluar dari tmux tanpa menghentikan Python:"
echo "  tekan Ctrl+B lalu D"
echo
echo "Hentikan 1 instance:"
echo "  tmux kill-session -t $TMUX_SESSION"
echo "============================================================"
