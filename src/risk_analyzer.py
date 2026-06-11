from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

@dataclass
class RiskItem:
    level: str
    category: str
    field: str
    message: str
    suggestion: str


def _get(d: dict[str, Any], path: str, default=None):
    cur = d
    for part in path.split('.'):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def analyze_fingerprint(fp: dict[str, Any]) -> dict[str, Any]:
    """Score browser/environment consistency for defensive QA.

    Input is the JSON exported by demo/event_diagnostics.html or equivalent.
    This does not spoof or modify any environment fields; it only highlights
    missing, inconsistent, or automation-looking signals.
    """
    risks: list[RiskItem] = []
    ua = str(fp.get('userAgent', ''))
    platform = str(fp.get('platform', ''))
    webdriver = fp.get('webdriver')
    languages = fp.get('languages') or []
    timezone = str(fp.get('timezone', ''))
    plugins = fp.get('plugins') or []
    mime_types = fp.get('mimeTypes') or []
    fonts = fp.get('fontsDetected') or []
    webgl = fp.get('webgl') or {}
    screen = fp.get('screen') or {}
    max_touch = fp.get('maxTouchPoints')
    hc = fp.get('hardwareConcurrency')
    mem = fp.get('deviceMemory')

    def add(level, cat, field, msg, sug):
        risks.append(RiskItem(level, cat, field, msg, sug))

    if webdriver is True:
        add('high', 'automation', 'navigator.webdriver', 'webdriver=true，明显自动化信号。', '授权测试报告中应标注自动化环境；生产防护可将其作为高风险信号之一。')
    if not ua:
        add('medium', 'fingerprint', 'userAgent', 'User-Agent 缺失。', '检查浏览器环境采集是否完整。')
    if 'Headless' in ua:
        add('high', 'automation', 'userAgent', 'UA 包含 Headless。', '生产防护可结合其他信号提高风险评分。')
    if 'Windows' in ua and platform and 'Win' not in platform:
        add('medium', 'consistency', 'ua/platform', 'UA 显示 Windows，但 platform 不像 Windows。', '检查 UA 与平台字段一致性。')
    if ('iPhone' in ua or 'Android' in ua or 'Mobile' in ua) and (not max_touch or int(max_touch) == 0):
        add('high', 'consistency', 'ua/maxTouchPoints', '移动端 UA 但 maxTouchPoints 为 0。', '移动端画像应具备触摸能力。')
    if 'Windows' in ua and max_touch and int(max_touch) > 5:
        add('low', 'consistency', 'ua/maxTouchPoints', '桌面 UA 但触摸点数量较高。', '可能是触屏设备，也可能是画像不一致，需结合其他字段。')
    if not languages:
        add('medium', 'fingerprint', 'languages', 'navigator.languages 为空。', '正常浏览器通常有语言列表。')
    if timezone in ('UTC', 'Etc/UTC'):
        add('medium', 'consistency', 'timezone', '时区为 UTC，常见于服务器/容器环境。', '结合 IP、语言、账号历史判断。')
    if len(plugins) == 0:
        add('medium', 'fingerprint', 'plugins', '插件列表为空。', '某些浏览器可能为空，但在自动化环境中更常见。')
    if len(mime_types) == 0:
        add('low', 'fingerprint', 'mimeTypes', 'MIME 类型列表为空。', '结合插件和浏览器版本判断。')
    renderer = str(webgl.get('renderer', ''))
    vendor = str(webgl.get('vendor', ''))
    if any(x.lower() in renderer.lower() for x in ['swiftshader', 'llvmpipe', 'software', 'mesa']):
        add('high', 'webgl', 'webgl.renderer', f'WebGL renderer 疑似软件/虚拟渲染：{renderer}', '生产防护可作为虚拟环境风险信号。')
    if not renderer:
        add('medium', 'webgl', 'webgl.renderer', 'WebGL renderer 缺失。', '检查 WebGL 是否被禁用或采集失败。')
    if 'Windows' in ua and fonts and not any(f in fonts for f in ['Microsoft YaHei', 'SimSun', 'Segoe UI']):
        add('medium', 'consistency', 'fonts', 'Windows UA 但未检测到常见 Windows 字体。', '检查字体与操作系统画像一致性。')
    iw, ih = screen.get('innerWidth'), screen.get('innerHeight')
    ow, oh = screen.get('outerWidth'), screen.get('outerHeight')
    if iw and ow and int(ow) < int(iw):
        add('medium', 'screen', 'outerWidth/innerWidth', 'outerWidth 小于 innerWidth，窗口尺寸关系异常。', '检查浏览器窗口环境。')
    if ih and oh and int(oh) < int(ih):
        add('medium', 'screen', 'outerHeight/innerHeight', 'outerHeight 小于 innerHeight，窗口尺寸关系异常。', '检查浏览器窗口环境。')
    if hc is not None and int(hc) <= 1:
        add('low', 'hardware', 'hardwareConcurrency', 'CPU 核心数很低。', '可能是受限环境，需结合其他信号。')
    if mem is not None:
        try:
            if float(mem) <= 1:
                add('low', 'hardware', 'deviceMemory', 'deviceMemory 很低。', '可能是低配设备或自动化环境。')
        except Exception:
            pass

    score = 100
    weights = {'high': 18, 'medium': 9, 'low': 4}
    for r in risks:
        score -= weights.get(r.level, 5)
    score = max(0, min(100, score))
    verdict = 'low_risk_observation' if score >= 80 else 'needs_review' if score >= 55 else 'high_risk_observation'
    return {
        'score': score,
        'verdict': verdict,
        'risk_count': len(risks),
        'risks': [asdict(r) for r in risks],
    }


def analyze_event_score(event_summary: dict[str, Any]) -> dict[str, Any]:
    risks: list[RiskItem] = []
    def add(level, cat, field, msg, sug): risks.append(RiskItem(level, cat, field, msg, sug))
    if event_summary.get('untrustedEvents', 0) > 0:
        add('high', 'events', 'isTrusted', '存在 isTrusted=false 的事件。', '作为脚本构造事件风险信号。')
    if event_summary.get('moveEvents', 0) < 3:
        add('medium', 'events', 'moveEvents', '移动事件数量过少。', '检查拖动链路是否完整。')
    if event_summary.get('downEvents', 0) < 1 or event_summary.get('upEvents', 0) < 1:
        add('high', 'events', 'down/up', '缺少按下或松开事件。', '完整交互应包含 down/move/up 链。')
    if event_summary.get('pointerEvents', 0) == 0 and event_summary.get('mouseEvents', 0) == 0 and event_summary.get('touchEvents', 0) == 0:
        add('high', 'events', 'eventTypes', '没有有效 pointer/mouse/touch 事件。', '检查事件监听或执行方式。')
    score = 100 - sum({'high': 20, 'medium': 10, 'low': 5}.get(r.level, 5) for r in risks)
    return {'score': max(0, score), 'risks': [asdict(r) for r in risks]}


def analyze_export(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    fp = data.get('fingerprint', data)
    event_summary = data.get('score', {})
    return {
        'fingerprint': analyze_fingerprint(fp),
        'events': analyze_event_score(event_summary) if event_summary else None,
    }

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Analyze exported fingerprint/event diagnostics JSON')
    parser.add_argument('json_file')
    args = parser.parse_args()
    print(json.dumps(analyze_export(args.json_file), ensure_ascii=False, indent=2))
