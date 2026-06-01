# Fresh Installation Setup Script for Lyraerp (PowerShell)
# Run this when setting up the project on a new machine

Write-Host ""
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Lyraerp Fresh Installation Setup" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Install dependencies
Write-Host "[1/4] Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Step 2: Patch cities_light migration
Write-Host ""
Write-Host "[2/4] Patching cities_light migration..." -ForegroundColor Yellow
python patch_cities_light.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Patch script had issues, but continuing..." -ForegroundColor Yellow
}

# Step 3: Run migrations
Write-Host ""
Write-Host "[3/4] Running database migrations..." -ForegroundColor Yellow
python manage.py migrate --database=default
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Migrations failed" -ForegroundColor Red
    Write-Host "See CITIES_LIGHT_FIX.md for troubleshooting" -ForegroundColor Yellow
    exit 1
}

# Step 4: Summary
Write-Host ""
Write-Host "[4/4] Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  - Create a superuser: python manage.py createsuperuser"
Write-Host "  - Run development server: python manage.py runserver"
Write-Host ""
