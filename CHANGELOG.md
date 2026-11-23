# Changelog

## Unreleased

### 中文

- 调整 Agent 输出纪律：P0/P1 完整展开，P2 一行问题加一句影响/建议，P3 默认只列一行；次要点仅在影响上线判断时展开。
- 新增 DeepSeek Harness 0.2.0-rc.2 + `deepseek-flash` 的长上下文行为观察：6 次自动压缩、累计 19,969,040 token，压缩后重新读取目录和 Git 基准并确认 HEAD 未漂移。该记录等级为 `observed`，不是 `validated`；测试、构建和部署仍未执行。
- 新增从 3M 测试请求到启发式修复的决策链，记录对象映射、冒烟门禁、复取证、恢复和脱敏边界。
- 在 token-meter 估算补丁后完成第二轮 3M 回归：22 个高熵块、16,788,836 token、5 次自动压缩、零压缩/溢出错误；连续 1M 字符不可分割消息的限制仍保留为未覆盖。
- 完成不可分割消息修复：保留当前 turn surface、合并锚定与 surface 压力、并在 headless 入队前预压缩；6 个连续 1M 字符块、5,764,276 token、零压缩/溢出错误。
- 新增 `tests/agent-evals/` 行为证据入口和契约检查，继续把确定性包校验与真实 Agent 行为验证分开。

### English

- Change the agent output contract: expand P0/P1, keep P2 to one problem line plus a brief impact/recommendation, and keep P3 to one line; expand secondary items only when they change the release decision.
- Add a long-context behavior observation for DeepSeek Harness 0.2.0-rc.2 with `deepseek-flash`: 6 automatic compactions and 19,969,040 cumulative provider tokens, followed by post-compaction re-reads that confirmed the retained Git baseline. The record is `observed`, not `validated`; tests, builds, and deployment were not executed.
- Add the decision path from the 3M test request through the heuristic fix, covering object mapping, smoke gates, re-acquisition, restoration, and sanitization boundaries.
- Complete a second 3M regression after the token-meter patch: 22 high-entropy blocks, 16,788,836 tokens, 5 automatic compactions, and zero compaction/overflow errors; the indivisible 1M-character message limitation remains explicitly uncovered.
- Fix the indivisible-message path by preserving current-turn surface nodes, combining anchored and surface pressure, and pre-compacting before headless admission; six consecutive 1M-character blocks used 5,764,276 tokens with zero compaction/overflow errors.
- Add the `tests/agent-evals/` evidence entry point and contract checks while keeping deterministic package validation separate from real agent behavior validation.

## 1.4.8 - 2026-11-18

### 中文

- 明确区分包校验、契约测试、CI 与真实 Agent 行为验证；确定性检查全绿不再作为行为验证证据。
- 在 `SKILL`、`SKILL.en`、README、验证 playbook 和验证纪律中写明：真实行为评测必须记录模型、宿主、权限模式、日期、结果、证据和未覆盖项，且不进入默认 CI 或发布闸门。
- 同步版本、CITATION、脱敏说明和契约测试；本次不运行真实 Agent 行为评测，1.4.3-1.4.7 的已有变更一并进入发布包。

### English

- Separate package checks, contract tests, and CI from real agent behavior validation; a deterministic green run is no longer evidence that behavior is validated.
- State in `SKILL`, `SKILL.en`, the READMEs, the verification playbooks, and the verification discipline that real behavior evaluation must record the model, host, permission mode, date, result, evidence, and uncovered scope, and is not part of default CI or a release gate.
- Sync versions, CITATION, sanitization notes, and contract tests. This release does not run a real agent behavior evaluation; the existing 1.4.3-1.4.7 changes are included in the package.

## 1.4.7 - 2026-11-16

### 中文

