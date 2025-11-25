Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "AI Red Teaming Multi-Agent Docker Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/6] Checking Docker installation..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found. Please install Docker Desktop first." -ForegroundColor Red
    Write-Host "Download from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[2/6] Checking Docker service..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "✅ Docker service is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker service is not running." -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[3/6] Navigating to project directory..." -ForegroundColor Yellow
$projectPath = "c:\Users\user\Desktop\test\agent - Copy (2)"
Set-Location $projectPath
Write-Host "✅ Working directory: $projectPath" -ForegroundColor Green

Write-Host ""
Write-Host "[4/6] Building Kali Linux container..." -ForegroundColor Yellow
Write-Host "⏳ This will take 10-30 minutes (downloads ~2GB and installs tools)" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to cancel, or wait..." -ForegroundColor Yellow
Write-Host ""

docker-compose build attacker

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container built successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Container build failed" -ForegroundColor Red
    Write-Host "Check your internet connection and Docker resources" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[5/6] Starting attacker container..." -ForegroundColor Yellow
docker-compose up -d attacker

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container started successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Container start failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[6/6] Verifying container status..." -ForegroundColor Yellow
$containerStatus = docker ps --filter "name=attacker" --format "{{.Names}}: {{.Status}}"

if ($containerStatus) {
    Write-Host "✅ $containerStatus" -ForegroundColor Green
} else {
    Write-Host "❌ Container not found" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Testing installed tools..." -ForegroundColor Yellow
Write-Host ""

Write-Host "Testing nmap..." -ForegroundColor Cyan
docker exec attacker nmap --version

Write-Host ""
Write-Host "Testing hydra..." -ForegroundColor Cyan
docker exec attacker hydra -h | Select-Object -First 3

Write-Host ""
Write-Host "Testing searchsploit..." -ForegroundColor Cyan
docker exec attacker searchsploit -h | Select-Object -First 3

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "✅ Docker Setup Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Container Status:" -ForegroundColor Yellow
docker ps --filter "name=attacker" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. MCP servers are already running (ports 3001, 3002)" -ForegroundColor White
Write-Host "2. Streamlit app is running (http://localhost:8501)" -ForegroundColor White
Write-Host "3. Go to browser and click 'Initialize Swarm'" -ForegroundColor White
Write-Host "4. Your agents now have full access to pentesting tools!" -ForegroundColor White
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Yellow
Write-Host "  docker ps                    " -ForegroundColor Gray
Write-Host "  docker logs attacker         " -ForegroundColor Gray
Write-Host "  docker exec -it attacker bash" -ForegroundColor Gray
Write-Host "  docker stop attacker         " -ForegroundColor Gray
Write-Host "  docker start attacker        " -ForegroundColor Gray
Write-Host ""
