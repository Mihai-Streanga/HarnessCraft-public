@echo off
REM ============================================
REM   Pornire HarnessCraft - dublu-click pentru start
REM ============================================
title HarnessCraft - server (nu inchide cat folosesti aplicatia)
REM %~dp0 = folderul in care sta acest fisier: merge oriunde e mutat proiectul
cd /d "%~dp0"
REM Python-ul proiectului (.venv), nu cel al sistemului
if not exist ".venv\Scripts\python.exe" (
    echo   Lipseste mediul Python al proiectului: .venv
    echo   Vezi docs\INSTALARE.md, pasul de instalare.
    pause
    exit /b 1
)
REM Fereastra serverului sta micsorata, in bara de jos (cerut de autor): fisierul se reia o data, cu /min
if /i not "%~1"=="min" (
    start "HarnessCraft - server" /min "%~f0" min
    exit /b
)
echo.
echo   HarnessCraft ruleaza; pagina s-a deschis in browser.
echo.
echo   NU inchide aceasta fereastra cat timp folosesti aplicatia.
echo   Cand termini, inchide-o ca sa opresti programul.
echo.
".venv\Scripts\python.exe" -m harnesscraft.interfata
pause
