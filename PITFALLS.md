# Agent 避坑记录 / Agent Pitfalls Log

格式：`YYYY-MM-DD | 标签 | 触发场景 | 错误做法 | 正确做法 | 验证方式`

规则：

- 任务开始时先读与当前任务、环境或工具相关的条目。
- 遇到坑就记录；先查重，重复的坑不新增同义条目。
- 重复坑需要更新时，只在原条目补充日期、适用范围或验证证据。
- 每条 1-3 行；不删除旧条目；过时条目标 `[已过时]` 并说明原因。
- 反复出现两次以上的坑，提升为 `AGENTS.md` 规则、测试或 CI 检查。
- 不写密钥、令牌、个人绝对路径、客户数据或未脱敏日志。

## 条目

- 2026-11-04 | codex-frontmatter | 给 Codex skill 写版本 | 把 `version` 放顶层，官方 `quick_validate.py` 报 Unexpected key(s) | 放 `metadata.version`，并保持仓库校验脚本可解析 | `quick_validate.py` 通过
- 2026-11-04 | review-scope | 项目没有 diff 时做全量体检 | 把 diff 为空当成没有可检查内容而中止 | 全量检查以 `HEAD` 和工作区清单为准；只有变更检查要求非空 diff | `SKILL.md` 与 README 对照
- 2026-11-04 | write-boundary | 检查阶段写报告或跑构建 | 把“只读”理解成什么都不能写，或反过来自动跑重资源命令 | 报告路径先确认；测试、构建、安装依赖、联网先取得同意，并对比前后 `git status` | `SKILL.md` 与报告模板对照
- 2026-11-04 | license-boundary | 同时维护两个相关项目 | 把 lite 的 Apache-2.0 可商用文案混进专业版，或反向收紧 lite | 专业版保持 PolyForm Noncommercial；lite 保持 Apache-2.0 可商用 | README/CHANGELOG 对照
- 2026-11-04 | tooling | Windows 上执行命令 | 在 PowerShell 会话里使用 bash 语法或把 shell 设成 bash | 每次命令显式使用 PowerShell；逐项检查多工具调用的 shell | 无 WSL/NAT 报错，退出码正常
