@echo off
setlocal
cd /d %~dp0
python --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found. Please install Python 3.10+ first.
  pause
  exit /b 1
)
python -m pip install --upgrade pip
python -m pip install matplotlib playwright pyinstaller
python -m playwright install chromium
pyinstaller --onefile --windowed --name LiuHen liuhen.py
xcopy /E /I /Y demo dist\demo >nul
xcopy /E /I /Y src dist\src >nul
copy slider_lab.py dist\slider_lab.py >nul
copy authorized_gui_tester.py dist\authorized_gui_tester.py >nul
copy behavior_gui.py dist\behavior_gui.py >nul
copy DISCLAIMER.md dist\DISCLAIMER.md >nul

echo.
echo Build finished.
echo EXE path: dist\LiuHen.exe
echo Chinese name: 留痕
pause
