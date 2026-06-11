# 指纹与风控检测面覆盖矩阵

> 本文档用于防御研究、授权测试和学习。目标是帮助理解高强度风控系统通常会观察哪些信号，以及“留痕”目前可诊断哪些信号。本文不提供绕过、伪装或规避真实网站风控的方法。

## 1. 高强度风控通常不是单点检测

类似高安全系数的验证码/风控产品，通常不会只看鼠标轨迹，而是综合：

- 行为轨迹
- 事件链路
- 浏览器自动化特征
- 浏览器指纹
- 环境一致性
- 网络/TLS/HTTP2 指纹
- IP/ASN/代理信誉
- Cookie/Session/Token
- Challenge 参数
- 页面 JS 执行完整性
- 业务行为路径
- 账号历史画像
- 服务端风险模型

因此，“只补一个环境字段”没有意义。真正关键的是：**多层信号之间是否一致，且与用户历史、网络、页面流程、服务端参数链路是否匹配。**

---

## 2. 浏览器与设备指纹检测项

### 2.1 基础环境

| 检测项 | 风险点 |
|---|---|
| User-Agent | 与真实浏览器版本、系统、Client Hints 不一致 |
| Client Hints | brands/platform/mobile 与 UA 不一致 |
| navigator.webdriver | 自动化特征 |
| language/languages | 与 IP 地区、时区、Accept-Language 不一致 |
| platform/vendor | 与 UA、字体、WebGL 不一致 |
| hardwareConcurrency | 与设备画像不合理 |
| deviceMemory | 与设备画像不合理 |
| maxTouchPoints | 移动端/触摸设备声明不一致 |
| cookieEnabled | 与正常浏览器行为不一致 |
| doNotTrack | 与用户画像不一致 |

### 2.2 屏幕与窗口

| 检测项 | 风险点 |
|---|---|
| screen.width/height | 分辨率异常或数据中心常见值 |
| availWidth/availHeight | 与系统任务栏/窗口环境不合理 |
| innerWidth/innerHeight | 与 outerWidth/outerHeight 不一致 |
| devicePixelRatio | 与设备类型/分辨率不一致 |
| colorDepth/pixelDepth | 异常值或过于默认 |

### 2.3 Canvas / WebGL / Audio

| 检测项 | 风险点 |
|---|---|
| Canvas 渲染 | 与系统、字体、GPU 不一致 |
| WebGL vendor/renderer | SwiftShader、虚拟 GPU、云环境特征 |
| WebGL extensions | 与浏览器/GPU 组合不一致 |
| Audio 指纹 | 与浏览器/系统组合异常 |
| 字体渲染 | 与 OS/语言不一致 |

### 2.4 插件、MIME、权限

| 检测项 | 风险点 |
|---|---|
| plugins | 为空或与浏览器版本不符 |
| mimeTypes | 异常为空或组合不合理 |
| Permissions API | 返回值异常、自动化痕迹 |
| MediaDevices | 设备枚举异常 |
| WebRTC | IP 暴露或禁用状态异常 |

---

## 3. 事件链路与行为检测项

### 3.1 鼠标/触摸事件链

- pointerover / pointerenter
- mouseover / mouseenter
- pointerdown / mousedown
- pointermove / mousemove
- pointerup / mouseup
- click
- touchstart / touchmove / touchend

风险点：

- 事件顺序不合理
- 缺少 down/up
- 只有 move 没有 pointer/mouse 链路
- 移动端 UA 没有 touch 能力
- 桌面 UA 却表现为触摸事件
- `isTrusted=false`
- buttons/button 状态异常
- timeStamp 不连续

### 3.2 轨迹行为

- 起步延迟
- 加速/减速
- 平均速度
- 最大速度
- 加速度变化
- jerk 变化
- Y 轴抖动
- 路径长度/直线距离
- 微停顿
- 过冲回拉
- 事件采样间隔

风险点：

- 完全直线
- 完全匀速
- 时间间隔固定
- 没有末端修正
- 轨迹过短或过长
- 点数异常

---

## 4. 网络与服务端参数链路

### 4.1 网络层

| 检测项 | 风险点 |
|---|---|
| IP 国家/地区 | 与时区/语言/账号历史不一致 |
| ASN | 数据中心/代理/VPN/Tor 风险 |
| IP 历史信誉 | 失败率高、账号关联多 |
| TLS JA3/JA4 | 与 UA 声称的浏览器不一致 |
| HTTP/2 SETTINGS | 与浏览器版本不一致 |
| Header 顺序 | 非真实浏览器顺序 |
| Accept-Language | 与 navigator.languages 不一致 |

### 4.2 Token / Challenge / 参数

高强度风控通常会校验：

- challenge_id
- session_id
- nonce
- 时间戳
- 行为数据摘要
- 轨迹压缩数据
- 环境摘要
- JS 计算参数
- 参数签名
- 一次性 token
- token 与 IP/UA/指纹绑定
- token 是否过期
- token 是否重复提交
- 页面流程是否完整

风险点：

- 参数缺失
- 参数顺序/格式异常
- 时间窗口不合理
- token 重放
- challenge 与 session 不匹配
- 前端行为数据与服务端记录不一致
- 页面初始化 JS 未完整执行

---

## 5. 留痕当前覆盖情况

| 模块 | 当前覆盖 |
|---|---|
| 轨迹生成 | Bezier、加减速、抖动、微停顿、过冲回拉、多模式 |
| 人工轨迹记录 | x/y/t 采集、CSV 导出、分析回灌 |
| 事件链路诊断 | pointer/mouse/touch、isTrusted、事件顺序、事件数量 |
| 浏览器指纹诊断 | UA、webdriver、Canvas、WebGL、Audio、字体、插件、分辨率、时区 |
| 网络诊断 | TLS 版本、cipher、ALPN、证书、公网 IP 上下文 |
| 授权页面测试 | URL、selector、四种策略、结果表格、JSON 导出 |
| 行为会话测试 | 停留、鼠标游走、滚动、点击、输入、等待、HTML 报告 |

## 6. 仍需人工/服务端配合的检测面

以下内容无法仅靠本地客户端完整判断：

- 服务端 challenge 参数正确性
- token 签名算法
- JA3/JA4 服务端视角
- HTTP/2 服务端指纹完整值
- IP 信誉库结果
- 账号画像
- Cookie/Session 历史
- 业务行为风险模型
- 服务端埋点接收情况

---

## 7. 防御侧建议

1. 不要只依赖滑块轨迹。
2. 前端采集只作为信号，核心判断放服务端。
3. challenge/token 必须与 session、IP、UA、时间窗口绑定。
4. 行为、指纹、网络、账号、业务路径要综合评分。
5. 对异常进行分级处理：放行、二次验证、限速、人工审核、拒绝。
6. 日志要保存可解释的风险原因，避免误杀。

---

## 8. 留痕后续优化方向

- 环境一致性评分
- 行为会话风险摘要
- 事件链完整性报告
- 指纹字段缺失/异常提示
- 授权测试综合 HTML 报告
- 失败原因分类
- 策略矩阵与对比报告
