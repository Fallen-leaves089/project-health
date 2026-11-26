<#
.SYNOPSIS
    Verify the skill package: required files, non-binary text encoding, relative Markdown links,
    skill frontmatter and version consistency, PITFALLS schemas, redaction self-test, and a clean scan.

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

$root = (Get-Item -LiteralPath $Path -Force).FullName
if (-not (Get-Item -LiteralPath $root -Force).PSIsContainer) {
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
    'commercial/README.md',
    'commercial/README.en.md',
    'commercial/guardian-authorization.template.md',
    'commercial/guardian-authorization.template.en.md',
    'commercial/commercial-license-agreement.template.md',
    'commercial/commercial-license-agreement.template.en.md',
    'commercial/order-form.template.md',
    'commercial/order-form.template.en.md',
    'commercial/license-certificate.template.md',
    'commercial/license-certificate.template.en.md',
    'commercial/first-reply-email.template.md',
    'commercial/first-reply-email.template.en.md',
    'commercial/license-registry.template.csv',
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
    'references/macos-pitfalls.md',
    'references/macos-pitfalls.en.md',
    'references/windows-pitfalls.md',
    'references/windows-pitfalls.en.md',
    'references/linux-server-pitfalls.md',
    'references/linux-server-pitfalls.en.md',
    'references/verification-playbook.md',
    'references/verification-playbook.en.md',
    'references/report-template.md',
    'references/report-template.en.md',
    'references/structural-experience.md',
    'references/structural-experience.en.md',
    'scripts/check_redaction.py',
    'scripts/verify_package.py',
    'scripts/record_pitfall.py',
    'scripts/record_structure.py',
    'scripts/structure-schema.json',
    'scripts/check-redaction.ps1',
    'scripts/verify-package.ps1',
    'tests/test_contract.py',
    'tests/test_structural_experience.py',
    'tests/test_record_structure.py',
    'tests/test_record_pitfall.py',
    'tests/test_agent_memory_eval.py',
    'tests/agent_memory_eval.py',
    'tests/fixtures/agent-memory-eval/prompt.txt',
    'tests/fixtures/agent-memory-eval/zero-tests/expect.json',
    'tests/fixtures/agent-memory-eval/zero-tests/target/README.md',
    'tests/fixtures/agent-memory-eval/zero-tests/target/check.py',
    'tests/fixtures/agent-memory-eval/zero-tests/target/tests/service_checks.py',
    'tests/fixtures/agent-memory-eval/coverage-threshold/expect.json',
    'tests/fixtures/agent-memory-eval/coverage-threshold/target/README.md',
    'tests/fixtures/agent-memory-eval/coverage-threshold/target/check.py',
    'tests/fixtures/agent-memory-eval/coverage-threshold/target/coverage.json',
    'tests/fixtures/agent-memory-eval/coverage-threshold/target/tests/test_stock.py',
    'tests/fixtures/malicious-target/malicious-agents.fixture'
)

foreach ($rel in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $rel))) {
        $failures.Add(('Missing required file: {0}' -f $rel))
    }
}

