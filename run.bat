@echo off
title PrivacySwarm Unified Stack
echo ============================================================
echo   PrivacySwarm — Starting Local Stack
echo ============================================================

:: 1. Check & start Ollama
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] Ollama service is running.
) else (
    echo [..] Starting Ollama service...
    start "" "C:\Users\ophun\AppData\Local\Programs\Ollama\ollama.exe" serve
    timeout /t 2 /nobreak >nul
)

:: 2. Launch PrivacySwarm Unified Server
echo [..] Launching PrivacySwarm Server on http://localhost:8000 ...
cd /d "%~dp0"
"C:\Users\ophun\AppData\Local\Programs\Python\Python314\python.exe" server.py
pause

