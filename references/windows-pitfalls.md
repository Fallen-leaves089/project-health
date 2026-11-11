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

## 13. Windows Server 部署与运维

这一节面向 Windows Server，不适用于普通 Windows 10/11 客户端排障。先确认角色、版本和是否有桌面体验，再执行命令。

### 13.1 先确认系统与角色

```powershell
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber, OsArchitecture
Get-WindowsFeature | Where-Object Installed | Select-Object Name, DisplayName
Get-Service | Where-Object Status -eq 'Running' | Select-Object Name, DisplayName
```

- Server Core 没有完整图形界面，不要假设能打开 IIS 管理器或浏览器；优先用 PowerShell、`sconfig` 和远程管理。
- 记录是物理机、虚拟机还是云主机；云主机的安全组和 Windows 防火墙是两层，必须同时检查。
- 确认是否加入域、是否有组策略、是否有杀毒/EDR、是否启用 WinRM 和 RDP。

### 13.2 IIS 与应用池

```powershell
Get-Website | Select-Object Name, State, PhysicalPath, Bindings
Get-WebAppPoolState -Name <pool>
Get-WebConfigurationProperty -PSPath 'IIS:\' -Filter 'system.applicationHost/applicationPools' -Name '.'
netsh http show sslcert
netsh http show urlacl
```

- 应用池身份默认可能是 `ApplicationPoolIdentity`；实际文件权限要授予 `IIS AppPool\<pool>`，不要图省事给 `Everyone` 或 `Users` 全开。
- 检查应用池的 .NET CLR 版本、托管管道模式、32 位开关、启动模式、空闲超时和回收设置。
- 站点物理路径、默认文档、身份验证、处理程序映射和 URL Rewrite 规则要逐项核对。
- 托管 ASP.NET Core 时检查 ANCM 模块、运行时版本和 `web.config` 的 `processPath`。
- 应用池回收会导致进程内会话、缓存和后台任务丢失；多实例时检查机器密钥、会话状态和分布式缓存。
- 访问失败先看 IIS 日志、HTTPERR 日志和失败请求跟踪：
  ```powershell
  Get-ChildItem "$env:SystemDrive\inetpub\logs\LogFiles" -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 10 FullName
  ```

### 13.3 Windows 服务

```powershell
sc.exe qc <service>
sc.exe qfailure <service>
Get-CimInstance Win32_Service -Filter "Name='<service>'" | Select-Object Name, State, StartMode, StartName, PathName
Get-WinEvent -LogName System -MaxEvents 100 | Where-Object ProviderName -match '<service>'
```

- 服务账号优先用 `NT AUTHORITY\NetworkService`、`LocalSystem` 之外的最小权限域账号或 gMSA；不要用个人域账号。
- 服务不能依赖交互式桌面、映射网络盘、用户环境变量或“登录时启动”的脚本。
- `PathName` 里含空格的路径要加引号；工作目录要用绝对路径，不要依赖 `C:\Windows\System32`。
- 配置失败恢复（第一次、第二次、后续失败）和依赖服务；`sc.exe qfailure` 验证。
- 服务启动失败先看 System 事件日志、应用日志和服务账号权限；不要直接把账号改成域管理员。
- 杀进程测试自动恢复；确认服务在无人登录、重启后都能启动。

### 13.4 NTFS、共享与 SMB

```powershell
icacls <path>
Get-Acl <path> | Format-List
Get-SmbShare
Get-SmbShareAccess -Name <share>
Get-SmbSession
```

- 共享权限和 NTFS 权限是两层，最终取交集；只改一层经常出现“看起来给了权限但仍拒绝”。
- 用目标服务账号做有效权限测试，不要用管理员账号代替。
- 检查继承、所有者、拒绝项和父目录执行位；不要用 `Everyone: FullControl` 解决。
- 停用 SMBv1，按需启用 SMB 签名和加密；限制管理共享访问。

### 13.5 防火墙、代理与网络

```powershell
Get-NetFirewallProfile | Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction
Get-NetFirewallRule -Enabled True | Where-Object Direction -eq 'Inbound' | Select-Object DisplayName, Profile, Action
Get-NetTCPConnection -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess
Test-NetConnection -ComputerName <host> -Port <port>
netsh winhttp show proxy
```

- Windows 防火墙有域、专用、公用三个配置文件；只改一个可能不生效。
- 云主机还要检查安全组/NACL；本机 `127.0.0.1` 能通不代表外部能通。
- 不要把 RDP 3389、SQL Server、Redis、Docker API 直接暴露公网；用 VPN、堡垒机、白名单和 NLA。
- 系统代理、WinHTTP 代理和应用自己的代理配置可能不同；构建能联网不等于服务能联网。

