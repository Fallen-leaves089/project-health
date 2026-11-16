# Debugging and Verification Playbook

[中文](verification-playbook.md) | **English**

This playbook addresses a common failure: **"the command finished" does not mean "the problem was proven"**. The most dangerous conclusion in a project health check is not "I found no problem"; it is "I used a check that proves nothing and concluded there is no problem".

## 1. Build a feedback loop that can turn red first

Before locating any bug, build a loop that reliably distinguishes "broken" from "working". Without that loop, reading code is just guessing.

Priority order:

1. **Failing test**: unit, integration, or end-to-end, at the smallest seam that reaches the bug.
2. **HTTP or CLI script**: send a request to a running service, or feed fixed input to a CLI and assert the output.
3. **Headless browser**: drive the real UI and assert DOM, console, and network behavior.
4. **Replay a capture**: save real requests, responses, or event logs and replay them in an isolated environment.
5. **One-off harness**: start only the small part of the system that fails and mock unrelated dependencies.
6. **Property or fuzz testing**: for output that is only sometimes wrong, run many random inputs to find the failure pattern.
7. **Bisect loop**: automate start, check, and repeat between a known-good and known-bad state.
8. **Differential loop**: run the same input through the old and new versions, or two configurations, and compare output.

Do not start with a "log everything" pass. First get a command that can turn red, then add logs.

## 2. Definition of a complete loop

A usable loop must be:

- **Able to turn red**: it asserts the symptom the user described, not merely "it did not crash". It must turn green after the fix.
- **Deterministic**: the same input produces the same conclusion. A flaky bug must at least reproduce with high probability.
- **Fast**: seconds is ideal; minutes is acceptable. A loop that takes fifteen minutes has too low a ceiling; shorten it first.
- **Automatable**: no mouse clicks. If a human must intervene, script the steps and record the output.

The completion signal is that you can name **one command you have actually run** (script path, test command, or curl) and show its output after redaction.

If that command does not exist yet, stay in Phase 1. Do not enter the "I think it might be..." stage.

## 3. Reproduce and minimize

After the loop turns red:

1. Confirm it reproduces **the problem the user described**, not a different problem that happens to fail nearby.
2. Record the exact symptom: error message, wrong output, duration, and conditions.
3. Remove one input, caller, configuration, data item, or step at a time, rerunning the loop after each change.
4. Keep only the elements whose removal makes the loop stop turning red.

The value of a minimal reproduction:

- it narrows the hypothesis space;
- it becomes a clean regression test;
- it makes post-fix verification more convincing.

## 4. List hypotheses before touching code

Before changing code, list **3-5 hypotheses ordered by likelihood**. Each hypothesis must be falsifiable:

> If X is the cause, changing Y makes the problem disappear, and changing Z makes it worse.

If you cannot state a prediction, it is a feeling, not a hypothesis. Discard the feeling.

Show the ranked hypotheses to the user when possible. Users often have context you do not have ("we just changed #3") and can reorder them instantly. If the user is unavailable, continue with your own ranking; do not stop.

## 5. Single-variable probing

Each probe tests one hypothesis and changes **one variable at a time**.

Tool priority:

1. debugger or REPL inspection;
2. targeted logging at a boundary that distinguishes hypotheses;
3. do not "log everything and grep".

Give every temporary log a unique prefix, such as `[DEBUG-a4f2]`. Remove all of them by prefix during wrap-up; logs without a prefix will remain and pollute the code.

For performance problems, do not start with logs. Establish a baseline first (timing harness, profiler, query plan), then bisect. Measure before fixing.

## 6. Fix and regression

Before writing a regression test, check whether the seam is right:

- The test must reach the **real bug pattern**, not just an isolated helper.
- If the only available seam is too shallow (single caller, key path mocked out), the test gives false confidence.
- "No suitable seam" is itself a finding: the architecture makes this bug impossible to pin down. Report it.

When a suitable seam exists:

1. turn the minimal reproduction into a failing test;
2. watch it fail;
3. fix;
4. watch it pass;
5. rerun the original, unminimized scenario from Phase 1.

After the fix, also check:

