@echo off
REM Stops the NPD Tracker v2 dev servers started by start-dev.bat (they run
REM hidden, so there's no window to close - this is how you stop them).

powershell -NoProfile -Command "$stopped = 0; Get-NetTCPConnection -LocalPort 8010,5173 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue; $stopped++ }; if ($stopped -gt 0) { Write-Host 'NPD Tracker dev servers stopped.' } else { Write-Host 'No NPD Tracker dev servers were running.' }"

pause
