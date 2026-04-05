@echo off
:: ================================================================
:: S.T.E.P.  ビルドスクリプト (Windows)
:: 使い方: build.bat をダブルクリック or コマンドプロンプトで実行
:: ================================================================

set APP_NAME=STEP
set SCRIPT=main.py

echo ======================================================
echo   S.T.E.P.  パッケージビルド
echo ======================================================

:: PyInstaller チェック
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ^>^>^> PyInstaller をインストールします...
    pip install pyinstaller
)

:: 依存パッケージ
echo ^>^>^> 依存パッケージを確認します...
pip install -r requirements.txt -q

:: ビルド実行
echo ^>^>^> ビルド開始: %APP_NAME%

pyinstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --name "%APP_NAME%" ^
    --hidden-import "mysql.connector" ^
    --hidden-import "mysql.connector.locales.eng.client_error" ^
    --hidden-import "sshtunnel" ^
    --hidden-import "paramiko" ^
    --hidden-import "paramiko.transport" ^
    --hidden-import "paramiko.auth_handler" ^
    --hidden-import "cryptography" ^
    "%SCRIPT%"

echo.
echo ======================================================
echo ✅ 完了！
echo.
echo    dist\%APP_NAME%\%APP_NAME%.exe
echo ======================================================

pause
