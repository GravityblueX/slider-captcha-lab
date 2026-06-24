# 留痕

**留痕** 是一个用于学习、研究、本地实验和授权测试的人类网页行为模拟与风险检查工具。

它的核心目标是：

- 模拟真实人类在网页中的操作行为；
- 检查行为轨迹、事件链和浏览器环境是否自然；
- 将测试结果可视化、日志化、报告化；
- 帮助理解网页反自动化、行为检测和环境指纹检测的基本原理。

> 本项目仅用于学习、本地实验、自有系统测试或明确授权的安全测试。请勿用于绕过任何真实网站的验证码、风控、反爬虫、访问控制或服务条款限制。

---

## 重要免责声明

本项目仅面向学习、研究、本地实验、自有系统测试和明确授权的安全测试场景。项目中涉及的轨迹生成、行为模拟、事件诊断、环境分析、授权页面测试等能力，均用于理解网页行为检测、环境指纹检测和风控评估的基本原理。

使用者不得将本项目用于任何未经授权的第三方网站测试、验证码绕过、风控规避、反爬虫绕过、批量抓取、批量下载、账号滥用、访问控制规避或其他违反法律法规、服务条款、数据协议的行为。

本项目不承诺、也不保证能够通过任何真实网站、平台或第三方验证码服务的验证。真实网站的安全策略通常包含账号、IP、Cookie、Session、Token、TLS/HTTP2 指纹、业务路径、访问频率、历史行为和服务端风控模型等多重因素，不能仅通过轨迹或环境模拟解决。

下载、运行、修改、分发或使用本项目，即表示你理解并同意：所有使用行为及其后果由使用者自行承担，项目作者和贡献者不对任何误用、滥用、未授权使用、账号封禁、法律纠纷、数据纠纷、经济损失或其他后果承担责任。详情请阅读 [DISCLAIMER.md](./DISCLAIMER.md)。

---

## 项目地址

```text
https://github.com/GravityblueX/slider-captcha-lab
```

---

## 主要功能

### 1. 轨迹实验室

入口文件：

```text
slider_lab.py
```

功能：

- 生成类似人类拖动的鼠标轨迹；
- 支持 `normal / careful / fast / hesitant` 多种行为模式；
- 模拟加速、减速、微抖动、微停顿、过冲回拉；
- 记录人工鼠标轨迹；
- 分析轨迹速度、加速度、抖动、时间间隔；
- 本地滑块模拟演示；
- 导出 CSV / PNG。

---

### 2. 授权滑块测试

入口文件：

```text
authorized_gui_tester.py
```

功能：

- 输入授权测试页面 URL；
- 输入滑块轨道 selector；
- 输入滑块按钮 selector；
- 输入成功判断 selector；
- 支持多个备用 selector，例如 `slider_selectors` / `knob_selectors` / `success_selectors`；
- 支持 iframe / 多层 frame 定位；
- 支持页面结构探测，导出 frames 与候选控件 JSON；
- 自动运行多种轨迹策略；
- 支持持久浏览器 Profile，用于保留授权测试环境中的登录态和本地存储；
- 支持加载本地 Chrome 扩展目录；
- 支持手动深层页面模式：先手动登录/跳转到授权目标页面，再继续测试；
- 表格展示通过/失败结果；
- 弹窗显示测试摘要；
- 导出 JSON 结果。

适用范围：

```text
本地页面 / 自有页面 / 明确授权的测试页面
```

---

### 3. 行为会话测试

入口文件：

```text
behavior_gui.py
```

功能：

- 编排网页行为流程；
- 模拟页面停留；
- 模拟鼠标自然游走；
- 模拟滚动；
- 模拟点击；
- 模拟逐字输入；
- 等待元素出现；
- 支持持久浏览器 Profile；
- 支持加载本地 Chrome 扩展目录；
- 支持手动深层页面模式，适合自有系统里入口较深、需要人工登录或人工导航的页面；
- 支持全局 frame 作用域，让点击、输入、等待元素动作落在授权 iframe 内；
- 导入/导出 Profile；
- 导出 HTML 测试报告。

示例行为链：

```text
打开页面 → 停留 → 鼠标游走 → 滚动 → 点击输入框 → 输入文本 → 点击按钮 → 等待结果
```

---

### 4. 风险分析中心

入口文件：

```text
risk_gui.py
```

功能：

