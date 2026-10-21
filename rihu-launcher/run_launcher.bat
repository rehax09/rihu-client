@echo off
rem Starts Rihu Client Launcher. The first run installs what it needs (needs internet).
cd /d "%~dp0"

set PYCMD=
py -3 --version >nul 2>nul && set PYCMD=py -3
if not defined PYCMD python --version >nul 2>nul && set PYCMD=python
if not defined PYCMD goto nopython

if exist .venv\Scripts\activate.bat goto havevenv
if exist .venv rmdir /s /q .venv
echo Creating a private Python environment...
%PYCMD% -m venv .venv
if errorlevel 1 goto venvfail

:havevenv
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 goto pipfail
python -m rihu_launcher
if errorlevel 1 pause
exit /b 0

:nopython
echo Python is not installed yet.
echo 1. Download it from https://www.python.org/downloads/ - not the Microsoft Store.
echo 2. In the installer, tick "Add python.exe to PATH", then press Install Now.
echo 3. Run this file again.
pause
exit /b 1

:venvfail
echo Could not create the Python environment. Tell Claude the message above.
pause
exit /b 1

:pipfail
echo Installing the launcher libraries failed. Check your internet connection.
pause
exit /b 1
