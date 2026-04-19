# LUMI — Windows startup uninstaller
# Removes the Lumi startup entry created by install_startup.ps1

$vbsPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\lumi.vbs"

if (Test-Path $vbsPath) {
    Remove-Item $vbsPath -Force
    Write-Host "[OK] Lumi startup entry removed."
} else {
    Write-Host "[INFO] No startup entry found at: $vbsPath"
}
