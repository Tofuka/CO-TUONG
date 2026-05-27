@echo off
REM Build Pygame client into a single Windows executable using PyInstaller
REM Usage: run this in a cmd/powershell from the repository root.

echo Creating virtual environment (optional)...
python -m venv .venv
necho Activating virtual environment...
.venv\Scripts\activate

echo Upgrading pip and installing requirements...
python -m pip install --upgrade pip
npython -m pip install -r requirements.txt pyinstaller
n
necho Running PyInstaller (onefile, windowed)...
npyinstaller --noconfirm --onefile --windowed client.py
n
necho Build finished. The executable will be in the dist\ directory.
necho To clean build artifacts run: rmdir /s /q build dist __pycache__ && del /f /q client.spec
pause