- 商业许可模板包新增国际客户章节，明确跨境合同默认以英文版为准，中文版供作者和监护人内部审阅。
- 订单表补充客户国家/地区、税号/VAT/GST、签署人、币种、预扣税/gross-up、W-8BEN/W-8BEN-E、银行手续费、付款方式、商业发票、控制语言、管辖、出口管制/制裁、DPA 和供应商准入字段。
- 商业许可协议补充预扣税 gross-up、银行费用、反商业贿赂、出口管制/制裁、数据保护、通知、语言优先级和协议/订单表/证书的冲突顺序。
- 授权证书补充被授权方国家/地区、控制语言和签署人权限；首次回复邮件和监护人授权补充跨境付款、外汇、税务表格、脱敏授权文件和认证翻译要求。
- 模板不构成 DPA、税务、外汇、出口管制或制裁合规意见；首份跨境合同仍需律师和会计师按中国及目标国规则审阅。

### English

- Add an international-customer section to the commercial template pack. Cross-border contracts default to the English version; the Chinese version is for the author and guardian.
- Extend the Order Form with customer country/region, tax ID/VAT/GST, signatory, currency, withholding/gross-up, W-8BEN/W-8BEN-E, bank charges, payment method, commercial invoice, controlling language, governing law, export-control/sanctions, DPA, and vendor-onboarding fields.
- Extend the Agreement with withholding gross-up, bank charges, anti-corruption, export-control/sanctions, data protection, notices, language precedence, and the order of precedence among the Agreement, Order Form, and certificate.
- Extend the certificate with licensee country/region, controlling language, and signatory capacity; extend the first-reply email and guardian authorization with cross-border payment, foreign-exchange, tax-form, redacted-authorization, and certified-translation requirements.
- The templates are not DPA, tax, foreign-exchange, export-control, or sanctions advice. A lawyer and accountant must review the first cross-border contract under Chinese and target-country rules.

## 1.4.6 - 2026-11-16

### 中文

- 新增 `commercial/` 商业许可模板包：监护人授权、商业许可协议、订单表、授权证书、首次回复邮件和许可证登记表。
- 明确未成年作者的商业授权由监护人作为法定代理人办理；若监护人已有经营主体，可使用该主体签约，但必须保持合同、收款、发票和证书主体一致。
- 授权证书模板从 Markdown 源文件导出为 PDF；PDF 适合签署、盖章、数字签名和采购归档，JPG/PNG 不作为唯一证书格式。
- 同步 `COMMERCIAL`、README、包校验必需文件列表和契约测试；模板明确标注不是法律意见，首份合同仍需律师审阅。

### English

- Add a `commercial/` template pack for guardian authorization, the commercial license agreement, order form, license certificate, first-reply email, and license register.
- Clarify that a minor author's commercial license is handled by the guardian as legal representative; a guardian-operated entity may sign if the authority chain is documented, while the contract, payee, invoice, and certificate must use the same party.
- Export the certificate template from Markdown to PDF for signature, stamping, digital signatures, and procurement archiving; JPG/PNG is not the primary certificate format.
- Sync `COMMERCIAL`, the READMEs, package-verifier required files, and contract tests. The templates are not legal advice; have a lawyer review the first contract.

## 1.4.5 - 2026-11-16

### 中文

- 在 `references/verification-playbook.md` / `.en.md` 新增“覆盖边界与未测试项”：记录当前云端公开证据、未覆盖环境、未测试原因和补测条件。
- 明确区分 `SKIP`、工具缺失、作业跳过与“已通过”；当前未覆盖 Windows Server 2019/2022、Windows 10、域控/AD/Kerberos/GPO/SPN、WinRM、故障转移集群、SQL 实例查询、IIS HTTP/TLS、SELinux、firewalld、dnf/RPM、SSH 权限、原生 macOS 行为、Python 3.11/3.13 和 Agent 自主记忆评测。
- 记录服务器冒烟当前不是必需检查：分支保护只要求六个 `Verify package` 矩阵作业，`Verify server playbooks` 受路径过滤且自建 roles 作业可能被跳过；PR 全绿不能替代服务器实测。
- 同步版本、README 入口、SKILL 报告提示、变更日志和契约测试；本次仅补验收边界，不改变检查流程或许可证。

