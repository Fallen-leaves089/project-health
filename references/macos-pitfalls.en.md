# macOS / Apple Silicon Pitfalls

[中文](macos-pitfalls.md) | [English](macos-pitfalls.en.md)

This file is the professional edition's resident macOS platform layer. Check the environment at task start, then apply these rules. It does not replace target-project evidence, and macOS experience must not be copied to Windows or Linux.

## 0. Check the environment at task start

Start with read-only probes; do not run builds or install dependencies yet:

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

- On Apple Silicon, a native arm64 session requires both `uname -m` and `arch` to return `arm64`, and `sysctl.proc_translated` to return `0`.
- On Apple Silicon, `x86_64` or `proc_translated=1` means the process may be running under Rosetta. Do not use it to validate native arm64 builds, wheels, Node native modules, or container images.
- Intel Macs can still receive a generic read-only review, but arm64-specific build, signing, performance, and container-architecture conclusions must be marked as not covered. The professional edition is not Apple Silicon-only.
- Report the macOS version, shell, architecture, Rosetta state, and actual tool paths. Do not reduce the evidence to "it passed on a Mac".

## Hidden-pitfall sync baseline

These eight IDs are shared by the professional `project-health` edition and the dedicated `project-health-macos` edition. Any addition, rewrite, or deletion must update both Chinese and English documents in both repositories. Contract tests check the IDs and key evidence; updating only one edition is incomplete.

| ID | Hidden pitfall | Minimum evidence |
|---|---|---|
| MAC-H01 | A Rosetta terminal, IDE, CI step, or parent process pushes the whole toolchain into x86_64 | `uname -m`, `arch`, `sysctl -in sysctl.proc_translated`, then `file` and `lipo -info` on interpreters and binaries |
| MAC-H02 | AirPlay Receiver occupies 5000/7000, `localhost` resolves to `::1`, or local-network/TCC permission fails without a prompt | `lsof -nP -iTCP:5000 -sTCP:LISTEN` and the same for 7000; `curl -4` / `curl -6`; record permission and session type |
| MAC-H03 | Only Command Line Tools are installed, the wrong Xcode is selected, or the license/SDK does not match | `xcode-select -p`, `xcodebuild -version`, `xcrun --show-sdk-path`, `xcodebuild -license check` |
| MAC-H04 | Python, Node, Java, or native modules mix arm64 and x86_64 | `file`, `lipo -info`, `platform.machine()`, `process.arch`, `java -XshowSettings` |
| MAC-H05 | A dylib has the wrong architecture, `DYLD_*` is ignored by SIP, or a modified library was not re-signed | `otool -L`, `codesign --verify --deep --strict`, `codesign -d --entitlements :-` |
| MAC-H06 | Quarantine, extended attributes, AppleDouble files, resource forks, or symlinks are lost in an archive | `xattr -p com.apple.quarantine`; package with `ditto`, then verify in a clean extraction directory |
| MAC-H07 | M1 thread counts, concurrency, connection pools, or performance baselines are copied to M5/M6 | `sysctl -n hw.ncpu`, `sysctl -n hw.memsize`, `vm_stat`, `system_profiler SPHardwareDataType` |
| MAC-H08 | One arm64 runner or one chip is presented as coverage for every M-series Mac or Intel | Record chip, CPU, memory, macOS, Xcode/SDK, and Rosetta state; list untested generations as uncovered |

## 1. Rosetta and architecture mixing (the easiest source of false green)

When a parent process starts under Rosetta, child processes usually inherit the x86_64 environment. `python3`, `node`, `java`, Homebrew, and the Docker client may each report a different architecture.

```bash
file "$(command -v python3)"
python3 -c 'import platform; print(platform.machine())'
node -p 'process.arch' 2>/dev/null || true
java -XshowSettings:properties -version 2>&1 | grep 'os.arch' || true
lipo -info <binary-or-dylib>
```

Rebuild dependencies in a native arm64 terminal, then repeat the formal regression. Never present a Rosetta pass as a native pass. When an Apple Silicon-only hard gate is required, use `project-health-macos`.

