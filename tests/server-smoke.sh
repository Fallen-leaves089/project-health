#!/usr/bin/env bash
# Read-only smoke checks for references/linux-server-pitfalls.md.
# This script does not install packages, edit firewall rules, restart services,
# or change system configuration. It is intended for GitHub Ubuntu runners,
# with a best-effort subset on WSL and other Linux environments.
set -u

PASS=0
SKIP=0
FAIL=0

run_check() {
    local name="$1"
    local command="$2"
    printf 'RUN  %s\n' "$name"
    if bash -o pipefail -c "$command"; then
        PASS=$((PASS + 1))
    else
        printf 'FAIL %s\n' "$name"
        FAIL=$((FAIL + 1))
    fi
}

skip_check() {
    printf 'SKIP %s: %s\n' "$1" "$2"
    SKIP=$((SKIP + 1))
}

optional_command() {
    local name="$1"
    local binary="$2"
    local command="$3"
    if command -v "$binary" >/dev/null 2>&1; then
        run_check "$name" "$command"
    else
        skip_check "$name" "$binary is not installed"
    fi
}

optional_root() {
    local name="$1"
    local binary="$2"
    local command="$3"
    if ! command -v "$binary" >/dev/null 2>&1; then
        skip_check "$name" "$binary is not installed"
    elif sudo -n true >/dev/null 2>&1; then
        run_check "$name" "sudo -n $command"
    else
        skip_check "$name" "read-only check needs non-interactive sudo"
    fi
}

probe_command() {
    local name="$1"
    local binary="$2"
    local command="$3"
    if ! command -v "$binary" >/dev/null 2>&1; then
        skip_check "$name" "$binary is not installed"
        return
    fi
    printf 'RUN  %s\n' "$name"
    bash -o pipefail -c "$command" || printf 'INFO %s returned a non-zero status; this is expected when the service is absent.\n' "$name"
    PASS=$((PASS + 1))
}

has_systemd=0
if [[ -d /run/systemd/system ]] && [[ "$(ps -p 1 -o comm= 2>/dev/null | tr -d '[:space:]')" == "systemd" ]]; then
    has_systemd=1
fi

if [[ "${REQUIRE_SYSTEMD:-0}" == "1" ]] && [[ "$has_systemd" -ne 1 ]]; then
    printf 'FAIL systemd is required for this validation run, but PID 1 is not systemd.\n'
    exit 1
fi

run_check "OS release" "cat /etc/os-release"
run_check "kernel" "uname -a"
run_check "systemctl version" "systemctl --version | head -n 1"
run_check "PID 1" "ps -p 1 -o comm="
run_check "word size" "getconf LONG_BIT"
optional_command "virtualization" systemd-detect-virt "systemd-detect-virt || true"
run_check "cgroup filesystem" "stat -fc %T /sys/fs/cgroup"

if [[ "$has_systemd" -eq 1 ]]; then
    run_check "systemctl cat" "systemctl cat systemd-journald 2>/dev/null | head -n 30"
    run_check "systemctl show" "systemctl show systemd-journald -p User -p Group -p WorkingDirectory -p Environment -p EnvironmentFiles -p ExecStart -p Restart -p LimitNOFILE"
    unit_file="$(mktemp /tmp/project-health-smoke.XXXXXX.service)"
    printf '%s\n' '[Unit]' 'Description=project-health smoke test' '[Service]' 'ExecStart=/bin/true' '[Install]' 'WantedBy=multi-user.target' >"$unit_file"
    run_check "systemd-analyze verify" "systemd-analyze verify '$unit_file'"
    rm -f -- "$unit_file"
    run_check "journalctl" "journalctl -u systemd-journald -n 5 --no-pager 2>/dev/null | head -n 20"
    run_check "systemctl status" "systemctl status systemd-journald --no-pager 2>/dev/null | head -n 20"
else
    skip_check "systemd service checks" "this environment does not run systemd as PID 1"
fi

run_check "namei" "namei -l /etc/os-release"
run_check "stat permissions" "stat -c '%U:%G %a %n' /etc/os-release"
run_check "service user" "id"
if command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
    run_check "target user read" "sudo -n -u nobody test -r /etc/os-release"
else
    skip_check "target user read" "non-interactive sudo is unavailable"
fi
optional_command "SELinux" getenforce "getenforce || true"
optional_command "AppArmor" aa-status "aa-status || true"
optional_command "SELinux audit" ausearch "ausearch -m avc -ts recent 2>/dev/null | tail -n 10 || true"

run_check "disk space" "df -hT | head -n 20"
run_check "inode space" "df -i | head -n 20"
run_check "large directories" "du -xhd1 /var /tmp /home 2>/dev/null | sort -h | tail -n 20 || true"
run_check "root mount" "findmnt -T / | head -n 10"
optional_root "deleted open files" lsof "lsof +L1 2>/dev/null | head -n 20 || true"
if [[ "$has_systemd" -eq 1 ]]; then
    run_check "journal disk usage" "journalctl --disk-usage"
    run_check "logrotate timer" "systemctl status logrotate.timer --no-pager 2>/dev/null | head -n 20 || true"
else
    skip_check "journal and logrotate timer" "systemd is not active"
fi
optional_command "logrotate debug" logrotate "logrotate -d /etc/logrotate.conf 2>&1 | head -n 40 || true"

run_check "shell ulimit" "ulimit -n"
run_check "PID 1 limits" "cat /proc/1/limits | head -n 30"
if [[ "$has_systemd" -eq 1 ]]; then
    run_check "service limits" "systemctl show systemd-journald -p LimitNOFILE -p MemoryMax -p TasksMax"
