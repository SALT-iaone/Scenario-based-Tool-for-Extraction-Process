#!/bin/bash
# ================================================================
# S.T.E.P.  ビルドスクリプト (Mac / Windows)
# 使い方:  bash build.sh
# ================================================================
set -e

APP_NAME="STEP"
SCRIPT="main.py"

echo "======================================================"
echo "  S.T.E.P.  パッケージビルド"
echo "======================================================"

# ── PyInstaller チェック ──────────────────────────────────────
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo ">>> PyInstaller をインストールします..."
    pip3 install pyinstaller
fi

# ── 依存パッケージチェック ────────────────────────────────────
echo ">>> 依存パッケージを確認します..."
pip3 install -r requirements.txt --quiet

# ── ビルド実行 ────────────────────────────────────────────────
echo ">>> ビルド開始: $APP_NAME"

pyinstaller \
    --noconfirm \
    --clean \
    --windowed \
    --name "$APP_NAME" \
    --hidden-import "mysql.connector" \
    --hidden-import "mysql.connector.locales.eng.client_error" \
    --hidden-import "sshtunnel" \
    --hidden-import "paramiko" \
    --hidden-import "paramiko.transport" \
    --hidden-import "paramiko.auth_handler" \
    --hidden-import "cryptography" \
    "$SCRIPT"

echo ""
echo "======================================================"
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "✅ 完了！"
    echo ""
    echo "   dist/$APP_NAME.app"
    echo ""
    echo "   → dist フォルダを開きますか？"
    read -p "     [y/N]: " yn
    if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
        open dist/
    fi
else
    echo "✅ 完了！"
    echo ""
    echo "   dist/$APP_NAME/$APP_NAME.exe"
fi
echo "======================================================"
