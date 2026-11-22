@echo off
REM Build script for Windows
REM Usage: build.bat

echo === DB Export Tool - Build Windows ===

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python 3.10+.
    pause
    exit /b 1
)

REM Create venv if not exists
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Install dependencies
echo Installing dependencies...
.venv\Scripts\pip.exe install --upgrade pip
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\pip.exe install pyinstaller

REM Build
echo Building executable...
.venv\Scripts\pyinstaller.exe --onefile --windowed --add-data "db_tool;db_tool" --add-data "logo.png;." --name "DBExportTool" app.py

echo.
echo === Build complete ===
echo Executable: dist\DBExportTool.exe
pause