### English

- Add "Coverage boundaries and untested items" to `references/verification-playbook.md` / `.en.md`, recording the current public evidence, uncovered environments, reasons, and closing conditions.
- Distinguish `SKIP`, missing tools, and skipped jobs from "passed"; current gaps include Windows Server 2019/2022, Windows 10, domain/AD/Kerberos/GPO/SPN, WinRM, failover clusters, SQL instance queries, IIS HTTP/TLS, SELinux, firewalld, dnf/RPM, SSH permissions, native macOS behavior, Python 3.11/3.13, and the autonomous agent-memory evaluation.
- Record that server smoke is not currently a required check: branch protection requires only the six `Verify package` matrix jobs, while `Verify server playbooks` is path-filtered and its self-hosted roles job may be skipped. A green pull request is not a substitute for server evidence.
- Sync the version, README entry points, SKILL report guidance, changelog, and contract tests. This release only records acceptance boundaries; it does not change the review workflow or license.

## 1.4.4 - 2026-11-16

### 中文

- 修正 Windows CI 覆盖判断：GitHub 托管的 `windows-latest` 实际为 Windows Server 2025。托管作业现在强制校验 Server OS 和 IIS，避免把服务器结果误标为客户端覆盖，也避免 IIS 检查缺失时静默跳过。
- 保留受仓库变量控制的自建 runner 作业，仅用于域控/GPO/SPN、WinRM 监听器和故障转移集群等托管环境缺失的专项；该作业继续只允许 main 分支 push 或手动 `workflow_dispatch`，不接受 `pull_request`。

### English

- Correct the Windows CI coverage assumption: GitHub-hosted `windows-latest` is Windows Server 2025. The hosted job now requires a Server OS and IIS, preventing server results from being mislabeled as client-only coverage or IIS checks from being silently skipped.
- Keep the repository-variable-gated self-hosted job only for domain/GPO/SPN, WinRM listener, and failover-cluster checks that the hosted image cannot provide. That job still runs only on main-branch pushes or manual `workflow_dispatch`, never on pull requests.

## 1.4.3 - 2026-11-16

### 中文

- 脱敏扫描器取消扩展名白名单，改为扫描所有非二进制文件，覆盖 `.env.*`、`.pem`、`.log`、`.ini`、`.cff` 等此前可能漏掉的文本；UTF-8 与 UTF-16（带 BOM，或字节顺序明确的无 BOM UTF-16）均可读取，无法可靠判断编码时 fail closed。
- 扫描器对空目录、零文件、无法解码、异常 NUL 和不可扫描文件 fail closed；密钥字段扩展到 `client_secret`、`access_token`、`refresh_token`、`private_key`、`session_token` 等常见命名。
- Python 与 PowerShell 包校验器统一目录过滤、二进制清单、严格 UTF-8 与 BOM/NUL 规则，并校验非空 `description`、嵌套在 `metadata` 下的 `version` 和 `PITFALLS.md` 六字段格式，同时覆盖无列表符号记录和空字段。
- `record_pitfall.py` 增加技能根目录指纹：校验真实 `SKILL.md` 的名称、许可和描述，要求规定结构文件与字节一致的记录器副本；`repo` 范围还要求 `.git`。完全重复只更新时间，不再重复追加或回显整条记录。
- 修复 Windows PowerShell 5.1 冒烟脚本把版本哈希表直接投影导致表头为空的问题；新增扫描器、校验器、记录器边界和编码回归测试。
- 拆分 Windows 冒烟 CI：`windows-latest` 只做客户端检查，真实 Windows Server 使用受仓库变量控制的自建 runner 作业，且只允许 main 分支 push 或手动 `workflow_dispatch`，避免 `pull_request`（包括 fork PR）在自建服务器执行代码，也避免把客户端结果当作服务器覆盖。
- 补充裸 `secret=` 赋值检测；新增 macOS `/Users/<name>` 路径检测；PowerShell 扫描器对带 BOM 的无效 UTF-8/UTF-16 改为严格失败，并修正文件名或根路径含 `build`/`dist` 等名称时误跳过扫描范围的问题。
- 修复无 BOM UTF-16 含非 BMP 字符时的字节序误判：Python 不再误报不可扫描，PowerShell 不再选错字节序后假阴性；两版都加入 emoji 正例回归。
- 修复 Linux 冒烟脚本在 `pipefail` 下用 `head` 截断长输出导致的 SIGPIPE 假失败；Docker Compose 校验改为从标准输入读取配置，兼容 WSL 调用 Windows Docker 客户端。
- 将 `PITFALLS.md` 中残留的内部平台标签改为中性的 `agent-shell`，并修复一条被分隔符破坏的六字段记录。

