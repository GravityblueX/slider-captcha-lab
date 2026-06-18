from __future__ import annotations

import importlib.util
import json
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    'liuhen.py', 'slider_lab.py', 'authorized_gui_tester.py', 'behavior_gui.py', 'risk_gui.py', 'report_center.py',
    'requirements.txt', 'DISCLAIMER.md', 'demo/event_diagnostics.html', 'demo/event_diagnostics.js',
    'src/trajectory.py', 'src/browser_context.py', 'src/human_behavior.py', 'src/risk_analyzer.py', 'src/network_diagnostics.py'
]
REQUIRED_MODULES = ['matplotlib', 'playwright', 'pandas']

def module_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None

def check_playwright_browser() -> dict[str, Any]:
    try:
        code = "from playwright.sync_api import sync_playwright;\nwith sync_playwright() as p:\n b=p.chromium.launch(headless=True); b.close(); print('ok')"
        r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=25)
        return {'ok': r.returncode == 0, 'stdout': r.stdout.strip(), 'stderr': r.stderr.strip()[-800:]}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def check_network() -> dict[str, Any]:
    out = {}
    for name, url in {'example': 'https://example.com', 'ipify': 'https://api.ipify.org?format=json'}.items():
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                out[name] = {'ok': True, 'status': getattr(r, 'status', None)}
        except Exception as e:
            out[name] = {'ok': False, 'error': str(e)}
    return out

def run_check() -> dict[str, Any]:
    modules = {m: module_exists(m) for m in REQUIRED_MODULES}
    files = {f: (ROOT / f).exists() for f in REQUIRED_FILES}
    py_ok = sys.version_info >= (3, 10)
    pw = check_playwright_browser() if modules.get('playwright') else {'ok': False, 'error': 'playwright not installed'}
    net = check_network()
    score = 100
    if not py_ok: score -= 25
    score -= sum(10 for ok in modules.values() if not ok)
    score -= sum(5 for ok in files.values() if not ok)
    if not pw.get('ok'): score -= 15
    if not all(v.get('ok') for v in net.values()): score -= 8
    score = max(0, score)
    suggestions = []
    if not py_ok: suggestions.append('安装 Python 3.10 或更高版本。')
    missing_modules = [m for m, ok in modules.items() if not ok]
    if missing_modules: suggestions.append('运行：pip install -r requirements.txt')
    if not pw.get('ok'): suggestions.append('运行：playwright install chromium')
    missing_files = [f for f, ok in files.items() if not ok]
    if missing_files: suggestions.append('项目文件不完整，建议重新 clone 仓库。缺失：' + ', '.join(missing_files[:8]))
    return {
        'score': score,
        'verdict': 'ready' if score >= 85 else 'needs_fix' if score >= 60 else 'broken',
        'system': {'python': sys.version, 'platform': platform.platform(), 'executable': sys.executable},
        'modules': modules,
        'files': files,
        'playwright_chromium': pw,
        'network': net,
        'suggestions': suggestions,
    }

if __name__ == '__main__':
    print(json.dumps(run_check(), ensure_ascii=False, indent=2))
