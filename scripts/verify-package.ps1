<#
.SYNOPSIS
    Verify the skill package: required files, UTF-8 without BOM, relative Markdown links,
    skill frontmatter and version consistency, redaction self-test, and a clean redaction scan.

.DESCRIPTION
    Exit codes:
      0 = package passed
      1 = one or more checks failed
      2 = usage error
#>
[CmdletBinding()]
param(
    [string]$Path = ''
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Path)) {
    $scriptPath = $PSCommandPath
    if ([string]::IsNullOrWhiteSpace($scriptPath)) { $scriptPath = $MyInvocation.MyCommand.Path }
    if (-not [string]::IsNullOrWhiteSpace($scriptPath)) {
        $Path = Split-Path -Parent (Split-Path -Parent $scriptPath)
    } else {
        $Path = (Get-Location).Path
    }
}

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Host ('ERROR: path not found: {0}' -f $Path) -ForegroundColor Red
    exit 2
}

$root = (Get-Item -LiteralPath $Path).FullName
if (-not (Get-Item -LiteralPath $root).PSIsContainer) {
    Write-Host 'ERROR: path must be a directory.' -ForegroundColor Red
    exit 2
}

$failures = New-Object System.Collections.Generic.List[string]
$required = @(
    'SKILL.md',
    'SKILL.en.md',
    'AGENTS.md',
    'PITFALLS.md',
    'README.md',
    'README.en.md',
    'LICENSE',
    'LICENSE.zh-CN.md',
    'COMMERCIAL.md',
    'COMMERCIAL.en.md',
    'NOTICE',
    'SANITIZATION.md',
    'SANITIZATION.en.md',
    'SECURITY.md',
    'SIGNING.md',
    'SIGNING.en.md',
    'release-signing-key.pub',
    'allowed_signers',
    'CHANGELOG.md',
    'CONTRIBUTING.md',
    'CONTRIBUTING.en.md',
    '.gitattributes',
    '.gitignore',
    '.editorconfig',
    '.github/workflows/verify.yml',
    'references/platform-commands.md',
    'references/platform-commands.en.md',
    'references/windows-pitfalls.md',
    'references/windows-pitfalls.en.md',
    'references/verification-playbook.md',
    'references/verification-playbook.en.md',
    'references/report-template.md',
    'references/report-template.en.md',
    'scripts/check_redaction.py',
    'scripts/verify_package.py',
    'scripts/check-redaction.ps1',
    'scripts/verify-package.ps1',
    'tests/test_contract.py',
    'tests/fixtures/malicious-target/malicious-agents.fixture'
)

foreach ($rel in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $rel))) {
        $failures.Add(('Missing required file: {0}' -f $rel))
    }
}

function Read-SkillFrontmatter {
    param([string]$Relative)

    $path = Join-Path $root $Relative
    $lines = [System.IO.File]::ReadAllLines($path, [System.Text.Encoding]::UTF8)
    if ($lines.Count -lt 2 -or $lines[0].Trim() -ne '---') {
        $failures.Add(('Missing or invalid frontmatter: {0}' -f $Relative))
        return $null
    }

    $fields = @{}
    $versionScopes = New-Object System.Collections.Generic.List[object]
    $inMetadata = $false
    $metadataIndent = -1
    $closed = $false

    for ($i = 1; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($line.Trim() -eq '---') {
            $closed = $true
            break
        }
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith('#') -or -not $trimmed.Contains(':')) {
            continue
        }

        $indent = $line.Length - $line.TrimStart(' ').Length
        if ($trimmed -eq 'metadata:') {
            $inMetadata = $true
            $metadataIndent = $indent
            continue
        }
        if ($inMetadata -and $indent -le $metadataIndent) {
            $inMetadata = $false
        }

        $parts = $trimmed.Split([char[]]@(':'), 2)
        $key = $parts[0].Trim()
        $value = if ($parts.Count -gt 1) { $parts[1].Trim().Trim('"').Trim("'") } else { '' }
        if ($key -eq 'version') {
            $versionScopes.Add([pscustomobject]@{ Indent = $indent; Nested = $inMetadata })
        }
        $fields[$key] = $value
    }

    if (-not $closed) {
        $failures.Add(('Skill frontmatter is not closed: {0}' -f $Relative))
        return $null
    }
    if ($fields['name'] -ne 'project-health') {
        $failures.Add(('Frontmatter name mismatch in {0}: {1}' -f $Relative, $(if ($fields.ContainsKey('name')) { $fields['name'] } else { '<missing>' })))
    }
    if ($fields['license'] -ne 'PolyForm-Noncommercial-1.0.0') {
        $failures.Add(('Frontmatter license mismatch in {0}: {1}' -f $Relative, $(if ($fields.ContainsKey('license')) { $fields['license'] } else { '<missing>' })))
    }
    if ($versionScopes.Count -eq 0) {
        $failures.Add(('Frontmatter version missing in {0}' -f $Relative))
        return $null
    }
    if (@($versionScopes | Where-Object { $_.Indent -eq 0 -or -not $_.Nested }).Count -gt 0) {
        $failures.Add(('Frontmatter version must be nested under metadata in {0}' -f $Relative))
        return $null
    }

    $version = $fields['version']
    if ($version -notmatch '^\d+\.\d+\.\d+$') {
        $failures.Add(('Frontmatter version missing or invalid in {0}: {1}' -f $Relative, $(if ($version) { $version } else { '<missing>' })))
        return $null
    }
    return $version
}

