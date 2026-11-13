# Cross-Platform Command Reference

[中文](platform-commands.md) | **English**

The same review task often needs different commands on different systems. This file provides copyable minimum equivalents so you do not put PowerShell syntax into bash/zsh, or Unix paths into Windows commands.

## 0. Identify the environment first

| Environment | Check first | Notes |
|---|---|---|
| Windows PowerShell 5.1 | `$PSVersionTable.PSVersion` | Does not support `&&`, `||`, or the ternary operator |
| PowerShell 7 | `$PSVersionTable.PSVersion` | Supports `&&`/`||`, but native exit codes still live in `$LASTEXITCODE` |
| macOS / Linux | `echo "$SHELL"`, `uname -s` | bash/zsh commands are usually the same; system tools may differ |
| WSL2 | `uname -a`, `echo "$WSL_DISTRO_NAME"` | This is Linux, not a Windows shell |
| Git Bash | `echo "$SHELL"` | Some Windows tools are callable, but do not assume all are |

Rule: identify the shell before running a command. Do not mix PowerShell and bash syntax in one command.

## 1. Common operations

| Operation | Windows PowerShell 5.1 / 7 | macOS / Linux (bash/zsh) | WSL2 |
|---|---|---|---|
| Current directory | `Get-Location` | `pwd` | `pwd` |
| List hidden files | `Get-ChildItem -Force` | `ls -la` | `ls -la` |
| Check whether a command exists | `Get-Command <cmd> -ErrorAction SilentlyContinue` or `where.exe <cmd>` | `command -v <cmd>` | `command -v <cmd>` |
| Read an environment variable | `$env:NAME` | `printenv NAME` or `${NAME}` | `printenv NAME` |
| Set a session variable | `$env:NAME='value'` | `export NAME=value` | `export NAME=value` |
| Set a variable for one command | PowerShell has no bash-style prefix; use a wrapper script or child-process environment | `NAME=value <command>` | `NAME=value <command>` |
| User home | `$env:USERPROFILE` | `$HOME` | `$HOME` |
| Temp directory | `$env:TEMP` | `${TMPDIR:-/tmp}` | `${TMPDIR:-/tmp}` |
| Join a path | `Join-Path $dir 'file.txt'` | `"$dir/file.txt"` | `"$dir/file.txt"` |
| Inspect file bytes/encoding | `Format-Hex -Path <file>` | `file <file>`, `xxd -l 32 <file>` | `file <file>`, `xxd -l 32 <file>` |
| Delete a file/directory | Verify the absolute path, then `Remove-Item -LiteralPath <path>` | Verify `realpath`, then `rm -- <path>` | Same as Linux, but avoid dangerous operations across `/mnt/*` |

In PowerShell, setting a session variable affects later commands. If you need isolation, start a separate process or wrap the work in a project script; do not assume it resets automatically.

## 2. Python, Node, and Java

### Python

