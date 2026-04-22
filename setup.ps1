# =============================================================
#  topic-to-youtube-video  一鍵安裝腳本 (Windows PowerShell)
# =============================================================
#  功能：
#    1. 檢查 Python / PowerPoint 是否存在
#    2. 安裝 Python 套件 (requirements.txt)
#    3. 透過 winget 安裝 FFmpeg
#    4. 把 skills/topic-to-youtube-video 複製到 ~/.claude/skills/
#
#  使用方式（在 repo 根目錄執行）：
#    powershell -ExecutionPolicy Bypass -File setup.ps1
# =============================================================

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "===== topic-to-youtube-video Setup =====" -ForegroundColor Cyan
Write-Host "Repo path: $RepoRoot"
Write-Host ""

# ---------- 1. 檢查 Python ----------
Write-Host "[1/4] 檢查 Python..." -ForegroundColor Yellow
try {
    $pyVer = & python --version 2>&1
    Write-Host "       ✓ $pyVer"
} catch {
    Write-Host "       ✗ 找不到 python，請先安裝 Python 3.10+  https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# ---------- 2. 檢查 PowerPoint ----------
Write-Host "[2/4] 檢查 Microsoft PowerPoint..." -ForegroundColor Yellow
$pptRegPath = "HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration"
$hasPPT = $false
try {
    $null = New-Object -ComObject PowerPoint.Application -ErrorAction Stop
    $hasPPT = $true
    Write-Host "       ✓ PowerPoint COM 可用"
} catch {
    Write-Host "       ✗ 偵測不到 PowerPoint。此 pipeline 必須有 Microsoft PowerPoint 才能把投影片轉成 PNG。" -ForegroundColor Red
    Write-Host "         （如果確定有裝，可以忽略警告繼續。）" -ForegroundColor DarkYellow
}

# ---------- 3. 安裝 Python 套件 ----------
Write-Host "[3/4] 安裝 Python 套件..." -ForegroundColor Yellow
& python -m pip install --upgrade pip | Out-Null
& python -m pip install -r "$RepoRoot\requirements.txt"
if ($LASTEXITCODE -ne 0) {
    Write-Host "       ✗ pip install 失敗" -ForegroundColor Red
    exit 1
}
Write-Host "       ✓ 完成"

# ---------- 4. 安裝 FFmpeg ----------
Write-Host "[4/4] 檢查 / 安裝 FFmpeg..." -ForegroundColor Yellow
$ffmpegFound = $false
try {
    $null = & ffmpeg -version 2>&1
    if ($LASTEXITCODE -eq 0) { $ffmpegFound = $true }
} catch {}

# 也看 winget 安裝的固定位置
if (-not $ffmpegFound) {
    $wingetFFmpeg = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter "ffmpeg.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($wingetFFmpeg) { $ffmpegFound = $true }
}

if ($ffmpegFound) {
    Write-Host "       ✓ FFmpeg 已安裝"
} else {
    Write-Host "       → 透過 winget 安裝 FFmpeg (Gyan.FFmpeg)..."
    & winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "       ✗ FFmpeg 安裝失敗，請手動安裝：https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor Red
        exit 1
    }
    Write-Host "       ✓ FFmpeg 安裝完成"
}

# ---------- 5. 安裝 Claude Skill ----------
Write-Host ""
Write-Host "===== 安裝 Claude Skill =====" -ForegroundColor Cyan
$SkillSrc = Join-Path $RepoRoot "skills\topic-to-youtube-video"
$SkillDst = Join-Path $env:USERPROFILE ".claude\skills\topic-to-youtube-video"

if (-not (Test-Path $SkillSrc)) {
    Write-Host "✗ 找不到來源 skill：$SkillSrc" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Path (Split-Path $SkillDst) -Force | Out-Null
if (Test-Path $SkillDst) {
    Remove-Item -Path $SkillDst -Recurse -Force
}
Copy-Item -Path $SkillSrc -Destination $SkillDst -Recurse

# 把 skill 裡的路徑替換成這台機器的實際位置
$SkillMd = Join-Path $SkillDst "SKILL.md"
(Get-Content $SkillMd -Raw -Encoding UTF8) `
    -replace '%PIPELINE_PATH%', $RepoRoot `
    | Set-Content $SkillMd -Encoding UTF8

Write-Host "✓ Skill 已安裝到：$SkillDst"
Write-Host "  Pipeline 路徑已設為：$RepoRoot"

# ---------- 最後提示 ----------
Write-Host ""
Write-Host "===== 安裝完成 🎉 =====" -ForegroundColor Green
Write-Host ""
Write-Host "還差一件事：YouTube OAuth 憑證" -ForegroundColor Yellow
$clientSecret = Join-Path $RepoRoot "client_secret.json"
if (Test-Path $clientSecret) {
    Write-Host "  ✓ client_secret.json 已就位"
} else {
    Write-Host "  ✗ client_secret.json 尚未放入 $RepoRoot" -ForegroundColor Red
    Write-Host "    請依照 README.md「YouTube API 憑證申請」步驟 1-4 申請並放入該檔。"
}

Write-Host ""
Write-Host "測試：" -ForegroundColor Cyan
Write-Host "  cd `"$RepoRoot`""
Write-Host "  python make_video.py topics\kd_indicator.json"
Write-Host ""
Write-Host "或直接對 Claude Code 說：做個 RSI 的教學影片"
Write-Host ""
