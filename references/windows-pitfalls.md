# Windows 环境坑与绕法

[中文](windows-pitfalls.md) | [English](windows-pitfalls.en.md)

这份清单来自真实的项目检查现场，目标是让检查者在 Windows 上少撞墙。命令以 PowerShell 为主；需要 Git Bash / WSL 时会单独标注。

> 原则：先确认当前 shell、解释器和工具路径，再执行命令。不要在 PowerShell 里套 bash 语法，也不要在 Git Bash 里假设 Windows 工具都能直接调用。

## 1. 先确认 shell 和版本

```powershell
$PSVersionTable.PSVersion
Get-Command powershell.exe, pwsh.exe -ErrorAction SilentlyContinue
```

- **Windows PowerShell 5.1** 不支持 `&&`、`||` 和三元运算符；用 `;`、`if` 或分开执行。
- **PowerShell 7+** 支持 `&&`、`||`，但调用原生程序时的退出码规则仍然要看 `$LASTEXITCODE`。
- 不确定工具是否存在时，先 `where.exe <tool>` 或 `Get-Command <tool>`，不要直接跑。

## 2. 路径与引号

- 用 `$env:USERPROFILE`、`$env:LOCALAPPDATA`、`$PSScriptRoot` 解析路径，不要写死 `C:\Users\<you>`。
- 含空格的路径必须加引号：
  ```powershell
  & 'C:\Program Files\Some Tool\bin\tool.exe' --version
  ```
- 需要把路径传给原生程序时，优先用数组参数，避免手工拼字符串：
  ```powershell
  & $exe @('--input', $inputPath, '--output', $outputPath)
  ```