$skillVersions = @{}
foreach ($relative in @('SKILL.md', 'SKILL.en.md')) {
    $version = Read-SkillFrontmatter -Relative $relative
    if (-not [string]::IsNullOrWhiteSpace($version)) {
        $skillVersions[$relative] = $version
    }
}
if (@($skillVersions.Values | Sort-Object -Unique).Count -gt 1) {
    $summary = ($skillVersions.Keys | Sort-Object | ForEach-Object { '{0}={1}' -f $_, $skillVersions[$_] }) -join ', '
    $failures.Add(('SKILL.md and SKILL.en.md versions do not match: {0}' -f $summary))
}

$textExtensions = @(
    '.md', '.txt', '.ps1', '.psm1', '.json', '.yml', '.yaml', '.toml',
    '.env', '.sh', '.cmd', '.bat', '.js', '.ts', '.py', '.fixture', '.xml', '.properties', '.pub', ''
)
$textNames = @('.gitattributes', '.gitignore', '.editorconfig', '.mailmap')

$textFiles = @(
    Get-ChildItem -LiteralPath $root -Recurse -File -Force -ErrorAction Stop |
        Where-Object {
            (($textExtensions -contains $_.Extension.ToLowerInvariant()) -or
            ($textNames -contains $_.Name)) -and
            ($_.FullName -notmatch '[\\/]\.git[\\/]')
        }
)

foreach ($file in $textFiles) {
    $rel = $file.FullName.Substring($root.Length).TrimStart([char[]]@('\', '/'))
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $failures.Add(('UTF-8 BOM found: {0}' -f $rel))
    }
}

$mdFiles = @(
    Get-ChildItem -LiteralPath $root -Recurse -File -Filter *.md -Force -ErrorAction Stop |
        Where-Object { $_.FullName -notmatch '[\\/]\.git[\\/]' }
)
foreach ($md in $mdFiles) {
    $mdRel = $md.FullName.Substring($root.Length).TrimStart([char[]]@('\', '/'))
    $lineNo = 0
    foreach ($line in (Get-Content -LiteralPath $md.FullName -Encoding UTF8 -ErrorAction Stop)) {
        $lineNo++
        foreach ($m in [regex]::Matches($line, '\]\(([^)]+)\)')) {
            $target = $m.Groups[1].Value.Trim()
            if ($target -match '^(https?://|mailto:|#)') { continue }
            $target = ($target -split '#')[0]
            if ([string]::IsNullOrWhiteSpace($target)) { continue }
            $candidate = Join-Path $md.DirectoryName $target
            if (-not (Test-Path -LiteralPath $candidate)) {
                $failures.Add(('Broken relative link: {0}:{1} -> {2}' -f $mdRel, $lineNo, $target))
            }
        }
    }
}

$shell = (Get-Command powershell.exe -ErrorAction SilentlyContinue).Source
if ([string]::IsNullOrWhiteSpace($shell)) {
    $shell = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
}
if ([string]::IsNullOrWhiteSpace($shell)) {
    $shell = (Get-Command pwsh.exe -ErrorAction SilentlyContinue).Source
}
if ([string]::IsNullOrWhiteSpace($shell)) {
    Write-Host 'ERROR: neither powershell.exe nor pwsh was found.' -ForegroundColor Red
    exit 2
}

$checkScript = Join-Path $PSScriptRoot 'check-redaction.ps1'
$checkArgs = @('-NoProfile')
if ([System.IO.Path]::GetFileName($shell) -ieq 'powershell.exe') {
    $checkArgs += @('-ExecutionPolicy', 'Bypass')
}
$checkArgs += @('-File', $checkScript)

$selfTestArgs = $checkArgs + @('-SelfTest')
& $shell @selfTestArgs
if ($LASTEXITCODE -ne 0) {
    $failures.Add('Redaction self-test failed.')
}

$scanArgs = $checkArgs + @('-Path', $root, '-Quiet')
& $shell @scanArgs
if ($LASTEXITCODE -ne 0) {
    $failures.Add('Redaction scan reported findings.')
}

Write-Host ('Checked {0} text file(s), {1} Markdown file(s).' -f $textFiles.Count, $mdFiles.Count)
if ($failures.Count -eq 0) {
    Write-Host 'PACKAGE VERIFY PASSED.' -ForegroundColor Green
    exit 0
}

foreach ($failure in $failures) {
    Write-Host (' - {0}' -f $failure) -ForegroundColor Red
}
Write-Host 'PACKAGE VERIFY FAILED.' -ForegroundColor Red
exit 1
