@echo off
echo Select scraper to run:
echo 1. Skills
echo 2. Characters
echo 3. Supports
echo 4. Races
echo 5. Race Icons
echo 0. All
set /p choice="Enter number: "

if "%choice%"=="1" set scraper=skills
if "%choice%"=="2" set scraper=characters
if "%choice%"=="3" set scraper=supports
if "%choice%"=="4" set scraper=races
if "%choice%"=="5" set scraper=race_icon
if "%choice%"=="0" set scraper=

pip install -r requirements.txt

if "%scraper%"=="" (
    python main.py
) else (
    python main.py %scraper%
)

pause