## 2. Homebrew prefixes and PATH shadowing

Native Homebrew usually uses `/opt/homebrew`, while Rosetta Homebrew may use `/usr/local`. Do not hard-code either prefix.

```bash
command -v brew
brew --prefix
brew config
brew doctor
printf '%s\n' "$PATH" | tr ':' '\n'
```

Check whether `PATH` contains both prefixes and whether `brew`, `python3`, and `node` come from the expected architecture. In CI, use explicit setup actions or absolute paths rather than relying on login-shell initialization.

## 3. BSD userland is not GNU

macOS ships BSD variants of `sed`, `stat`, `date`, `xargs`, and others; Linux flags may not work:

```bash
sed -i '' 's/old/new/' file
stat -f '%z %N' file
date -r 0
ditto --help
```

`gsed`, `gstat`, and `gtimeout` exist only after installing coreutils. Re-test in a clean macOS environment; do not assume a developer's GNU tools are part of the system.

## 4. The system bash is still 3.2

```bash
/bin/bash --version
command -v bash
```

System `/bin/bash` lacks bash 4+ associative arrays, `mapfile`, `wait -n`, `${var,,}`, and similar features. Prefer `#!/bin/sh`; when newer bash is required, use an explicit shebang and pin it in CI. Do not depend on interactive `.zshrc`, aliases, or a user-installed bash.

## 5. APFS case sensitivity and Unicode normalization

The default APFS volume is usually case-insensitive and may normalize Unicode filenames. Git's `core.ignorecase` / `core.precomposeUnicode` can hide path problems.

```bash
diskutil info / | grep -i 'File System Personality'
git config --show-origin --get core.ignorecase || true
git config --show-origin --get core.precomposeUnicode || true
find . -maxdepth 2 -print | LC_ALL=C sort
```

For case-only renames, resource paths, or cross-platform synchronization, re-check on a case-sensitive volume or Linux. A clean `git status` alone does not prove path compatibility.

## 6. Gatekeeper, quarantine, codesign, and notarization

Downloaded `.app`, `.dmg`, binary, or script files may carry `com.apple.quarantine`, and Gatekeeper may block unverified artifacts.

```bash
xattr -p com.apple.quarantine <file>
codesign -dv --verbose=4 <app-or-binary>
codesign --verify --deep --strict --verbose=2 <app-or-binary>
spctl --assess --type execute --verbose=4 <app-or-binary>
xcrun stapler validate <app-or-dmg>
shasum -a 256 <file>
```

"Unsigned or not notarized" and "malicious" are different findings; do not turn an `spctl` failure into a malware verdict. Verify signatures and notarization for release artifacts. Never recommend disabling Gatekeeper or SIP as a workaround.

## 7. TCC, SIP, and automation permissions

Access to Desktop, Documents, Downloads, Photos, Contacts, Calendar, screen recording, or automation of other apps can trigger TCC prompts. CI, SSH, and headless sessions may fail outright. SIP also blocks changes to system directories and protected files.

- Explain why permission is needed and request the minimum scope; do not ask for Full Disk Access just to run tests.
- Do not misclassify a TCC denial as a code bug; record it as an environment limitation and an uncovered area.
- Do not disable SIP, weaken Gatekeeper, or modify system directories with `sudo` to bypass it.
- GUI automation, AppleScript, `screencapture`, and accessibility permissions are especially unreliable on GitHub runners and must be listed as uncovered.

## 8. launchd is not systemd

Do not copy Linux `systemctl`, `service`, or `journalctl` commands to macOS. macOS uses launchd and separates the `gui/$UID` and `system` domains.

```bash
launchctl print gui/$(id -u)/<label>
launchctl print system/<label>
launchctl bootstrap gui/$(id -u) <plist>
launchctl bootout gui/$(id -u)/<label>
```

Check plist paths, log paths, environment variables, and executable permissions. Do not treat a service that requires a logged-in GUI session as testable in CI.

