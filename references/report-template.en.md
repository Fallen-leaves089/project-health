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

## Three actions to take now

1. `...`
2. `...`
3. `...`

> At most 3 actions the user can take today. If evidence is insufficient, name the verification to add first; do not pad the list.

## Executive summary

- P0: `N`
- P1: `N`
- P2: `N`
- P3: `N`
- Overall decision: `ready to deploy / deploy after P0 and P1 are fixed / not ready`
- One-line risk: `...`

> Reading priority: expand P0/P1 fully; keep P2 to one problem line plus a brief impact/recommendation; keep P3 to one line. Expand a secondary item only when it changes the release, handover, or rollback decision.

## P0 Will break on deployment day

| ID | Location | Problem | Impact | Recommendation | Verification | Confidence | Status |
|---|---|---|---|---|---|---|---|
| P0-1 | `file:line` | ... | ... | ... | ... | verified / observed / inferred | Open |

## P1 Must be fixed before deployment

| ID | Location | Problem | Impact | Recommendation | Verification | Confidence | Status |
|---|---|---|---|---|---|---|---|
| P1-1 | `file:line` | ... | ... | ... | ... | verified / observed / inferred | Open |

## P2 Recommended before deployment

| ID | Location | Problem + impact | Minimum recommendation | Confidence | Status |
|---|---|---|---|---|---|
| P2-1 | `file:line` | One sentence covering problem and impact | One-sentence recommendation | verified / observed / inferred | Open |

## P3 Hygiene and maintainability

| ID | Location | Problem | Recommendation | Confidence | Status |
|---|---|---|---|---|---|
| P3-1 | `file:line` | ... | ... | verified / observed / inferred | Open |

> Keep P3 to one line by default; do not write long explanations for low-impact hygiene items.

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

## Resident hidden-pitfall coverage

### Baseline resident set (RES-01 through RES-08)

| Tripwire | Status | Evidence | Full entry |
|---|---|---|---|
| RES-01 false green / skipped tests | checked / not applicable / uncovered | `...` | CICD-02 |
| RES-02 exit code swallowed by a pipe or wrapper | checked / not applicable / uncovered | `...` | CICD-02 |
| RES-03 secrets or personal data in artifacts/logs | checked / not applicable / uncovered | `...` | SEC-01, SEC-07 |
| RES-04 tenant or resource boundary supplied by the client | checked / not applicable / uncovered | `...` | IAM-04 |
| RES-05 backup exists but restore/rollback was not exercised | checked / not applicable / uncovered | `...` | DAT-01, OBS-07 |
| RES-06 Rosetta treated as native architecture | checked / not applicable / uncovered | `...` | MAC-H01 |
| RES-07 Windows service depends on desktop or personal account | checked / not applicable / uncovered | `...` | WIN-02 |
| RES-08 Linux disk/inode/log/memory exhaustion | checked / not applicable / uncovered | `...` | LNX-05 |

### User-promoted resident set (triggered by RES-09)

| URES ID | Source entry | Minimal user quote | Upgraded at | Scope | Revocation/downgrade condition | Current status |
|---|---|---|---|---|---|---|
| none | - | - | - | - | - | RES-09 not triggered |

- RES-09 promotion control: not triggered / applied / not applicable / uncovered
- Resident capacity: baseline 8 + user-promoted `N` = `M`; when `M > 12`, warn that the resident layer is heavy and recommend reviewing downgrade candidates

> The eight baseline rows and RES-09 control must have a status; every user-promoted entry must also be `checked / not applicable / uncovered`. `uncovered` must never be reported as passed.

## Structural experience harvest

| Primary chapter | Deepest path | Chapter coverage | Branch result | Entry matched | Entry status | Injection | Evidence |
|---|---|---|---|---|---|---|---|
| A | `A/<slug>/...` | opened / no signal / not applicable / cross-chapter reference / unclassified | leaf match / ancestor match / explored with no match (report only) / insufficient granularity / conflict (group not injected) / cross-chapter reference | none / `S-...` | none / `verified / pending verification / obsolete` | none / `detailed / brief / soft hint` | `...` |
| B | ... | ... | ... | ... | ... | ... | `...` |
| C | ... | ... | ... | ... | ... | ... | `...` |
| D | ... | ... | ... | ... | ... | ... | `...` |
| E | ... | ... | ... | ... | ... | ... | `...` |
| F | ... | ... | ... | ... | ... | ... | `...` |

> Keep at least one row for each A-F chapter. Add rows for additional branches in the same chapter, but never omit another chapter.

- Entries matched: none / `S-...` (primary chapter `X`; primary branch `...`; related branches `...`)
- Conflict group: none / `S-..., S-...` (same branch, trigger category, status, and level; no entry injected)
- Sibling granularity warning: none / `...` (report-only; the recorder does not reject the write)
- Current-project verification: none / `evidence and result`
- Added: none / `N` (`references/structural-experience.en.md` or `STRUCTURE.local.md`)
- Over-limit justification: not applicable / for more than two entries, explain each entry's independence and why it cannot be merged or deferred

## Memory result

- Memory: appended `<N>` entry/entries, `<M>` duplicate(s) (`<PITFALLS.md or PITFALLS.local.md>`)
- Pending: none (or `<summary and write-failure reason>`)

## Notes

- Secrets, tokens, cookies, client names, real domains, and private IPs in this report have been redacted.
- Line numbers refer to the baseline; recheck them after fixes.
