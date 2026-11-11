# Linux Server Pitfalls and Troubleshooting

[中文](linux-server-pitfalls.md) | [English](linux-server-pitfalls.en.md)

For common distributions such as Ubuntu / Debian, RHEL / CentOS / Rocky / AlmaLinux, and SUSE. Commands differ by distribution, version, systemd, and cgroup generation. Confirm the system facts before acting.

> Principle: observe read-only first, then make the smallest change. Do not "rule out" a problem by disabling SELinux, opening 777, turning off the firewall, upgrading the whole system, or rebooting production. Those actions widen the blast radius.

## 1. Confirm system facts

```bash
cat /etc/os-release
uname -a
systemctl --version
ps -p 1 -o comm=
getconf LONG_BIT
systemd-detect-virt
```

- Determine whether this is a physical host, VM, container, or WSL. Containers often lack a full systemd; many "service will not start" cases are entrypoint or PID 1 problems.
- Check cgroups: `stat -fc %T /sys/fs/cgroup`. cgroup v2 usually shows `cgroup2fs`, and resource limits and OOM observation differ.
- Check whether the distribution is EOL. Repositories, TLS certificates, and patch status may already be unusable.

## 2. systemd services

### Common traps

- `ExecStart` uses a relative path or depends on the current shell `PATH`.
- `EnvironmentFile` is set but missing, unreadable, or contains quoting and comments systemd cannot parse.
- `WorkingDirectory` is missing, so the app looks for config and uploads under `/`.
- The service runs as `root`, or the service account cannot access its directories.
- `Type=simple`, `forking`, and `notify` are mixed up, so systemd misjudges startup.
- `Restart` is not configured; a crashed process stays failed.
- `After` / `Requires` are treated as a universal fix for ordering, without a real health check.
- `ProtectSystem`, `PrivateTmp`, and `ReadWritePaths` are enabled but the app cannot write temp files or uploads.

### Read-only checks

```bash
systemctl cat <service>
systemctl show <service> -p User -p Group -p WorkingDirectory -p Environment -p EnvironmentFiles -p ExecStart -p Restart -p LimitNOFILE
systemd-analyze verify /etc/systemd/system/<service>.service
journalctl -u <service> -n 100 --no-pager
systemctl status <service> --no-pager
```

### Minimal repair order

1. Read `systemctl cat` and `journalctl -u` to separate configuration, permission, port, and dependency failures.
2. Prefer a drop-in at `/etc/systemd/system/<service>.service.d/override.conf`; do not edit package-managed files.
3. Run `systemctl daemon-reload`, then `systemctl restart <service>`.
4. Confirm the effective values with `systemctl show`, not only the file on disk.
5. Kill the process once to verify that `Restart` actually recovers the service.

## 3. Permissions, SELinux, and AppArmor

```bash
namei -l /path/to/file
stat -c '%U:%G %a %n' /path/to/file
id <service-user>
sudo -u <service-user> test -r /path/to/file && echo readable
getenforce 2>/dev/null || true
aa-status 2>/dev/null || true
ausearch -m avc -ts recent 2>/dev/null | tail -50
```

- Do not "fix" permissions with `chmod -R 777`. Check the service account, ownership, umask, ACLs, and execute bits on parent directories.
- `Permission denied` is not always Unix permissions. SELinux and AppArmor can deny access too. Read the audit log and allow the minimum policy.
- To bind 80/443, prefer a reverse proxy or `CAP_NET_BIND_SERVICE`; do not run the app as root permanently.
- Separate upload, temp, and log directories. Upload directories should not be executable and should stay outside the web root.
- If systemd hardening blocks writes, inspect `ReadWritePaths` and `PrivateTmp` instead of disabling all protections.

## 4. Disk, inodes, and logs

```bash
df -hT
df -i
du -xhd1 /var /tmp /home 2>/dev/null | sort -h
sudo lsof +L1 | head -50
journalctl --disk-usage
systemctl status logrotate.timer 2>/dev/null || true
logrotate -d /etc/logrotate.conf
```

- If `df -h` shows free space but writes fail, check inode exhaustion.
- If `df` and `du` disagree, look for deleted files still held open by a process; use `lsof +L1`.
- In containers, also check `/var/lib/docker`, overlay2, and the container log driver.
- Configure log rotation with size, retention, compression, and awareness of `copytruncate` side effects. Do not keep a rotated file open forever.
- Set `SystemMaxUse`, `SystemKeepFree`, and retention for journald. `journalctl --vacuum-size` is an emergency action, not a long-term policy.

## 5. Resources, processes, and OOM

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

- "Too many open files" is about the service process's `LimitNOFILE`, not only the login shell's `ulimit`.
- Container and systemd memory limits differ. OOM can happen at the cgroup layer while host `free` looks fine.
- For zombies, fix the parent's reaping. Killing the zombie itself does nothing.
- Do not blindly raise `somaxconn`, `tcp_tw_reuse`, and other sysctls. Check connection counts, port exhaustion, conntrack, and the real bottleneck first.
- Calculate threads, connection pools, queue consumers, and database connections together; one metric alone is misleading.

## 6. Network, firewall, and DNS

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