- 长路径可能触发 MAX_PATH；优先缩短目录层级，或在支持的场景使用 `\\?\` 前缀。
- 不要把项目复制到 OneDrive/同步目录里跑构建；文件锁和同步会制造随机失败。

## 3. 编码与 BOM

- 公开/提交的文本统一 **UTF-8 无 BOM**。
- Windows PowerShell 5.1 的 `Set-Content -Encoding UTF8` 和 `Out-File -Encoding utf8` 可能写 BOM；需要无 BOM 时用 .NET：
  ```powershell
  [System.IO.File]::WriteAllText($path, $text, [System.Text.UTF8Encoding]::new($false))
  ```
- 检查 BOM：
  ```powershell
  $b = [System.IO.File]::ReadAllBytes($path)
  $hasBom = $b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF
  ```
- 没有 `file` 命令时，用 `Format-Hex` 或 Python 读 bytes 判断编码。
- 中文补丁经 `apply_patch` 失败时，先检查是否是参数编码问题；可改用按字节替换并断言唯一匹配，不要盲目重发整份补丁。

## 4. 退出码、管道与假阴性

- 原生程序的退出码看 `$LASTEXITCODE`，不是 `$?`。
- 管道会把“命令本身失败”和“下游格式化成功”混在一起。先保存退出码，再过滤：
  ```powershell
  & $exe @args
  $code = $LASTEXITCODE
  # 再做 Select-String / Format-Table
  if ($code -ne 0) { throw "command failed: $code" }
  ```
- 不要用 `2>&1 | Out-Null` 或 `>/dev/null 2>&1` 吞掉被检查命令的退出状态；这会把“崩了”和“干净跑完”变成同一种结果。
- 需要同时看输出和退出码时：
  ```powershell
  $out = & $exe @args 2>&1
  $code = $LASTEXITCODE
  $out | Select-Object -Last 50
  if ($code -ne 0) { throw "command failed: $code" }
  ```
- `Start-Process -Wait -PassThru` 拿 `.ExitCode`，适合需要独立窗口或提权的程序。

## 5. Maven / Java

- Git Bash 下 `mvn` 可能找不到或行为异常；Windows 优先用 PowerShell 调 `mvn.cmd`。
- 项目有 wrapper 时优先 `.\mvnw.cmd`，避免全局 Maven 版本漂移。
- `mvn.cmd -q test` 可能不打印汇总；直接解析 Surefire XML：
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
- 用 awk 统计时注意属性名是 `tests=`（带等号）；写 `s["tests"]` 会全得 0。
- `-DskipTests` 仍会编译测试；`-Dmaven.test.skip=true` 连测试编译都跳过。两者语义不同，报告里要写清楚。
- `JAVA_HOME` 指向 JDK 根目录，不是 `bin`；路径含空格时不要手工拼未加引号的命令。

## 6. Python

- 先确认解释器：
  ```powershell
  where.exe python
  py -3 --version
  Get-Command python | Select-Object Source
  ```
- Windows Store 的 `python` 可能是别名；优先 `py -3` 或明确解释器路径。
- 依赖装进项目 venv，不要污染全局 site-packages：
  ```powershell
  py -3 -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  .\.venv\Scripts\python.exe -m pytest
  ```
- PyPI 直连失败时，先判断是网络/证书/镜像问题；换镜像要记录在环境说明里，不要把镜像配置写进仓库密钥文件。
- 读写文本显式 `encoding='utf-8'`；Windows 默认编码不一定是 UTF-8。
- 需要强制 UTF-8 时，可在当前进程设置 `PYTHONUTF8=1`，但不要假设所有子进程都继承。

## 7. Git

- 在 Windows 仓库里统一用 PowerShell 调 Git，避免 WSL Git 和 Windows Git 混用导致大量仅换行差异。
- 看到大量“只有换行”的 `M`，先复核：
  ```powershell
  git status --short
  git diff --ignore-cr-at-eol --stat
  ```
- `.gitattributes` 可以固定 `eol`；但历史 blob 与 index 规范化不一致时，仍可能显示 modified。只暂存目标文件，不要 `git add -A`。
- `git mv` 保留旧 blob：先改内容再 `git mv` 会得到 `RM`（重命名已暂存 + 修改未暂存），直接 commit 只提交移动。看 `git status --short` 的**第二列**：`M ` / `R ` 已暂存，` M` / `RM` 未暂存。
- 检查基准点必须先验证：
  ```powershell
  git rev-parse <fixed-point>
  git log <fixed-point>..HEAD --oneline
  git diff <fixed-point>...HEAD --stat
  ```
- 提交前跑 `git diff --check`，检查空白错误和冲突标记。

## 8. Docker Desktop 与 WSL2

- Docker 守护进程没起时，容器化回归会直接失败。先征得用户同意，再启动 Docker Desktop，轮询：
  ```powershell
  # 常见路径；按实际安装位置调整
  Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -WindowStyle Hidden
  $deadline = (Get-Date).AddMinutes(3)
  do {
      docker info *> $null
      if ($LASTEXITCODE -eq 0) { break }
      Start-Sleep -Seconds 3
  } while ((Get-Date) -lt $deadline)
  ```
- `docker compose config` 只做变量插值和语法检查，**不需要**守护进程；可以先用它排除配置错误。
- WSL2 里 `localhost` 可能优先解析到 IPv6 `::1`，而转发只走 IPv4；连 Windows 侧服务优先用 `127.0.0.1`。
- WSL2 会把 `127.0.0.1` 上的监听转发到 Windows；如果目标必须“仅 WSL 内可达”，用 `127.0.0.2` 并实测。
- 不要把 Unix socket 放在 `/mnt/*`（9p/drvfs 不支持 socket）；放 `/run` 或 Linux 原生文件系统。
- 在 `/mnt/*` 上 `chmod/chown` 不等于真正的 Unix 权限；需要权限隔离时用带 `metadata` 的挂载视图，并实测目标 UID 是否被拒绝。
- 同一卷的两个挂载视图之间 `cp -a` 可能递归复制自身；先比较 `realpath` / inode，确认不是同一目录。
- `wsl.exe ... bash -lc '...'` 里不要让 PowerShell 先展开 `$var`；复杂逻辑写成 `.sh` 文件再执行。
- 通过 `wsl.exe` 传含 JSON/双引号的命令容易被 Windows 参数解析吞掉；用文件传参或 `--data-binary @file`。

## 9. 数据库与迁移

- 容器刚启动时 `mysqladmin ping` 可能命中临时实例；用真实查询同时验证服务与认证：
  ```powershell
  # 密码从密钥存储注入 MYSQL_PWD，不要写进命令历史
  docker exec -e MYSQL_PWD <container> mysql --no-defaults -uroot -e "SELECT 1"
  ```
- `mysql:8.0` 初始化阶段可能起两个 mysqld；单次探活会命中临时实例，随后 socket 消失。要**连续 N 次**探活成功，中途掉线归零重数。
- MySQL 冷启动读系统 `my.cnf` 可能引入意外配置；需要干净环境时加 `--no-defaults`。
- Ubuntu 24.04 上旧版 MySQL 可能缺 `libaio.so.1`；确认包名后再做兼容软链，不要把发行版补丁写死进应用镜像。
- schema 迁移与 seed 数据分离；验收脚本自建测试数据，不碰真实数据。迁移后断言测试账号/测试门店行数为 0 或符合预期。
- 迁移脚本必须可重复执行；用容器化回归跑两次，第二次仍成功才算幂等。

## 10. 文件、进程与清理

- 受控环境可能拦截递归删除。先核对绝对路径和删除目标；只清理已知生成物，不要为了绕过策略移动未知目录。无法安全清理时停下报告，不要对计算出来的路径直接递归删除。
- 清理测试产物前先 `git ls-files <dir>`，确认没有受控占位文件或用户数据。
- 文件被占用时先查进程：
  ```powershell
  Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '<path>*' }
  Get-NetTCPConnection -LocalPort <port> -ErrorAction SilentlyContinue
  ```
- `.cmd` 在非交互环境里用 `timeout /t` 会报 “Input redirection is not supported”；用 `ping -n <seconds> 127.0.0.1 >nul` 延迟。
- 后台辅助进程用 `Start-Process -WindowStyle Hidden`，不要弹出可见窗口干扰用户。

## 11. 网络与 JSON 请求

- PowerShell 里的 `curl` 可能是 `Invoke-WebRequest` 的别名；要真正的 curl 时写 `curl.exe`。
- 纯 ASCII JSON 可以：
  ```powershell
  $payload | curl.exe -sS -X POST -H 'Content-Type: application/json' --data-binary '@-' <url>
  ```
- 含中文或复杂正文时优先 `Invoke-RestMethod`，并把 body 先写成 UTF-8 文件；不要依赖管道编码。
- 写操作失败后要重新查询真实状态，不要沿用上一次请求的变量误报成功。
- 判断端口/连通性：
  ```powershell
  Test-NetConnection -ComputerName 127.0.0.1 -Port <port>
  ```

## 12. Android / Java 构建

- `ANDROID_HOME` 和 `ANDROID_SDK_ROOT` 指向本机 SDK；不要把 `local.properties` 提交进仓库。
- Windows 用 `.\gradlew.bat`，不要用 `./gradlew`。
- 多 flavor 项目逐 flavor 编译；只跑一个 flavor 不能代表全部。
- JDK 版本与 Gradle/AGP 匹配；升级前先看项目文档，不要凭最新版本硬上。

## 13. 快速检查清单

- [ ] 当前 shell 是 PowerShell 还是 Git Bash？
- [ ] `python` / `mvn` / `docker` / `git` 解析到哪个路径？
- [ ] 文本文件是否 UTF-8 无 BOM？
- [ ] 原生命令退出码是否在管道前保存？
- [ ] 基准点 `git rev-parse` 是否成功？
- [ ] Docker 守护进程是否就绪，还是只需要 `compose config`？
- [ ] WSL 服务用 `127.0.0.1` 还是 `127.0.0.2`？是否实测？
- [ ] 迁移是否跑了两次？
- [ ] 清理路径是否核对过绝对路径和 `git ls-files`？
- [ ] 日志/报告是否已脱敏？
