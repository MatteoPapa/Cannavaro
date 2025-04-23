@echo off
setlocal

:: Ask the user about retrieving the previous session
set /p choice=Do you want to retrieve the previous session? (y/n): 

:: Check user's response
if /i "%choice%"=="n" (
    echo Starting a new session...
    if exist ".\backend\services.yaml" (
        del /q ".\backend\services.yaml"
        echo Deleted ./backend/services.yaml
    ) else (
        echo No existing ./backend/services.yaml to delete
    )
) else (
    echo Retrieving previous session...
)

:: Stop existing Docker containers
echo Stopping any running containers...
docker compose down

:: Build and start containers in foreground (same terminal)
echo Starting containers...
docker compose up --build
