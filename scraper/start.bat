@echo off
echo Select scraper to run:
echo 1. Skills
echo 2. Characters
echo 3. Characters URL
echo 4. Supports
echo 5. Support URL
echo 6. Races
echo 0. Main Database Update (Characters/Supports)
set /p choice="Enter number: "

if "%choice%"=="1" set scraper=skills
if "%choice%"=="2" set scraper=characters
if "%choice%"=="3" set scraper=characters_url
if "%choice%"=="4" set scraper=supports
if "%choice%"=="5" set scraper=supports_url
if "%choice%"=="6" set scraper=races
if "%choice%"=="0" set scraper=

pip install -r requirements.txt

if "%scraper%"=="" (
    py main.py
) else (
    py main.py %scraper%
)

pause