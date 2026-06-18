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
python -m pip install -r requirements.txt
python -m playwright install chromium
python scripts\smoke_check.py
pyinstaller --clean --onefile --windowed --name LiuHen ^
  --hidden-import slider_lab ^
  --hidden-import authorized_gui_tester ^
  --hidden-import risk_gui ^
  --hidden-import behavior_gui ^
  --hidden-import report_center ^
  --hidden-import src.trajectory ^
  --hidden-import src.analyzer ^
  --hidden-import src.browser_context ^
  --hidden-import src.human_behavior ^
  --hidden-import src.risk_analyzer ^
  --hidden-import src.network_diagnostics ^
  --hidden-import playwright.sync_api ^
  liuhen.py
xcopy /E /I /Y demo dist\demo >nul
xcopy /E /I /Y src dist\src >nul
copy slider_lab.py dist\slider_lab.py >nul
copy authorized_gui_tester.py dist\authorized_gui_tester.py >nul
copy risk_gui.py dist\risk_gui.py >nul
copy behavior_gui.py dist\behavior_gui.py >nul
copy report_center.py dist\report_center.py >nul
copy DISCLAIMER.md dist\DISCLAIMER.md >nul
dist\LiuHen.exe --smoke-check

echo.
echo Build finished.
echo EXE path: dist\LiuHen.exe
echo Chinese name: 留痕
pause
