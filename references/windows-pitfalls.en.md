# Windows Environment Traps and Workarounds

[中文](windows-pitfalls.md) | **English**

This list comes from real project checks. Its purpose is to keep reviewers from hitting the same Windows walls. Commands use PowerShell by default; Git Bash or WSL is called out explicitly when needed.

> Rule: confirm the current shell, interpreter, and tool path before running a command. Do not put bash syntax inside PowerShell, and do not assume every Windows tool is directly callable from Git Bash.

## 1. Confirm the shell and version

```powershell
$PSVersionTable.PSVersion
Get-Command powershell.exe, pwsh.exe -ErrorAction SilentlyContinue
```

- **Windows PowerShell 5.1** does not support `&&`, `||`, or the ternary operator. Use `;`, `if`, or separate commands.
- **PowerShell 7+** supports `&&` and `||`, but native process exit codes still live in `$LASTEXITCODE`.
- If you are not sure a tool exists, run `where.exe <tool>` or `Get-Command <tool>` first. Do not just try it.

## 2. Paths and quoting

- Resolve paths with `$env:USERPROFILE`, `$env:LOCALAPPDATA`, and `$PSScriptRoot`. Do not hard-code `C:\Users\<you>`.
- Quote paths that contain spaces:
  ```powershell
  & 'C:\Program Files\Some Tool\bin\tool.exe' --version
  ```
- When passing paths to a native program, prefer an argument array instead of hand-built strings:
  ```powershell
  & $exe @('--input', $inputPath, '--output', $outputPath)
  ```