### 13.6 证书、TLS 与私钥

```powershell
Get-ChildItem Cert:\LocalMachine\My | Select-Object Subject, NotAfter, Thumbprint
netsh http show sslcert
```

- 证书要装在计算机存储，不是用户存储；IIS 应用池或服务账号要有私钥读权限。
- 检查证书链、到期时间、SAN/域名匹配、SNI 绑定和中间证书。
- 不要只看浏览器能打开；从服务器外部和另一台机器验证 TLS 握手、协议版本和加密套件。
- 更换证书后同步更新绑定、应用配置和监控到期时间。

### 13.7 AD、Kerberos 与组策略

```powershell
setspn -L <account>
klist
w32tm /query /status
nltest /dsgetdc:<domain>
gpresult /h gp-report.html
```

- 认证随机失败先查 DNS、时间偏差、SPN、委派和组策略，不要先怀疑密码。
- 应用不要用域管理员运行；需要访问网络资源时优先 gMSA 或受约束委派。
- 双跳场景要理解 CredSSP、Kerberos 委派和凭据传递边界；不要为了“能访问”就放开无约束委派。
- 组策略变更要记录影响范围、刷新时间和回滚方式。

### 13.8 SQL Server 与数据

```powershell
Get-Service MSSQL* | Select-Object Name, Status, StartType
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 1433,1434
sqlcmd -S <server> -E -Q "SELECT 1"
```

- 明确 Windows 身份验证还是 SQL 身份验证、默认实例还是命名实例、静态端口还是动态端口。
- 应用连接账号最小权限；不要让应用用 `sa`。
- 备份要覆盖系统库、用户库、作业、凭据和证书；在另一台实例恢复验证。
- 检查最大内存、tempdb、磁盘、备份链和恢复模式；不要把 Simple 和 Full 混着用还不做日志备份。

### 13.9 PowerShell、WinRM 与自动化

```powershell
Get-ExecutionPolicy -List
winrm enumerate winrm/config/listener
Test-WSMan <host>
```

- 不要为了跑脚本把整机执行策略改成 `Unrestricted`；优先签名脚本和按进程最小化。
- 密码、令牌和连接串不要放在命令行、脚本明文或命令历史里；用 SecretManagement 或托管身份。
- WinRM 要限制来源、使用 HTTPS 或受信网络，并开启必要日志。
- 远程批量操作先小范围验证，确认幂等、失败退出码和回滚；不要把“所有节点同时执行”当默认。

### 13.10 杀毒、EDR、补丁与重启

```powershell
Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10
Get-CimInstance Win32_QuickFixEngineering | Sort-Object InstalledOn -Descending | Select-Object -First 10
```

- 构建、解压、上传或数据库文件随机被锁时，先看杀毒/EDR 扫描日志和排除策略；不要直接关闭防护。
- 补丁安装不等于生效；检查是否需要重启，安排维护窗口并验证关键服务。
- 记录补丁级别、重启时间、回滚方式和受影响节点；集群不要同时重启所有节点。

### 13.11 任务计划程序与故障转移集群

```powershell
Get-ScheduledTask | Where-Object TaskName -match '<name>' | Select-Object TaskName, State, Principal
schtasks /query /tn "<task>" /v /fo LIST
Get-ClusterNode 2>$null
Get-ClusterQuorum 2>$null
```

- 任务计划要明确运行账号、是否“无论用户是否登录都运行”、网络连接、时区、并发策略和上次结果。
- 不要用交互式用户或映射盘；任务可能需要“最高权限”但并不等于应该用域管理员。
- 故障转移集群检查 quorum、见证、节点网络、共享存储和验证报告；补丁和重启要逐节点进行。

## 14. 快速检查清单

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
- [ ] IIS 应用池身份、位数、管道和物理路径是否验证？
- [ ] Windows 服务账号、路径、依赖和失败恢复是否验证？
- [ ] NTFS 与共享权限是否用目标账号实测？
- [ ] 防火墙三个配置文件和云安全组是否都检查？
- [ ] 证书存储、私钥权限、SNI 和到期时间是否验证？
- [ ] AD/Kerberos 的 DNS、时间、SPN 和委派是否检查？
- [ ] SQL Server 实例、端口、认证和恢复演练是否完成？
- [ ] 补丁、重启、EDR 排除和集群逐节点策略是否记录？
