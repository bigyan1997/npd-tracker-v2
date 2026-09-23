@echo off
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
waitress-serve --listen=0.0.0.0:8001 npd_tracker.wsgi:application