- the original reproduction no longer occurs;
- the regression test passes, or "no suitable seam" is recorded;
- every `[DEBUG-...]` line is gone;
- one-off prototypes are deleted or moved to a clearly marked debug directory;
- the hypothesis that turned out correct is written into the commit or PR description for the next debugger.

## 7. Guard scripts must run positive and negative cases

**A guard that can only report green is not a guard.**

Every guard script must verify at least:

- **Positive case**: input that should pass must pass.
- **Negative case**: input that should fail must fail.

Choose the negative case carefully:

- Do not use a sample that "also fails for another reason". For example, using an old version that also has a syntax error to verify "seed accounts are detected" only proves the verification is invalid.
- The negative case should trigger only the target behavior; no other error may mask it.
- If the reason for a negative failure is unclear, fix the negative case first. Do not count it as a working guard.

## 8. Common false negatives

| False negative | Consequence | Correct approach |
|---|---|---|
| `2>&1 \| Out-Null` swallows the exit code | A crash is counted as a pass | Save `$LASTEXITCODE` before filtering |
| `cmd \| tail` followed by `$?` | You see `tail` succeeding | Save the native exit code before the pipeline |
| The negative case has its own syntax error | It cannot prove the guard detects the target issue | Make the negative case contain only the target error |
| Empty or missing fixture tables | The check passes without covering the real schema | Cover every referenced table and include data rows |
| Only the positive case is run | The guard may report green forever | Run both positive and negative cases |
| Only "the command did not error" is checked | Business results are unverified | Assert specific output, row counts, or status codes |
| A migration is run only once | A non-idempotent script looks fine | Run the containerized migration twice; the second run must also succeed |
| Build artifacts are not inspected | A test endpoint or debug switch reaches production | grep key strings in the built artifact |
| The baseline is not validated | You reviewed the wrong range | Stop when `git rev-parse` fails |

## 9. Three common examples

### 9.1 Idempotent migration

- Positive: run the migration twice on a clean database; the second run succeeds and the schema is correct.
- Negative: deliberately create a migration that inserts duplicate rows on the second run; the guard must fail.
- Assertion: test accounts and test data are zero or match the expected count; real data is untouched.

### 9.2 Build artifact inspection

- Positive: inject the production API address and build; the artifact contains only the production address.
- Negative: inject a test address and build; the inspection must fail.
- Assertion: the artifact contains no test IP, test domain, or debug switch.

### 9.3 Configuration fail-fast

- Positive: all critical production variables are present; startup succeeds.
- Negative: a critical variable is an empty string; startup must fail.
- Note: an empty string does not always trigger a framework default. Do not assume it falls back.

## 10. Coverage boundaries and untested items

> As of **2026-11-16 / 1.4.6**. This is the current acceptance boundary, not a list of known defects. A result counts as "tested" only when the check was actually executed and its result was inspected. A `SKIP`, a missing tool, a skipped job, or a check that only verified a tool's help or enumeration output must be classified as **untested / uncovered**. Untested does not mean broken, and it must never be reported as passed.

### 10.1 Current public evidence

