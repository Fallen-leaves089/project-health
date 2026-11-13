# 跨平台命令对照

[中文](platform-commands.md) | [English](platform-commands.en.md)

同一条检查任务，在不同系统上往往要写不同命令。本文件给出可直接照抄的最小对照，避免把 PowerShell 语法套到 bash/zsh，或反过来把 Unix 路径套到 Windows。

## 0. 先确认自己在哪一层

| 环境 | 先确认 | 说明 |
|---|---|---|
| Windows PowerShell 5.1 | `$PSVersionTable.PSVersion` | 不支持 `&&`、`||`、三元运算符 |
| PowerShell 7 | `$PSVersionTable.PSVersion` | 支持 `&&`/`||`，但原生命令退出码仍看 `$LASTEXITCODE` |
| macOS / Linux | `echo "$SHELL"`、`uname -s` | bash/zsh 命令通常相同；系统工具可能有差异 |
| WSL2 | `uname -a`、`echo "$WSL_DISTRO_NAME"` | 这是 Linux 环境，不是 Windows shell |
| Git Bash | `echo "$SHELL"` | 可以调用部分 Windows 工具，但不要假设全部可用 |

原则：先确认 shell，再执行命令。不要在同一条命令里混用 PowerShell 和 bash 语法。

## 1. 常用操作对照

| 操作 | Windows PowerShell 5.1 / 7 | macOS / Linux（bash/zsh） | WSL2 |
|---|---|---|---|
| 当前目录 | `Get-Location` | `pwd` | `pwd` |
| 列出隐藏文件 | `Get-ChildItem -Force` | `ls -la` | `ls -la` |
| 判断命令是否存在 | `Get-Command <cmd> -ErrorAction SilentlyContinue` 或 `where.exe <cmd>` | `command -v <cmd>` | `command -v <cmd>` |
| 读取环境变量 | `$env:NAME` | `printenv NAME` 或 `${NAME}` | `printenv NAME` |
| 当前会话设置变量 | `$env:NAME='value'` | `export NAME=value` | `export NAME=value` |
| 只给一条命令设置变量 | PowerShell 没有 bash 式前缀；用包装脚本或子进程环境 | `NAME=value <command>` | `NAME=value <command>` |
| 用户主目录 | `$env:USERPROFILE` | `$HOME` | `$HOME` |
| 临时目录 | `$env:TEMP` | `${TMPDIR:-/tmp}` | `${TMPDIR:-/tmp}` |
| 拼接路径 | `Join-Path $dir 'file.txt'` | `"$dir/file.txt"` | `"$dir/file.txt"` |
| 查看文件头/编码 | `Format-Hex -Path <file>` | `file <file>`、`xxd -l 32 <file>` | `file <file>`、`xxd -l 32 <file>` |
| 删除文件/目录 | 先核对绝对路径，再 `Remove-Item -LiteralPath <path>` | 先核对 `realpath`，再 `rm -- <path>` | 同左，但不要跨 `/mnt/*` 做危险操作 |

PowerShell 当前会话设置变量会影响后续命令。需要隔离时，启动独立进程，或使用项目脚本封装，不要假设它会自动恢复。

## 2. Python、Node、Java

### Python

