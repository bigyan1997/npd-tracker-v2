@echo off
rem NPD Tracker v2 server (port 8001). Started at login by the Startup-folder
rem shortcut and, if it ever stops responding, by keep_alive.ps1.
rem If the server stops for any reason it is started again after 5 seconds.
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
:loop
rem Another copy already serving? Then this one isn't needed.
netstat -ano -p tcp | findstr "LISTENING" | findstr /c:"0.0.0.0:8001 " >nul && (
    echo NPD Tracker v2 is already running on port 8001 - nothing to do.
    exit /b 0
)
echo %date% %time% Starting NPD Tracker v2 on port 8001...
waitress-serve --listen=0.0.0.0:8001 npd_tracker.wsgi:application
echo %date% %time% Server stopped - restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto loop
