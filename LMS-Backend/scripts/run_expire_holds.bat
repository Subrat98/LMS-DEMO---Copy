@echo off
REM Run from Windows Task Scheduler every 10-15 minutes.
cd /d "%~dp0\.."
call venv\Scripts\activate.bat
python manage.py expire_holds