### English

- Remove the redaction scanner's extension allowlist and scan every non-binary file, including `.env.*`, `.pem`, `.log`, `.ini`, and `.cff`; accept UTF-8 and UTF-16 with BOM or unambiguous no-BOM byte order, and fail closed when the encoding is not reliable.
- Fail closed on empty directories, zero files, undecodable input, anomalous NUL, or unscannable files; extend assigned-secret detection to `client_secret`, `access_token`, `refresh_token`, `private_key`, `session_token`, and similar names.
- Align the Python and PowerShell package verifiers on directory filters, binary extensions, strict UTF-8 and BOM/NUL rules, non-empty `description`, `metadata.version`, and the six-field `PITFALLS.md` format, including non-bulleted records and empty fields.
- Harden `record_pitfall.py` with a skill-root fingerprint: validate the real `SKILL.md` name, license, and description, require the structural files and a byte-identical recorder, and require `.git` for repository scope. Exact duplicates refresh only the date, without appending or echoing the full entry.
- Fix the Windows PowerShell 5.1 smoke script's empty version table by projecting an explicit object; add regression coverage for scanners, verifiers, recorder boundaries, and encoding.
- Split the Windows smoke CI path: `windows-latest` covers the client only, while a repository-variable-gated self-hosted job covers a real Windows Server role; that job runs only on main-branch pushes or manual `workflow_dispatch`, never on pull requests, preventing fork PR code from running on the self-hosted server and preventing a client result from being presented as server coverage.
- Detect bare `secret=` assignments; add macOS `/Users/<name>` path detection; make the PowerShell scanner fail closed on invalid UTF-8/UTF-16 after a BOM, and stop skipping files or packages when a file name or root path contains `build`, `dist`, or another skipped directory name.
- Fix byte-order selection for no-BOM UTF-16 containing non-BMP characters: Python no longer reports a false unscannable failure, and PowerShell no longer selects the wrong byte order and returns a false negative; both scanners now have an emoji regression.
- Fix false SIGPIPE failures in the Linux smoke script when `pipefail` is combined with `head`; validate Docker Compose through standard input so WSL can use a Windows Docker client.
- Replace residual internal platform tags in `PITFALLS.md` with the neutral `agent-shell` label and repair one six-field entry split by a literal separator.

## 1.4.2 - 2026-11-13

### 中文

- 新增 `scripts/record_pitfall.py`：只写技能根目录下的 `PITFALLS.md` 或 `PITFALLS.local.md`，精确查重、保留历史，并拦截分隔符、换行、常见密钥和个人路径。
- 明确记忆分流：安装技能使用 `PITFALLS.local.md`，首次自动创建、升级保留；维护仓库使用 `PITFALLS.md`。
- `SKILL.md`、`AGENTS.md` 增加任务结束前的自主记忆检查、同类新机制引用父 ID、记忆范围（工具坑 + 可复用项目失败模式）和最终报告的记忆结果。
- 新增记录器单元测试、评测器测试和两个基线未覆盖的假绿场景；真实 Agent 行为评测可选运行，默认 CI 不调用 Codex。
- README 补充本地记忆说明，并提醒覆盖安装前备份 `PITFALLS.local.md`。
- 修复 macOS 上 `/var` 与 `/private/var` 符号链接造成的路径断言假失败；跨平台路径比较先规范化。

