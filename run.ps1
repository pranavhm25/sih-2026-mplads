Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Drishti — MPLADS Risk Intelligence Platform" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "[✓] Docker detected." -ForegroundColor Green
    Write-Host "[*] Launching services at http://localhost:5173 ..." -ForegroundColor Yellow
    Write-Host "[*] Backend API docs at http://localhost:8000/docs" -ForegroundColor Yellow
    Write-Host ""
    docker compose up --build
} else {
    Write-Host "[ERROR] Docker is not installed or not found in PATH." -ForegroundColor Red
    Write-Host "Please install Docker Desktop for Windows: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}
