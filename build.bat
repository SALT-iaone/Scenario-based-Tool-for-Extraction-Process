@echo off
:: ================================================================
:: S.T.E.P. - Build Script for Windows
:: Double-click or run from Command Prompt
:: ================================================================

set APP_NAME=STEP
set SCRIPT=main.py

echo ======================================================
echo   S.T.E.P. - Windows Build
echo ======================================================

:: Check PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    python -m pip install pyinstaller
)

:: Install dependencies
echo [INFO] Checking dependencies...
python -m pip install -r requirements.txt -q

:: Run build
echo [INFO] Building %APP_NAME%...

python -m PyInstaller ^
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

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo ======================================================
echo [DONE] dist\%APP_NAME%\%APP_NAME%.exe
echo ======================================================

pause