## 9. Docker Desktop, image architecture, and volume performance

Apple Silicon pulls arm64 images by default. An amd64-only image runs through QEMU, which is slower and can behave differently.

```bash
docker context ls
docker version --format 'client={{.Client.Arch}} server={{.Server.Arch}}'
docker image inspect <image> --format '{{.Architecture}}/{{.Os}}'
docker run --rm <image> uname -m
```

- Record the client, server, and image architectures separately.
- Use `--platform linux/amd64` only when no arm64 image exists, and document the emulation cost.
- Prefer `host.docker.internal` for host access from a container; do not assume `localhost` is the host.
- Do not blindly place `node_modules`, database files, or large trees on a macOS bind mount. Prefer named volumes, ignored project directories, or VM-native storage, and establish an A/B baseline.
- Colima and Docker Desktop are not equivalent in context, networking, or volume behavior; re-verify after switching.

## 10. Archives, extended attributes, and symlinks

Plain zip archives may lose extended attributes, resource forks, executable bits, or symlinks. Use `ditto` for metadata-preserving delivery and verify the extracted result.

```bash
ditto -c -k --sequesterRsrc --keepParent <dir> <archive.zip>
unzip -l <archive.zip>
find <dir> -maxdepth 2 -type l -ls
```

Verify signatures, quarantine, executable bits, symlinks, and the actual extraction result; a zero exit status from the archive command is not enough.

## 11. GitHub macOS runners are not fixed hardware

The free `macos-latest` runner may receive different chips, CPU counts, memory sizes, and macOS versions. Do not hard-code M1 or M2 Pro or a fixed macOS release. Treat only "arm64 and Rosetta 0" as hard conditions, and record the actual chip, CPU, memory, and OS from each run.

Performance, GPU/Metal, Neural Engine, media encoding, and newest SDK conclusions need a real target-machine follow-up. CI success does not prove every Apple Silicon generation has been validated.

## 12. Ports, processes, and local networking

AirPlay Receiver may occupy 5000/7000, and the listener may be `ControlCenter`; this is not a target-project bug. `localhost` may also resolve to IPv6 `::1` first while the service binds only `127.0.0.1`.

```bash
lsof -nP -iTCP:5000 -sTCP:LISTEN
lsof -nP -iTCP:7000 -sTCP:LISTEN
lsof -nP -iTCP:<port> -sTCP:LISTEN
ps -axo pid,ppid,comm,args
curl -4 -v http://127.0.0.1:<port>/
curl -6 -v "http://[::1]:<port>/" 2>/dev/null || true
```

- Identify the listener with `lsof` and `ps` before using `kill -9`, repeatedly force-killing, or defaulting to `sudo`.
- macOS 15+ may request Local Network permission on first access. CI, SSH, or a no-GUI session may be unable to show the prompt. Record this as an environment limit, not as proof that the service is broken.
- If a system service owns the port, change the test port or bind explicitly; do not disable AirPlay Receiver just to "fix" the project.
- Linux habits such as `ss` and `netstat -tulpn` do not transfer directly. If `lsof` cannot see a protected process, assess permissions first and do not default to elevation.

## 13. Multi-language toolchain architecture

`python3`, `node`, `java`, pip, npm caches, and native modules may come from different architectures. Version strings alone are insufficient.

```bash
file "$(command -v python3)"
python3 -c 'import platform,sys; print(platform.machine()); print(sys.executable)'
python3 -m pip debug --verbose | grep -i 'tags'
node -p 'process.arch'
npm config get arch
printenv npm_config_arch 2>/dev/null || true
/usr/libexec/java_home -V
java -XshowSettings:properties -version 2>&1 | grep -E 'os.arch|java.home'
lipo -info <binary-or-dylib>
otool -L <binary-or-dylib>
```