| Environment | Actual result | Evidence |
|---|---|---|
| GitHub Actions `Verify package` | Ubuntu 24.04, `macos-latest`, and Windows Server 2025 all passed on Python 3.9 and 3.12; Windows also ran the PowerShell 5.1 and 7 package verifiers | [run 43792286318](https://github.com/Fallen-leaves089/project-health/actions/runs/43792286318) |
| GitHub Actions `Verify server playbooks` | Linux `pass=61 skip=7 fail=0 systemd=1`; hosted Windows Server `Windows Server: True` and `pass=33 skip=6 fail=0`; the self-hosted roles job was `skipped` | [run 43792286327](https://github.com/Fallen-leaves089/project-health/actions/runs/43792286327) |
| Local Windows 11 | Python 3.10 and 3.14.2 each passed 53 tests; Python and PowerShell package verification passed | Maintainer-local run, not public CI |
| Ubuntu 24.04 containers | Python 3.9 and 3.12 each passed 52 tests with 11 skips; run before 1.4.4 and not rerun for 1.4.5 | Maintainer historical record |

### 10.2 Untested or uncovered

| Scope | Current evidence | Why it is untested | Environment needed to close it |
|---|---|---|---|
| Windows Server 2019/2022 | Server smoke ran only on Windows Server 2025 | Hosted `windows-latest` does not provide 2019/2022 | A real VM or runner with the target version |
| Windows 10 | The local machine is Windows 11; hosted `windows-latest` is Server 2025 | No Windows 10 environment | A Windows 10 machine/VM, rerun with PowerShell 5.1 |
| Domain controller, AD, Kerberos, GPO, SPN | `klist.exe` returned nonzero; domain controller, GPO, and SPN checks were skipped | The runner is not domain-joined and has no domain account | A domain-joined Windows host, reachable domain controller, and read-only test account |
| WinRM listener | `winrm` is absent; the self-hosted roles job was skipped | The hosted image lacks `winrm` and no self-hosted runner is configured | A Windows Server runner with WinRM enabled, read-only listener enumeration and `Test-WSMan` |
| Failover cluster | The `FailoverClusters` module is absent; cluster checks were skipped | The hosted image has no cluster module or cluster node | A Windows Server node with the failover-cluster feature installed |
| SQL Server instance connection and query | Only `sqlcmd -?` help ran; no instance was connected and no query was executed | No SQL Server instance or read-only credential is available | A test instance and read-only login, with a version query and minimal health query |
| IIS end-to-end HTTP/TLS request | IIS websites and application pools were enumerated; no real site request or certificate handshake was made | The hosted image has no business site or usable certificate | A target IIS site, a test certificate, and a read-only HTTP/TLS probe |
| Linux SELinux | `getenforce` and `ausearch` are absent; the checks were skipped | The Ubuntu hosted image lacks the tooling/policy environment | A host with SELinux enabled, such as RHEL, Rocky, Alma, or Fedora |
| Linux firewalld | `firewall-cmd` is absent; the check was skipped | The Ubuntu hosted image does not use firewalld | A Linux host using firewalld |
| Linux dnf/RPM package management | `dnf` and `needs-restarting` are absent; the checks were skipped | The current image uses apt | A Fedora, RHEL, Rocky, or Alma Linux host |
| Linux SSH directory and authorized-file permissions | The CI service user's `$HOME/.ssh` is absent; the checks were skipped | The CI runner has no service-user SSH configuration | The target server's real service-user `.ssh` and `authorized_keys` |
| Native macOS system behavior | CI ran package and contract tests only; native arm64, Rosetta, Gatekeeper/TCC, launchd, and APFS behavior were not exercised | A macOS runner is not the target Mac and did not run system-level scenarios | An Apple Silicon Mac, an Intel/Rosetta session, and the corresponding system test plan |
| Python 3.11/3.13 | The CI matrix covers only 3.9/3.12; 3.14 has only a local Windows result | Not in the matrix and not rerun in an independent environment | Run the full tests and package verification on 3.11/3.13, or add them to the CI matrix |
| Agent autonomous memory evaluation | `tests/agent_memory_eval.py` is optional and was not run against a real Codex agent this round | It depends on an external non-deterministic agent | Run it explicitly in a controlled environment and record the model, prompt, and results |

### 10.3 Gate boundaries

- The current `main` required checks are only the six `Verify package` matrix jobs (Ubuntu, macOS, and Windows, each on Python 3.9 and 3.12), with strict status checks and administrators enforced too.
- `Verify server playbooks` is path-filtered and is not a required check; its self-hosted roles job can also report `skipped`. A green pull request therefore does not by itself prove that server smoke ran.
- When a report reaches one of the rows above, cite the untested reason and the closing condition. After a rerun, update the date, version, and actual evidence; do not keep using a historical skip as the current result.

## 11. Wrap-up

- the original reproduction no longer occurs;
- regression tests pass, or the missing seam is recorded;
- temporary logs, scripts, and data are removed;
- line numbers in the report are rechecked;
- the report and commit message are redacted;
- the next debugger can see from the commit or PR description which hypothesis was correct.
