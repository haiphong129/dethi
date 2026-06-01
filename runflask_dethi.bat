@echo off
title Flask Auto Runner

echo ===============================
echo 🚀 KHOI DONG FLASK SERVER
echo ===============================
echo.

:: 1. Mo CMD tai thu muc hien tai
cd /d "%~dp0"

:: 2. Chay Flask
echo.
echo 🌐 Dang chay Flask tren http://localhost
echo (Nhan Ctrl+C de dung server)
echo.

start "" cmd /k "flask run --host=0.0.0.0 --port=80"

:: 4. Mo Chrome
timeout /t 3 >nul

start chrome http://localhost

exit
