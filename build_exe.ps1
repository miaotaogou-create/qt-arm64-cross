# Build portable QtArm64Cross.exe (single-file, PySide6)
# Requires: pip install -r requirements.txt pyinstaller
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$root = $PSScriptRoot

Get-Process QtArm64Cross -ErrorAction SilentlyContinue | Stop-Process -Force

python -c "import PySide6" 2>$null
if ($LASTEXITCODE -ne 0) { throw "need: pip install PySide6" }
python -c "import qrcode, PIL" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "installing qrcode[pil]..."
  python -m pip install "qrcode[pil]>=7.4"
  if ($LASTEXITCODE -ne 0) { throw "pip install qrcode[pil] failed" }
}

# 从 images/图标.png 生成多尺寸 app.ico + app.png
python (Join-Path $root "tools\gen_app_icon.py")
if ($LASTEXITCODE -ne 0) { throw "gen app icon failed" }

if (Test-Path ".\build") { Remove-Item -Recurse -Force ".\build" }
if (Test-Path ".\QtArm64Cross.exe") { Remove-Item -Force ".\QtArm64Cross.exe" }
Get-ChildItem -Filter "QtArm64Cross.smoke_ok" -ErrorAction SilentlyContinue | Remove-Item -Force

# Write BUILD stamp (date + short git hash)
$verDate = Get-Date -Format "yyyy.M.d"
$gitHash = "nogit"
try { $gitHash = (git -C $root rev-parse --short HEAD 2>$null).Trim() } catch {}
if (-not $gitHash) { $gitHash = "nogit" }
$verFile = Join-Path $root "crosskit\app_version.py"
$nl = [char]10
$verBody = '"""App version (BUILD rewritten by build_exe.ps1)."""' + $nl + $nl +
  'VERSION = "1.2.0"' + $nl +
  ('BUILD = "{0}+{1}"' -f $verDate, $gitHash) + $nl
[System.IO.File]::WriteAllText($verFile, $verBody, [System.Text.UTF8Encoding]::new($false))

$runPy = Join-Path $root "run.py"
$toolsDir = Join-Path $root "tools"
$imagesDir = Join-Path $root "images"
$icoPath = Join-Path $imagesDir "app.ico"
if (-not (Test-Path -LiteralPath $icoPath)) { throw "app.ico missing" }
$addDataTools = $toolsDir + ";tools"
$addDataImages = $imagesDir + ";images"

# onefile portable; do not --collect-all PySide6 (WebEngine/3D/QML bloat)
python -m PyInstaller --noconfirm --clean --onefile --windowed --noupx `
  --name QtArm64Cross `
  --icon $icoPath `
  --distpath $root `
  --workpath (Join-Path $root "build\pyi") `
  --specpath (Join-Path $root "build") `
  --hidden-import PySide6.QtCore `
  --hidden-import PySide6.QtGui `
  --hidden-import PySide6.QtWidgets `
  --hidden-import PySide6.QtSvg `
  --hidden-import PySide6.QtSvgWidgets `
  --hidden-import gui.app `
  --hidden-import gui.theme `
  --hidden-import crosskit.resources `
  --hidden-import qrcode `
  --hidden-import qrcode.image.pil `
  --hidden-import PIL `
  --hidden-import PIL.Image `
  --exclude-module numpy `
  --exclude-module lxml `
  --exclude-module tkinter `
  --exclude-module matplotlib `
  --exclude-module PySide6.scripts `
  --exclude-module PySide6.QtWebEngineCore `
  --exclude-module PySide6.QtWebEngineWidgets `
  --exclude-module PySide6.QtWebEngineQuick `
  --exclude-module PySide6.Qt3DCore `
  --exclude-module PySide6.Qt3DRender `
  --exclude-module PySide6.Qt3DExtras `
  --exclude-module PySide6.QtQuick `
  --exclude-module PySide6.QtQml `
  --exclude-module PySide6.QtMultimedia `
  --exclude-module PySide6.QtBluetooth `
  --exclude-module PySide6.QtPdf `
  --exclude-module PySide6.QtSql `
  --exclude-module qrcode.tests `
  --add-data $addDataTools `
  --add-data $addDataImages `
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
try { Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue } catch { Write-Host "cleanup tmp skipped" }

Write-Host "=== gui launch ==="
$g = Start-Process -FilePath $exe -PassThru -WorkingDirectory $root
Start-Sleep -Seconds 4
if ($g.HasExited) { throw "GUI exited early code=$($g.ExitCode)" }
Stop-Process -Id $g.Id -Force
Write-Host "GUI_ALIVE_OK"

$len = (Get-Item $exe).Length
Write-Host ("OK " + $exe + " bytes=" + $len + " mb=" + [math]::Round($len / 1MB, 1))