- Local `127.0.0.1` connectivity does not prove external access. Check listen addresses, firewalld/nftables/iptables, cloud security groups, and upstream load balancers.
- `ss -ltnp` shows listeners; `ss -tnp` shows established connections. Do not confuse them.
- Ephemeral port exhaustion, TIME_WAIT pressure, and a full conntrack table all look like random connection failures. Check `ss -s`, `nf_conntrack_count`, and `nf_conntrack_max`.
- For DNS, verify the system resolver path with `getent hosts`, then inspect `resolvectl` or `/etc/resolv.conf`; `dig` alone is not enough.
- Before changing a firewall, preserve the current rules and an out-of-band access path. A remote mistake can lock you out.

## 7. Time, timezone, and locale

```bash
timedatectl
chronyc tracking 2>/dev/null || true
systemctl status systemd-timesyncd 2>/dev/null || true
locale
localectl status
```

- Clock skew breaks TLS, Kerberos, JWT, log ordering, and database timestamps.
- Use a consistent policy: store UTC, render in the business timezone. Do not let the app, database, and reports each use a different zone.
- For mojibake, inspect `LANG`, `LC_ALL`, application startup flags, and database character sets. Changing only the terminal display is not a fix.

## 8. Package management, kernel, and reboots

```bash
uname -r
apt list --installed 2>/dev/null | head
dnf history 2>/dev/null | head
needs-restarting -r 2>/dev/null || true
needrestart -b 2>/dev/null || true
```

- If a package manager lock is held, confirm whether an upgrade is running. Do not delete the lock file blindly.
- Upgrading one critical library can break ABI compatibility. Record versions before and after, and keep a rollback path.
- Kernel, glibc, OpenSSL, and systemd upgrades usually need a reboot. Schedule a window and verify services recover automatically.
- Do not leave production unpatched. Treat EOL distributions as an explicit risk instead of assuming security updates continue.

## 9. SSH and host security

```bash
sshd -T | grep -E 'permitrootlogin|passwordauthentication|pubkeyauthentication|maxauthtries'
stat -c '%a %U:%G %n' ~/.ssh ~/.ssh/authorized_keys
ss -ltnp
last -n 20
lastb -n 20 2>/dev/null || true
```

- Disable root password login and password authentication. Key permissions should be at least `600`, and `.ssh` should be `700`.
- Restrict management ports. Do not expose databases, Redis, the Docker API, or monitoring dashboards directly to the internet.
- If you find a suspicious process, cron entry, SSH key, or systemd unit, preserve evidence before cleanup. Do not delete logs while investigating.

## 10. Databases and backups

```bash
pg_isready -h <host> -p <port> 2>/dev/null || true
mysqladmin ping -h <host> 2>/dev/null || true
```

- A successful liveness probe does not prove the application is usable. Run a real read-only query to verify authentication, database, tables, and privileges.
- Back up the database, uploads, configuration, and secrets. Record the restore order and dependencies.
- Restore backups regularly. Verify ownership, permissions, character set, timezone, and application connectivity.
- Back up before migrations. Make migrations repeatable and run them against both an empty database and existing data.

## 11. Containers and orchestration

```bash
docker info
docker inspect <container>
docker logs --tail 100 <container>
docker compose config
```

- Do not use `--privileged`, mount `/var/run/docker.sock`, or mount the host root to "fix" permissions.
- Configure the container log driver and retention, or `/var/lib/docker` will fill with logs.
- Inside a container, `127.0.0.1` is the container itself. Use the host address or the correct network mode to reach host services.
- For Kubernetes, check probes, resources, PDB, securityContext, Secret mounts, and persistent-volume backups.

## 12. Release and rollback

- Keep the previous artifact and configuration. Use versioned or timestamped release directories instead of overwriting the only copy.
- Understand `reload` versus `restart`. For graceful shutdown, configure `KillSignal`, `TimeoutStopSec`, and connection draining.
- Migrate in the order "compatible first, migrate next, clean up last". Test code rollback and database rollback separately.
- After release, verify process, port, health check, login, core business flow, and dependencies. `systemctl active` alone is not enough.
- On failure, preserve `journalctl`, `dmesg`, `ss`, `ps`, disk, and configuration snapshots before rebooting.

## 13. Quick checklist

- [ ] Distribution, kernel, systemd, cgroup, and virtualization type confirmed
- [ ] Effective values from `systemctl cat` and `systemctl show` verified
- [ ] Service account, directory ownership, umask, SELinux/AppArmor verified
- [ ] Disk, inodes, logs, and journald retention have headroom
- [ ] `LimitNOFILE`, memory limits, OOM behavior, and thread counts checked
- [ ] Listen addresses, firewall, cloud security groups, and external reachability tested
- [ ] DNS, certificates, NTP, timezone, and locale verified
- [ ] Package versions, kernel reboot, and EOL risk recorded
- [ ] SSH, management ports, databases, and container APIs are not unnecessarily public
- [ ] Database probes use real queries; migrations and backups are repeatable
- [ ] Containers are not root/privileged; logs and persistent volumes have retention
- [ ] Previous version, rollback script, and restore order have been exercised
