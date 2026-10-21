@echo off
rem Packages the launcher into dist\RihuClientLauncher.exe
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install --quiet -r requirements.txt pyinstaller
pyinstaller --noconfirm --onefile --noconsole --name RihuClientLauncher ^
  --hidden-import keyring.backends.Windows --collect-submodules keyring.backends ^
  run_launcher.py
echo.
echo Done. Your program is in the dist folder: dist\RihuClientLauncher.exe
pause
