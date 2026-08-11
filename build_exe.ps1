# Build portable QtArm64Cross.exe (single-file, PySide6)
# Requires: pip install pyinstaller PySide6
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$root = $PSScriptRoot

Get-Process QtArm64Cross -ErrorAction SilentlyContinue | Stop-Process -Force

python -c "import PySide6" 2>$null
if ($LASTEXITCODE -ne 0) { throw "需要先 pip install PySide6" }

if (Test-Path ".\build") { Remove-Item -Recurse -Force ".\build" }
if (Test-Path ".\QtArm64Cross.exe") { Remove-Item -Force ".\QtArm64Cross.exe" }
Get-ChildItem -Filter "QtArm64Cross.smoke_ok" -ErrorAction SilentlyContinue | Remove-Item -Force

# 写入版本 BUILD（日期 + git 短 hash），便于排障认 exe
$verDate = Get-Date -Format "yyyy.M.d"
$gitHash = "nogit"
try { $gitHash = (git -C $root rev-parse --short HEAD 2>$null).Trim() } catch {}
if (-not $gitHash) { $gitHash = "nogit" }
$verFile = Join-Path $root "crosskit\app_version.py"
$verBody = @"
"""App version (BUILD rewritten by build_exe.ps1)."""

VERSION = "1.2.0"
BUILD = "$verDate+$gitHash"
"@
[System.IO.File]::WriteAllText($verFile, $verBody + "`n", [System.Text.UTF8Encoding]::new($false))

$runPy = Join-Path $root "run.py"
$toolsDir = Join-Path $root "tools"

python -m PyInstaller --noconfirm --clean --onefile --windowed --noupx `
  --name QtArm64Cross `
  --distpath $root `
  --workpath (Join-Path $root "build\pyi") `
  --specpath (Join-Path $root "build") `
  --collect-all PySide6 `
  --hidden-import gui.app `
  --hidden-import gui.theme `
  --add-data ($toolsDir + ";tools") `
  $runPy

if ($LASTEXITCODE -ne 0) { throw "PyInstaller exit $LASTEXITCODE" }
$exe = Join-Path $root "QtArm64Cross.exe"
if (-not (Test-Path $exe)) { throw "exe missing" }

function Invoke-Smoke([string]$ExePath, [string]$WorkDir) {
  $mark = Join-Path $WorkDir ((Split-Path $ExePath -Leaf) -replace '\.exe$','.smoke_ok')
  if (Test-Path $mark) { Remove-Item -Force $mark }
  $p = Start-Process -FilePath $ExePath -ArgumentList "--smoke" -PassThru -Wait -WorkingDirectory $WorkDir
  if ($p.ExitCode -ne 0) { throw "smoke exit $($p.ExitCode) for $ExePath" }
  if (-not (Test-Path $mark)) { throw "smoke mark missing for $ExePath" }
  $txt = (Get-Content $mark -Raw).Trim()
  if ($txt -notmatch 'QT_OK') { throw "smoke content bad: $txt" }
  Write-Host $txt
  Remove-Item -Force $mark -ErrorAction SilentlyContinue
}

Write-Host "=== smoke in repo ==="
Invoke-Smoke $exe $root

Write-Host "=== portable smoke (empty dir) ==="
$tmp = Join-Path $env:TEMP ("qtarm-empty-smoke-" + [guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Path $tmp | Out-Null
Copy-Item $exe (Join-Path $tmp "QtArm64Cross.exe")
Invoke-Smoke (Join-Path $tmp "QtArm64Cross.exe") $tmp
try { Remove-Item -Recurse -Force $tmp -ErrorAction Stop } catch { Write-Host "cleanup tmp skipped" }

Write-Host "=== gui launch ==="
$g = Start-Process -FilePath $exe -PassThru -WorkingDirectory $root
Start-Sleep -Seconds 4
if ($g.HasExited) { throw "GUI exited early code=$($g.ExitCode)" }
Stop-Process -Id $g.Id -Force
Write-Host "GUI_ALIVE_OK"

$len = (Get-Item $exe).Length
Write-Host ("OK " + $exe + " bytes=" + $len)
