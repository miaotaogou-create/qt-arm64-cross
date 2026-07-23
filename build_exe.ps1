# Build portable QtArm64Cross.exe (single-file)
# Tcl cannot use init.tcl under C:\WINDOWS\TEMP; run.py copies tcl/tk to %LOCALAPPDATA%.
# Requires: pip install pyinstaller
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$root = $PSScriptRoot

Get-Process QtArm64Cross,diag_tk -ErrorAction SilentlyContinue | Stop-Process -Force

$pyRoot = (python -c "import sys; print(sys.base_prefix)").Trim()
$tcl = Join-Path $pyRoot "tcl\tcl8.6"
$tk = Join-Path $pyRoot "tcl\tk8.6"
if (-not (Test-Path (Join-Path $tcl "init.tcl"))) { throw "missing init.tcl" }
if (-not (Test-Path (Join-Path $tk "tk.tcl"))) { throw "missing tk.tcl" }

if (Test-Path ".\build") { Remove-Item -Recurse -Force ".\build" }
if (Test-Path ".\QtArm64Cross.exe") { Remove-Item -Force ".\QtArm64Cross.exe" }
Get-ChildItem -Filter "QtArm64Cross.smoke_ok" -ErrorAction SilentlyContinue | Remove-Item -Force
# 清掉错误字面量目录
if (Test-Path ".\`$LOCALAPPDATA") { Remove-Item -Recurse -Force ".\`$LOCALAPPDATA" }

$runPy = Join-Path $root "run.py"
$toolsDir = Join-Path $root "tools"

# Default onefile temp is fine; run.py relocates Tcl/Tk out of WINDOWS\TEMP
python -m PyInstaller --noconfirm --clean --onefile --windowed --noupx --name QtArm64Cross --distpath $root --workpath (Join-Path $root "build\pyi") --specpath (Join-Path $root "build") --add-data ($tcl + ";_tcl_data") --add-data ($tk + ";_tk_data") --add-data ($toolsDir + ";tools") $runPy

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
  if ($txt -notmatch 'TK_OK') { throw "smoke content bad: $txt" }
  # Must not keep using WINDOWS\TEMP as TCL_LIBRARY
  if ($txt -match 'TCL_LIBRARY=.*\\WINDOWS\\TEMP\\') { throw "TCL still in WINDOWS\TEMP: $txt" }
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

# GUI process should stay up without error dialog (best-effort: alive > 3s)
Write-Host "=== gui launch ==="
$g = Start-Process -FilePath $exe -PassThru -WorkingDirectory $root
Start-Sleep -Seconds 4
if ($g.HasExited) { throw "GUI exited early code=$($g.ExitCode)" }
Stop-Process -Id $g.Id -Force
Write-Host "GUI_ALIVE_OK"

$len = (Get-Item $exe).Length
Write-Host ("OK " + $exe + " bytes=" + $len)
