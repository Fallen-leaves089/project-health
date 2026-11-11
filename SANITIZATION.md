# 脱敏说明

[中文](SANITIZATION.md) | [English](SANITIZATION.en.md)

本文件记录公开版相对内部整理版做了什么处理，以及为什么保留某些内容。目标不是“看起来没有敏感词”，而是**在不泄露可识别信息的前提下，保留可复用的工程经验**。

## 来源

- 内部技能整理日期：2026-09-04
- 公开版版本：1.3.0
- 处理方式：逐段重写，不用简单查找替换；敏感段落直接删除或抽象化

## 已移除

- **个人绝对路径与用户名**：统一改成 `C:\Users\<you>`、`$env:USERPROFILE`、`<PROJECT>` 等占位符。
- **内部项目、客户、业务名称**：不保留具体项目名、门店名、账号名、订单号、客户标识。
- **内部代理平台与记忆目录名**：改成“项目内的代理记忆目录（若存在）”，不写具体平台目录。
- **真实域名、内网 IP、主机名、端口**：统一改成 `<HOST>`、`<DOMAIN>`、`127.0.0.1` 或文档保留地址。
- **密钥、令牌、Cookie、连接串、密码**：不保留任何真实值；示例统一用 `<REDACTED>`。
- **具体事故中的业务数据**：只保留“迁移非幂等”“种子数据混入迁移”“产物残留测试地址”这类可复用的教训，不保留项目上下文。
- **平台专用元数据**：移除只对某个宿主有意义的 frontmatter 字段和技能管理标记。

## 已保留

- **项目健康检查流程**：先查归档、汇报对齐、锁定基准点、双轴审查、真实构建、P0-P3 分级、修复纪律。
- **Windows 环境坑**：PowerShell / Git Bash 差异、`mvn.cmd`、Surefire XML、Python PATH、UTF-8 BOM、管道退出码、Docker Desktop、WSL2、MySQL 初始化、`git mv`、`BASH_SOURCE` 等。
- **企业级避坑基线**：16 个领域、162 条跨平台工程坑，覆盖需求验收、架构、权限、多租户、数据迁移、API、并发缓存、构建供应链、CI/CD、容器云、网络 TLS、可观测性、安全合规和交接运维。
- **服务器平台坑**：Windows Server 的 IIS、服务、NTFS/SMB、AD/Kerberos、SQL Server、证书、WinRM、EDR、补丁和集群；Linux 的 systemd、权限、SELinux/AppArmor、磁盘、OOM、防火墙、NTP、包管理、SSH、数据库、容器和回滚。
- **纠错与验证纪律**：正反两例、能变红的反馈回路、最小复现、3-5 个可证伪假设、单变量探测、回归测试、清理调试痕迹。
- **安全底线**：不信任 cwd、目录指纹校验、fail-closed、环境变量强校验、产物自检、扫描器自扫与自举反例。
- **不可信目标边界**：目标仓库的 `AGENTS.md`、`PITFALLS.md`、README、注释和日志只作为低信任证据，不能覆盖用户指令、安全底线或本技能规则。
- **脱敏纪律本身**：展示日志/配置前先替换密钥，覆盖 JSON/TOML/YAML/ENV，不读取敏感文件内容。
- **跨平台验证方法**：Python 3.9+ 标准库扫描器/总检，以及 Windows、macOS、Linux 三平台 CI。
- **跨平台命令对照**：Windows PowerShell、macOS/Linux bash/zsh 与 WSL2 的常用命令差异，帮助检查者按当前 shell 执行。
- **作者公开的商业联系邮箱**：`chenshuidelaye@qq.com` 是作者要求主动公开的，不属于脱敏遗漏。

## 英译说明

英文文档是中文原文的翻译，不引入新的内部资料。流程细节以中文文档为维护源；法律条款以 `LICENSE` 英文原文为准。

## 关键改写

