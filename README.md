# 留痕

**留痕** 是一个用于学习、研究、本地实验和授权测试的人类网页行为模拟与风险检查工具。

它的核心目标是：

- 模拟真实人类在网页中的操作行为；
- 检查行为轨迹、事件链和浏览器环境是否自然；
- 将测试结果可视化、日志化、报告化；
- 帮助理解网页反自动化、行为检测和环境指纹检测的基本原理。

> 本项目仅用于学习、本地实验、自有系统测试或明确授权的安全测试。请勿用于绕过任何真实网站的验证码、风控、反爬虫、访问控制或服务条款限制。

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
- 自动运行多种轨迹策略；
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

### 6. 网络诊断

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

打开后会看到四个入口：

```text
轨迹实验室
授权滑块测试
风险分析中心
行为会话测试
```

推荐使用流程：

```text
1. 先打开「轨迹实验室」观察轨迹生成和分析效果；
2. 用「行为会话测试」编排真实人类网页操作；
3. 用「授权滑块测试」测试自有或授权页面；
4. 用「风险分析中心」分析事件链和环境自然度；
5. 导出 JSON / HTML / PNG / CSV 留档。
```

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

## 项目结构

```text
slider-captcha-lab/
├─ liuhen.py                    # 统一中文启动器
├─ slider_lab.py                # 轨迹实验室
├─ authorized_gui_tester.py     # 授权滑块测试台
├─ behavior_gui.py              # 行为会话测试台
├─ risk_gui.py                  # 风险分析中心
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
│  ├─ recorder.py               # 鼠标轨迹记录
│  ├─ authorized_page_tester.py # 授权页面测试命令行工具
│  ├─ human_behavior.py         # 人类行为会话模拟
│  ├─ network_diagnostics.py    # 网络诊断
│  └─ risk_analyzer.py          # 环境与事件风险分析
└─ docs/
   ├─ research-notes.md
   └─ fingerprint-defense-matrix.md
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
