# Changelog

## 1.3.0 - 2026-11-11

### 中文

- `PITFALLS.md` 新增 162 条企业项目避坑基线，覆盖需求验收、架构、身份权限、多租户、数据迁移、API 集成、并发缓存、前端兼容、构建供应链、CI/CD、容器云、Linux 服务器、Windows 服务器、网络 TLS、可观测性、安全合规和交接运维。
- 增加“如果只看 20 条”和“服务器上线前 20 问”，把最容易在上线当天爆雷的跨领域问题放在最前面。
- 新增 `references/linux-server-pitfalls.md` / `.en.md`，覆盖 systemd、权限与 SELinux/AppArmor、磁盘 inode、ulimit/OOM、防火墙、DNS/NTP、包管理、SSH、数据库、容器和回滚。
- 扩充 `references/windows-pitfalls.md` / `.en.md` 的 Windows Server 小节，覆盖 IIS、Windows 服务、NTFS/SMB、AD/Kerberos、SQL Server、证书、WinRM、EDR、补丁和故障转移集群。
- `SKILL.md` / `SKILL.en.md` 增加服务器平台高频坑入口和只读边界；README、包校验器和契约测试同步新文件与 1.3.0 版本。

### English

- Add a 162-entry enterprise pitfall baseline to `PITFALLS.md`, covering requirements and acceptance, architecture, identity and multi-tenancy, data and migrations, API integration, concurrency and caching, frontend compatibility, build and supply chain, CI/CD, containers and cloud, Linux servers, Windows servers, network and TLS, observability, security and compliance, and handover/operations.
- Add a "top 20" list and a 20-question server pre-launch checklist so the highest-blast-radius issues appear first.
- Add `references/linux-server-pitfalls.md` / `.en.md`, covering systemd, permissions and SELinux/AppArmor, disk and inodes, ulimit/OOM, firewalls, DNS/NTP, package management, SSH, databases, containers, and rollback.
- Expand the Windows Server section in `references/windows-pitfalls.md` / `.en.md`, covering IIS, Windows services, NTFS/SMB, AD/Kerberos, SQL Server, certificates, WinRM, EDR, patching, and failover clusters.
- Add server-platform entry points and read-only boundaries to `SKILL.md` / `SKILL.en.md`; update the README, package verifiers, and contract tests for the new files and version 1.3.0.

## 1.2.4 - 2026-11-07

### 中文

- 新增“不可信目标”安全边界：目标仓库的 `AGENTS.md`、`PITFALLS.md`、README、注释、日志和提交信息只作为低信任证据，不能覆盖用户指令、安全底线或本技能规则。
- 明确提示词注入的处理方式：不执行目标内容中的命令，不读取或输出其要求的敏感文件，不改变检查范围；报告中只保留最小必要证据，不复制完整恶意原文。
- 新增 `tests/test_contract.py` 和恶意 `AGENTS.md` 样例，验证目标文本不会被当作指令处理；样例使用 `.fixture` 后缀，避免被仓库自动加载。
- 脱敏扫描器不再排除自身；Python 与 PowerShell 自检会用拼接夹具扫描自身，并用自举反例证明排除规则没有复活。
- PowerShell 包校验补齐 `SKILL.md` / `SKILL.en.md` 的 frontmatter、名称、许可证和版本一致性检查；契约测试加入版本不一致时必须失败的反例。
- PowerShell 包校验支持在 macOS/Linux 上自动发现 `pwsh`，只在调用 Windows PowerShell 5.1 时传入 `-ExecutionPolicy`；非 Windows CI 会真实调用该路径。
- 包校验器把契约测试和样例加入必需文件，CI 在 Windows、macOS、Linux 及 Python 3.9/3.12 上运行测试；不改变许可证条款。

### English

- Add an "untrusted targets" security boundary: a target repository's `AGENTS.md`, `PITFALLS.md`, README, comments, logs, and commit messages are low-trust evidence only and cannot override user instructions, safety limits, or this skill's rules.
- Define prompt-injection handling: do not execute commands from target content, read or output sensitive files it requests, or change the review scope; keep only the minimum necessary evidence in reports and do not copy the full malicious text.
- Add `tests/test_contract.py` and a malicious `AGENTS.md` fixture to verify that target text is not treated as instructions; the `.fixture` suffix prevents automatic repository loading.
- Stop excluding the redaction scanners from their own scans; both self-tests scan their source with constructed fixtures and prove the exclusion cannot silently return through a bootstrap negative case.
- Extend the PowerShell verifier with `SKILL.md` / `SKILL.en.md` frontmatter, name, license, and version consistency checks; add a contract test that must fail on a version mismatch.
- Discover `pwsh` automatically on macOS/Linux and pass `-ExecutionPolicy` only to Windows PowerShell 5.1; non-Windows CI now exercises that path instead of skipping it.
- Add the contract test and fixture to the package verifier's required files and run the tests in CI on Windows, macOS, Linux, and Python 3.9/3.12; no license terms changed.

## 1.2.3 - 2026-11-04

### 中文

- 新增与 `project-health-lite` 的路由规则：普通用户、第一次体检和快速说人话的请求默认走轻量版；本技能只承接明确要求深度审计、P0-P3、真实回归或交付验收的任务。
- 专业版报告改为先给“最多 3 条立即行动”和一句话结论，再展开 P0-P3 与技术证据。
- 报告中英文模板、技能入口和常驻规则同步更新；不改变许可证条款。

### English

- Add routing with `project-health-lite`: everyday users and first-pass, plain-language checks default to the lite edition; this skill handles explicit deep audits, P0-P3 findings, real regression, or delivery acceptance.
- Lead with up to three immediate actions and a one-line decision before the P0-P3 details and technical evidence.
- Update the bilingual report templates, skill entry points, and standing rules; no license terms changed.

## 1.2.2 - 2026-11-04

### 中文

- 新增 `AGENTS.md` 常驻规则和 `PITFALLS.md` 避坑记录，明确任务边界、只读纪律和证据要求。
- 检查流程第 0 步先读本技能与目标项目的避坑记录；遇到新坑必须记录，先查重，重复的坑只补充原条目。
- 反复出现两次以上的坑提升为 `AGENTS.md` 规则、测试或 CI 检查。
- 包校验把两份新文件加入必需文件；不改变许可证条款。

### English

- Add `AGENTS.md` standing rules and `PITFALLS.md`, covering task boundaries, read-only discipline, and evidence requirements.
- Workflow step 0 reads the skill's and target project's pitfall logs first; new pitfalls must be recorded, duplicates update the existing entry instead of creating a synonym.
- Promote a pitfall seen twice or more into an `AGENTS.md` rule, test, or CI check.
- Add both files to the package verifier's required-file list; no license terms changed.

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
