# Changelog

## 1.2.1 - 2026-11-04

### 中文

- 区分变更检查、全量检查和无 Git 快照；全量检查不再因为 diff 为空而中止。
- 明确只读边界：不修改源码、配置、依赖或 Git 历史；写报告前确认路径，构建/测试前说明写入、依赖、服务和网络影响并取得同意。
- 子代理改为“可用且用户允许时并行”，并强调主代理必须复核关键证据。
- 报告增加置信度字段，区分 `已验证 / 观察到 / 推断`。
- 修正 Docker 权限和递归删除的安全表述，去掉为绕过策略移动未知目录的做法。
- 不改变许可证条款。

### English

- Distinguish change review, full review, and no-Git snapshots; a full review no longer stops merely because the diff is empty.
- Clarify the read-only boundary: do not modify source, configuration, dependencies, or Git history; confirm report paths and obtain consent before builds or tests that write files, install dependencies, start services, or use the network.
- Run subagents in parallel only when available and authorized, and require the primary agent to verify key evidence.
- Add confidence to findings: `verified / observed / inferred`.
- Correct the Docker privilege and recursive-delete guidance; stop instead of moving unknown directories to bypass policy.
- No license terms changed.

## 1.2.0 - 2026-10-30

### 中文

- 项目、Skill ID、仓库目录和发布包统一更名为 `project-health`。
- 将定位从“全栈体检”扩展为“软件项目健康检查”；全栈、服务、Web / 移动客户端、数据库与容器部署都属于适用范围。
- 更新安装路径、克隆链接、签名 principal、发布包名、GitHub 描述和 topics。
- 旧仓库 URL 由 GitHub 自动重定向；历史 `v1.1.2` 发布物保持原名，不重写历史记录。
- 检查流程与报告格式不变；版本升级到 1.2.0。

### English

- Renamed the project, skill ID, repository directory, and release artifacts to `project-health`.
- Reframed the project from a full-stack check to a software-project health check; full-stack, services, web and mobile clients, databases, and containerized deployment are all in scope.
- Updated install paths, clone URLs, signing principal, artifact names, GitHub description, and topics.
- The old repository URL redirects automatically; the historical `v1.1.2` release keeps its original asset names.
- The review workflow and report format are unchanged; bumped the version to 1.2.0.

## 1.1.2 - 2026-10-29

### 中文

- 新增 OpenSSH Ed25519 发布签名：`release-signing-key.pub`、`allowed_signers`、`SIGNING.md` / `SIGNING.en.md`。
- 下载说明补充 SHA256SUMS、`SHA256SUMS.sig` 和跨平台验证命令。
- 明确签名私钥只保存在维护者本机，不进入仓库、Release 或 CI 日志。
- 发布 zip 使用 ASCII 文件名 `fullstack-health-check-<version>.zip`，便于跨平台下载和校验；中文文件名作为本地副本保留。
- 版本升级到 1.1.2。

### English

- Added OpenSSH Ed25519 release signing: `release-signing-key.pub`, `allowed_signers`, and `SIGNING.md` / `SIGNING.en.md`.
- Expanded download instructions with `SHA256SUMS`, `SHA256SUMS.sig`, and cross-platform verification commands.
- Documented that the private key stays on the maintainer's machine and never enters the repository, a Release, or CI logs.
- Release zips use the ASCII name `fullstack-health-check-<version>.zip` for cross-platform downloads; the Chinese filename remains as a local copy.
- Bumped the version to 1.1.2.

## 1.1.1 - 2026-10-29

### 中文

- 新增 `references/platform-commands.md` 与英文版，按 Windows PowerShell 5.1/7、macOS/Linux bash/zsh、WSL2 分列常用命令。
- 覆盖路径与环境变量、Python/Node/Java、Docker/端口/进程、权限与清理、退出码与命令串联、WSL2 路径与 socket 差异。
- 在 `README` 和 `SKILL` 中加入平台命令对照入口，避免用户把不同 shell 的命令混用。
- 校验脚本的必需文件清单加入平台命令手册；不改变核心检查流程。

### English

- Added `references/platform-commands.md` and its English companion with side-by-side commands for Windows PowerShell 5.1/7, macOS/Linux bash/zsh, and WSL2.
- Covers paths and environment variables, Python/Node/Java, Docker/ports/processes, permissions and cleanup, exit codes and command chaining, and WSL2 path/socket differences.
- Linked the command guide from the README and SKILL files so users do not mix shells.
- Added the platform guide to the verifier's required-file list; the core review workflow is unchanged.

## 1.1.0 - 2026-10-29

### 中文

- 新增完整英文文档：`README.en.md`、`SKILL.en.md`、商业授权、贡献指南、脱敏说明和三份 `references/*.en.md`。
- 新增 Python 3.9+ 标准库实现的跨平台脚本：`check_redaction.py` 与 `verify_package.py`。
- 保留 PowerShell 5.1/7 脚本作为 Windows 的第二条自检路径。
- 新增 GitHub Actions，在 Windows、macOS、Ubuntu 上以 Python 3.9 和 3.12 验证包完整性；Windows 额外跑 PowerShell 5.1 与 PowerShell 7。
- 新增平台支持矩阵、`.gitattributes`、`.gitignore`、`.editorconfig` 和 `SECURITY.md`。
- 核心技能保持纯 Markdown + Git；Windows 专用命令继续隔离在 `references/windows-pitfalls*.md`。
- 说明 GitHub 许可证识别不支持 PolyForm 时显示 `NOASSERTION / Other` 属于正常现象，以 `LICENSE` 原文为准。

### English

- Added complete English companions for the README, skill body, commercial terms, contributing guide, sanitization notes, and all three reference documents.
- Added cross-platform Python 3.9+ standard-library tools: `check_redaction.py` and `verify_package.py`.
- Kept the PowerShell 5.1/7 scripts as a second Windows verification path.
- Added GitHub Actions for Windows, macOS, and Ubuntu with Python 3.9 and 3.12; Windows also runs PowerShell 5.1 and PowerShell 7.
- Added a platform support matrix, `.gitattributes`, `.gitignore`, `.editorconfig`, and `SECURITY.md`.
- The core skill remains plain Markdown plus Git; Windows-only commands stay isolated in `references/windows-pitfalls*.md`.
- Documented that GitHub may show `NOASSERTION / Other` for PolyForm because it is not in GitHub's recognized license list; `LICENSE` remains controlling.

## 1.0.0 - 2026-09-04 内部整理 / 2026-10-29 公开发布

- 从内部全栈体检技能整理出公开版。
- 移除个人路径、项目/客户标识、内部平台名称、真实域名与内网地址、密钥和具体事故数据。
- 保留全栈检查流程、Windows 环境坑、纠错与正反例验证纪律、安全底线。
- 新增 `references/windows-pitfalls.md`、`references/verification-playbook.md`、`references/report-template.md`。
- 新增 `scripts/check-redaction.ps1`，自带正反例自检。
- 新增 `scripts/verify-package.ps1`，检查文件完整性、UTF-8 无 BOM、相对链接和脱敏扫描。
- 采用 PolyForm Noncommercial License 1.0.0；商业授权可协商。
- 补充商业授权联系邮箱。
