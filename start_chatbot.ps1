$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $projectRoot "frontend-react"
$defaultPort = 8000
$maxPort = 8010

function Get-FreePort {
    param(
        [int]$StartPort,
        [int]$EndPort
    )

    for ($port = $StartPort; $port -le $EndPort; $port++) {
        $listener = $null
        try {
            $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), $port)
            $listener.Start()
            $listener.Stop()
            return $port
        } catch {
            if ($listener) {
                try { $listener.Stop() } catch {}
            }
        }
    }

    throw "No free port found between $StartPort and $EndPort."
}

Write-Host "Building React frontend..." -ForegroundColor Cyan
Push-Location $frontendDir
try {
    npm run build
} finally {
    Pop-Location
}

$port = Get-FreePort -StartPort $defaultPort -EndPort $maxPort
$url = "http://127.0.0.1:$port"

Write-Host "Starting chatbot server on $url ..." -ForegroundColor Cyan
$serverCommand = "cd /d `"$projectRoot`" && python -m uvicorn fastapi_server:app --host 127.0.0.1 --port $port"
Start-Process cmd.exe -ArgumentList "/k", $serverCommand -WorkingDirectory $projectRoot | Out-Null

Start-Sleep -Seconds 3
Start-Process $url | Out-Null

Write-Host "Chatbot opened at $url" -ForegroundColor Green
