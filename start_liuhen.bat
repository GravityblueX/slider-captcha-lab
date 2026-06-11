@echo off
setlocal
cd /d %~dp0

echo ========================================
echo            留痕 - 一键启动
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo [错误] 没有检测到 Python。
  echo 请先安装 Python 3.10+，并勾选 Add Python to PATH。
  pause
  exit /b 1
)

if not exist .venv (
  echo [1/4] 创建虚拟环境...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/4] 安装/检查依赖...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [3/4] 安装/检查 Playwright Chromium...
python -m playwright install chromium

echo [4/4] 启动留痕...
python liuhen.py

pause
