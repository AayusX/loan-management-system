@echo off
echo ============================================
echo   Saving Group Loan Management — Builder
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo [1/3] Installing required packages...
pip install customtkinter pillow openpyxl pandas pyinstaller --quiet
if %errorlevel% neq 0 (
    echo ERROR: Failed to install packages
    pause
    exit /b 1
)

echo [2/3] Building .exe file (this may take 2-3 minutes)...
pyinstaller --onefile --windowed --name "SavingGroup_LoanManagement" ^
    --hidden-import customtkinter ^
    --hidden-import openpyxl ^
    --hidden-import pandas ^
    --hidden-import PIL ^
    app.py
if %errorlevel% neq 0 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
echo.
echo Your application is ready at:
echo   dist\SavingGroup_LoanManagement.exe
echo.
echo Copy the .exe file anywhere — it runs standalone.
echo The database (saving_group.db) will be created in the same folder as the .exe
echo.
echo Default login:  username: admin    password: admin123
echo (Change your password in Settings after first login!)
echo.
pause
