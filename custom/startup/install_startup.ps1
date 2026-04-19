# LUMI — Windows startup installer
# Run once as Administrator to register Lumi in Windows startup.
# Adds a hidden-window VBScript launcher so the terminal doesn't appear on login.
#
# Usage:
#   Right-click install_startup.ps1 → "Run with PowerShell" (as Administrator)
#
# To uninstall:
#   Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\lumi.vbs"

$ErrorActionPreference = "Stop"

# Resolve the actual project root (two levels up from this script's location)
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
$startBat   = Join-Path $projectDir "custom\startup\start_lumi.bat"
$startupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$vbsPath    = Join-Path $startupDir "lumi.vbs"

# VBScript wrapper: launches the .bat silently (no console window on login)
$vbsContent = @"
Set oShell = CreateObject("WScript.Shell")
oShell.Run """$startBat""", 0, False
"@

Write-Host "Project root : $projectDir"
Write-Host "Batch script : $startBat"
Write-Host "Startup entry: $vbsPath"
Write-Host ""

if (-not (Test-Path $startBat)) {
    Write-Error "Batch script not found: $startBat"
    exit 1
}

$vbsContent | Out-File -FilePath $vbsPath -Encoding ASCII -Force
Write-Host "[OK] Lumi startup entry installed."
Write-Host "     Lumi will start automatically on next Windows login."
Write-Host ""
Write-Host "To test without rebooting, run: start_lumi.bat"
