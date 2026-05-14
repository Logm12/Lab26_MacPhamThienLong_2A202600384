# Fix DNS and Proxy resolution for Node.js on Windows
$env:NODE_OPTIONS="--dns-result-order=ipv4first"
$env:NO_PROXY="*"

# Ensure Python user-site scripts directory is in PATH so spawned Node processes can resolve fastmcp
$env:PATH = "C:\Users\longm\AppData\Roaming\Python\Python313\Scripts;" + $env:PATH

# Completely bypass Authentication and OAuth metadata discovery
$env:DANGEROUSLY_OMIT_AUTH="true"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ">>> PREPARING ENVIRONMENT & CLEANING PORTS..." -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Auto-cleanup hanging processes on ports 3000 and 3001 to avoid PORT IN USE
$ports = 3000, 3001
foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        Write-Host "Cleaning up existing process on port $port..." -ForegroundColor Yellow
        foreach ($conn in $connections) {
            if ($conn.OwningProcess -gt 0) {
                Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host ">>> STARTING NATIVE FASTMCP INSPECTOR..." -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Ports cleaned, auth bypassed, launching..." -ForegroundColor Yellow

# Run native FastMCP dev tool forcing official default ports
& "C:\Users\longm\AppData\Roaming\Python\Python313\Scripts\fastmcp.exe" dev inspector mcp_server.py --ui-port 3000 --server-port 3001

Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
