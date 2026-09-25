@echo off
title RealJarvis 24/7 Always-On Daemon
echo ============================================================
echo   Starting RealJarvis 24/7 Always-On Autonomous Daemon
echo   (Runs in background without GUI - Reachable via Phone/API)
echo ============================================================
cd /d "%~dp0"

if exist venv\Scripts\python.exe (
    set PYTHON_EXE=venv\Scripts\python.exe
) else (
    set PYTHON_EXE=python
)

:loop
echo [%date% %time%] Launching RealJarvis Daemon Gateway...
%PYTHON_EXE% daemon_api_server.py
echo [%date% %time%] Daemon exited. Restarting in 5 seconds... (Press Ctrl+C to abort)
timeout /t 5 /nobreak >nul
goto loop
