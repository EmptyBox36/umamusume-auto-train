@echo off
echo Select scraper to run:
echo 1. Skills Data
echo 2. Characters Event
echo 3. Supports Event
echo 4. Support Images
echo 5. Races Data
echo 0. Main Database Update (Characters / Supports / Support Images)

set /p choice="Enter number: "

if "%choice%"=="1" set scraper=skills
if "%choice%"=="2" set scraper=characters
if "%choice%"=="3" set scraper=supports
if "%choice%"=="4" set scraper=support_images
if "%choice%"=="5" set scraper=races
if "%choice%"=="0" set scraper=

set "PYEXE="
where python >nul 2>&1 && set "PYEXE=python"
if not defined PYEXE where py >nul 2>&1 && set "PYEXE=py"
if not defined PYEXE (
  echo ERROR: Neither "python" nor "py" is on PATH.
  exit /b 1
)

pip install -r requirements.txt

if "%scraper%"=="" (
  %PYEXE% main.py
) else (
  %PYEXE% main.py %scraper%
)

pause