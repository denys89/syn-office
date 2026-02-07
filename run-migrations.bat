@echo off
REM Database Migration Runner for Synoffice
REM This script runs all pending SQL migrations

echo ========================================
echo Synoffice Database Migration Runner
echo ========================================
echo.

REM Check if PostgreSQL environment variables are set
if "%DATABASE_URL%"=="" (
    echo ERROR: DATABASE_URL environment variable not set
    echo Please set it to your PostgreSQL connection string
    echo Example: postgresql://postgres:password@localhost:5432/synoffice
    pause
    exit /b 1
)

echo Running migrations...
echo.

REM Run each migration file in order
for %%f in (infra\migrations\*.sql) do (
    echo Running migration: %%f
    psql %DATABASE_URL% -f "%%f"
    if errorlevel 1 (
        echo ERROR: Migration %%f failed
        pause
        exit /b 1
    )
    echo ✓ Completed: %%f
    echo.
)

echo.
echo ========================================
echo All migrations completed successfully!
echo ========================================
pause
