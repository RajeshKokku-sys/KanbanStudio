# PowerShell script to start the Project Management MVP containers (backend & frontend)
# Builds images if they are missing or have changed.

Write-Host "Starting backend and frontend containers..."
docker compose up -d --build
