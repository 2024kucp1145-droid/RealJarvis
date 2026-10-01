@echo off
:: ============================================================
::  RealJarvis - Harshit ke liye Windows Setup Script
::  Ek baar chalao, sab auto install ho jayega!
::  Author: Generated for Harshit from Piyush's Jarvis project
:: ============================================================

title RealJarvis Setup - Harshit ka Jarvis Install Ho Raha Hai...
color 0A
echo.
echo  =====================================================
echo   WELCOME TO REALJARVIS SETUP - HARSHIT KA JARVIS
echo  =====================================================
echo.
echo  Ye script aapke liye:
echo   1. Repo clone karega
echo   2. Python virtual environment banayega
echo   3. Saari dependencies install karega
echo   4. .env file setup karega
echo   5. Jarvis run karega
echo.
echo  REQUIREMENT: Python 3.10+ aur Git install hona chahiye
echo  -------------------------------------------------------
pause

:: ---- Step 1: Python Check ----
echo.
echo [1/6] Python version check kar raha hoon...
python --version 2>nul
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python nahi mila! 
    echo  Download: https://www.python.org/downloads/
    echo  ZAROOR check karo: "Add Python to PATH" option
    pause
    exit /b 1
)
echo  Python mil gaya!

:: ---- Step 2: Git Check ----
echo.
echo [2/6] Git check kar raha hoon...
git --version 2>nul
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Git nahi mila!
    echo  Download: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo  Git mil gaya!

:: ---- Step 3: Clone Repo ----
echo.
echo [3/6] RealJarvis clone ho raha hai GitHub se...
set INSTALL_DIR=%USERPROFILE%\RealJarvis
if exist "%INSTALL_DIR%" (
    echo  Folder pehle se hai: %INSTALL_DIR%
    echo  Sirf latest changes pull kar raha hoon...
    cd /d "%INSTALL_DIR%"
    git pull origin main
) else (
    git clone https://github.com/2024kucp1145-droid/RealJarvis.git "%INSTALL_DIR%"
    cd /d "%INSTALL_DIR%"
)
echo  Repo ready hai at: %INSTALL_DIR%

:: ---- Step 4: Virtual Environment ----
echo.
echo [4/6] Python virtual environment bana raha hoon...
if not exist "venv" (
    python -m venv venv
    echo  Virtual environment bana diya!
) else (
    echo  Virtual environment pehle se exist karta hai.
)

:: Activate venv
call venv\Scripts\activate.bat

:: ---- Step 5: Install Dependencies ----
echo.
echo [5/6] Saari libraries install ho rahi hain (isme 2-5 min lag sakte hain)...
pip install --upgrade pip
pip install -r requirements.txt
echo.
echo  Saari dependencies install ho gayi!

:: ---- Step 6: Setup .env file ----
echo.
echo [6/6] .env configuration setup...
if not exist ".env" (
    copy ".env.example" ".env"
    echo.
    echo  =======================================================
    echo   IMPORTANT: .env FILE MEIN APNI DETAILS BHARO!
    echo  =======================================================
    echo.
    echo  Ye file open hogi. Inhe fill karo:
    echo.
    echo   USER_NAME=Harshit       ^<-- apna naam
    echo   GEMINI_API_KEY=...      ^<-- Google AI Studio se free key lo
    echo                               https://aistudio.google.com/apikey
    echo.
    echo  Save karke close karo, phir Enter dabaao.
    echo.
    notepad .env
    pause
) else (
    echo  .env file pehle se set hai!
)

:: ---- Step 7: Set Password ----
echo.
echo  =====================================================
echo   PASSWORD SETUP (Jarvis login ke liye)
echo  =====================================================
echo  Ek naya password set karo Jarvis ke liye:
echo.
python config.py set-password

:: ---- Done! ----
echo.
echo  =====================================================
echo   SETUP COMPLETE! JARVIS RUN KARO!
echo  =====================================================
echo.
echo  Command:   cd %INSTALL_DIR%  ^&^&  venv\Scripts\activate  ^&^&  python main.py
echo.
echo  Ya shortcut use karo: start_jarvis.bat (neeche bana raha hoon)
echo.

:: Create a convenient start shortcut
echo @echo off > start_jarvis.bat
echo title RealJarvis >> start_jarvis.bat
echo cd /d "%INSTALL_DIR%" >> start_jarvis.bat
echo call venv\Scripts\activate.bat >> start_jarvis.bat
echo python main.py >> start_jarvis.bat
echo pause >> start_jarvis.bat

echo  start_jarvis.bat bana diya! Double-click karke Jarvis chalu karo.
echo.
pause