- 导入浏览器诊断页导出的 JSON；
- 分析环境一致性；
- 分析事件链完整性；
- 检测自动化风险信号；
- 给出环境评分和事件评分；
- 展示风险项、风险等级、问题描述和建议；
- 导出 HTML 风险分析报告。

当前可检查：

- `navigator.webdriver`；
- Headless UA；
- UA 与 platform 一致性；
- 移动端 UA 与触摸能力；
- languages；
- timezone；
- plugins / mimeTypes；
- WebGL renderer；
- 字体一致性；
- 屏幕窗口尺寸关系；
- hardwareConcurrency / deviceMemory；
- pointer / mouse / touch 事件链；
- `isTrusted`；
- down / move / up 事件完整性。

---

### 5. 浏览器事件与指纹诊断页

文件：

```text
demo/event_diagnostics.html
demo/event_diagnostics.js
```

功能：

- 记录 pointer / mouse / touch 事件；
- 显示事件链完整性评分；
- 采集浏览器环境信息；
- 采集 Canvas / WebGL / Audio 指纹样本；
- 检测字体、插件、分辨率、时区等信息；
- 导出诊断 JSON，供风险分析中心使用。

---

### 6. 综合报告中心

入口文件：

```text
report_center.py
```

功能：

- 导入行为会话、授权滑块测试、风险分析、环境体检、CDP 授权诊断等 JSON；
- 自动识别报告类型与摘要；
- 生成统一 HTML 报告；
- 对报告内容进行 HTML 转义，避免测试数据中的特殊字符破坏报告结构。

---

### 7. 网络诊断

文件：

```text
src/network_diagnostics.py
```

功能：

- TLS 版本诊断；
- Cipher 信息；
- ALPN / HTTP2 协议观察；
- 证书信息；
- 公网 IP 上下文。

---

### 8. CDP 授权诊断

文件：

```text
src/cdp_diagnostics.py
```

功能：

- 连接本地、自有或明确授权页面的 Chromium CDP session；
- 可接入本机已启动的 Chrome 调试端口，复用授权测试会话、Cookie、扩展和已打开页面；
- 导出浏览器版本、target 列表、frame 摘要、运行时环境字段；
- 仅记录 Cookie 名称与数量，不记录 Cookie 值；
- 输出 JSON，可导入综合报告中心；
- 不实现验证码自动求解，不用于真实网站风控绕过。

运行：

```bash
python src/cdp_diagnostics.py examples/authorized_deep_page_profile.json --headless --out cdp-diagnostics-result.json
```