| 操作 | Windows | macOS / Linux / WSL2 |
|---|---|---|
| 查看版本 | `py -3 --version` 或 `python --version` | `python3 --version` |
| 找到解释器 | `where.exe python`、`Get-Command python` | `command -v python3` |
| 创建 venv | `py -3 -m venv .venv` | `python3 -m venv .venv` |
| venv 解释器 | `.\.venv\Scripts\python.exe` | `.venv/bin/python` |
| 安装依赖 | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` | `.venv/bin/python -m pip install -r requirements.txt` |
| 跑测试 | `.\.venv\Scripts\python.exe -m pytest` | `.venv/bin/python -m pytest` |
| 跑本包自检 | `python scripts\verify_package.py` | `python3 scripts/verify_package.py` |

Windows Store 的 `python` 可能是别名；优先 `py -3`，或使用 `Get-Command python` 确认真实路径。不要写死某个用户的安装目录。

### Node / Java

| 操作 | Windows | macOS / Linux / WSL2 |
|---|---|---|
| npm | `npm.cmd`（脚本或 PowerShell 中） | `npm` |
| Maven wrapper | `.\mvnw.cmd` | `./mvnw` |
| Gradle wrapper | `.\gradlew.bat` | `./gradlew` |
| 运行 Java | `java -version` | `java -version` |
| 查看 `JAVA_HOME` | `$env:JAVA_HOME` | `printenv JAVA_HOME` |

在 Windows 上优先使用项目自带的 wrapper，避免全局 Maven/Gradle 版本漂移。`JAVA_HOME` 指向 JDK 根目录，不是 `bin`。

## 3. Docker、端口与进程

### Docker

| 操作 | Windows | macOS / Linux / WSL2 |
|---|---|---|
| 检查守护进程 | `docker info` | `docker info` |
| 启动 Docker Desktop | 启动 Docker Desktop 后轮询 `docker info` | macOS 可打开 Docker Desktop；Linux 按发行版启动服务 |
| 只校验 compose | `docker compose config` | `docker compose config` |
| 查看容器 | `docker ps -a` | `docker ps -a` |

`docker compose config` 只做配置解析，不需要守护进程。需要真正启动容器时，再确认 Docker 已就绪。

### 端口与进程

| 操作 | Windows | macOS / Linux / WSL2 |
|---|---|---|
| 查端口 | `Get-NetTCPConnection -LocalPort <port> -ErrorAction SilentlyContinue` | `ss -ltnp 'sport = :<port>'` 或 `lsof -nP -iTCP:<port> -sTCP:LISTEN` |
| 查进程 | `Get-Process` | `ps aux` |
| 按名字查进程 | `Get-Process -Name <name> -ErrorAction SilentlyContinue` | `pgrep -af <name>` |

没有 `ss` 或 `lsof` 时，先确认工具是否存在，再决定安装或用替代命令；不要把某个发行版的工具当成所有 Linux 都有。

## 4. 权限与清理

| 操作 | Windows | macOS / Linux / WSL2 |
|---|---|---|
| 查看权限 | `Get-Acl <path>` 或 `icacls <path>` | `stat <path>` 或 `ls -l <path>` |
| 修改权限 | `icacls <path> /grant ...` | `chmod`、`chown` |
| 核对真实路径 | `(Resolve-Path -LiteralPath <path>).Path` | `realpath <path>` |
| 删除前确认 | 先 Test-Path、核对绝对路径 | 先 Test-Path/`test -e`、核对 `realpath` |

清理时只删除明确目标，不要对计算出来的目录直接递归删除。WSL 的 `/mnt/*` 上 `chmod/chown` 不等于真正的 Unix 权限，需要权限隔离时使用带 `metadata` 的挂载并实测。

## 5. 命令串联与退出码

### PowerShell

```powershell
# Windows PowerShell 5.1：不要用 && 或 ||
& $exe @args
$code = $LASTEXITCODE
if ($code -ne 0) { throw "command failed: $code" }
```

PowerShell 7 可以使用 `&&`，但原生命令失败后仍要检查 `$LASTEXITCODE`。不要把 `$?` 当成原生命令退出码。

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

管道会把上游失败和下游成功混在一起。需要判断命令本身是否失败时，先保存退出码，或在 bash 中启用 `pipefail`；不要用 `>/dev/null 2>&1` 吞掉状态。

## 6. WSL2 专项

- WSL2 是 Linux，不是 Windows PowerShell；优先使用 Linux 路径和 `python3`。
- Windows 与 WSL 之间转换路径：`wslpath -w /home/<you>/project`、`wslpath -u 'C:\Users\<you>\project'`。
- WSL2 中 `localhost` 可能解析到 IPv6 `::1`；连接 Windows 侧服务优先试 `127.0.0.1`。
- 需要“仅 WSL 内可达”的监听时，绑定 `127.0.0.2` 并实测；不要假设 `127.0.0.1` 不会转发到 Windows。
- Unix socket 不要放在 `/mnt/*`；使用 `/run` 或 Linux 原生文件系统。
- 通过 `wsl.exe ... bash -lc '...'` 传复杂 JSON/引号时，优先写临时 `.sh` 文件再执行，避免 Windows 参数解析吞字符。

## 7. 发布包下载校验

把 zip、`SHA256SUMS`、`SHA256SUMS.sig` 和 `allowed_signers` 下载到同一目录。三个平台都可以用 `ssh-keygen` 核对公钥指纹，并在 OpenSSH 8.1+ 下验证签名，但哈希工具不同：

`ssh-keygen -Y verify` 需要 OpenSSH 8.1 或更高版本；先运行 `ssh -V`。低于 8.1 时无法验证 SSHSIG 签名，只能核对 SHA256 和公钥指纹，处理方式见 `SIGNING.md`。

| 操作 | Windows PowerShell 5.1 / 7 | macOS | Linux |
|---|---|---|---|
| 核对公钥指纹 | `ssh-keygen -lf release-signing-key.pub` | 同左 | 同左 |
| 校验文件哈希 | `Get-FileHash -LiteralPath .\project-health-<version>.zip -Algorithm SHA256` | `shasum -a 256 project-health-<version>.zip` | `sha256sum project-health-<version>.zip` |
| 验证签名 | `cmd /c "ssh-keygen.exe -Y verify -f allowed_signers -I project-health-release -n file -s SHA256SUMS.sig < SHA256SUMS"` | `ssh-keygen -Y verify -f allowed_signers -I project-health-release -n file -s SHA256SUMS.sig < SHA256SUMS` | 同左 |

PowerShell 5.1 不支持 `<` 输入重定向，所以 Windows 用 `cmd /c` 只负责把 `SHA256SUMS` 送给 `ssh-keygen`；不要改成 `Get-Content | ssh-keygen`，管道编码可能改变被验证的字节。完整说明见 `SIGNING.md`。

## 8. 最小验证清单

- [ ] 已确认当前是 PowerShell 5.1、PowerShell 7、bash/zsh 还是 WSL2。
- [ ] Python、Node、Maven、Gradle 使用的是当前平台对应的命令。
- [ ] Windows 路径和环境变量没有直接套到 bash/zsh。
- [ ] Docker 只在需要时启动；配置校验和真实运行分开。
- [ ] 原生命令退出码在管道前保存。
- [ ] 删除/移动/权限操作前核对绝对路径和真实路径。
- [ ] 报告里写明了实际使用的 shell、解释器和工具版本。

Windows 专项坑和绕法见 `windows-pitfalls.md`；完整调试方法见 `verification-playbook.md`。