function Test-StructureManuals {
    param([string]$Root)

    $schemaPath = Join-Path $Root 'scripts/structure-schema.json'
    if (-not (Test-Path -LiteralPath $schemaPath)) {
        $failures.Add('Missing structure schema.')
        return
    }
    try {
        $schema = Get-Content -LiteralPath $schemaPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $failures.Add(('Invalid structure schema: {0}' -f $_.Exception.Message))
        return
    }

    $chapterIds = @($schema.chapter_ids)
    $statusLabels = @()
    foreach ($statusKey in @($schema.status_keys)) {
        $statusLabels += @($schema.status_labels.PSObject.Properties[$statusKey].Value)
    }
    $injectionLabels = @()
    foreach ($injectionKey in @($schema.injection_keys)) {
        $injectionLabels += @($schema.injection_labels.PSObject.Properties[$injectionKey].Value)
    }
    $pendingLabels = @($schema.status_labels.pending)
    $detailedLabels = @($schema.injection_labels.detailed)
    $pitfallPattern = [string]$schema.pitfall_id_pattern

    foreach ($rel in @(
        'references/structural-experience.md',
        'references/structural-experience.en.md'
    )) {
        $manualPath = Join-Path $Root $rel
        if (-not (Test-Path -LiteralPath $manualPath)) { continue }
        $lines = [System.IO.File]::ReadAllLines($manualPath, [System.Text.Encoding]::UTF8)
        $versionLine = 'schema-version: {0}' -f $schema.schema_version
        if (-not ($lines -contains $versionLine)) {
            $failures.Add(('Structure manual {0} is missing {1}' -f $rel, $versionLine))
        }
        $language = if ($rel.EndsWith('.en.md')) { 'en' } else { 'zh' }
        $labelMapName = 'chapter_labels_' + $language
        $chapterLabels = $schema.PSObject.Properties[$labelMapName].Value
        foreach ($chapterId in $chapterIds) {
            $title = [string]$chapterLabels.PSObject.Properties[$chapterId].Value
            $heading = '### {0}. {1}' -f $chapterId, $title
            if (-not ($lines -contains $heading)) {
                $failures.Add(('Structure manual {0} is missing heading: {1}' -f $rel, $heading))
            }
        }

        $segmentPattern = [string]$schema.branch_segment_pattern
        $segmentPattern = $segmentPattern.Trim('^').Trim('$')
        $branchPattern = '^[A-F]/' + $segmentPattern + '(?:/' + $segmentPattern + ')*$'
        $currentChapter = $null
        $seenIds = @{}
        for ($i = 0; $i -lt $lines.Count; $i++) {
            $line = $lines[$i]
            if ($line -match '^### ([A-F])\. ') {
                $currentChapter = $matches[1]
                continue
            }
            if (-not $line.StartsWith('- S-')) { continue }
            $lineNo = $i + 1
            $parts = @($line -split '\|' | ForEach-Object { $_.Trim() })
            if ($parts.Count -ne 10) {
                $failures.Add(('{0}:{1}: structural entry must contain 10 fields' -f $rel, $lineNo))
                continue
            }
            if ($parts[0] -notmatch '^-\s+S-([A-F])-\d{3}$') {
                $failures.Add(('{0}:{1}: invalid structural entry ID' -f $rel, $lineNo))
                continue
            }
            $entryChapter = $matches[1]
            $entryId = ($parts[0] -replace '^-\s+', '')
            if ($null -eq $currentChapter -or $entryChapter -ne $currentChapter) {
                $failures.Add(('{0}:{1}: structural entry is outside chapter {2}' -f $rel, $lineNo, $entryChapter))
            }
            if ($seenIds.ContainsKey($entryId)) {
                $failures.Add(('{0}:{1}: duplicate structural entry ID {2}' -f $rel, $lineNo, $entryId))
            } else {
                $seenIds[$entryId] = $true
            }
            if ($statusLabels -notcontains $parts[1]) {
                $failures.Add(('{0}:{1}: invalid structural status {2}' -f $rel, $lineNo, $parts[1]))
            }
            if ($injectionLabels -notcontains $parts[2]) {
                $failures.Add(('{0}:{1}: invalid injection level {2}' -f $rel, $lineNo, $parts[2]))
            }
            if (($pendingLabels -contains $parts[1]) -and ($detailedLabels -contains $parts[2])) {
                $failures.Add(('{0}:{1}: pending entry cannot use detailed injection' -f $rel, $lineNo))
            }
            if ($parts[3] -notmatch $branchPattern) {
                $failures.Add(('{0}:{1}: invalid primary branch {2}' -f $rel, $lineNo, $parts[3]))
            } elseif (($parts[3] -split '/')[0] -ne $entryChapter) {
                $failures.Add(('{0}:{1}: primary branch chapter mismatch' -f $rel, $lineNo))
            }
            foreach ($fieldIndex in @(4, 5, 6, 7, 8, 9)) {
                if ([string]::IsNullOrWhiteSpace($parts[$fieldIndex])) {
                    $failures.Add(('{0}:{1}: required structural field is empty' -f $rel, $lineNo))
                }
            }
            $note = ''
            for ($j = $i + 1; $j -lt [Math]::Min($i + 5, $lines.Count); $j++) {
                if (-not [string]::IsNullOrWhiteSpace($lines[$j])) {
                    $note = $lines[$j].Trim()
                    break
                }
            }
            if ($note -notmatch '^-\s*(?:区域关联|Region links)\s*[:：]\s*(.+)$') {
                $failures.Add(('{0}:{1}: entry is missing its region-link note' -f $rel, $lineNo))
            }
        }
    }
}

