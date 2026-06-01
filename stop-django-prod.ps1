Write-Host "Stopping Django production services..."

# Stop Waitress (Python server)
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue

# Stop Nginx
Stop-Process -Name "nginx" -Force -ErrorAction SilentlyContinue

Write-Host "✅ All stopped."
