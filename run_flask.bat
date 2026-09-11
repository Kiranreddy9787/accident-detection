@echo off
REM Launcher for the AI Accident Detection & Emergency Alert System.
REM Sets the non-secret local MySQL settings for THIS window, then starts Flask.
REM NOTE: The MySQL password is NOT hardcoded here. It is loaded from the local
REM       .env file (see .env.example) by database.py, so it is never committed.
REM       Create .env from .env.example before first run:
REM         copy .env.example .env   (then edit .env with your password)

set MYSQL_HOST=localhost
set MYSQL_PORT=3306
set MYSQL_USER=root
set MYSQL_DATABASE=accident_detection
set FLASK_SECRET_KEY=change-me-to-a-long-random-string
REM Use 0.0.0.0 only when you want to open the app from another device on this Wi-Fi.
set FLASK_HOST=0.0.0.0

python database.py
if errorlevel 1 (
    echo.
    echo MySQL connection failed - check the MYSQL_* values and your local .env file.
    pause
    exit /b 1
)

python app.py
