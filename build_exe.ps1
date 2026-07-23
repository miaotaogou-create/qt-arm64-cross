# Build portable QtArm64Cross.exe (embed tools + Tcl/Tk)
# Requires: pip install pyinstaller
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$root = $PSScriptRoot

$pyRoot = (python -c "import sys; print(sys.base_prefix)").Trim()
$tcl = Join-Path $pyRoot "tcl\tcl8.6"
$tk = Join-Path $pyRoot "tcl\tk8.6"
$tclInit = Join-Path $tcl "init.tcl"
$tkTcl = Join-Path $tk "tk.tcl"
if (-not (Test-Path $tclInit)) { throw "missing init.tcl" }
if (-not (Test-Path $tkTcl)) { throw "missing tk.tcl" }

if (Test-Path ".\build") { Remove-Item -Recurse -Force ".\build" }
if (Test-Path ".\QtArm64Cross.exe") { Remove-Item -Force ".\QtArm64Cross.exe" }

$runPy = Join-Path $root "run.py"
$toolsDir = Join-Path $root "tools"

python -m PyInstaller --noconfirm --clean --onefile --windowed --name QtArm64Cross --distpath $root --workpath (Join-Path $root "build\pyi") --specpath (Join-Path $root "build") --add-data ($tcl + ";_tcl_data") --add-data ($tk + ";_tk_data") --add-data ($toolsDir + ";tools") $runPy

if ($LASTEXITCODE -ne 0) { throw "PyInstaller exit $LASTEXITCODE" }
$exe = Join-Path $root "QtArm64Cross.exe"
if (-not (Test-Path $exe)) { throw "exe missing" }

$len = (Get-Item $exe).Length
Write-Host ("size_bytes=" + $len)
if ($len -lt 10000000) { throw "exe too small, resources missing" }
Write-Host ("OK " + $exe + " bytes=" + $len)