- A universal2 wheel may contain both architectures; `platform.machine()` describes the current process, not a guarantee that the artifact is single-architecture.
- If `node-gyp`, `sharp`, `canvas`, SQLite, or another native module has mixed architecture, delete `node_modules` and reinstall in a native arm64 terminal. Do not copy caches across architectures.
- JDKs, JNI libraries, and container base images must share one architecture. Replacing `JAVA_HOME` without reinstalling JNI dependencies may still load the wrong `.dylib`.
- Re-sign after modifying a dylib. `DYLD_LIBRARY_PATH` may be ignored for protected processes or under SIP; environment injection is not a long-term compatibility strategy.
- Use `codesign -d --entitlements :-` to inspect JIT, debugger, or hardened-runtime entitlements. Do not disable SIP to work around them.

## 14. Xcode, Command Line Tools, and SDKs

`xcode-select -p` pointing at Command Line Tools does not mean full Xcode is installed. With multiple Xcodes, `xcodebuild` may select the wrong one. An unaccepted CLT license often appears as an opaque CI failure.

```bash
xcode-select -p
xcodebuild -version
xcrun --show-sdk-path
xcrun --sdk macosx --show-sdk-version
xcodebuild -showsdks
xcodebuild -license check
```

- Record Xcode, SDK, Command Line Tools, the target `MACOSX_DEPLOYMENT_TARGET`, and the actual `xcodebuild` path.
- `xcodebuild -license check` is a read-only check. Do not run `sudo xcodebuild -license accept`, `sudo xcode-select -s`, or `xcodebuild -runFirstLaunch` during an audit.
- A CLT-only environment cannot prove a full Xcode project, Interface Builder, simulator, or signing flow works. Mark those conclusions as uncovered.
- On Apple Silicon, also verify the target architecture, signing, and entitlements. "It compiled" does not mean the artifact is distributable.

## 15. Do not reuse performance baselines across generations

M1 through M6 differ in CPU/GPU cores, unified-memory bandwidth, and Neural Engine size. Copying fixed M1 worker counts, connection pools, Docker CPU limits, or concurrency settings to M5/M6 can cause contention, timeouts, or false performance regressions.

```bash
sysctl -n hw.ncpu
sysctl -n hw.memsize
vm_stat
system_profiler SPHardwareDataType
```

Bind performance conclusions to chip, memory, macOS, Xcode/SDK, workload, and concurrency. CI proves functional and basic regressions only; it does not replace real M6 or M5 Ultra hardware testing. `powermetrics` requires additional privileges and must not be assumed available.

## 16. Common false-pass checklist

- The terminal is under Rosetta, but only `python3 --version` was checked, not `platform.machine()`.
- `brew`, `python3`, and `node` come from different Homebrew prefixes or architectures.
- A script passes on the developer machine because GNU tools are installed, then fails on a clean Mac.
- Paths were tested only on case-insensitive APFS, missing a case collision.
- Removing quarantine with `xattr -d` is treated as proof that the app is runnable.
- A Docker image starts, so its architecture is assumed to match the host.
- `lsof` shows no listener, so the service is declared dead without ruling out AirPlay, IPv6, or permission limits.
- Only Command Line Tools are installed, but an iOS/macOS project is reported as built successfully.
- One arm64 runner or chip passes, and the result is presented as "all M-series Macs pass".

## 17. Minimum verification checklist

- [ ] macOS version, shell, chip, `uname -m`, `arch`, and Rosetta state are recorded.
- [ ] Dependencies, interpreters, native modules, and binaries use a consistent architecture; no Rosetta pass was presented as native.
- [ ] No Homebrew prefix is hard-coded, and PATH shadowing was checked.
- [ ] BSD versus GNU tool differences were considered.
- [ ] Case sensitivity, Unicode, signing, TCC, local-network, and launchd limits are documented.
- [ ] Docker client, server, and image architectures are confirmed separately.
- [ ] Port conflicts, AirPlay 5000/7000, and IPv4/IPv6 behavior are ruled out.
- [ ] Xcode/CLT/SDK/license state and deployment target are recorded.
- [ ] Performance baselines are tied to chip and resource specifications; untested generations and hardware are listed.
- [ ] The report states macOS coverage and uncovered areas.
