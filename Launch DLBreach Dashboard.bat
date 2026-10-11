@echo off
REM ====================================================================
REM  DLBreach Dashboard - launcher
REM
REM  Double-click this file to start the dashboard. On the first run it
REM  creates an isolated Python environment in this folder and installs
REM  the required packages, which takes a couple of minutes. Every run
REM  after that starts in a few seconds.
REM
REM  Requires Python 3.11 to 3.14 (3.13 recommended), installed with the
REM  "Add python.exe to PATH" option ticked.
REM ====================================================================

setlocal
cd /d "%~dp0"
title DLBreach Dashboard

echo.
echo  ============================================
echo   DLBreach Dashboard
echo  ============================================
echo.

REM ---- check Python is available -------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo  Python was not found on this computer.
    echo.
    echo  Install Python 3.13 from https://www.python.org/downloads/
    echo  During installation, tick "Add python.exe to PATH" on the first
    echo  screen. Then run this file again.
    echo.
    pause
    exit /b 1
)

REM ---- create the environment on first run ---------------------------
if not exist ".venv\Scripts\python.exe" (
    python -c "import sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 14) else 1)"
    if errorlevel 1 (
        echo  This dashboard needs Python 3.11 to 3.14. This computer has:
        python --version
        echo.
        echo  Install Python 3.13 from https://www.python.org/downloads/
        echo  ^(under "Looking for a specific release?"^), tick
        echo  "Add python.exe to PATH", then run this file again.
        echo.
        pause
        exit /b 1
    )
    echo  First run: setting up. This takes a couple of minutes.
    echo.
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo  Could not create the environment. See the message above.
        pause
        exit /b 1
    )
    call ".venv\Scripts\activate.bat"
    echo  Installing packages...
    python -m pip install --upgrade pip --quiet
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo  Package installation failed. See the message above.
        pause
        exit /b 1
    )
    copy /y requirements.txt ".venv\requirements.installed" >nul
    echo.
    echo  Setup complete.
    echo.
) else (
    call ".venv\Scripts\activate.bat"
)

REM ---- make sure the installed packages match requirements.txt ---------
REM  requirements.txt pins exact versions. After an update changes it, the
REM  packages are reinstalled once; otherwise this takes a second.
fc /b requirements.txt ".venv\requirements.installed" >nul 2>&1
if errorlevel 1 goto install
python -c "import streamlit, pandas, numpy, matplotlib, openpyxl, docx" >nul 2>&1
if errorlevel 1 goto install
goto ready

:install
    echo  Installing the package versions this release needs...
    echo.
    python -m pip install -r requirements.txt --disable-pip-version-check
    if errorlevel 1 (
        echo.
        echo  Package installation failed. See the message above.
        pause
        exit /b 1
    )
    copy /y requirements.txt ".venv\requirements.installed" >nul
    echo.

:ready
REM ---- Streamlit asks for an email on its very first run unless this ---
REM  file exists; create it empty so the window never waits for input.
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
    >"%USERPROFILE%\.streamlit\credentials.toml" echo [general]
    >>"%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

REM ---- start ----------------------------------------------------------
echo  Starting the dashboard. A browser tab will open shortly.
echo.
echo  Keep this window open while you are using the dashboard.
echo  To stop it, close this window or press Ctrl+C.
echo.

REM  If the server stops unexpectedly it is restarted here (a new browser
REM  tab opens). Inputs are autosaved, so after a
REM  page refresh they can be restored from the Project page.
set RESTARTS=0
:serve
streamlit run app.py
REM a normal stop (Ctrl+C) returns 0: do not restart then
if %ERRORLEVEL% EQU 0 goto stopped
if %RESTARTS% GEQ 5 goto stopped
set /a RESTARTS+=1
echo.
echo  The dashboard stopped unexpectedly. Restarting (%RESTARTS% of 5)...
echo.
timeout /t 2 /nobreak >nul
goto serve

:stopped
echo.
echo  The dashboard has stopped.
pause
endlocal
