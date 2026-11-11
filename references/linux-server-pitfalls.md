# Linux 服务器避坑与排查手册

[中文](linux-server-pitfalls.md) | [English](linux-server-pitfalls.en.md)

适用于 Ubuntu / Debian、RHEL / CentOS / Rocky / AlmaLinux、SUSE 等常见发行版。命令会因发行版、版本、systemd 和 cgroup 版本不同而略有差异；先确认系统事实，再执行命令。

> 原则：先只读观察，再最小改动。不要用关闭 SELinux、放开 777、关闭防火墙、升级全系统或重启生产机来“排除问题”；这些操作会扩大故障面。

## 1. 先确认系统事实

```bash
cat /etc/os-release
uname -a
systemctl --version
ps -p 1 -o comm=
getconf LONG_BIT
systemd-detect-virt
```

- 确认是物理机、虚拟机、容器还是 WSL；容器里通常没有完整 systemd，很多“服务起不来”是入口命令或 PID 1 的问题。
- 确认 cgroup 版本：`stat -fc %T /sys/fs/cgroup`。cgroup v2 通常是 `cgroup2fs`，资源限制和 OOM 观察方式不同。
- 确认发行版是否 EOL；EOL 系统的软件源、TLS 证书和补丁状态都可能已经不可用。

## 2. systemd 服务

### 高频坑

- `ExecStart` 使用相对路径，或依赖当前 shell 的 `PATH`。
- 只写了 `EnvironmentFile`，但文件不存在、权限不可读，或 systemd 解析不了引号和注释。
- `WorkingDirectory` 缺失，应用按 `/` 找配置和上传目录。
- 用 `root` 跑服务，或服务账号没有目标目录权限。
- `Type=simple`、`forking`、`notify` 用错，systemd 误判启动完成。
- `Restart` 没配，进程崩溃后服务停在 failed。
- `After` / `Requires` 写成“启动顺序”的万能药，但没有真正的健康检查。
- `ProtectSystem`、`PrivateTmp`、`ReadWritePaths` 开启后，应用写不了临时文件或上传目录。

### 只读检查

```bash
systemctl cat <service>
systemctl show <service> -p User -p Group -p WorkingDirectory -p Environment -p EnvironmentFiles -p ExecStart -p Restart -p LimitNOFILE
systemd-analyze verify /etc/systemd/system/<service>.service
journalctl -u <service> -n 100 --no-pager
systemctl status <service> --no-pager
```

### 最小修复顺序

1. 先看 `systemctl cat` 和 `journalctl -u`，确认是配置、权限、端口还是依赖问题。
2. 修改用 drop-in：`/etc/systemd/system/<service>.service.d/override.conf`，不要直接改包管理器生成的文件。
3. 执行 `systemctl daemon-reload`，再 `systemctl restart <service>`。
4. 用 `systemctl show` 确认最终生效值，不要只看配置文件。
5. 杀进程测试 `Restart`，确认能自动恢复。

## 3. 权限、SELinux 与 AppArmor

```bash
namei -l /path/to/file
stat -c '%U:%G %a %n' /path/to/file
id <service-user>
sudo -u <service-user> test -r /path/to/file && echo readable
getenforce 2>/dev/null || true
aa-status 2>/dev/null || true
ausearch -m avc -ts recent 2>/dev/null | tail -50
```

- 不要用 `chmod -R 777` 解决权限。先确认服务账号、目录属主、umask、ACL 和父目录执行位。
- `Permission denied` 不一定是 Unix 权限；SELinux/AppArmor 也会拒绝。先看审计日志，再按最小策略放行。
- 需要绑定 80/443 时优先用反向代理或 `CAP_NET_BIND_SERVICE`，不要长期用 root 跑应用。
- 上传目录、临时目录、日志目录分开；上传目录不要可执行，尽量不在 Web 根目录下。
- systemd 加固后如果写不了文件，先看 `ReadWritePaths` 和 `PrivateTmp`，不要直接关掉全部保护。