接入已打开的授权 Chrome：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-authorized-chrome-cdp.ps1
python src/page_probe.py examples/attached_chrome_profile.json --out page-probe-result.json
python src/cdp_diagnostics.py examples/attached_chrome_profile.json --out cdp-diagnostics-result.json
```

---

## 快速开始

### Windows 一键启动

下载仓库后，双击：

```text
start_liuhen.bat
```

它会自动：

1. 创建虚拟环境；
2. 安装依赖；
3. 安装 Playwright Chromium；
4. 启动 `liuhen.py`。

---

### 手动启动

```bash
pip install -r requirements.txt
playwright install chromium
python liuhen.py
```

---

## 统一启动器

入口文件：

```text
liuhen.py
```

运行：

```bash
python liuhen.py
```

打开后会看到五个入口：

```text
轨迹实验室
授权滑块测试
风险分析中心
综合报告中心
行为会话测试
```

推荐使用流程：

```text
1. 先打开「轨迹实验室」观察轨迹生成和分析效果；
2. 用「行为会话测试」编排真实人类网页操作；
3. 用「授权滑块测试」测试自有或授权页面；
4. 用「风险分析中心」分析事件链和环境自然度；
5. 用 `src/cdp_diagnostics.py` 对本地/自有/授权页面做 CDP 会话诊断；
6. 用「综合报告中心」汇总 JSON 结果并导出 HTML 留档；
7. 导出 JSON / HTML / PNG / CSV 留档。
```

---

## 浏览器 Profile 与扩展

授权滑块测试和行为会话测试都支持在 Profile JSON 中配置浏览器上下文：

```json
{
  "browser": {
    "user_data_dir": ".liuhen/profiles/default",
    "extension_paths": ["C:/path/to/your-extension"],
    "manual_navigation": true,
    "manual_wait_ms": 60000
  },
  "target": {
    "frame_chain": [
      {"selector": "iframe#outer"},
      {"url_contains": "/embedded/"}
    ]
  }
}
```

说明：

- `user_data_dir` 会创建 Chromium persistent context，用于保留自有/授权测试环境中的登录态、Cookie 和 localStorage；
- `extension_paths` 用于加载本地未打包 Chrome 扩展目录，多个扩展可用数组或 GUI 中的分号分隔；
- `manual_navigation` 开启后，浏览器会先打开起始 URL，并等待指定时间；你可以在这段时间内手动完成登录、进入深层页面或切换标签页；
- 等待结束后，工具会从当前页面继续执行动作链或滑块测试；
- `connect_existing_chrome` 会连接本机 Chrome CDP 调试端口，适合复用已经手动进入的授权测试页面；
- `reuse_current_page` 为 `true` 时，页面探测与 CDP 诊断会复用调试会话中的当前页面，不主动跳转；
- `target.frame_chain` 用于多层 iframe。每一层可使用 `selector`、`url_contains` 或 `name`；
- 滑块测试支持多个备用 selector，例如：

```json
{
  "slider_selectors": ["#slider", ".slider", "[data-testid='slider']"],
  "knob_selectors": ["#knob", ".knob", "[role='button']"],
  "success_selectors": ["#status", ".result"]
}
```

- 这些能力仅用于本地、自有或明确授权测试，不用于绕过第三方网站验证码、风控、反爬虫或访问控制。

可以用目标表面注册表复核 Profile、扩展、CDP attach、frame chain 和 selector 配置是否仍处于授权边界内：

```bash
python scripts/target_surface_registry.py
```

它会生成 `docs/target-surface-registry.md` 和 `docs/target-surface-registry.json`。

---

## 页面结构探测

当授权页面入口较深、包含 iframe、或 selector 不好找时，可以先用页面探测工具导出结构：

```bash
python src/page_probe.py examples/authorized_deep_page_profile.json --headless --out page-probe-result.json
```

它会导出：

- 当前页面 URL 和标题；
- 所有 frame 的 `index / name / url`；
- 每个 frame 的 `depth / parent_index / frame_chain / target_hint`；
- 常见按钮、输入框、可拖动元素、slider/captcha/drag 命名元素；
- 每个候选元素的建议 selector、文本、可见性、位置、评分和命中原因；
- `summary.best_candidates`，用于人工复核最值得尝试的授权 selector 线索。

GUI 中的「授权滑块测试」也提供「探测页面结构」按钮，结果会保存为 `page-probe-result.json`。

如果目标页面已经在本机授权 Chrome 中打开，可以使用：

```bash
python src/page_probe.py examples/attached_chrome_profile.json --out page-probe-result.json
```

该模式会在 JSON 中记录 `browser_session.attached_to_existing_chrome`，方便在综合报告中心区分真实 Chrome 会话和托管 Chromium 会话。

更完整的深层页面映射说明见 [docs/deep-page-map.md](./docs/deep-page-map.md)。

---

## 打包 EXE

Windows 下可以运行：

```text
build_exe.bat
```

生成：

```text
dist/LiuHen.exe
```

GitHub Actions 也会自动构建 Windows 版本，Artifact 名称：

```text
LiuHen-windows
```

---

## 开发与验证

快速静态检查：

```bash
python scripts/smoke_check.py
```

它会检查统一启动器中的入口文件、关键资源文件以及基础轨迹生成/分析是否可用。GitHub Actions 在打包 Windows EXE 前也会运行该检查。

语言原生单元测试：

```bash
python -m unittest discover -s tests
```

它会验证轨迹分析、本地授权示例 Profile 和文档中的授权使用边界，避免项目偏离“本地 / 自有 / 明确授权”的范围。

本地端到端回归检查：

```bash
python scripts/regression_check.py
```

它会使用 `examples/authorized_deep_page_profile.json` 跑本地授权滑块 demo，并验证页面结构探测能导出 frame 与候选控件。

CDP 授权诊断检查：

```bash
python src/cdp_diagnostics.py examples/authorized_deep_page_profile.json --headless --out cdp-diagnostics-result.json
```

它会导出授权页面的 CDP/session 诊断 JSON，可导入综合报告中心。

CDP attach 链路检查：

```bash
python scripts/cdp_attach_smoke.py
```

它会临时启动一个带调试端口的 Playwright Chromium，再通过 `src/chrome_session.py` 反连验证，不会触碰日常 Chrome 配置。

授权证据包：

```bash
python scripts/evidence_pack.py
python scripts/target_surface_registry.py
python scripts/evidence_manifest.py
```

它会对默认本地授权 demo 生成 `docs/authorized-evidence-pack-local-demo.json`、`docs/authorized-evidence-pack-local-demo.md`、`docs/target-surface-registry.md/json` 和 `docs/evidence-manifest.md/json`，记录 profile 边界、浏览器表面、frame 摘要、候选 selector 和 CDP 诊断摘要。该证据包只用于复核本地/自有/明确授权页面的诊断链路，不包含验证码求解、第三方绕过或 Cookie 值。

---

## 项目结构

```text
slider-captcha-lab/
├─ liuhen.py                    # 统一中文启动器
├─ slider_lab.py                # 轨迹实验室
├─ authorized_gui_tester.py     # 授权滑块测试台
├─ behavior_gui.py              # 行为会话测试台
├─ risk_gui.py                  # 风险分析中心
├─ report_center.py             # 综合报告中心
├─ start_liuhen.bat             # Windows 一键启动
├─ build_exe.bat                # Windows 打包脚本
├─ requirements.txt             # 依赖列表
├─ DISCLAIMER.md                # 免责声明
├─ demo/
│  ├─ index.html                # 本地滑块 Demo
│  ├─ style.css
│  ├─ slider.js
│  ├─ event_diagnostics.html    # 事件与指纹诊断页
│  └─ event_diagnostics.js
├─ src/
│  ├─ trajectory.py             # 轨迹生成引擎
│  ├─ analyzer.py               # 轨迹分析
│  ├─ browser_context.py        # 持久Profile与扩展上下文
│  ├─ chrome_session.py         # 已有Chrome CDP会话接入
│  ├─ page_probe.py             # 页面结构探测
│  ├─ page_targets.py           # frame与备用selector解析
│  ├─ recorder.py               # 鼠标轨迹记录
│  ├─ authorized_page_tester.py # 授权页面测试命令行工具
│  ├─ human_behavior.py         # 人类行为会话模拟
│  ├─ cdp_diagnostics.py        # CDP 授权会话诊断
│  ├─ network_diagnostics.py    # 网络诊断
│  └─ risk_analyzer.py          # 环境与事件风险分析
└─ docs/
   ├─ research-notes.md
   ├─ fingerprint-defense-matrix.md
   ├─ cdp-authorized-diagnostics.md
   └─ lux-net-dev-reference.md