### English

- Add `scripts/record_pitfall.py`, which can only write `PITFALLS.md` or `PITFALLS.local.md` under the skill root, performs exact deduplication, preserves history, and rejects separators, newlines, common secrets, and personal paths.
- Define two memory stores: installed skills use `PITFALLS.local.md` (created on first use, preserved across upgrades); maintainers use `PITFALLS.md`.
- Add an autonomous memory checkpoint before the final report to `SKILL.md` and `AGENTS.md`, including parent IDs for new mechanisms, scope for tooling traps plus reusable project failure modes, and a memory result in the report.
- Add recorder unit tests, evaluator tests, and two false-green scenarios not covered by the baseline. The real agent behavior evaluation is optional and is not invoked by default CI.
- Document local memory in the README and warn users to back up `PITFALLS.local.md` before a replacement install.
- Fix false path-assertion failures caused by the `/var` to `/private/var` symlink on macOS; normalize paths before cross-platform comparisons.

## 1.4.1 - 2026-11-13

### 中文

- 与 `project-health-macos` 建立 `MAC-H01`～`MAC-H08` 隐藏坑同步基线，覆盖 Rosetta、AirPlay/本地网络、Xcode/SDK、多语言工具链、dylib 签名、归档元数据、性能基线和 runner 覆盖范围。
- 专业版 `references/macos-pitfalls.md` / `.en.md` 新增端口与本地网络、多语言工具链、Xcode/CLT/SDK、性能资源和常见假绿清单；`SKILL.md`、`PITFALLS.md` 同步速查项。
- 两版契约测试检查共享编号和中英文关键证据，防止只更新专用版或只更新一个语言版本。

### English

- Establish the shared `MAC-H01` through `MAC-H08` hidden-pitfall baseline with `project-health-macos`, covering Rosetta, AirPlay/local networking, Xcode/SDK, multi-language toolchains, dylib signing, archive metadata, performance baselines, and runner coverage.
- Add ports and local networking, multi-language toolchains, Xcode/CLT/SDK, performance resources, and a false-pass checklist to the professional `references/macos-pitfalls.md` / `.en.md`, with matching quick-reference rows in `SKILL.md` and `PITFALLS.md`.
- Contract tests in both editions now check the shared IDs and bilingual evidence so a one-edition or one-language update cannot pass CI.

## 1.4.0 - 2026-11-13

### 中文

- 专业版新增 macOS / Apple Silicon 常驻避坑层：任务开始时先确认系统、shell、架构和 Rosetta 状态，再加载 macOS 专项规则。
- 新增 `references/macos-pitfalls.md` / `.en.md`，覆盖 Rosetta 架构混用、Homebrew 双前缀、BSD 工具、系统 bash 3.2、APFS、Gatekeeper/TCC、launchd、Docker 架构与卷性能、归档签名和 macOS runner 差异。
- 将环境探测加入 `SKILL.md` 第 0 步和 `AGENTS.md` 常驻规则；Apple Silicon 非原生 arm64 时仍可做通用只读检查，但必须把原生构建、签名、性能和容器架构结论标为未覆盖。
- `PITFALLS.md`、README、包校验器、PowerShell 校验器和契约测试同步；专业版保持跨平台，不变成 Apple Silicon-only 技能。

### English

