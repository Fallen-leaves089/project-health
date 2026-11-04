# project-health

[中文](README.md) | [English](README.en.md)

**One line: evidence-driven health checks and delivery acceptance for existing software projects, surfacing issues that would block release, handover, or delivery.**

**Built for non-specialists too**: you do not need to know code, build systems, or audit terminology. If you can use an agent, you can ask for a check in plain language; the agent runs it and explains the technical evidence.

Use it before release, before handover, for periodic reviews, and to accept work produced or modified by an agent. The output is not "please pay attention"; it is a graded P0-P3 list with `file:line` evidence, impact, recommendation, and verification.

> **Boundary**: Code generation is handled by the host agent; this skill does not replace that capability. It verifies generated results with evidence checks, real regressions, and delivery acceptance. It does not promise zero defects, but it can significantly reduce detectable defects within the checks it covers. Actual results depend on the project baseline, agent capability, test coverage, and execution depth.

> Read-only by default during review. Report first; do not change code without an explicit instruction.

Quick navigation: [Quick start](#quick-start) · [What it's for](#what-its-for) · [What it caught](#what-it-caught-a-real-two-pass-health-check) · [Triggers](#triggers) · [Self-check](#self-check) · [License](#license)

## Quick start

This is a host-neutral skill package, not tied to Codex, and not a double-click installer. Any host that supports the Agent Skills / `SKILL.md` directory format can use it.

| Host | Common skills directory |
|---|---|
| Codex | `~/.codex/skills/` |
| Claude Code | `~/.claude/skills/` |
| Other Agent Skills hosts | The host's configured skills directory; check its documentation |

Windows PowerShell:

```powershell
Copy-Item -LiteralPath '.\project-health' -Destination '<HOST_SKILLS_DIR>' -Recurse -Force
Test-Path '<HOST_SKILLS_DIR>\project-health\SKILL.md'
```

macOS / Linux:

```bash
cp -R ./project-health "<HOST_SKILLS_DIR>/"
test -f "<HOST_SKILLS_DIR>/project-health/SKILL.md"
```

Or clone the repository:

```bash
git clone https://github.com/Fallen-leaves089/project-health.git "<HOST_SKILLS_DIR>/project-health"
```

The directory root must contain `SKILL.md`; do not copy only that file. `AGENTS.md`, `PITFALLS.md`, `references/`, and `scripts/` must travel with it.

> **Upgrading from 1.1.x**: remove the old `fullstack-health-check` skill directory before installing `project-health`, so both versions do not coexist.

Skill hosts load the Chinese `SKILL.md` by default. For English, copy `SKILL.en.md` over `SKILL.md`. Both files stay in the repository for comparison and updates.

## What it's for

- **Pre-release audit**: find issues that block deployment, migration, or startup.
- **Periodic review**: re-align previous findings, build baselines, environment traps, and user prohibitions.
- **Handover acceptance**: give the next owner an evidence-linked list of findings, gaps, and verification methods.
- **Agent delivery acceptance**: verify work produced or modified by an agent with evidence, regression, and explicit boundaries.

It applies to services, web and mobile clients, database migrations, containerized deployment, and other project layers; full-stack is one common case, not the boundary.

## How it works

1. **Read the project's own history first**: `AGENTS.md`, `PITFALLS.md`, historical reports, `docs/`, change logs, previous findings, and build baselines are closer to the truth than a generic checklist. Search before recording a new pitfall; update the existing entry when it is a duplicate.
2. **Define the scope first**: a change review covers a fixed point through `HEAD`, a full review covers the current `HEAD` and worktree, and a repository without Git gets a read-only snapshot with explicit limits.
3. **Two-axis review**: standards compliance and spec compliance are reviewed separately, so "ugly code" and "missing requirement" do not get mixed into one bucket.
4. **Real regression**: tests, builds, migrations, compose configuration, and key paths are actually run, not just read; obtain consent before commands that write files, install dependencies, or start services.
5. **Evidence output**: every finding includes `file:line`, impact, recommendation, verification method, and confidence; the report also lists "verified clean" areas and "not covered this round".

It also checks whether the verification method itself is valid: positive and negative cases, failure exit codes, whether commands actually ran, and whether a guard script can produce a false green.

## What it caught: a real two-pass health check

> The following comes from two health-check passes on a real multi-client project (2026-08-30 and 2026-09-02). Project names, addresses, credentials, and business details have been removed. This is not demo data, and it is not an industry-wide benchmark.

| Result | Evidence |
|---|---|
| **30 graded findings** | 10 P0/P1, 9 P2, and 11 P3; all 10 P0/P1 findings were closed |
| **Multiple release blockers found before deployment** | A MySQL 8.0 migration would always fail; deployment scripts skipped migrations; a production migration would insert an enabled test account with a known password |
| **Security risks traced to concrete paths** | Runtime configuration hard-coded JWT/DB/Redis credentials; using the dev profile could enable a default SMS code and mock WeChat login while skipping production validation |
| **Real regression after fixes** | Backend tests passed 115/115; containerized migrations passed 10/10 three times in a row; Android both flavors and the merchant Web build succeeded |
| **Two more real bugs found during repair** | A deployment script resolved the wrong project root; unstable database readiness made migration regressions fail randomly |
| **One false green eliminated** | A guard script swallowed migration failures and still reported GREEN; it now treats failure as invalid verification and is proven with positive and negative cases |
| **Deployment drift exposed** | The deployed JAR differed from local build output in 33 classes and was missing 7 classes; the report explicitly marked that this was not re-verified later |

> These numbers do not mean "the checklist is long." They mean findings moved from **unknown** to **quantified**, fixes moved from **claimed complete** to **re-runnable**, and the verifier itself is now protected by failing cases.

**The limits are stated too**: the project did not claim "all clear"; some P2/P3 items remained open; credentials already in Git history still required real rotation; and the deployed-JAR drift was not re-checked later. Keeping those limits prevents "passed this pass" from being misread as "secure forever."

## Triggers

Say any of these:

- "Run a project health check"
- "Do a comprehensive project review"
- "Pre-release audit"
- "Check this project before handover"
- "Find P0/P1 issues before deployment"
- "Use project-health on this repo"

## Requirements

- Git is preferred. A change review validates the baseline with `git rev-parse`. Without Git, the skill can still take a read-only snapshot, but must state that history, a fixed point, and an exact diff are unavailable.
- Docker must be available if you want containerized migration/regression checks.
- The review phase is read-only by default; confirm the report path, and require an explicit instruction before code changes.
- For Windows-specific troubleshooting, read `references/windows-pitfalls.en.md` first.

## Package layout

```text
project-health/
├── SKILL.md / SKILL.en.md                # skill body (Chinese default / English mirror)
├── README.md / README.en.md              # this file
├── AGENTS.md                            # standing rules (task boundaries and pitfall discipline)
├── PITFALLS.md                          # reusable pitfalls log
├── references/                           # platform commands, Windows traps, verification, reports
├── scripts/                              # cross-platform verification and redaction scanners
└── LICENSE / COMMERCIAL / SIGNING / SANITIZATION
```

## Platform support

The core skill uses only Markdown and Git commands. It works on Windows 10/11 + PowerShell 5.1/7, macOS / Linux + Python 3.9+, and WSL2. The Python verifier uses only the standard library and needs no network access.

## Self-check

From the package root:

```bash
python3 scripts/verify_package.py
```

On Windows:

```powershell
python scripts\verify_package.py
```

If Python is unavailable, use the PowerShell verifier:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-package.ps1
```

It checks required files, UTF-8 without BOM, Markdown links, the redaction self-test, sensitive patterns in the package, and `SKILL.md` / `SKILL.en.md` frontmatter, version, and language links.

Run only the redaction scanner:

```bash
python3 scripts/check_redaction.py --self-test
python3 scripts/check_redaction.py --path .
```

On Windows PowerShell, use `scripts/check-redaction.ps1`; see `SANITIZATION.en.md` for the full commands.

## Download and signatures

Download official artifacts from [GitHub Releases](https://github.com/Fallen-leaves089/project-health/releases): `project-health-<version>.zip`, `SHA256SUMS`, `SHA256SUMS.sig`, `allowed_signers`, and `release-signing-key.pub`.

Check the public-key fingerprint first:

```bash
ssh-keygen -lf release-signing-key.pub
```

See `SIGNING.md` / `SIGNING.en.md` for the complete macOS, Linux, and Windows verification commands. `SHA256SUMS` and `SHA256SUMS.sig` are separate assets created after the zip; they are not inside the zip.

## Security and redaction

The review phase is read-only by default. The public version removes personal absolute paths, usernames, project/client identifiers, internal platform names, real domains and private addresses, secrets, and incident details. If you find a possible leak, open an issue or contact the maintainer through a public channel; do not paste the sensitive value.

See `SANITIZATION.en.md` for the full scope and `SECURITY.md` for reporting.

## Contributing

See `CONTRIBUTING.en.md`. New environment traps should include "trap / workaround / verification"; new guard scripts must include positive and negative cases.

## License

This work is licensed under the **PolyForm Noncommercial License 1.0.0**. The English original is in `LICENSE`; the Chinese summary is in `LICENSE.zh-CN.md`.

Commercial use requires a written license from the author, but **the author is open to discussing it**. For commercial licensing, contact `chenshuidelaye@qq.com`; terms and scope are negotiable. See `COMMERCIAL.en.md`.

> GitHub's license detector does not list PolyForm, so the repository page may show `NOASSERTION / Other`. That does not mean the package is unlicensed; the `LICENSE` text controls.

## Version

- Version: 1.2.2
- Internal source date: 2026-09-04
- Public release: 2026-10-30