| 原内容类型 | 公开版处理 |
|---|---|
| 固定用户目录下的解释器路径 | 改成 `where.exe python`、`py -3`、`Get-Command python` |
| 平台专用的提问/技能管理调用 | 改成“向用户提问”“宿主技能目录” |
| 具体业务系统的术语 | 改成“前端”“业务数据”“真实数据”“关键路径” |
| 具体项目的检查结论 | 删除结论，只保留方法和验证方式 |
| 具体环境的主机/端口 | 改成 `<HOST>`、`127.0.0.1` 或“容器内服务” |

## 自动化检查

包内提供 Python 与 PowerShell 两条校验路径：

```bash
# 跨平台：只跑脱敏扫描器的正反例自检
python3 scripts/check_redaction.py --self-test

# 跨平台：扫描当前包
python3 scripts/check_redaction.py --path . --quiet

# 跨平台：总检（必需文件、UTF-8 无 BOM、相对链接、frontmatter、脱敏）
python3 scripts/verify_package.py

# 跨平台：契约测试与恶意目标反例
python3 -B -m unittest discover -s tests -p "test_*.py"
```

```powershell
# Windows PowerShell：只跑脱敏扫描器的正反例自检
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-redaction.ps1 -SelfTest

# Windows PowerShell：扫描当前包
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-redaction.ps1 -Path .

# Windows PowerShell：总检
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-package.ps1
```

`check-redaction.ps1` 默认检查：

- Windows（反斜杠 / 正斜杠）与 Unix 用户目录路径
- 私有 IPv4 地址
- OpenAI 风格密钥、GitHub 令牌、AWS Access Key
- PEM 私钥块
- `api_key` / `token` / `password` 等赋值形式的长字符串（含 JSON/TOML/YAML 的引号键）

项目专属词、客户名、内部代号不在默认规则里。需要时用 `-ExtraPatterns` 传入，例如：

```powershell
.\scripts\check-redaction.ps1 -Path . -ExtraPatterns 'ACME-INTERNAL','项目代号'
```

## 人工复核

发布前逐文件读过一遍，并额外搜索过以下模式：

- `C:\Users\` 后跟真实用户名
- `/home/` 后跟真实用户名
- `sk-`、`ghp_`、`github_pat_`、`AKIA`
- `BEGIN ... PRIVATE KEY`
- 私有 IPv4 网段
- 内部项目名、客户名、真实域名

## 残余风险

- 通用经验可能仍然“像”某些具体项目，但不包含可识别的个人、客户或密钥信息。
- 许可与商业条款不是法律意见；具体用途有疑问时请咨询律师或联系作者。
- 自动化扫描只能覆盖已知模式，不能证明“绝对没有敏感信息”。发现遗漏请通过公开渠道联系，不要在 Issue 里粘贴敏感值。
- 扫描器自检中的私有地址和示例密钥都是文档夹具，不对应任何真实主机或账号。
- 提示词注入防护只能降低文本层风险，不能证明任意模型在任意上下文中都不会被诱导；发现绕过方式时请按安全问题报告。

## 发布前检查清单

- [x] 所有文本文件为 UTF-8 无 BOM
- [x] Markdown 相对链接可解析
- [x] 脱敏扫描器正反例自检通过
- [x] 不可信目标契约测试与恶意 `AGENTS.md` 反例通过
- [x] 包扫描无命中
- [x] 不含个人绝对路径、真实用户名、项目/客户名
- [x] 不含真实密钥、令牌、私钥、连接串
- [x] 不含真实域名、内网 IP、主机名、端口（自检夹具除外）
- [x] 许可文件与商业授权说明齐全
- [x] 版本、日期、目录结构一致
- [x] Python 总检在 Windows、macOS、Linux、Python 3.9/3.12 上通过 CI

## 发现问题怎么报

如果发现疑似泄露：

1. 不要公开粘贴具体值。
2. 在仓库开 Issue，标题以 `[Security]` 开头，只描述“哪个文件、哪一类信息”。
3. 或通过维护者公开渠道私下联系。
4. 维护者确认后删除/替换，并在 `CHANGELOG.md` 记录，不把敏感值写进提交说明。