```

---

## 工作原理简述

### 轨迹生成

软件会生成一串轨迹点：

```text
x 坐标 / y 坐标 / 时间戳
```

并加入：

- Bezier 曲线；
- 加速与减速；
- 微抖动；
- 微停顿；
- 过冲回拉；
- 非均匀时间间隔。

### 行为模拟

通过 Playwright 控制浏览器执行：

- 鼠标移动；
- 鼠标按下/松开；
- 滚动；
- 点击；
- 输入；
- 等待元素。

### 风险分析

通过浏览器诊断页导出的 JSON，分析：

- 环境字段是否缺失；
- 字段之间是否一致；
- 是否存在自动化特征；
- 事件链是否完整；
- 是否存在高风险环境信号。

---

## 适用场景

- Web 自动化学习；
- 鼠标轨迹研究；
- 本地滑块交互实验；
- 自有网站 QA 测试；
- 授权安全测试；
- 风控检测面学习；
- 行为数据可视化与报告生成。

---

## 不适用场景

请勿用于：

- 绕过真实网站验证码；
- 绕过风控、反爬虫或访问控制；
- 未经授权测试第三方网站；
- 批量抓取、下载或干扰第三方服务；
- 违反法律法规、服务条款或数据使用协议的行为。

---

## 免责声明

请阅读：

```text
DISCLAIMER.md
```

本项目仅用于学习、研究、本地实验、自有系统测试和明确授权的安全测试。使用者应自行确保使用场景合法合规，因误用、滥用或未授权使用造成的任何后果由使用者自行承担。

---

## 中文名

```text
留痕
```

含义：

> 鼠标划过会留下轨迹，行为发生会留下痕迹，环境暴露也会留下信号。
