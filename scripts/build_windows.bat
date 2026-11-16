@echo off
setlocal
cd /d %~dp0..
cd frontend
call npm install
if errorlevel 1 exit /b 1
call npm run build
if errorlevel 1 exit /b 1
cd ..ackend
py -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
py -m PyInstaller --noconfirm --clean --onefile --name FinancePresentation --add-data "static;static" --collect-all pptx --collect-all pandas --collect-all openpyxl --collect-all sqlalchemy run.py
if errorlevel 1 exit /b 1
echo EXE: backend\dist\FinancePresentation.exe