## 4. 磁盘、inode 与日志

```bash
df -hT
df -i
du -xhd1 /var /tmp /home 2>/dev/null | sort -h
sudo lsof +L1 | head -50
journalctl --disk-usage
systemctl status logrotate.timer 2>/dev/null || true
logrotate -d /etc/logrotate.conf
```

- `df -h` 有空间但写不进去，检查 inode 是否耗尽。
- `df` 和 `du` 对不上，常见原因是已删除但仍被进程打开的文件；用 `lsof +L1` 找。
- 容器环境还要看 `/var/lib/docker`、overlay2 和容器日志驱动。
- 日志轮转要同时配置大小、保留份数、压缩和 `copytruncate` 的副作用；不要让应用一直持有被轮转的文件。
- `journald` 要设置 `SystemMaxUse`、`SystemKeepFree` 和保留时间；`journalctl --vacuum-size` 只能作为应急，不是长期方案。

## 5. 资源、进程与 OOM

```bash
ulimit -n
cat /proc/<pid>/limits
systemctl show <service> -p LimitNOFILE -p MemoryMax -p TasksMax
free -m
vmstat 1 5
ss -s
ps -eo stat,ppid,pid,cmd | awk '$1 ~ /Z/'
dmesg -T | grep -i -E 'oom|killed process' | tail -20
systemd-cgtop 2>/dev/null || true
```

- 高并发下“Too many open files”先看服务进程的 `LimitNOFILE`，不是只看登录 shell 的 `ulimit`。
- 容器和 systemd 服务的内存限制不同；OOM 可能发生在 cgroup 层，宿主 `free` 看起来很空。
- 僵尸进程要看父进程是否回收；杀僵尸本身没用，要修父进程。
- 不要盲目调大 `somaxconn`、`tcp_tw_reuse` 等 sysctl；先看连接数、端口耗尽、conntrack 和实际瓶颈。
- 线程数、连接池、队列消费者和数据库连接数要一起算，单看一个指标会误判。

## 6. 网络、防火墙与 DNS

```bash
ip addr
ip route
ss -ltnp
ss -tnp state established
firewall-cmd --state 2>/dev/null || true
firewall-cmd --list-all 2>/dev/null || true
nft list ruleset 2>/dev/null | head -100
iptables -S 2>/dev/null | head -100
resolvectl status 2>/dev/null || cat /etc/resolv.conf
getent hosts <host>
curl -v --max-time 10 https://<host>/
```

- 本机 `127.0.0.1` 能通不代表外部能通；同时检查监听地址、firewalld/nftables/iptables、云安全组和上游负载均衡。
- `ss -ltnp` 看的是监听；`ss -tnp` 看的是已建立连接。不要把两者混为一谈。
- 端口范围耗尽、TIME_WAIT 过多、conntrack 表满都会表现为随机连接失败；先看 `ss -s`、`nf_conntrack_count` 和 `nf_conntrack_max`。
- DNS 问题先用 `getent hosts` 验证系统解析路径，再看 `resolvectl` 或 `/etc/resolv.conf`；不要只测 `dig`。
- 改防火墙前先保留当前规则和带外访问方式；远程改错会导致自己再也连不上。

## 7. 时间、时区与 locale

```bash
timedatectl
chronyc tracking 2>/dev/null || true
systemctl status systemd-timesyncd 2>/dev/null || true
locale
localectl status
```

- 服务器时间漂移会导致 TLS、Kerberos、JWT、日志排序和数据库时间字段异常。
- 统一“存储用 UTC、展示按业务时区”的策略；不要让应用、数据库和报表各用一套。
- 中文乱码先看 `LANG`、`LC_ALL`、应用启动参数和数据库字符集；不要只改终端显示。

## 8. 包管理、内核与重启

```bash
uname -r
apt list --installed 2>/dev/null | head
dnf history 2>/dev/null | head
needs-restarting -r 2>/dev/null || true
needrestart -b 2>/dev/null || true
```

