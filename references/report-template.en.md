# <PROJECT> Project Health Check Report

[中文](report-template.md) | **English**

- Check date: `YYYY-MM-DD`
- Reviewer: `<NAME>`
- Review mode: `change review / full review / no-Git snapshot`
- Baseline: `<COMMIT / BRANCH / TAG>`
- Worktree state: `clean / uncommitted changes (describe handling)`
- Rules used: `project conventions / external rule pack / combination`
- Coverage: `backend / frontend / mobile / database / containers / deployment`
- Not covered: `...`

## Executive summary

- P0: `N`
- P1: `N`
- P2: `N`
- P3: `N`
- Overall decision: `ready to deploy / deploy after P0 and P1 are fixed / not ready`
- One-line risk: `...`

## P0 Will break on deployment day

| ID | Location | Problem | Impact | Recommendation | Verification | Confidence | Status |
|---|---|---|---|---|---|---|---|
| P0-1 | `file:line` | ... | ... | ... | ... | verified / observed / inferred | Open |

## P1 Must be fixed before deployment

| ID | Location | Problem | Impact | Recommendation | Verification | Confidence | Status |
|---|---|---|---|---|---|---|---|
| P1-1 | `file:line` | ... | ... | ... | ... | verified / observed / inferred | Open |

## P2 Recommended before deployment

| ID | Location | Problem | Impact | Recommendation | Verification | Confidence | Status |
|---|---|---|---|---|---|---|---|
| P2-1 | `file:line` | ... | ... | ... | ... | verified / observed / inferred | Open |

## P3 Hygiene and maintainability

| ID | Location | Problem | Recommendation | Confidence | Status |
|---|---|---|---|---|---|
| P3-1 | `file:line` | ... | ... | verified / observed / inferred | Open |

## Verified with no issue

- `<module / check>`: `evidence / command / result`
- ...

## Not covered this round

- `<module / check>`: `reason (environment, permission, time, missing fixture)`
- ...

## Reproduction commands

```powershell
# Baseline
git rev-parse <COMMIT>
git diff <COMMIT>...HEAD --stat

# Tests
<command>

# Build
<command>

# Migration/container regression
<command>
```

## Environment and versions

- OS: `Windows <version>`
- PowerShell: `<version>`
- Node / Java / Python: `<version>`
- Docker / Compose: `<version>`
- Database: `<version>`
- Browser / emulator: `<version>`

## Evidence and attachments

- Logs: `<path>` (redacted)
- Screenshots: `<path>` (redacted)
- Packet capture: `<path>` (redacted)
- Build artifact: `<path>`

## Fix log

| Date | Item | Change | Regression result | Commit |
|---|---|---|---|---|
| `YYYY-MM-DD` | P0-1 | ... | ... | `<sha>` |

## Notes

- Secrets, tokens, cookies, client names, real domains, and private IPs in this report have been redacted.
- Line numbers refer to the baseline; recheck them after fixes.
