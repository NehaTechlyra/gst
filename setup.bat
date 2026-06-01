@echo off
REM Fresh Installation Setup Script for Lyraerp
REM Run this when setting up the project on a new machine

echo.
echo ===================================
echo Lyraerp Fresh Installation Setup
echo ===================================
echo.

REM Step 1: Install dependencies
echo [1/4] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 goto :error

REM Step 2: Patch cities_light migration
echo.
echo [2/4] Patching cities_light migration...
python patch_cities_light.py
if errorlevel 1 goto :error

REM Step 3: Run migrations
echo.
echo [3/4] Running database migrations...
python manage.py migrate --database=default
if errorlevel 1 goto :error

REM Step 4: Create superuser (optional)
echo.
echo [4/4] Setup complete!
echo.
echo Next steps:
echo   - Create a superuser: python manage.py createsuperuser
echo   - Run development server: python manage.py runserver
echo.
goto :end

:error
echo.
echo ERROR: Setup failed! Check the error messages above.
echo See CITIES_LIGHT_FIX.md for troubleshooting.
exit /b 1

:end
