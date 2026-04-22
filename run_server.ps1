# ================================================
#  啟動 video-pipeline API 伺服器
#
#  用法：
#    # 不設 token（只在區網 / Tailscale 用）
#    powershell -ExecutionPolicy Bypass -File run_server.ps1
#
#    # 設 token（暴露到公網時強烈建議）
#    $env:VP_TOKEN="你自己設一個夠長的隨機字串"
#    powershell -ExecutionPolicy Bypass -File run_server.ps1
# ================================================
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

if (-not $env:VP_TOKEN) {
    Write-Host "[WARN] VP_TOKEN 未設定，API 會在沒有授權下開放" -ForegroundColor Yellow
    Write-Host "       只在區網 / Tailscale 內用沒關係；要暴露到公網請先設 VP_TOKEN。" -ForegroundColor Yellow
}

$port = if ($env:VP_PORT) { $env:VP_PORT } else { 8000 }
Write-Host "Starting API server on http://0.0.0.0:$port ..." -ForegroundColor Cyan
& python api_server.py --port $port