Test-StructureManuals -Root $root

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
    if ([string]::IsNullOrWhiteSpace($fields['description'])) {
        $failures.Add(('Frontmatter description missing in {0}' -f $Relative))
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

$binaryExtensions = @(
    '.7z', '.a', '.avi', '.bin', '.bmp', '.class', '.dll', '.docx', '.dylib',
    '.eot', '.exe', '.gif', '.gz', '.ico', '.jar', '.jpeg', '.jpg', '.lib',
    '.mkv', '.mov', '.mp3', '.mp4', '.o', '.otf', '.p12', '.pdf', '.pfx',
    '.png', '.pptx', '.pyc', '.pyo', '.rar', '.so', '.sqlite', '.sqlite3',
    '.tar', '.tgz', '.tif', '.tiff', '.ttf', '.wav', '.webm', '.webp', '.whl',
    '.woff', '.woff2', '.xlsx', '.zip'
)
$skipDirPattern = '(?:^|[\\/])(\.git|node_modules|bin|obj|dist|build|\.venv|__pycache__|\.vs|\.idea)(?:[\\/]|$)'

$textFiles = @(
    Get-ChildItem -LiteralPath $root -Recurse -File -Force -ErrorAction Stop |
        Where-Object {
            $relativePath = $_.FullName.Substring($root.Length).TrimStart([char[]]@('\', '/'))
            $relativeDir = [System.IO.Path]::GetDirectoryName($relativePath)
            ($binaryExtensions -notcontains $_.Extension.ToLowerInvariant()) -and
            ($relativeDir -notmatch $skipDirPattern)
        }
)

$utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
foreach ($file in $textFiles) {
    $rel = $file.FullName.Substring($root.Length).TrimStart([char[]]@('\', '/'))
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    if (($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) -or
        ($bytes.Length -ge 2 -and (($bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) -or ($bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF)))) {
        $failures.Add(('BOM found: {0}' -f $rel))
    }
    try {
        $text = $utf8Strict.GetString($bytes)
        if ($text.IndexOf([char]0) -ge 0) {
            $failures.Add(('NUL byte in text file: {0}' -f $rel))
        }
    } catch {
        $failures.Add(('Not valid UTF-8: {0}' -f $rel))
    }
}

$mdFiles = @(
    $textFiles | Where-Object { $_.Extension.ToLowerInvariant() -eq '.md' }
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

$pitfallsPath = Join-Path $root 'PITFALLS.md'
if (Test-Path -LiteralPath $pitfallsPath) {
    $pitfallLine = 0
    foreach ($line in [System.IO.File]::ReadAllLines($pitfallsPath, [System.Text.Encoding]::UTF8)) {
        $pitfallLine++
        if ($line -match '^(?:-\s+)?\d{4}-\d{2}-\d{2}\s+\|') {
            $fields = @($line -split '\|' | ForEach-Object { $_.Trim() })
            if ($fields.Count -ne 6) {
                $failures.Add(('PITFALLS entry must contain exactly 6 fields: PITFALLS.md:{0}' -f $pitfallLine))
            } elseif (@($fields | Where-Object { [string]::IsNullOrWhiteSpace($_) }).Count -gt 0) {
                $failures.Add(('PITFALLS entry fields must not be empty: PITFALLS.md:{0}' -f $pitfallLine))
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