- 包管理器锁被占用时，先确认是否有正在运行的升级，不要直接删锁文件。
- 只升级一个关键库可能导致 ABI 不匹配；记录升级前后的版本和回滚方式。
- 内核、glibc、OpenSSL 和 systemd 升级后通常需要重启；安排维护窗口并验证重启后服务能自动恢复。
- 不要让生产机长期无补丁；EOL 发行版要单列风险，不要假设还能持续获得安全更新。

## 9. SSH 与主机安全

```bash
sshd -T | grep -E 'permitrootlogin|passwordauthentication|pubkeyauthentication|maxauthtries'
stat -c '%a %U:%G %n' ~/.ssh ~/.ssh/authorized_keys
ss -ltnp
last -n 20
lastb -n 20 2>/dev/null || true
```

- 禁止 root 密码直登和密码登录；密钥权限至少 `600`，`.ssh` 目录 `700`。
- 管理端口限制来源；数据库、Redis、Docker API 和监控面板不要直接暴露公网。
- 发现异常进程、定时任务、SSH 密钥或 systemd 单元时，先保留证据再清理；不要边排查边删日志。

## 10. 数据库与备份

```bash
pg_isready -h <host> -p <port> 2>/dev/null || true
mysqladmin ping -h <host> 2>/dev/null || true
```

- 探活成功不等于业务可用；用真实只读查询验证认证、库、表和权限。
- 备份要覆盖数据库、上传文件、配置和密钥；记录恢复顺序和依赖。
- 备份必须做恢复演练，确认权限、属主、字符集、时区和应用连接都正确。
- 迁移前先备份；迁移脚本要可重复执行，空库和已有数据都要跑。

## 11. 容器与编排

```bash
docker info
docker inspect <container>
docker logs --tail 100 <container>
docker compose config
```

- 不要用 `--privileged`、挂载 `/var/run/docker.sock` 或宿主根目录来“解决”权限问题。
- 容器日志驱动和保留策略要配置，否则 `/var/lib/docker` 会被日志写满。
- 容器内 `127.0.0.1` 是容器自己；连接宿主服务要用宿主地址或正确的网络模式。
- Kubernetes 要检查 probes、resources、PDB、securityContext、Secret 挂载和持久卷备份。

## 12. 发布与回滚

- 保留上一版本制品和配置，发布目录用版本号或时间戳，不要原地覆盖唯一副本。
- 明确 `reload` 和 `restart` 的语义；需要优雅停机时设置 `KillSignal`、`TimeoutStopSec` 和连接 draining。
- 数据库迁移按“先兼容、再迁移、后清理”的顺序；代码回滚和数据库回滚要分别演练。
- 发布后验证进程、端口、健康检查、登录、核心业务和依赖，不要只看 `systemctl active`。
- 出故障先保留现场：`journalctl`、`dmesg`、`ss`、`ps`、磁盘和配置快照；不要重启后才开始找原因。

## 13. 快速检查清单

- [ ] 发行版、内核、systemd、cgroup 和虚拟化类型已确认
- [ ] `systemctl cat` 与 `systemctl show` 的最终生效值已核对
- [ ] 服务账号、目录属主、umask、SELinux/AppArmor 已验证
- [ ] 磁盘、inode、日志和 journald 保留策略有余量
- [ ] `LimitNOFILE`、内存限制、OOM 和线程数已核对
- [ ] 监听地址、防火墙、云安全组和外部连通性都测过
- [ ] DNS、证书、NTP、时区和 locale 已验证
- [ ] 包版本、内核重启和 EOL 风险已记录
- [ ] SSH、管理端口、数据库和容器 API 没有不必要的公网暴露
- [ ] 数据库探活使用真实查询，迁移和备份都可重复
- [ ] 容器不是 root/特权，日志和持久卷有保留策略
- [ ] 上一版本、回滚脚本和恢复顺序已实际演练