- Long paths may hit MAX_PATH. Reduce directory depth, or use the `\\?\` prefix where the tool supports it.
- Do not put a project in OneDrive or another sync directory and run builds there. File locks and sync can create random failures.

## 3. Encoding and BOM

- Public and committed text uses **UTF-8 without BOM**.
- Windows PowerShell 5.1 `Set-Content -Encoding UTF8` and `Out-File -Encoding utf8` may write a BOM. For no BOM, use .NET:
  ```powershell
  [System.IO.File]::WriteAllText($path, $text, [System.Text.UTF8Encoding]::new($false))
  ```
- Check for a BOM:
  ```powershell
  $b = [System.IO.File]::ReadAllBytes($path)
  $hasBom = $b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF
  ```
- If the `file` command is unavailable, use `Format-Hex` or read the bytes with Python.
- If a patch containing Chinese text fails through `apply_patch`, check argument encoding first. You can replace bytes with Python and assert a unique match; do not blindly resend the whole patch.

## 4. Exit codes, pipelines, and false negatives

- A native process exit code is in `$LASTEXITCODE`, not `$?`.
- A pipeline mixes "the command failed" with "the downstream formatter succeeded". Save the exit code before filtering:
  ```powershell
  & $exe @args
  $code = $LASTEXITCODE
  # Then run Select-String or Format-Table.
  if ($code -ne 0) { throw "command failed: $code" }
  ```
- Do not use `2>&1 | Out-Null` or `>/dev/null 2>&1` to swallow the status of the command under test. That makes "it crashed" and "it finished cleanly" look identical.
- To inspect output and the exit code together:
  ```powershell
  $out = & $exe @args 2>&1
  $code = $LASTEXITCODE
  $out | Select-Object -Last 50
  if ($code -ne 0) { throw "command failed: $code" }
  ```
- `Start-Process -Wait -PassThru` exposes `.ExitCode` and is useful for programs that need a separate window or elevation.

## 5. Maven and Java

- Under Git Bash, `mvn` may be missing or behave oddly. On Windows, prefer PowerShell with `mvn.cmd`.
- If the project has a wrapper, prefer `.\mvnw.cmd` to avoid a global Maven version drift.
- `mvn.cmd -q test` may print no summary. Parse the Surefire XML instead:
  ```powershell
  $reports = Get-ChildItem -Path .\target\surefire-reports -Filter *.xml -File
  $total = 0; $failures = 0; $errors = 0; $skipped = 0
  foreach ($r in $reports) {
      [xml]$x = Get-Content -LiteralPath $r.FullName -Encoding UTF8
      $total += [int]$x.testsuite.tests
      $failures += [int]$x.testsuite.failures
      $errors += [int]$x.testsuite.errors
      $skipped += [int]$x.testsuite.skipped
  }
  "tests=$total failures=$failures errors=$errors skipped=$skipped"
  ```
- When counting with awk, remember the attribute is `tests=` (with the equals sign). Writing `s["tests"]` silently returns zero.
- `-DskipTests` still compiles tests; `-Dmaven.test.skip=true` skips test compilation too. They are not equivalent; state which one you ran.
- `JAVA_HOME` points to the JDK root, not `bin`. If the path has spaces, do not build an unquoted command by hand.

## 6. Python

- Confirm the interpreter first:
  ```powershell
  where.exe python
  py -3 --version
  Get-Command python | Select-Object Source
  ```
- The Windows Store `python` may be an alias. Prefer `py -3` or an explicit interpreter path.
- Install dependencies into a project venv; do not pollute global site-packages:
  ```powershell
  py -3 -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  .\.venv\Scripts\python.exe -m pytest
  ```
- If direct PyPI access fails, first identify whether it is a network, certificate, or mirror problem. Record any mirror change in the environment notes; do not put mirror configuration into a repository secret file.
- Always use `encoding='utf-8'` when reading or writing text. The Windows default is not guaranteed to be UTF-8.
- To force UTF-8, set `PYTHONUTF8=1` in the current process, but do not assume every child process inherits it.

## 7. Git

- Use PowerShell's Git consistently inside a Windows repository. Mixing WSL Git and Windows Git can create a large number of newline-only changes.
- If you see many `M` entries that differ only by newline, inspect them first:
  ```powershell
  git status --short
  git diff --ignore-cr-at-eol --stat
  ```
- `.gitattributes` can pin `eol`, but historical blobs and index normalization can still show modified files. Stage only the intended file; do not reflexively run `git add -A`.
- `git mv` keeps the old blob. If you edit the content before `git mv`, you get `RM` (rename staged, modification unstaged); a direct commit records only the move. Read the **second column** of `git status --short`: `M ` / `R ` are staged, ` M` / `RM` are not.
- Validate the review baseline before using it:
  ```powershell
  git rev-parse <fixed-point>
  git log <fixed-point>..HEAD --oneline
  git diff <fixed-point>...HEAD --stat
  ```
- Before committing, run `git diff --check` to catch whitespace errors and conflict markers.

## 8. Docker Desktop and WSL2

- If the Docker daemon is not running, container regressions fail immediately. Ask the user first, then start Docker Desktop and poll:
  ```powershell
  # Common path; adjust to the actual installation.
  Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -WindowStyle Hidden
  $deadline = (Get-Date).AddMinutes(3)
  do {
      docker info *> $null
      if ($LASTEXITCODE -eq 0) { break }
      Start-Sleep -Seconds 3
  } while ((Get-Date) -lt $deadline)
  ```
- `docker compose config` only checks interpolation and syntax; it does **not** need the daemon. Use it first to rule out configuration errors.
- Inside WSL2, `localhost` may resolve to IPv6 `::1` while forwarding listens on IPv4. Prefer `127.0.0.1` for services on the Windows side.
- WSL2 forwards `127.0.0.1` listeners to Windows. If a service must be reachable only inside WSL, bind `127.0.0.2` and verify it.
- Do not put a Unix socket on `/mnt/*` (9p/drvfs does not support sockets). Use `/run` or a Linux-native filesystem.
- `chmod`/`chown` on `/mnt/*` is not real Unix permission control. For isolation, use a mount with `metadata`, then verify that the target UID is actually rejected.
- Copying between two mount views of the same volume with `cp -a` can recurse into itself. Compare `realpath` or inode first.
- In `wsl.exe ... bash -lc '...'`, do not let PowerShell expand `$var` first. Put complex logic in a `.sh` file and execute that file.
- Passing JSON or double-quoted commands through `wsl.exe` is fragile. Pass a file or use `--data-binary @file`.

## 9. Databases and migrations

- Just after a container starts, `mysqladmin ping` may hit a temporary instance. Use a real query to validate both service and authentication:
  ```powershell
  # Inject the password from a secret store into MYSQL_PWD; do not put it in shell history.
  docker exec -e MYSQL_PWD <container> mysql --no-defaults -uroot -e "SELECT 1"
  ```
- A `mysql:8.0` initialization can start two mysqld processes. A single probe may hit the temporary one before the socket disappears. Require **N consecutive** successful probes and reset the count on a drop.
- MySQL cold start may read a system `my.cnf` and introduce unexpected configuration. Add `--no-defaults` when you need a clean environment.
- Older MySQL on Ubuntu 24.04 may lack `libaio.so.1`. Confirm the package name before adding a compatibility symlink; do not bake a distribution patch into the application image.
- Keep schema migrations separate from seed data. Test scripts create their own data and never touch real data. After migration, assert that test accounts and test records are zero or match the expected count.
- Migrations must be repeatable. Run the containerized regression twice; only a successful second run proves idempotence.

## 10. Files, processes, and cleanup

- A controlled environment may block recursive deletes. Verify the absolute path and target first; clean only known generated artifacts, and never move unknown directories just to bypass policy. If safe cleanup is impossible, stop and report it. Never recursively delete a computed path without checking it.
- Before cleaning test artifacts, run `git ls-files <dir>` and confirm there are no controlled placeholder files or user data.
- When a file is locked, inspect the process first:
  ```powershell
  Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '<path>*' }
  Get-NetTCPConnection -LocalPort <port> -ErrorAction SilentlyContinue
  ```
- In a non-interactive environment, `.cmd` files using `timeout /t` report "Input redirection is not supported". Use `ping -n <seconds> 127.0.0.1 >nul` to delay instead.
- Start background helpers with `Start-Process -WindowStyle Hidden`; do not pop up a visible window that interferes with the user.

## 11. Network and JSON requests

- In PowerShell, `curl` may be an alias for `Invoke-WebRequest`. Use `curl.exe` when you need the real curl.
- For pure ASCII JSON:
  ```powershell
  $payload | curl.exe -sS -X POST -H 'Content-Type: application/json' --data-binary '@-' <url>
  ```
- For Chinese text or complex bodies, prefer `Invoke-RestMethod` and write the body to a UTF-8 file first. Do not depend on pipeline encoding.
- After a write fails, query the real state again. Do not report success based on a stale variable from the previous request.
- To test a port or connection:
  ```powershell
  Test-NetConnection -ComputerName 127.0.0.1 -Port <port>
  ```

## 12. Android and Java builds

- `ANDROID_HOME` and `ANDROID_SDK_ROOT` point to the local SDK; do not commit `local.properties`.
- On Windows use `.\gradlew.bat`, not `./gradlew`.
- Build every flavor in a multi-flavor project. One flavor does not represent all of them.
- Match the JDK version to Gradle and AGP. Read the project documentation before upgrading; do not force the newest version.

## 13. Quick checklist

- [ ] Am I in PowerShell or Git Bash?
- [ ] Which path does `python`, `mvn`, `docker`, or `git` resolve to?
- [ ] Are text files UTF-8 without BOM?
- [ ] Did I save the native exit code before the pipeline?
- [ ] Did `git rev-parse` on the baseline succeed?
- [ ] Is the Docker daemon ready, or do I only need `compose config`?
- [ ] Should the WSL service use `127.0.0.1` or `127.0.0.2`, and did I verify it?
- [ ] Did I run the migration twice?
- [ ] Did I verify the absolute path and run `git ls-files` before cleanup?
- [ ] Are logs and reports redacted?
