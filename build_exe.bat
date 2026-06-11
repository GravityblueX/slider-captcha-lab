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
python -m pip install matplotlib pyinstaller
pyinstaller --onefile --windowed --name SliderTrajectoryLab slider_lab.py
xcopy /E /I /Y demo dist\demo >nul

echo.
echo Build finished.
echo EXE path: dist\SliderTrajectoryLab.exe
echo.
pause
