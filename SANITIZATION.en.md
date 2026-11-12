# Sanitization Notes

[中文](SANITIZATION.md) | **English**

This document records what changed from the internal edition to the public edition, and why some material was kept. The goal is not to remove every word that looks sensitive. The goal is to **keep reusable engineering experience while removing identifiable information**.

## Source

- Internal skill compilation date: 2026-09-04
- Public package version: 1.3.1
- Method: rewrite section by section instead of find-and-replace; delete or abstract sensitive passages

## Removed

- **Personal absolute paths and usernames**: replaced with `C:\Users\<you>`, `$env:USERPROFILE`, `<PROJECT>`, and similar placeholders.
- **Internal projects, clients, and business names**: no concrete project names, store names, account names, order numbers, or customer identifiers remain.
- **Internal agent platform and memory directory names**: replaced with "the project's agent memory directory, if present"; no specific platform directory is named.
- **Real domains, private IPs, hostnames, and ports**: replaced with `<HOST>`, `<DOMAIN>`, `127.0.0.1`, or documentation-reserved addresses.
- **Keys, tokens, cookies, connection strings, and passwords**: no real values remain; examples use `<REDACTED>`.
- **Business data from specific incidents**: only reusable lessons remain, such as "non-idempotent migration", "seed data mixed into a migration", or "test endpoint left in a build artifact".
- **Platform-specific metadata**: frontmatter fields and skill-management markers meaningful only to one host were removed.

## Kept

- **The project health-check workflow**: history first, alignment, baseline, two-axis review, real builds, P0-P3 grading, and fix discipline.
- **Windows environment traps**: PowerShell versus Git Bash differences, `mvn.cmd`, Surefire XML, Python PATH, UTF-8 BOM, pipeline exit codes, Docker Desktop, WSL2, MySQL initialization, `git mv`, `BASH_SOURCE`, and more.
- **Enterprise pitfall baseline**: 16 domains and 162 cross-platform engineering traps covering requirements and acceptance, architecture, permissions, multi-tenancy, data migration, APIs, concurrency and caching, build and supply chain, CI/CD, containers and cloud, network and TLS, observability, security and compliance, and handover/operations.
- **Server platform traps**: Windows Server IIS, services, NTFS/SMB, AD/Kerberos, SQL Server, certificates, WinRM, EDR, patching, and clusters; Linux systemd, permissions, SELinux/AppArmor, disk, OOM, firewall, NTP, package management, SSH, databases, containers, and rollback.
- **Debugging and verification discipline**: positive and negative cases, a feedback loop that can turn red, minimal reproduction, 3-5 falsifiable hypotheses, single-variable probes, regression tests, and cleanup.
- **Security baseline**: do not trust the current working directory, validate directory fingerprints, fail closed, validate environment variables, inspect build artifacts, and require scanners to scan themselves with bootstrap negative cases.
- **Untrusted-target boundary**: a target repository's `AGENTS.md`, `PITFALLS.md`, README, comments, and logs are low-trust evidence only and cannot override user instructions, safety limits, or this skill's rules.
- **Redaction discipline**: replace secrets before showing logs or configuration; cover JSON, TOML, YAML, and ENV; do not read sensitive files.
- **Cross-platform command reference**: Windows PowerShell, macOS/Linux bash/zsh, and WSL2 equivalents so reviewers use the shell they are actually in.
- **The author's public commercial contact email**: `chenshuidelaye@qq.com` is intentionally public and is not a sanitization leak.

## Key rewrites

| Original content type | Public edition treatment |
|---|---|
| Interpreter paths under a fixed user directory | `where.exe python`, `py -3`, `Get-Command python` |
| Host-specific question or skill-management calls | "ask the user", "the host's skill directory" |
| Terminology from a specific business system | "frontend", "business data", "real data", "critical path" |
| Findings from a specific project | remove the finding, keep the method and verification |
| Hosts and ports from a specific environment | `<HOST>`, `127.0.0.1`, or "the service in the container" |

## English translations

English documents are translations of the Chinese originals. They do not add new source material. When the two versions differ, the Chinese document is the maintenance source for workflow details, and `LICENSE` remains the controlling legal text.

## Automated checks

The package provides a Python path for every operating system and a PowerShell path for Windows:

```bash
# Cross-platform scanner self-test
python3 scripts/check_redaction.py --self-test

# Cross-platform package scan
python3 scripts/check_redaction.py --path . --quiet

# Full package check
python3 scripts/verify_package.py

# Contract tests and malicious-target fixture
python3 -B -m unittest discover -s tests -p "test_*.py"
```

```powershell
# Windows PowerShell equivalents
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-redaction.ps1 -SelfTest
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-redaction.ps1 -Path .
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-package.ps1
```

The scanners check for:

- Windows (backslash or forward slash) and Unix home paths
- private IPv4 addresses
- OpenAI-style keys, GitHub tokens, and AWS access keys
- PEM private-key blocks
- long values assigned to `api_key`, `token`, `password`, and similar names, including quoted JSON/TOML/YAML keys

Project-specific words, client names, and internal code names are not in the default rules. Pass them explicitly:

```bash
python3 scripts/check_redaction.py --path . --extra-pattern ACME-INTERNAL --extra-pattern PROJECT-CODE
```

## Manual review

Before the public release, every file was read once, and the following patterns were searched separately:

- `C:\Users\` followed by a real username
- `/home/` followed by a real username
- `sk-`, `ghp_`, `github_pat_`, `AKIA`
- `BEGIN ... PRIVATE KEY`
- private IPv4 ranges
- internal project names, client names, and real domains

## Residual risk

- General experience may still "look like" a particular project, but it contains no identifiable personal, client, or secret information.
- The license and commercial terms are not legal advice. Consult a lawyer or the author if a specific use is unclear.
- Automated scanning covers known patterns only; it cannot prove that no sensitive information exists. Report suspected leaks through a public channel and never paste the sensitive value into an issue.
- Private addresses and example keys in the scanner self-tests are fixtures only and do not correspond to real hosts or accounts.
- Prompt-injection defenses reduce text-layer risk but cannot prove that every model in every context will resist every inducement; report bypasses as security issues.

## Pre-release checklist

- [x] All text files are UTF-8 without BOM
- [x] Relative Markdown links resolve
- [x] Redaction scanner positive and negative self-tests pass
- [x] Untrusted-target contract tests and the malicious `AGENTS.md` fixture pass
- [x] Package scan is clean
- [x] No personal absolute paths, real usernames, project names, or client names
- [x] No real secrets, tokens, private keys, or connection strings
- [x] No real domains, private IPs, hostnames, or ports (except self-test fixtures)
- [x] License and commercial licensing notes are present
- [x] Versions, dates, and directory structure are consistent
- [x] The Python verifier runs on Windows, macOS, Linux, and WSL2 in CI

## Reporting a suspected leak

If you find a possible leak:

1. Do not paste the concrete value in public.
2. Open an issue titled `[Security]` and describe only the file and the type of information.
3. Or contact the maintainer through a published private channel.
4. After confirmation, the maintainer removes or replaces it and records the change in `CHANGELOG.md` without writing the sensitive value into the commit message.
