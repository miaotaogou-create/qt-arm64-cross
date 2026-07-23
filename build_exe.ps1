# Build QtArm64Cross.exe next to tools/
# Requires: pip install pyinstaller
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m PyInstaller --noconfirm --clean --onefile --windowed --name QtArm64Cross --distpath . --workpath build\pyi --specpath build run.py

if (-not (Test-Path ".\QtArm64Cross.exe")) {
  Write-Host "build failed" -ForegroundColor Red
  exit 1
}
Write-Host "OK: $PSScriptRoot\QtArm64Cross.exe"
Write-Host "Keep this exe next to the tools\ folder, then double-click."