| Operation | Windows | macOS / Linux / WSL2 |
|---|---|---|
| Show version | `py -3 --version` or `python --version` | `python3 --version` |
| Locate the interpreter | `where.exe python`, `Get-Command python` | `command -v python3` |
| Create a venv | `py -3 -m venv .venv` | `python3 -m venv .venv` |
| venv interpreter | `.\.venv\Scripts\python.exe` | `.venv/bin/python` |
| Install dependencies | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` | `.venv/bin/python -m pip install -r requirements.txt` |
| Run tests | `.\.venv\Scripts\python.exe -m pytest` | `.venv/bin/python -m pytest` |
| Run this package's verifier | `python scripts\verify_package.py` | `python3 scripts/verify_package.py` |

The Windows Store `python` may be an alias. Prefer `py -3`, or use `Get-Command python` to find the real path. Do not hard-code a user's install directory.

### Node / Java

| Operation | Windows | macOS / Linux / WSL2 |
|---|---|---|
| npm | `npm.cmd` (from a script or PowerShell) | `npm` |
| Maven wrapper | `.\mvnw.cmd` | `./mvnw` |
| Gradle wrapper | `.\gradlew.bat` | `./gradlew` |
| Run Java | `java -version` | `java -version` |
| Read `JAVA_HOME` | `$env:JAVA_HOME` | `printenv JAVA_HOME` |

On Windows, prefer the project's wrapper to avoid global Maven/Gradle version drift. `JAVA_HOME` points to the JDK root, not `bin`.

## 3. Docker, ports, and processes

### Docker

| Operation | Windows | macOS / Linux / WSL2 |
|---|---|---|
| Check the daemon | `docker info` | `docker info` |
| Start Docker Desktop | Start Docker Desktop, then poll `docker info` | On macOS open Docker Desktop; on Linux start the service for the distribution |
| Validate compose only | `docker compose config` | `docker compose config` |
| List containers | `docker ps -a` | `docker ps -a` |

`docker compose config` only parses configuration and does not need the daemon. Confirm Docker is ready before starting containers.

### Ports and processes

| Operation | Windows | macOS / Linux / WSL2 |
|---|---|---|
| Inspect a port | `Get-NetTCPConnection -LocalPort <port> -ErrorAction SilentlyContinue` | `ss -ltnp 'sport = :<port>'` or `lsof -nP -iTCP:<port> -sTCP:LISTEN` |
| List processes | `Get-Process` | `ps aux` |
| Find a process by name | `Get-Process -Name <name> -ErrorAction SilentlyContinue` | `pgrep -af <name>` |

If `ss` or `lsof` is unavailable, check whether the tool exists before installing it or choosing an alternative. Do not assume every Linux distribution ships the same tool.

## 4. Permissions and cleanup

| Operation | Windows | macOS / Linux / WSL2 |
|---|---|---|
| Inspect permissions | `Get-Acl <path>` or `icacls <path>` | `stat <path>` or `ls -l <path>` |
| Change permissions | `icacls <path> /grant ...` | `chmod`, `chown` |
| Resolve the real path | `(Resolve-Path -LiteralPath <path>).Path` | `realpath <path>` |
| Confirm before deletion | Check `Test-Path` and the absolute path first | Check `test -e` and the `realpath` first |

Delete only an explicit target. Never recursively delete a computed directory. On WSL `/mnt/*`, `chmod`/`chown` is not real Unix permission control; use a mount with `metadata` and verify when isolation matters.

## 5. Command chaining and exit codes

### PowerShell

```powershell
# Windows PowerShell 5.1: do not use && or ||
& $exe @args
$code = $LASTEXITCODE
if ($code -ne 0) { throw "command failed: $code" }
```

PowerShell 7 supports `&&`, but native failures still need a `$LASTEXITCODE` check. Do not use `$?` as the native process exit code.

### bash/zsh

```bash
set -o pipefail
command
code=$?
if [ "$code" -ne 0 ]; then
  echo "command failed: $code" >&2
  exit "$code"
fi
```

A pipeline mixes upstream failure with downstream success. To check the command itself, save the exit code first, or enable `pipefail` in bash. Do not swallow the status with `>/dev/null 2>&1`.

## 6. WSL2 specifics

- WSL2 is Linux, not Windows PowerShell; prefer Linux paths and `python3`.
- Convert paths between Windows and WSL with `wslpath -w /home/<you>/project` and `wslpath -u 'C:\Users\<you>\project'`.
- Inside WSL2, `localhost` may resolve to IPv6 `::1`; try `127.0.0.1` first for services on the Windows side.
- For a listener that must be reachable only inside WSL, bind `127.0.0.2` and verify it. Do not assume `127.0.0.1` stays inside WSL.
- Do not put Unix sockets on `/mnt/*`; use `/run` or a Linux-native filesystem.
- When passing complex JSON or quotes through `wsl.exe ... bash -lc '...'`, write a temporary `.sh` file and execute it instead of fighting Windows argument parsing.

## 7. Release-download verification

Put the zip, `SHA256SUMS`, `SHA256SUMS.sig`, and `allowed_signers` in the same directory. All three platforms use `ssh-keygen` for the fingerprint and, with OpenSSH 8.1+, for signature verification, but their hash tools differ:

`ssh-keygen -Y verify` requires OpenSSH 8.1 or newer; run `ssh -V` first. Below 8.1, SSHSIG signatures cannot be verified, and only the SHA256 hash and public-key fingerprint are available. See `SIGNING.en.md` for the fallback procedure.

| Operation | Windows PowerShell 5.1 / 7 | macOS | Linux |
|---|---|---|---|
| Check the public-key fingerprint | `ssh-keygen -lf release-signing-key.pub` | Same | Same |
| Check the archive hash | `Get-FileHash -LiteralPath .\project-health-<version>.zip -Algorithm SHA256` | `shasum -a 256 project-health-<version>.zip` | `sha256sum project-health-<version>.zip` |
| Verify the signature | `cmd /c "ssh-keygen.exe -Y verify -f allowed_signers -I project-health-release -n file -s SHA256SUMS.sig < SHA256SUMS"` | `ssh-keygen -Y verify -f allowed_signers -I project-health-release -n file -s SHA256SUMS.sig < SHA256SUMS` | Same as macOS |

Windows PowerShell 5.1 does not support `<` input redirection, so Windows uses `cmd /c` only to feed `SHA256SUMS` to `ssh-keygen`. Do not replace it with `Get-Content | ssh-keygen`; pipeline encoding can change the bytes being verified. See `SIGNING.en.md` for the complete instructions.

## 8. Minimum verification checklist

- [ ] Confirmed whether the shell is PowerShell 5.1, PowerShell 7, bash/zsh, or WSL2.
- [ ] Python, Node, Maven, and Gradle use the command for the current platform.
- [ ] Windows paths and environment variables were not copied into bash/zsh.
- [ ] Docker is started only when needed; config validation and real execution are separate.
- [ ] Native exit codes are saved before a pipeline.
- [ ] Delete/move/permission operations verify the absolute and real paths.
- [ ] The report states the actual shell, interpreter, and tool versions.

For Windows-specific traps and workarounds, see `windows-pitfalls.en.md`; for the full debugging method, see `verification-playbook.en.md`.
