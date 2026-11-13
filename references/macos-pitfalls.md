# macOS / Apple Silicon 专项避坑

[中文](macos-pitfalls.md) | [English](macos-pitfalls.en.md)

本文件是专业版在 macOS 上的常驻平台层。任务开始时先确认环境，再按本文件检查；它不替代目标项目证据，也不能把 macOS 经验套到 Windows 或 Linux。

## 0. 任务开始时的环境检查

先只读记录，不要直接运行构建或安装依赖：

```bash
sw_vers -productVersion
uname -s
uname -m
arch
sysctl -in sysctl.proc_translated
printf '%s\n' "$SHELL"
command -v brew && brew --prefix
xcode-select -p
```

- Apple Silicon 上只有 `uname -m` 和 `arch` 都为 `arm64`，且 `sysctl.proc_translated` 为 `0`，才算原生 arm64 会话。
- Apple Silicon 上出现 `x86_64` 或 `proc_translated=1`，说明当前进程可能在 Rosetta 下；不要用它验证原生 arm64 构建、wheel、Node 原生模块或容器镜像。
- Intel Mac 仍可做通用只读检查，但 arm64 专属构建、签名、性能和容器架构结论必须标为未覆盖；专业版不是 Apple Silicon-only 技能。
- 报告中写清 macOS 版本、shell、架构、Rosetta 状态和实际工具路径，不要只写“Mac 上通过”。

## 1. Rosetta 与架构混用（最容易造成假绿）

父进程在 Rosetta 下启动时，子进程通常继续继承 x86_64 环境。`python3`、`node`、`java`、Homebrew、Docker client 可能各自报告不同架构。

```bash
file "$(command -v python3)"
python3 -c 'import platform; print(platform.machine())'
node -p 'process.arch' 2>/dev/null || true
java -XshowSettings:properties -version 2>&1 | grep 'os.arch' || true
lipo -info <binary-or-dylib>
```

发现混用后，在原生 arm64 终端重建依赖，再跑正式回归；不要把 Rosetta 下的通过结果写成原生通过。需要强制 Apple Silicon 硬门禁时，改用 `project-health-macos`。

## 2. Homebrew 双前缀与 PATH 遮蔽

原生 Homebrew 通常使用 `/opt/homebrew`，Rosetta Homebrew 可能在 `/usr/local`。脚本不要写死前缀。

```bash
command -v brew
brew --prefix
brew config
brew doctor
printf '%s\n' "$PATH" | tr ':' '\n'
```

检查 `PATH` 是否同时包含两套前缀，以及 `brew`、`python3`、`node` 是否来自预期架构。CI 使用显式 setup action 或绝对路径，不依赖登录 shell 的初始化文件。

## 3. BSD 用户态工具不是 GNU

macOS 自带 `sed`、`stat`、`date`、`xargs` 等多为 BSD 版本，Linux 参数不一定可用：

```bash
sed -i '' 's/old/new/' file
stat -f '%z %N' file
date -r 0
ditto --help
```

只有安装了 coreutils 才有 `gsed`、`gstat`、`gtimeout` 等命令。审计时在干净 macOS 环境复测，不要把开发者机器上的 GNU 工具当成系统自带。

## 4. 系统 bash 仍是 3.2

```bash
/bin/bash --version
command -v bash
```

系统 `/bin/bash` 不支持 bash 4+ 的关联数组、`mapfile`、`wait -n`、`${var,,}` 等写法。脚本优先 `#!/bin/sh`；确实需要新 bash 时使用明确 shebang，并在 CI 固定版本。不要依赖交互式 `.zshrc`、alias 或用户安装的 bash。

## 5. APFS 大小写与 Unicode 规范化

默认 APFS 卷通常大小写不敏感，文件名还可能经历 Unicode 规范化；Git 的 `core.ignorecase` / `core.precomposeUnicode` 可能掩盖问题。

```bash
diskutil info / | grep -i 'File System Personality'
git config --show-origin --get core.ignorecase || true
git config --show-origin --get core.precomposeUnicode || true
find . -maxdepth 2 -print | LC_ALL=C sort
```

涉及大小写重命名、资源路径或跨平台同步时，在大小写敏感卷或 Linux 上复核；不要只看 `git status` 干净就判定路径兼容。

## 6. Gatekeeper、quarantine、codesign 与 notarization

下载的 `.app`、`.dmg`、二进制或脚本可能带 `com.apple.quarantine`，Gatekeeper 会拦截未验证产物。

