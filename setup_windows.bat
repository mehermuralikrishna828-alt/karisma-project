@echo off
setlocal
cd /d "%~dp0"

echo === Karisma setup ===
where py >nul 2>nul
if errorlevel 1 (
    echo Python Launcher was not found. Install Python 3.10+ from https://www.python.org/downloads/ and try again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error
python manage.py makemigrations
if errorlevel 1 goto :error
python manage.py migrate
if errorlevel 1 goto :error

echo.
echo Setup complete.
echo Optional: run "python manage.py seed_demo_data" to load sample content.
echo Then run run_windows.bat to start the local site.
pause
exit /b 0

:error
echo.
echo Setup failed. Read the error above, check your Python installation and internet connection, then try again.
pause
exit /b 1
