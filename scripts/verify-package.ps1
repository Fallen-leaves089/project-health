<#
.SYNOPSIS
    Verify the skill package: required files, UTF-8 without BOM, relative Markdown links,
    redaction self-test, and a clean redaction scan.

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
    'scripts/verify-package.ps1'
)

foreach ($rel in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $rel))) {
        $failures.Add(('Missing required file: {0}' -f $rel))
    }
}

$textExtensions = @(
    '.md', '.txt', '.ps1', '.psm1', '.json', '.yml', '.yaml', '.toml',
    '.env', '.sh', '.cmd', '.bat', '.js', '.ts', '.py', '.xml', '.properties', '.pub', ''
)
$textNames = @('.gitattributes', '.gitignore', '.editorconfig')

$textFiles = @(
    Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction Stop |
        Where-Object {
            ($textExtensions -contains $_.Extension.ToLowerInvariant()) -or
            ($textNames -contains $_.Name)
        }
)

foreach ($file in $textFiles) {
    $rel = $file.FullName.Substring($root.Length).TrimStart([char[]]@('\', '/'))
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $failures.Add(('UTF-8 BOM found: {0}' -f $rel))
    }
}

$mdFiles = @(Get-ChildItem -LiteralPath $root -Recurse -File -Filter *.md -ErrorAction Stop)
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
    $shell = (Get-Command pwsh.exe -ErrorAction SilentlyContinue).Source
}
if ([string]::IsNullOrWhiteSpace($shell)) {
    Write-Host 'ERROR: neither powershell.exe nor pwsh.exe was found.' -ForegroundColor Red
    exit 2
}

$checkScript = Join-Path $PSScriptRoot 'check-redaction.ps1'
& $shell -NoProfile -ExecutionPolicy Bypass -File $checkScript -SelfTest
if ($LASTEXITCODE -ne 0) {
    $failures.Add('Redaction self-test failed.')
}

& $shell -NoProfile -ExecutionPolicy Bypass -File $checkScript -Path $root -Quiet
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