```bash
xattr -p com.apple.quarantine <file>
codesign -dv --verbose=4 <app-or-binary>
codesign --verify --deep --strict --verbose=2 <app-or-binary>
spctl --assess --type execute --verbose=4 <app-or-binary>
xcrun stapler validate <app-or-dmg>
shasum -a 256 <file>
```

区分“未签名/未公证”和“恶意”是两件事；不要把 `spctl` 失败直接写成恶意软件。发布产物要验证签名和 notarization；不要建议关闭 Gatekeeper 或 SIP 来绕过。

## 7. TCC、SIP 与自动化权限

访问 Desktop、Documents、Downloads、照片、通讯录、日历、屏幕录制或自动化其他 App 时，macOS TCC 会弹出权限请求；CI、SSH 或无 GUI 会话可能直接失败。SIP 还会阻止修改系统目录和部分受保护文件。

- 先说明为什么需要权限，再请求最小权限；不要为了跑测试让用户授予 Full Disk Access。
- 不把“TCC 拒绝”误判成代码 bug；记录为环境限制和未覆盖项。
- 不通过关闭 SIP、降低 Gatekeeper 或 `sudo` 修改系统目录来绕过。
- GUI 自动化、AppleScript、`screencapture` 和辅助功能权限在 GitHub runner 上尤其不可靠，必须单列为未覆盖。

## 8. launchd 不是 systemd

不要把 Linux 的 `systemctl`、`service`、`journalctl` 直接搬到 macOS。macOS 服务使用 launchd，并区分 `gui/$UID` 和 `system` 域。

```bash
launchctl print gui/$(id -u)/<label>
launchctl print system/<label>
launchctl bootstrap gui/$(id -u) <plist>
launchctl bootout gui/$(id -u)/<label>
```

核对 plist 路径、日志路径、环境变量和可执行文件权限；不要把需要登录 GUI 会话的服务当成 CI 可测试项。

## 9. Docker Desktop、镜像架构与卷性能

Apple Silicon 默认拉 arm64 镜像；只有 amd64 的镜像会通过 QEMU 运行，速度慢且行为可能不同。

```bash
docker context ls
docker version --format 'client={{.Client.Arch}} server={{.Server.Arch}}'
docker image inspect <image> --format '{{.Architecture}}/{{.Os}}'
docker run --rm <image> uname -m
```

- 记录 client、server 和镜像三者架构，不要只看其中一项。
- 只有在镜像没有 arm64 版本时才使用 `--platform linux/amd64`，并说明仿真影响。
- 容器访问宿主机优先用 `host.docker.internal`，不要假设 `localhost` 就是宿主机。
- `node_modules`、数据库文件和大量小文件不要盲目放在 macOS bind mount；优先命名卷、项目内已忽略目录或 VM 原生存储，并先做 A/B 基线。
- Colima 与 Docker Desktop 的 context、网络和卷行为不完全等价，切换后重新验证。

## 10. 归档、扩展属性与符号链接

普通 zip 可能丢失扩展属性、资源叉、可执行位或符号链接。交付前用 `ditto` 保留元数据，并核对解压后的签名和权限。

```bash
ditto -c -k --sequesterRsrc --keepParent <dir> <archive.zip>
unzip -l <archive.zip>
find <dir> -maxdepth 2 -type l -ls
```

发布包至少要验证签名、quarantine、可执行位、符号链接和实际解压结果，不能只看压缩命令退出码。

## 11. GitHub macOS runner 不是固定机型

免费 `macos-latest` 可能分配到不同芯片、CPU 和内存规格；不要把 runner 写死为 M1、M2 Pro 或某个固定 macOS 版本。只把“arm64 且 Rosetta 为 0”当作硬条件，芯片、CPU、内存和系统版本每次从日志记录。

性能、GPU/Metal、Neural Engine、媒体编码和最新 SDK 的结论需要真实目标机补测；CI 通过不等于所有 Apple Silicon 世代都已验证。

## 12. 最小验证清单

- [ ] 已记录 macOS 版本、shell、`uname -m`、`arch` 和 Rosetta 状态。
- [ ] 依赖、解释器和二进制架构一致；没有把 Rosetta 结果当成原生结果。
- [ ] 没有写死 Homebrew 前缀，且已检查 PATH 遮蔽。
- [ ] macOS 系统工具与 GNU 工具差异已考虑。
- [ ] 大小写、Unicode、签名、TCC 和 launchd 限制已记录。
- [ ] Docker client、server 和镜像架构已分别确认。
- [ ] 报告写明了 macOS 覆盖范围和未覆盖项。
