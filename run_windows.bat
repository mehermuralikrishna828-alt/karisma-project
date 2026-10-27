@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo First run setup_windows.bat to install dependencies and create the database.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
python manage.py runserver
