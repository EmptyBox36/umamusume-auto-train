@echo off
set /p choice="Run check for update before starting? (y/n): "

if /i "%choice%"=="y" (
    git pull
) else (
    echo Skipping update...
)

python main.py
pause
