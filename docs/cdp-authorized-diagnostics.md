# CDP 授权诊断

`src/cdp_diagnostics.py` 用于本地、自有或明确授权页面的 CDP 会话诊断。

它会记录：

- 浏览器版本与 CDP target 摘要；
- 当前页面 URL、标题、frame 数量；
- 基础 navigator/screen/timezone/storage 诊断字段；
- Cookie 数量和 Cookie 名称；
- 多 frame、`navigator.webdriver` 等 QA 诊断建议。

它不会：

- 求解验证码；
- 绕过真实网站风控；
- 输出 Cookie 值；
- 生成第三方页面自动通过策略。

## 运行

```bash
python src/cdp_diagnostics.py examples/authorized_deep_page_profile.json --headless --out cdp-diagnostics-result.json
```

输出 JSON 可以导入 `report_center.py` 生成综合 HTML 报告。

## 接入已打开的 Chrome

如果要复用一个本地授权 Chrome 会话，可以先启动带 CDP 调试端口的 Chrome：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-authorized-chrome-cdp.ps1
```

然后在这个 Chrome 中手动登录、进入自有或明确授权的测试页面，再运行：

```bash
python src/page_probe.py examples/attached_chrome_profile.json --out page-probe-result.json
python src/cdp_diagnostics.py examples/attached_chrome_profile.json --out cdp-diagnostics-result.json
```

`examples/attached_chrome_profile.json` 的关键配置是：

```json
{
  "browser": {
    "connect_existing_chrome": true,
    "cdp_endpoint": "http://127.0.0.1:9222",
    "reuse_current_page": true
  },
  "authorized_only": true
}
```

当 `reuse_current_page` 为 `true` 时，工具会优先复用当前调试会话里的页面，不主动跳转到 `url`。如果希望自动打开 profile 里的 `url`，把它改为 `false`。

## Profile 要求

Profile 必须包含：

```json
{
  "authorized_only": true
}
```

这是硬性边界，用于避免误把工具用于未经授权目标。

## 与 CDP POC 的安全区别

本项目只吸收 CDP 的工程化思路：会话观测、target/frame 枚举、运行时状态采样、报告化留档。
它不实现滑动验证码自动求解，也不提供真实站点绕过逻辑。
