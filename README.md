# project-health

[中文](README.md) | [English](README.en.md)

**一句话：给已有软件项目做证据驱动的体检和交付验收，找出会阻断上线、交接或交付的问题。**

**普通人也能直接用**：不需要自己懂代码、构建或审计术语。只要能使用 Agent，就可以用日常语言发起检查；执行和证据核对由 Agent 完成，报告会解释技术结论。

用于上线前、交接前、周期性体检，以及 Agent 写完代码后的验收。输出不是“建议关注”，而是带 `file:line` 证据、影响、建议和验证方式的 P0-P3 问题清单。

> **边界**：代码生成由宿主 Agent 完成，本 Skill 不替代生成能力；它负责对生成结果做证据检查、真实回归和交付验收。它不承诺零缺陷，但在覆盖到的检查面上可以显著降低可检测缺陷。实际效果取决于项目基线、Agent 能力、测试覆盖和执行深度。

> 检查阶段默认只读。发现问题先报告，不擅自改代码。

快速导航：[30 秒开始](#30-秒开始) · [主要用途](#主要用途) · [真实收益](#真实收益) · [触发方式](#触发方式) · [自检](#自检) · [许可](#许可)

## 30 秒开始

这是一个通用 Skill 包，不绑定 Codex，也不是双击安装的软件。宿主只要支持 Agent Skills / `SKILL.md` 目录格式即可使用。

| 宿主 | 常见技能目录 |
|---|---|
| Codex | `~/.codex/skills/` |
| Claude Code | `~/.claude/skills/` |
| 其他 Agent Skills 宿主 | 宿主配置的技能目录，以宿主文档为准 |

Windows PowerShell：

```powershell
Copy-Item -LiteralPath '.\project-health' -Destination '<宿主技能目录>' -Recurse -Force
Test-Path '<宿主技能目录>\project-health\SKILL.md'
```

macOS / Linux：

```bash
cp -R ./project-health "<宿主技能目录>/"
test -f "<宿主技能目录>/project-health/SKILL.md"
```

也可以克隆仓库：

```bash
git clone https://github.com/Fallen-leaves089/project-health.git "<宿主技能目录>/project-health"
```

装好后目录根部必须有 `SKILL.md`，不要只复制这个文件；`AGENTS.md`、`PITFALLS.md`、`references/` 和 `scripts/` 也要一起带走。

> **从 1.1.x 升级**：请先删除旧的 `fullstack-health-check` 技能目录，再安装 `project-health`，避免两个技能同时存在。

技能宿主默认加载中文 `SKILL.md`。如需英文版，把 `SKILL.en.md` 复制为 `SKILL.md`；仓库保留两份文件，方便对照和更新。

## 主要用途

- **上线前审计**：找出会阻断部署、迁移或启动的问题。
- **周期性体检**：把上一轮遗留、构建基线、环境坑和用户禁区重新对齐。
- **交接验收**：让接手者拿到带证据的问题清单、未覆盖项和验证方式。
- **Agent 交付验收**：对 Agent 生成或修改的项目结果做证据检查、回归和边界确认。

适用于服务、Web / 移动客户端、数据库迁移、容器化部署等多层项目；全栈只是其中一种常见场景。

## 它如何工作

1. **先查项目自己的历史**：`AGENTS.md`、`PITFALLS.md`、历史报告、`docs/`、变更记录、上一轮遗留项和构建基线，比通用清单更接近事实。遇到新坑先查重再记录，重复的坑只补充原条目。
2. **先定检查范围**：变更是看固定基准点到 `HEAD`，全量是看当前 `HEAD` 和整个工作区，没有 Git 则做只读快照并说明限制。
3. **双轴审查**：规范符合度（Standards）和需求符合度（Spec）分开看，避免把“代码写得丑”和“需求没做完”混在一起。
4. **真实回归**：测试、构建、迁移、compose 配置和关键路径要实际跑，不只做静态阅读；会写文件、装依赖或启动服务时先取得同意。
5. **证据输出**：每条问题写清 `file:line`、影响、建议、验证方式和置信度；另列“已核验无问题”和“本轮未覆盖”。

它还会检查“检查方法本身是否有效”，包括正反例、失败退出码、命令是否真的执行，以及检查脚本是否会假绿。

## 真实收益：一次两轮体检抓到了什么

> 以下来自一个真实多端项目的两轮体检（2026-08-30、2026-09-02），已移除项目名、地址、凭据和业务细节。它不是演示数据，也不是全行业基准。

| 结果 | 证据 |
|---|---|
| **30 条分级问题** | 10 条 P0/P1、9 条 P2、11 条 P3；其中 10 条 P0/P1 已闭环 |
| **多个上线阻断项提前暴露** | MySQL 8.0 迁移语法必失败；部署脚本漏执行迁移；生产迁移会写入启用状态、已知密码的测试账号 |
| **安全风险定位到具体链路** | 运行时配置硬编码 JWT/DB/Redis 凭据；误用 dev profile 可同时打开默认短信码、mock 微信登录并跳过生产校验 |
| **修复后真实回归** | 后端测试 115/115；容器化迁移连续 3 次 10/10；Android 双 flavor 与商户 Web 构建通过 |
| **修复过程又发现 2 个真 bug** | 部署脚本根目录算错；数据库容器探活抖动导致回归随机失败 |
| **消除 1 个假绿** | 守护脚本吞掉迁移失败后仍报 GREEN；改为失败即无效，并用正反例验证 |
| **发现部署态漂移** | 线上 JAR 与本地编译产物有 33 个类不一致、7 个类缺失；该结论当时明确标注未再复核 |

> 这些数字说明的不是“检查项很多”，而是问题从**未知**变成**可量化**，修复从**口头完成**变成**可复跑**，并且开始用失败用例保护检查器本身。

**边界同样写清楚**：上述项目并未宣称“全部清零”，P2/P3 仍有未处理项；已进入 Git 历史的旧凭据必须实际轮换；线上 JAR 漂移后来没有再次复核。报告保留这些限制，避免把“本轮通过”写成“永远安全”。

## 触发方式

对话里说这些会命中：

- 「做个项目体检」
- 「全面问题检查」
- 「上线前审计」或「上线前体检」
- 「项目交接前检查」
- 「检查这个软件项目」或「检查全栈项目」
- 「用 project-health 检查这个仓库」

## 使用前提

- 项目最好使用 Git；变更检查会用 `git rev-parse` 校验基准点。没有 Git 时仍可做只读快照检查，但必须明确说明看不到历史、基准点和精确 diff。
- 需要跑容器化回归时，Docker 守护进程要能启动。
- 检查阶段默认只读；写报告前确认路径，要修代码则等用户明确指令。
- 需要 Windows 专项排障时，先读 `references/windows-pitfalls.md`，不要凭记忆试。

## 包内结构

```text
project-health/
├── SKILL.md / SKILL.en.md                # 技能本体（中文默认 / 英文镜像）
├── README.md / README.en.md              # 本文件
├── AGENTS.md                            # 常驻规则（任务边界与避坑纪律）
├── PITFALLS.md                          # 可复用的避坑记录
├── references/                           # 平台命令、Windows 坑、验证手册、报告模板
├── scripts/                              # 跨平台自检与脱敏扫描
└── LICENSE / COMMERCIAL / SIGNING / SANITIZATION
```

## 平台支持

核心技能只依赖 Markdown 和 Git 命令；Windows 10/11 + PowerShell 5.1/7、macOS / Linux + Python 3.9+、WSL2 都可使用。Python 自检只用标准库，不需要联网。

## 自检

在包根目录运行：

```bash
python3 scripts/verify_package.py
```

Windows 也可以运行：

```powershell
python scripts\verify_package.py
```

没有 Python 时可用 PowerShell 版：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-package.ps1
```

它检查必需文件、UTF-8 无 BOM、Markdown 链接、脱敏自检、包内敏感模式，以及 `SKILL.md` / `SKILL.en.md` 的 frontmatter、版本和语言链接是否一致。

只跑脱敏扫描：

```bash
python3 scripts/check_redaction.py --self-test
python3 scripts/check_redaction.py --path .
```

Windows PowerShell 版使用 `scripts/check-redaction.ps1`；完整命令见 `SANITIZATION.md`。

## 下载与签名

正式下载请从 [GitHub Releases](https://github.com/Fallen-leaves089/project-health/releases) 获取，并同时下载 `project-health-<version>.zip`、`SHA256SUMS`、`SHA256SUMS.sig`、`allowed_signers` 和 `release-signing-key.pub`。

先核对公钥指纹：

```bash
ssh-keygen -lf release-signing-key.pub
```

完整的 macOS、Linux 和 Windows 校验命令见 `SIGNING.md` / `SIGNING.en.md`。`SHA256SUMS` 和 `SHA256SUMS.sig` 是 zip 生成后的独立发布资产，不放进 zip 内部。

## 安全与脱敏

检查阶段默认只读。公开版已移除个人绝对路径、用户名、项目/客户标识、内部平台名称、真实域名与内网地址、密钥和事故细节。发现可疑信息时，请通过仓库 Issue 或维护者公开渠道联系，不要直接贴出敏感值。

详细范围见 `SANITIZATION.md`；安全问题报告方式见 `SECURITY.md`。

## 参与贡献

见 `CONTRIBUTING.md`。新增环境坑请写清“坑 / 绕法 / 验证方式”；新增守护脚本必须自带正反例。

## 许可

本作品采用 **PolyForm Noncommercial License 1.0.0**，仅允许非商业用途。英文原文见 `LICENSE`，中文说明见 `LICENSE.zh-CN.md`。

商业使用需要作者书面授权，但**可以和作者商量**。如需商业化，可以联系 `chenshuidelaye@qq.com`；授权方式、范围和费用按实际使用场景协商，见 `COMMERCIAL.md`。

> GitHub 的许可证识别列表不包含 PolyForm，因此仓库页面可能显示 `NOASSERTION / Other`。这不代表没有许可证；以仓库中的 `LICENSE` 英文原文为准。

## 版本

- 版本：1.2.2
- 对应内部整理日期：2026-09-04
- 公开发布整理：2026-10-30
