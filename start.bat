@echo off
set /p choice="Run check for update before starting? (y/n): "

if /i "%choice%"=="y" (
    git pull
) else (
    echo Skipping update...
)

py -m pip install --upgrade pip
pip install -r requirements.txt

py main.py
pause
