@echo off

:: Check if Python is installed
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python and try again.
    exit /b 1
)

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies. Please check the requirements.txt file.
    exit /b 1
)

:: Run the main script
echo Running main script...
py src/app.py
if %errorlevel% neq 0 (
    echo Failed to run the main script.
    exit /b 1
)

echo Script completed successfully.