# lux_net dev 参考记录

参考对象：`tmzncty/lux_net` 的 `dev` 分支，观察时间：2026-06-24。

本项目只参考其工程组织方式，不复制或复刻任何验证码自动求解能力。

可借鉴点：

- 将工具能力拆成清晰模块，并通过统一入口暴露；
- 使用持久 session、状态恢复、诊断报告来支撑长流程调试；
- 将安全边界和工具策略写进文档与运行时检查；
- release 前跑 smoke/regression；
- 把报告、配置样例、使用说明作为发布资产的一部分。

落地到 `slider-captcha-lab` 的改动：

- 新增 CDP 授权诊断 CLI；
- CDP 输出可进入综合报告中心；
- smoke/regression 覆盖 CDP 诊断；
- README 明确 CDP 诊断范围和非绕过边界。