else
    skip_check "service limits" "systemd is not active"
fi
run_check "memory" "free -m"
run_check "vmstat" "vmstat 1 2"
run_check "socket summary" "ss -s"
run_check "zombie processes" "ps -eo stat,ppid,pid,cmd | awk '\$1 ~ /Z/' | head -n 20 || true"
run_check "sysctl network limits" "sysctl net.core.somaxconn net.ipv4.tcp_tw_reuse 2>/dev/null || true"
optional_root "kernel OOM messages" dmesg "dmesg -T 2>/dev/null | grep -i -E 'oom|killed process' | tail -n 20 || true"
if [[ "$has_systemd" -eq 1 ]]; then
    probe_command "cgroup top" systemd-cgtop "timeout 5 systemd-cgtop -n 1 2>/dev/null | head -n 20 || true"
else
    skip_check "cgroup top" "systemd is not active"
fi

run_check "IP addresses" "ip addr | head -n 40"
run_check "routes" "ip route"
run_check "listening sockets" "ss -ltnp 2>/dev/null | head -n 30"
run_check "established sockets" "ss -tnp state established 2>/dev/null | head -n 30"
optional_command "firewalld" firewall-cmd "firewall-cmd --state 2>/dev/null || true"
optional_root "nftables" nft "nft list ruleset 2>/dev/null | head -n 30 || true"
optional_root "iptables" iptables "iptables -S 2>/dev/null | head -n 30 || true"
if command -v resolvectl >/dev/null 2>&1; then
    run_check "resolver" "resolvectl status 2>/dev/null | head -n 40 || cat /etc/resolv.conf"
else
    run_check "resolver file" "cat /etc/resolv.conf"
fi
run_check "getent hosts" "getent hosts localhost"
probe_command "HTTPS reachability" curl "curl -fsS --max-time 10 -o /dev/null -w 'HTTP %{http_code}\n' https://github.com/"
for file in /proc/sys/net/netfilter/nf_conntrack_count /proc/sys/net/netfilter/nf_conntrack_max; do
    if [[ -r "$file" ]]; then
        run_check "conntrack values" "cat '$file'"
    else
        skip_check "conntrack values" "$file is not readable"
    fi
done

if [[ "$has_systemd" -eq 1 ]]; then
    run_check "timedatectl" "timedatectl"
else
    skip_check "timedatectl" "systemd is not active"
fi
optional_command "chrony" chronyc "chronyc tracking 2>/dev/null || true"
if [[ "$has_systemd" -eq 1 ]]; then
    run_check "timesyncd" "systemctl status systemd-timesyncd --no-pager 2>/dev/null | head -n 20 || true"
else
    skip_check "timesyncd" "systemd is not active"
fi
run_check "locale" "locale"
run_check "localectl" "localectl status 2>/dev/null || true"

run_check "kernel release" "uname -r"
run_check "installed packages" "apt list --installed 2>/dev/null | head -n 10 || true"
optional_command "dnf history" dnf "dnf history 2>/dev/null | head -n 10 || true"
optional_command "needs-restarting" needs-restarting "needs-restarting -r 2>/dev/null || true"
optional_command "needrestart" needrestart "needrestart -b 2>/dev/null || true"

if command -v sshd >/dev/null 2>&1 && [[ -f /etc/ssh/sshd_config ]]; then
    run_check "sshd effective config" "sshd -T 2>/dev/null | grep -E 'permitrootlogin|passwordauthentication|pubkeyauthentication|maxauthtries' || true"
else
    skip_check "sshd effective config" "sshd or /etc/ssh/sshd_config is unavailable"
fi
if [[ -d "$HOME/.ssh" ]]; then
    run_check "ssh directory permissions" "stat -c '%a %U:%G %n' '$HOME/.ssh'"
else
    skip_check "ssh directory permissions" "$HOME/.ssh does not exist"
fi
if [[ -f "$HOME/.ssh/authorized_keys" ]]; then
    run_check "authorized_keys permissions" "stat -c '%a %U:%G %n' '$HOME/.ssh/authorized_keys'"
else
    skip_check "authorized_keys permissions" "$HOME/.ssh/authorized_keys does not exist"
fi
optional_command "login history" last "last -n 5 || true"
optional_root "failed login history" lastb "lastb -n 5 2>/dev/null || true"

probe_command "PostgreSQL readiness" pg_isready "pg_isready -h 127.0.0.1 -p 5432 2>/dev/null || true"
probe_command "MySQL readiness" mysqladmin "mysqladmin ping -h 127.0.0.1 2>/dev/null || true"

probe_command "Docker info" docker "docker info 2>/dev/null | head -n 20"
if command -v docker >/dev/null 2>&1; then
    compose_dir="$(mktemp -d /tmp/project-health-compose.XXXXXX)"
    printf '%s\n' 'services:' '  smoke:' '    image: alpine:3.20' '    command: ["true"]' >"$compose_dir/compose.yaml"
    run_check "Docker compose config" "docker compose -f '$compose_dir/compose.yaml' config"
    rm -rf -- "$compose_dir"
else
    skip_check "Docker compose config" "docker is not installed"
fi

printf 'RESULT pass=%d skip=%d fail=%d systemd=%d\n' "$PASS" "$SKIP" "$FAIL" "$has_systemd"
if [[ "$FAIL" -ne 0 ]]; then
    exit 1
fi
