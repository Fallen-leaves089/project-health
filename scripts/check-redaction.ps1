<#
.SYNOPSIS
    Scan a skill package for personal paths, private addresses, and common secret patterns.

.DESCRIPTION
    Exit codes:
      0 = clean
      1 = findings
      2 = usage error or self-test failure

    The scanner prints only file:line and the pattern name. It never prints the matched value,
    so a finding cannot leak a secret into a report or terminal scrollback.

.PARAMETER Path
    File or directory to scan. Defaults to the parent directory of this script.

.PARAMETER ExtraPatterns
    Additional literal strings to flag, such as an internal project code name or client name.

.PARAMETER SelfTest
    Run built-in positive and negative cases, then exit.

.PARAMETER Quiet
    Do not print individual findings; print only the summary.

.EXAMPLE
    .\check-redaction.ps1 -SelfTest

.EXAMPLE
    .\check-redaction.ps1 -Path . -ExtraPatterns 'ACME-INTERNAL'
#>
[CmdletBinding()]
param(
    [string]$Path = '',
    [switch]$SelfTest,
    [switch]$Quiet,
    [string[]]$ExtraPatterns = @()
)

$ErrorActionPreference = 'Stop'
$scannerPath = $PSCommandPath
if ([string]::IsNullOrWhiteSpace($scannerPath)) { $scannerPath = $MyInvocation.MyCommand.Path }

if ([string]::IsNullOrWhiteSpace($Path)) {
    $scriptPath = $PSCommandPath
    if ([string]::IsNullOrWhiteSpace($scriptPath)) { $scriptPath = $MyInvocation.MyCommand.Path }
    if (-not [string]::IsNullOrWhiteSpace($scriptPath)) {
        $Path = Split-Path -Parent (Split-Path -Parent $scriptPath)
    } else {
        $Path = (Get-Location).Path
    }
}

function Get-ScanPatterns {
    param([string[]]$Extra = @())

    $patterns = @(
        @{ Name = 'Windows user path'; Regex = '(?i)\b[A-Z]:\\Users\\(?!<)[^\\\s"''`<>]+' },
        @{ Name = 'Windows user path (slash)'; Regex = '(?i)\b[A-Z]:/Users/(?!<)[^/\s"''`<>]+' },
        @{ Name = 'Unix home path'; Regex = '(?i)(?<![\w.])/' + 'home/(?!<)[^/\s"''`<>]+' },
        @{ Name = 'Private IPv4'; Regex = '\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b' },
        @{ Name = 'OpenAI-style key'; Regex = '\bsk-[A-Za-z0-9_-]{20,}\b' },
        @{ Name = 'GitHub token'; Regex = '\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b' },
        @{ Name = 'AWS access key'; Regex = '\bAKIA[0-9A-Z]{16}\b' },
        @{ Name = 'Private key block'; Regex = '-----BEGIN [A-Z ]*PRIVATE KEY-----' },
        @{ Name = 'Assigned secret'; Regex = '(?i)["'']?\b(api[_-]?key|secret|token|password|passwd|pwd)\b["'']?\s*[:=]\s*["'']?(?!<|\$|\{|%|\[|REDACTED|CHANGE_ME|example|placeholder)[A-Za-z0-9_\-\.]{12,}' }
    )

    for ($i = 0; $i -lt $Extra.Count; $i++) {
        $patterns += @{
            Name  = ('Extra pattern {0}' -f ($i + 1))
            Regex = [regex]::Escape($Extra[$i])
        }
    }

    return $patterns
}