- Add a resident macOS / Apple Silicon pitfall layer to the professional edition: identify the OS, shell, architecture, and Rosetta state at task start before loading macOS-specific rules.
- Add `references/macos-pitfalls.md` / `.en.md` for Rosetta architecture mixing, dual Homebrew prefixes, BSD tools, system bash 3.2, APFS, Gatekeeper/TCC, launchd, Docker architecture and volume performance, archive signing, and macOS runner differences.
- Add environment probing to step 0 of `SKILL.md` and the standing rules in `AGENTS.md`; a non-native arm64 Apple Silicon session may continue with a generic read-only review, but native build, signing, performance, and container-architecture conclusions must be marked as uncovered.
- Update `PITFALLS.md`, the READMEs, package verifiers, PowerShell verifier, and contract tests. The professional edition remains cross-platform rather than becoming Apple Silicon-only.

## 1.3.1 - 2026-11-12

### 中文

- 调整专业版技能入口：明确推荐企业项目建设与日常维护，同时允许普通用户直接使用。
- 同步 README、SKILL、AGENTS 和路由规则，避免“主页推荐专业版、技能说明却把普通用户一律推给轻量版”的不一致。
- 本版本为说明与路由修订，不改变检查流程、许可证或安全边界。

### English

- Reposition the professional skill entry: recommended for enterprise project construction and routine maintenance while remaining directly usable by everyday users.
- Align the README, SKILL, AGENTS, and routing rules so the repository positioning does not contradict the skill behavior.
- This is a documentation and routing revision; audit workflows, licensing, and safety boundaries are unchanged.

## 1.3.0 - 2026-11-11

### 中文

- `PITFALLS.md` 新增 162 条企业项目避坑基线，覆盖需求验收、架构、身份权限、多租户、数据迁移、API 集成、并发缓存、前端兼容、构建供应链、CI/CD、容器云、Linux 服务器、Windows 服务器、网络 TLS、可观测性、安全合规和交接运维。
- 增加“如果只看 20 条”和“服务器上线前 20 问”，把最容易在上线当天爆雷的跨领域问题放在最前面。
- 新增 `references/linux-server-pitfalls.md` / `.en.md`，覆盖 systemd、权限与 SELinux/AppArmor、磁盘 inode、ulimit/OOM、防火墙、DNS/NTP、包管理、SSH、数据库、容器和回滚。
- 扩充 `references/windows-pitfalls.md` / `.en.md` 的 Windows Server 小节，覆盖 IIS、Windows 服务、NTFS/SMB、AD/Kerberos、SQL Server、证书、WinRM、EDR、补丁和故障转移集群。
- `SKILL.md` / `SKILL.en.md` 增加服务器平台高频坑入口和只读边界；README、包校验器和契约测试同步新文件与 1.3.0 版本。
- README 定位调整为面向企业级项目的审计与交付验收；新增 Linux / Windows Server 只读冒烟检查，在 GitHub Ubuntu 24.04 与 Windows Server 运行器上验证安全命令。

### English

- Add a 162-entry enterprise pitfall baseline to `PITFALLS.md`, covering requirements and acceptance, architecture, identity and multi-tenancy, data and migrations, API integration, concurrency and caching, frontend compatibility, build and supply chain, CI/CD, containers and cloud, Linux servers, Windows servers, network and TLS, observability, security and compliance, and handover/operations.
- Add a "top 20" list and a 20-question server pre-launch checklist so the highest-blast-radius issues appear first.
- Add `references/linux-server-pitfalls.md` / `.en.md`, covering systemd, permissions and SELinux/AppArmor, disk and inodes, ulimit/OOM, firewalls, DNS/NTP, package management, SSH, databases, containers, and rollback.
- Expand the Windows Server section in `references/windows-pitfalls.md` / `.en.md`, covering IIS, Windows services, NTFS/SMB, AD/Kerberos, SQL Server, certificates, WinRM, EDR, patching, and failover clusters.
- Add server-platform entry points and read-only boundaries to `SKILL.md` / `SKILL.en.md`; update the README, package verifiers, and contract tests for the new files and version 1.3.0.
- Position the README for enterprise project audits and delivery acceptance; add Linux and Windows Server read-only smoke checks for GitHub Ubuntu 24.04 and Windows Server runners.

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
