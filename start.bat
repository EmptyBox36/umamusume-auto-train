@echo off
set /p choice="Run git pull before starting? (y/n): "

if /i "%choice%"=="y" (
    git pull
) else (
    echo Skipping git pull...
)

python main.py
pause