function Invoke-RedactionScan {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [string[]]$Extra = @(),
        [switch]$Quiet
    )

    $rootItem = Get-Item -LiteralPath $Root
    $isSingleFile = -not $rootItem.PSIsContainer
    if ($isSingleFile) {
        $rootFull = $rootItem.DirectoryName.TrimEnd([char[]]@('\', '/'))
    } else {
        $rootFull = $rootItem.FullName.TrimEnd([char[]]@('\', '/'))
    }
    $patterns = Get-ScanPatterns -Extra $Extra

    $textExtensions = @(
        '.md', '.txt', '.ps1', '.psm1', '.json', '.yml', '.yaml', '.toml',
        '.env', '.sh', '.cmd', '.bat', '.js', '.ts', '.py', '.fixture', '.xml', '.properties', '.pub', ''
    )
    $textNames = @('.gitattributes', '.gitignore', '.editorconfig', '.mailmap')
    $skipDirPattern = '[\\/](\.git|node_modules|bin|obj|dist|build|\.vs|\.idea)[\\/]'

    if ($isSingleFile) {
        $files = @($rootItem)
    } else {
        $files = @(
            Get-ChildItem -LiteralPath $rootFull -Recurse -File -Force -ErrorAction Stop |
                Where-Object {
                    (($textExtensions -contains $_.Extension.ToLowerInvariant()) -or ($textNames -contains $_.Name)) -and
                    ($_.FullName -notmatch $skipDirPattern)
                }
        )
    }

    $findings = New-Object System.Collections.Generic.List[string]
    foreach ($file in $files) {
        $rel = $file.FullName.Substring($rootFull.Length).TrimStart([char[]]@('\', '/'))
        $lineNo = 0
        foreach ($line in (Get-Content -LiteralPath $file.FullName -Encoding UTF8 -ErrorAction Stop)) {
            $lineNo++
            foreach ($p in $patterns) {
                if ([regex]::IsMatch($line, $p.Regex)) {
                    $findings.Add(('{0}:{1}  [{2}]' -f $rel, $lineNo, $p.Name)) | Out-Null
                }
            }
        }
    }

    if (-not $Quiet) {
        foreach ($finding in $findings) {
            Write-Host $finding -ForegroundColor Yellow
        }
    }

    return [pscustomobject]@{
        Findings     = $findings
        FilesScanned = $files.Count
    }
}

function Test-ScanExpectation {
    param(
        [string]$Root,
        [string[]]$Extra,
        [bool]$ShouldFind,
        [string]$Label
    )

    $scanArgs = @{
        Root  = $Root
        Extra = $Extra
        Quiet = $true
    }
    $result = Invoke-RedactionScan @scanArgs
    $actual = $result.Findings.Count -gt 0

    if ($actual -ne $ShouldFind) {
        Write-Host ('SELF-TEST FAIL: {0} (expected findings={1}, got {2})' -f $Label, $ShouldFind, $result.Findings.Count) -ForegroundColor Red
        return $false
    }

    Write-Host ('SELF-TEST OK: {0} (findings={1})' -f $Label, $result.Findings.Count) -ForegroundColor Green
    return $true
}

function Invoke-SelfTest {
    $temp = Join-Path ([System.IO.Path]::GetTempPath()) ('fhc-redaction-' + [guid]::NewGuid().ToString('N'))
    $ok = $true
    try {
        New-Item -ItemType Directory -Path $temp -Force | Out-Null

        $clean = @(
            '# Clean sample',
            'Install under C:\Users\<you>\.agent-skills\',
            'Use <REDACTED> for secrets.',
            'Host: 192.168.x.x',
            'Token: <REDACTED>'
        ) -join "`n"
        [System.IO.File]::WriteAllText((Join-Path $temp 'clean.md'), $clean, [System.Text.UTF8Encoding]::new($false))

        $dirtyPath = 'Path: C:' + '\' + 'Users' + '\' + 'example-user' + '\work\project'
        [System.IO.File]::WriteAllText((Join-Path $temp 'dirty-path.md'), $dirtyPath, [System.Text.UTF8Encoding]::new($false))

        $dirtyKey = 'key: sk-' + 'abcdefghijklmnopqrstuvwxyz123456'
        [System.IO.File]::WriteAllText((Join-Path $temp 'dirty-key.md'), $dirtyKey, [System.Text.UTF8Encoding]::new($false))

        $dirtyIp = 'host: ' + '192' + '.168' + '.1' + '.10'
        [System.IO.File]::WriteAllText((Join-Path $temp 'dirty-ip.md'), $dirtyIp, [System.Text.UTF8Encoding]::new($false))

        $dirtyPathSlash = 'Path: C:/' + 'Users/example-user/work/project'
        [System.IO.File]::WriteAllText((Join-Path $temp 'dirty-path-slash.md'), $dirtyPathSlash, [System.Text.UTF8Encoding]::new($false))

        $dirtyJsonKey = '{"API_KEY": "' + 'abcdefghijklmnopqrstuvwxyz' + '"}'
        [System.IO.File]::WriteAllText((Join-Path $temp 'dirty-json-key.md'), $dirtyJsonKey, [System.Text.UTF8Encoding]::new($false))

        $dirtyExtra = 'marker: ACME-' + 'INTERNAL-TOKEN'
        [System.IO.File]::WriteAllText((Join-Path $temp 'dirty-extra.md'), $dirtyExtra, [System.Text.UTF8Encoding]::new($false))

        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'clean.md') -Extra @() -ShouldFind $false -Label 'clean sample passes') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-path.md') -Extra @() -ShouldFind $true -Label 'personal path is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-path-slash.md') -Extra @() -ShouldFind $true -Label 'personal path with slashes is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-key.md') -Extra @() -ShouldFind $true -Label 'secret-looking key is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-json-key.md') -Extra @() -ShouldFind $true -Label 'quoted JSON secret is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-ip.md') -Extra @() -ShouldFind $true -Label 'private IPv4 is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-extra.md') -Extra @('ACME-INTERNAL') -ShouldFind $true -Label 'extra literal pattern is caught') -and $ok

        $scriptsDir = Split-Path -Parent $scannerPath
        $selfScan = Invoke-RedactionScan -Root $scriptsDir -Quiet
        if ($selfScan.Findings.Count -gt 0) {
            Write-Host ('SELF-TEST FAIL: scripts directory contains {0} redaction finding(s).' -f $selfScan.Findings.Count) -ForegroundColor Red
            $ok = $false
        } else {
            Write-Host 'SELF-TEST OK: scripts directory passes the package scan (findings=0)' -ForegroundColor Green
        }

        $bootstrapPath = Join-Path $temp 'check-redaction.ps1'
        $bootstrapText = [System.IO.File]::ReadAllText($scannerPath) + "`n" + $dirtyPath + "`n"
        [System.IO.File]::WriteAllText($bootstrapPath, $bootstrapText, [System.Text.UTF8Encoding]::new($false))
        $bootstrapScan = Invoke-RedactionScan -Root $bootstrapPath -Quiet
        if ($bootstrapScan.Findings.Count -eq 0) {
            Write-Host 'SELF-TEST FAIL: bootstrap copy was not scanned for sensitive content' -ForegroundColor Red
            $ok = $false
        } else {
            Write-Host ('SELF-TEST OK: bootstrap copy is scanned for sensitive content (findings={0})' -f $bootstrapScan.Findings.Count) -ForegroundColor Green
        }
    }
    finally {
        if (Test-Path -LiteralPath $temp) {
            [System.IO.Directory]::Delete($temp, $true)
        }
    }

    if (-not $ok) {
        Write-Host 'SELF-TEST FAIL' -ForegroundColor Red
        return 2
    }

    Write-Host 'SELF-TEST PASS' -ForegroundColor Green
    return 0
}

if ($SelfTest) {
    exit (Invoke-SelfTest)
}

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Host ('ERROR: path not found: {0}' -f $Path) -ForegroundColor Red
    exit 2
}

$scanArgs = @{
    Root  = $Path
    Extra = $ExtraPatterns
    Quiet = $Quiet
}
$result = Invoke-RedactionScan @scanArgs

Write-Host ('Scanned {0} file(s); {1} finding(s).' -f $result.FilesScanned, $result.Findings.Count)
if ($result.Findings.Count -gt 0) {
    Write-Host 'REDACTION CHECK FAILED: review the findings above.' -ForegroundColor Red
    exit 1
}

Write-Host 'REDACTION CHECK PASSED.' -ForegroundColor Green
exit 0
