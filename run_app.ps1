Write-Host "Starting AI Red Teaming Multi-Agent System..." -ForegroundColor Cyan

function Test-PortInUse {
    param($Port)
    $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return $null -ne $conns
}

if (Test-PortInUse 3001) {
    Write-Host "⚠️  Port 3001 is already in use. Assuming Reconnaissance Server is running." -ForegroundColor Yellow
} else {
    Write-Host "🚀 Starting Reconnaissance Server on port 3001..." -ForegroundColor Green
    $reconProcess = Start-Process -FilePath "python" -ArgumentList "src/tools/mcp/Reconnaissance.py" -PassThru -WindowStyle Minimized
    Write-Host "   Started with PID: $($reconProcess.Id)"
}

if (Test-PortInUse 3002) {
    Write-Host "⚠️  Port 3002 is already in use. Assuming Initial Access Server is running." -ForegroundColor Yellow
} else {
    Write-Host "🚀 Starting Initial Access Server on port 3002..." -ForegroundColor Green
    $initAccessProcess = Start-Process -FilePath "python" -ArgumentList "src/tools/mcp/Initial_Access.py" -PassThru -WindowStyle Minimized
    Write-Host "   Started with PID: $($initAccessProcess.Id)"
}

Write-Host "⏳ Waiting 5 seconds for servers to initialize..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host "🚀 Starting Streamlit Frontend..." -ForegroundColor Green
streamlit run frontend/streamlit_app.py
