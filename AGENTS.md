# AGENTS.md — 项目健康检查常驻规则

本文件是维护者和使用本技能的 Agent 的常驻规则。`SKILL.md` 负责工作流，本文件负责每次任务都不能破的底线；用户明确指令和安全/合规要求优先。

## 每次任务先做

1. 先读 `PITFALLS.md` 中与当前任务、环境和工具相关的条目；命中就应用。
2. 确认任务属于检查、计划、修改还是发布；不要把“体检”自动升级为“修复”。
3. 检查阶段默认只读：不改源码、配置、依赖、Git 历史；不 commit、push、stash、迁移数据库或部署。
4. 写报告先确认路径；测试、构建、安装依赖、启动服务或联网前说明影响并取得同意；检查前后看 `git status --short`。
5. 计划或修改任务先做只读影响评估：改什么、为什么、影响范围、验证方式、回滚点；未确认前不动手。

## 与轻量版的路由

- 普通用户、第一次体检、要求“快速看看 / 说人话 / 能不能上线 / 交接前看看”时，默认入口是 `project-health-lite`。
- 只有用户明确要求深度审计、P0-P3、证据链、真实构建/迁移/容器回归、交付验收或安全复核时，才升级到本技能。
- 两版同时安装时，不要并行跑两套完整检查。先给轻量版结论；需要升级时说明专业版会多做哪些验证，并征得同意。
- 如果本技能已经被选中，但用户只想要快速结论，先给“三件事 + 一句话判断”，再说明可以继续展开完整证据。

## 证据与输出

- 结论必须有文件位置或命令证据；推断标为推断，不写成事实。
- 报告必须写覆盖范围和未覆盖范围；环境问题不等于 P0。
- 全量检查不以 diff 非空为前提；变更检查才要求基准点和 diff。
- 修复只做被点名条目；修复与体检报告分开提交；修完重跑回归。

## 避坑记忆

- 遇到坑就记录到 `PITFALLS.md`；先检索是否已有同类条目，重复的坑不重复追加。
- 重复坑需要补充时，只在原条目补充日期、适用范围或验证证据，不新开同义条目。
- 不删除旧条目；过时条目标 `[已过时]` 并说明原因。
- 反复出现两次以上的坑，提升为 `AGENTS.md` 规则、测试或 CI 检查，不能只留在日志里。
- 不写密钥、令牌、个人绝对路径、客户数据或未脱敏日志。

## 项目边界

- 本仓库是 `project-health` 专业版，许可是 PolyForm Noncommercial 1.0.0；不要改成可商用，或混入 lite 的 Apache-2.0 文案。
- `fullstack-health-check` 是旧仓库名的重定向，不是第三个独立项目。

## English summary

- Read `PITFALLS.md` at task start.
- Route everyday, plain-language, first-pass requests to `project-health-lite`; use this skill for explicit deep audits, P0-P3 evidence, real regression, or delivery acceptance.
- When both editions are available, do not run both full reviews in parallel. Summarize the lite result first and obtain consent before escalating.
- Review is read-only: do not edit source, configuration, dependencies, or Git history.
- Confirm report paths; obtain consent before builds, tests, installs, services, or network access.
- A health-check report is not authorization to modify code.
- Record every pitfall in `PITFALLS.md`, except duplicates; promote recurring pitfalls to rules, tests, or CI.
