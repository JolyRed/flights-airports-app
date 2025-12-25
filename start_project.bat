@echo off
title AviaData Pro Launcher
echo ========================================
echo    Starting "AviaData Pro" Application
echo ========================================
echo.

:: Проверка наличия Python через launcher (py)
py -V >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python Launcher (py) not found.
    echo.
    echo Install Python from https://www.python.org/downloads/
    echo Make sure to check "Install launcher for all users" and "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo Python Launcher found. Using 'py' command.
echo.

:: Создание виртуального окружения
if not exist venv (
    echo Creating virtual environment...
    py -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Активация виртуального окружения
call venv\Scripts\activate.bat

:: Установка зависимостей через py -m pip
echo Installing required packages...
py -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    echo Check your internet connection and try again.
    pause
    exit /b 1
)

:: Загрузка данных в базу
if not exist database.db (
    echo.
    echo Loading data into database (first run only, may take 5-10 minutes)...
    py data_loader.py
    if errorlevel 1 (
        echo ERROR: Data loading failed.
        pause
        exit /b 1
    )
    echo.
) else (
    echo Database already exists - skipping data load.
)

:: Запуск приложения
echo.
echo ========================================
echo SUCCESS! Application is running
echo ========================================
echo Open your browser and go to:
echo http://127.0.0.1:8000
echo.
echo To stop the server, press Ctrl+C
echo ========================================
echo.

py -m uvicorn main:app --reload

pause
