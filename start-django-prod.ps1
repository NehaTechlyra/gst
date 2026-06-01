# ----------------------------
# start-django-prod.ps1
# Starts Django Production Stack (Waitress + Nginx)
# ----------------------------

# Paths
$python = "C:\Users\lyra-two\AppData\Local\Programs\Python\Python313\python.exe"
$projectDir = "D:\Lyraerp"
$nginxExe = "C:\nginx\nginx.exe"
$nginxDir = "C:\nginx"

# Move into project
Set-Location $projectDir

# Collect static files
Write-Host "Collecting static files..."
& $python manage.py collectstatic --noinput

# Stop old servers (if running)
Write-Host "Stopping old processes..."
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "nginx" -Force -ErrorAction SilentlyContinue

# Start Django via Waitress
Write-Host "Starting Waitress (Django app server)..."
Start-Process -NoNewWindow -FilePath $python -ArgumentList "-m waitress --listen=127.0.0.1:8000 Lyraerp.wsgi:application"

# Give Waitress time to initialize
Start-Sleep -Seconds 2

# Start Nginx for reverse proxy
Write-Host "Starting Nginx..."
Start-Process -NoNewWindow -FilePath $nginxExe -WorkingDirectory $nginxDir

Write-Host "✅ Django Production Server is running at: http://localhost/"
