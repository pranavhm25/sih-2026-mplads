@echo off
setlocal
title Drishti Platform

echo ==========================================================
echo  Starting Drishti - MPLADS Risk Intelligence Platform
echo ==========================================================
echo.

where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not installed or not in your PATH.
    echo Please install Docker Desktop for Windows:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

echo [*] Starting containers with Docker Compose...
echo [*] Once started, access the UI at: http://localhost:5317
echo [*] Backend API docs at: http://localhost:8317/docs
echo.

docker compose up --build %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Standard 'docker compose' failed, trying legacy 'docker-compose'...
    docker-compose up --build %*
)

pause
