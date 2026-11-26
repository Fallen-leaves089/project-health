<#
.SYNOPSIS
    Scan a skill package for personal paths, private addresses, and common secret patterns.

.DESCRIPTION
    Exit codes:
      0 = clean
      1 = findings or unscannable input
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
$binaryExtensions = @(
    '.7z', '.a', '.avi', '.bin', '.bmp', '.class', '.dll', '.docx', '.dylib',
    '.eot', '.exe', '.gif', '.gz', '.ico', '.jar', '.jpeg', '.jpg', '.lib',
    '.mkv', '.mov', '.mp3', '.mp4', '.o', '.otf', '.p12', '.pdf', '.pfx',
    '.png', '.pptx', '.pyc', '.pyo', '.rar', '.so', '.sqlite', '.sqlite3',
    '.tar', '.tgz', '.tif', '.tiff', '.ttf', '.wav', '.webm', '.webp', '.whl',
    '.woff', '.woff2', '.xlsx', '.zip'
)
$assignedSecretField = '(?:api[_-]?key|(?:client|signing|encryption)[_-]?(?:secret|key|token)|aws[_-]?secret[_-]?access[_-]?key|access[_-]?key(?:[_-]?id)?|secret[_-]?key|private[_-]?key|secret|(?:access|refresh|session|auth|bearer|id)[_-]?token|token|password|passwd|pwd|passphrase)'
$assignedSecretRegex = '(?i)(?<![A-Za-z0-9_])["'']?' + $assignedSecretField + '(?![A-Za-z0-9_])["'']?\s*[:=]\s*["'']?(?!<|\$|\{|%|\[|REDACTED|CHANGE_ME|example|placeholder|null|true|false|none|\*+)[A-Za-z0-9_\-\./+=$]{12,}'

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
        @{ Name = 'Windows user path (slash)'; Regex = '(?i)\b[A-Z]:/' + 'Users/(?!<)[^/\s"''`<>]+' },
        @{ Name = 'Unix home path'; Regex = '(?i)(?<![\w.])/' + 'home/(?!<)[^/\s"''`<>]+' },
        @{ Name = 'macOS user path'; Regex = '(?i)(?<![\w.])/' + 'Users/(?!(?:<|Shared\b|Guest\b))[^/\s"''`<>]+' },
        @{ Name = 'Private IPv4'; Regex = '\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b' },
        @{ Name = 'OpenAI-style key'; Regex = '\bsk-[A-Za-z0-9_-]{20,}\b' },
        @{ Name = 'GitHub token'; Regex = '\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b' },
        @{ Name = 'AWS access key'; Regex = '\bAKIA[0-9A-Z]{16}\b' },
        @{ Name = 'Private key block'; Regex = '-----BEGIN [A-Z ]*PRIVATE KEY-----' },
        @{ Name = 'Authorization bearer token'; Regex = '(?i)\bAuthorization\s*[:=]\s*Bearer\s+[A-Za-z0-9._~+/=-]{8,}' },
        @{ Name = 'Cookie header'; Regex = '(?i)\bCookie\s*:\s*[^;\r\n]{1,80}=[A-Za-z0-9._~+/=-]{8,}' },
        @{ Name = 'JWT'; Regex = '\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b' },
        @{ Name = 'Assigned secret'; Regex = $assignedSecretRegex }
    )

    for ($i = 0; $i -lt $Extra.Count; $i++) {
        $patterns += @{
            Name  = ('Extra pattern {0}' -f ($i + 1))
            Regex = [regex]::Escape($Extra[$i])
        }
    }

    return $patterns
}

function Test-PlausibleText {
    param([string]$Text)

    if ($Text.IndexOf([char]0) -ge 0) { return $false }
    if ($Text.Length -eq 0) { return $true }

    $bad = 0
    for ($i = 0; $i -lt $Text.Length; $i++) {
        $ch = $Text[$i]
        if ($ch -eq "`r" -or $ch -eq "`n" -or $ch -eq "`t") { continue }
        if ([char]::IsHighSurrogate($ch) -and ($i + 1) -lt $Text.Length -and [char]::IsLowSurrogate($Text[$i + 1])) {
            $i++
            continue
        }
        $category = [System.Globalization.CharUnicodeInfo]::GetUnicodeCategory($ch).ToString()
        if ($category -in @('Control', 'Surrogate', 'PrivateUse', 'OtherNotAssigned')) {
            $bad++
        }
    }
    return ($bad -le [Math]::Max(1, [int]($Text.Length / 50)))
}

function Get-TextAsciiScore {
    param([string]$Text)

    $score = 0
    foreach ($ch in $Text.ToCharArray()) {
        $code = [int]$ch
        if (($code -ge 32 -and $code -le 126) -or $code -eq 9 -or $code -eq 10 -or $code -eq 13) {
            $score++
        }
    }
    return $score
}

function Get-Utf16WithoutBomText {
    param(
        [byte[]]$Bytes,
        [System.Text.Encoding]$LittleEndian,
        [System.Text.Encoding]$BigEndian
    )

    if ($Bytes.Length -eq 0 -or ($Bytes.Length % 2) -ne 0) { return $null }

    $candidates = New-Object System.Collections.Generic.List[object]
    foreach ($entry in @(
        @{ Name = 'utf-16-le'; Encoding = $LittleEndian },
        @{ Name = 'utf-16-be'; Encoding = $BigEndian }
    )) {
        try { $candidate = $entry.Encoding.GetString($Bytes) } catch { continue }
        if (Test-PlausibleText -Text $candidate) {
            $candidates.Add([pscustomobject]@{ Name = $entry.Name; Text = $candidate }) | Out-Null
        }
    }
    if ($candidates.Count -eq 0) { return $null }

    $half = [int]($Bytes.Length / 2)
    $zeroFloor = [Math]::Max(2, [int]($half / 4))
    $evenZero = 0
    $oddZero = 0
    for ($i = 0; $i -lt $Bytes.Length; $i++) {
        if ($Bytes[$i] -eq 0) {
            if (($i % 2) -eq 0) { $evenZero++ } else { $oddZero++ }
        }
    }
    $le = $candidates | Where-Object { $_.Name -eq 'utf-16-le' } | Select-Object -First 1
    $be = $candidates | Where-Object { $_.Name -eq 'utf-16-be' } | Select-Object -First 1
    if ($oddZero -ge $zeroFloor -and $oddZero -gt ($evenZero * 2) -and $null -ne $le) { return $le.Text }
    if ($evenZero -ge $zeroFloor -and $evenZero -gt ($oddZero * 2) -and $null -ne $be) { return $be.Text }
    if ($candidates.Count -eq 1) { return $candidates[0].Text }
    if ($evenZero -eq 0 -and $oddZero -eq 0) {
        if ($null -ne $le -and ($null -eq $be -or (Get-TextAsciiScore -Text $le.Text) -gt ((Get-TextAsciiScore -Text $be.Text) * 2))) {
            return $le.Text
        }
        if ($null -ne $be -and ($null -eq $le -or (Get-TextAsciiScore -Text $be.Text) -gt ((Get-TextAsciiScore -Text $le.Text) * 2))) {
            return $be.Text
        }
    }
    return $null
}

function Invoke-RedactionScan {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [string[]]$Extra = @(),
        [switch]$Quiet
    )

    $rootItem = Get-Item -LiteralPath $Root -Force
    $isSingleFile = -not $rootItem.PSIsContainer
    if ($isSingleFile) {
        $rootFull = $rootItem.DirectoryName.TrimEnd([char[]]@('\', '/'))
    } else {
        $rootFull = $rootItem.FullName.TrimEnd([char[]]@('\', '/'))
    }
    $patterns = Get-ScanPatterns -Extra $Extra

    $skipDirPattern = '(?:^|[\\/])(\.git|node_modules|bin|obj|dist|build|\.venv|__pycache__|\.vs|\.idea)(?:[\\/]|$)'

    if ($isSingleFile) {
        $files = @($rootItem)
    } else {
        $files = @(
            Get-ChildItem -LiteralPath $rootFull -Recurse -File -Force -ErrorAction Stop |
                Where-Object {
                    $relativePath = $_.FullName.Substring($rootFull.Length).TrimStart([char[]]@('\', '/'))
                    $relativeDir = [System.IO.Path]::GetDirectoryName($relativePath)
                    ($relativeDir -notmatch $skipDirPattern)
                }
        )
    }

    $findings = New-Object System.Collections.Generic.List[string]
    $errors = New-Object System.Collections.Generic.List[string]
    $filesScanned = 0
    $filesSkippedBinary = 0
    $utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
    $utf16LeStrict = [System.Text.UnicodeEncoding]::new($false, $true, $true)
    $utf16BeStrict = [System.Text.UnicodeEncoding]::new($true, $true, $true)
    foreach ($file in $files) {
        $rel = $file.FullName.Substring($rootFull.Length).TrimStart([char[]]@('\', '/'))
        if ($binaryExtensions -contains $file.Extension.ToLowerInvariant()) {
            $filesSkippedBinary++
            continue
        }

        try {
            $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
            $text = $null
            if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
                try { $text = $utf8Strict.GetString($bytes).TrimStart([char]0xFEFF) } catch { $text = $null }
            } elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
                try { $text = $utf16LeStrict.GetString($bytes).TrimStart([char]0xFEFF) } catch { $text = $null }
            } elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF) {
                try { $text = $utf16BeStrict.GetString($bytes).TrimStart([char]0xFEFF) } catch { $text = $null }
            } else {
                $utf8Text = $null
                try { $utf8Text = $utf8Strict.GetString($bytes) } catch { $utf8Text = $null }
                if ($null -ne $utf8Text -and $utf8Text.IndexOf([char]0) -lt 0) {
                    $text = $utf8Text
                } else {
                    $utf16Text = Get-Utf16WithoutBomText -Bytes $bytes -LittleEndian $utf16LeStrict -BigEndian $utf16BeStrict
                    if ($null -ne $utf16Text) { $text = $utf16Text }
                    elseif ($null -ne $utf8Text) { $text = $utf8Text }
                }
            }

            if ($null -eq $text) {
                $errors.Add(('{0}: [unscannable file: not UTF-8/UTF-16 text]' -f $rel)) | Out-Null
                continue
            }
            if ($text.IndexOf([char]0) -ge 0) {
                $errors.Add(('{0}: [unscannable file: anomalous NUL byte]' -f $rel)) | Out-Null
                continue
            }
            $filesScanned++
            $lineNo = 0
            foreach ($line in [regex]::Split($text, '\r?\n')) {
                $lineNo++
                foreach ($p in $patterns) {
                    if ([regex]::IsMatch($line, $p.Regex)) {
                        $findings.Add(('{0}:{1}  [{2}]' -f $rel, $lineNo, $p.Name)) | Out-Null
                    }
                }
            }
        } catch {
            $errors.Add(('{0}: [unscannable file: read or decode failed]' -f $rel)) | Out-Null
        }
    }

    if (-not $Quiet) {
        foreach ($finding in $findings) {
            Write-Host $finding -ForegroundColor Yellow
        }
    }

    return [pscustomobject]@{
        Findings           = $findings
        FilesScanned       = $filesScanned
        FilesSkippedBinary = $filesSkippedBinary
        Errors             = $errors
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
    if ($result.Errors.Count -gt 0) {
        Write-Host ('SELF-TEST FAIL: {0} (unscannable files={1})' -f $Label, $result.Errors.Count) -ForegroundColor Red
        return $false
    }
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

        $secretValue = 'abcdefghijklmnopqrstuvwxyz'
        $dirtyFields = 'client_secret=' + $secretValue + "`naccess_token=" + $secretValue + "`nrefresh_token=" + $secretValue + "`nsecret=" + $secretValue
        [System.IO.File]::WriteAllText((Join-Path $temp 'dirty-fields.json'), $dirtyFields, [System.Text.UTF8Encoding]::new($false))

        $dirtyBearer = 'Authorization: Bearer ' + $secretValue
        [System.IO.File]::WriteAllText((Join-Path $temp 'dirty-bearer.txt'), $dirtyBearer, [System.Text.UTF8Encoding]::new($false))
        $dirtyCookie = 'Cookie: sessionid=' + $secretValue
        [System.IO.File]::WriteAllText((Join-Path $temp 'dirty-cookie.txt'), $dirtyCookie, [System.Text.UTF8Encoding]::new($false))
        $dirtyJwt = 'jwt_value ' + 'eyJhbGciOiJIUzI1NiJ9.' + $secretValue + '.' + $secretValue
        [System.IO.File]::WriteAllText((Join-Path $temp 'dirty-jwt.txt'), $dirtyJwt, [System.Text.UTF8Encoding]::new($false))

        [System.IO.File]::WriteAllText((Join-Path $temp '.env.local'), ('API_KEY=' + $secretValue), [System.Text.UTF8Encoding]::new($false))
        [System.IO.File]::WriteAllText((Join-Path $temp 'server.pem'), ('-----BEGIN ' + 'PRIVATE KEY-----'), [System.Text.UTF8Encoding]::new($false))
        $utf16Path = Join-Path $temp 'utf16-notes.txt'
        $utf16Bytes = [byte[]](0xFF, 0xFE) + [System.Text.Encoding]::Unicode.GetBytes(('password=' + $secretValue))
        [System.IO.File]::WriteAllBytes($utf16Path, $utf16Bytes)
        $dirtyMacPath = 'Path: /' + 'Users/example-user/private'
        [System.IO.File]::WriteAllText((Join-Path $temp 'dirty-macos-path.md'), $dirtyMacPath, [System.Text.UTF8Encoding]::new($false))

        $utf16NoBomPath = Join-Path $temp 'utf16-no-bom.txt'
        $utf16NoBomBytes = [System.Text.Encoding]::Unicode.GetBytes(('password=' + $secretValue))
        [System.IO.File]::WriteAllBytes($utf16NoBomPath, $utf16NoBomBytes)

        $utf16NoBomEmojiPath = Join-Path $temp 'utf16-no-bom-emoji.txt'
        $utf16NoBomEmojiBytes = [System.Text.Encoding]::Unicode.GetBytes(('password=' + $secretValue + [char]::ConvertFromUtf32(0x1F512)))
        [System.IO.File]::WriteAllBytes($utf16NoBomEmojiPath, $utf16NoBomEmojiBytes)

        $skipNameDir = Join-Path $temp 'skip-name'
        New-Item -ItemType Directory -Path $skipNameDir -Force | Out-Null
        [System.IO.File]::WriteAllText((Join-Path $skipNameDir 'build'), ('password=' + $secretValue), [System.Text.UTF8Encoding]::new($false))

        $binaryDir = Join-Path $temp 'binary-only'
        New-Item -ItemType Directory -Path $binaryDir -Force | Out-Null
        [System.IO.File]::WriteAllBytes((Join-Path $binaryDir 'image.png'), [byte[]](0x89, 0x50, 0x4E, 0x47, 0x00, 0x00))
        [System.IO.File]::WriteAllBytes((Join-Path $temp 'invalid.txt'), [byte[]](0xFF, 0x80, 0x6E, 0x6F, 0x74))
        [System.IO.File]::WriteAllBytes((Join-Path $temp 'invalid-bom.txt'), [byte[]](0xEF, 0xBB, 0xBF, 0xFF))
        [System.IO.File]::WriteAllBytes((Join-Path $temp 'nul-text.txt'), [byte[]](0x70, 0x72, 0x65, 0x66, 0x69, 0x78, 0x00, 0x73, 0x75, 0x66, 0x66, 0x69, 0x78))

        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'clean.md') -Extra @() -ShouldFind $false -Label 'clean sample passes') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-path.md') -Extra @() -ShouldFind $true -Label 'personal path is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-path-slash.md') -Extra @() -ShouldFind $true -Label 'personal path with slashes is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-key.md') -Extra @() -ShouldFind $true -Label 'secret-looking key is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-json-key.md') -Extra @() -ShouldFind $true -Label 'quoted JSON secret is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-bearer.txt') -Extra @() -ShouldFind $true -Label 'Authorization bearer token is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-cookie.txt') -Extra @() -ShouldFind $true -Label 'Cookie header is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-jwt.txt') -Extra @() -ShouldFind $true -Label 'JWT is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-ip.md') -Extra @() -ShouldFind $true -Label 'private IPv4 is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-extra.md') -Extra @('ACME-INTERNAL') -ShouldFind $true -Label 'extra literal pattern is caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-fields.json') -Extra @() -ShouldFind $true -Label 'prefixed secret fields are caught') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp '.env.local') -Extra @() -ShouldFind $true -Label '.env.local is scanned') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'server.pem') -Extra @() -ShouldFind $true -Label '.pem private key block is scanned') -and $ok
        $ok = (Test-ScanExpectation -Root $utf16Path -Extra @() -ShouldFind $true -Label 'UTF-16 text is scanned') -and $ok
        $ok = (Test-ScanExpectation -Root (Join-Path $temp 'dirty-macos-path.md') -Extra @() -ShouldFind $true -Label 'macOS user path is caught') -and $ok
        $ok = (Test-ScanExpectation -Root $utf16NoBomPath -Extra @() -ShouldFind $true -Label 'unambiguous UTF-16 without BOM is scanned') -and $ok
        $ok = (Test-ScanExpectation -Root $utf16NoBomEmojiPath -Extra @() -ShouldFind $true -Label 'UTF-16 without BOM with non-BMP text is scanned') -and $ok
        $ok = (Test-ScanExpectation -Root $skipNameDir -Extra @() -ShouldFind $true -Label 'a text file named build is still scanned') -and $ok

        $binaryScan = Invoke-RedactionScan -Root $binaryDir -Quiet
        if ($binaryScan.FilesScanned -ne 0 -or $binaryScan.FilesSkippedBinary -ne 1) {
            Write-Host ('SELF-TEST FAIL: binary file accounting is wrong (scanned={0}, skipped={1})' -f $binaryScan.FilesScanned, $binaryScan.FilesSkippedBinary) -ForegroundColor Red
            $ok = $false
        } else {
            Write-Host 'SELF-TEST OK: known binary files are reported as skipped' -ForegroundColor Green
        }

        $invalidScan = Invoke-RedactionScan -Root (Join-Path $temp 'invalid.txt') -Quiet
        if ($invalidScan.Errors.Count -eq 0) {
            Write-Host 'SELF-TEST FAIL: invalid text was silently skipped' -ForegroundColor Red
            $ok = $false
        } else {
            Write-Host 'SELF-TEST OK: invalid text fails closed' -ForegroundColor Green
        }

        $invalidBomScan = Invoke-RedactionScan -Root (Join-Path $temp 'invalid-bom.txt') -Quiet
        if ($invalidBomScan.Errors.Count -eq 0) {
            Write-Host 'SELF-TEST FAIL: invalid UTF-8 after BOM was silently accepted' -ForegroundColor Red
            $ok = $false
        } else {
            Write-Host 'SELF-TEST OK: invalid UTF-8 after BOM fails closed' -ForegroundColor Green
        }

        $nulScan = Invoke-RedactionScan -Root (Join-Path $temp 'nul-text.txt') -Quiet
        if ($nulScan.Errors.Count -eq 0) {
            Write-Host 'SELF-TEST FAIL: anomalous NUL text was silently scanned' -ForegroundColor Red
            $ok = $false
        } else {
            Write-Host 'SELF-TEST OK: anomalous NUL text fails closed' -ForegroundColor Green
        }

        $scriptsDir = Split-Path -Parent $scannerPath
        $selfScan = Invoke-RedactionScan -Root $scriptsDir -Quiet
        if ($selfScan.Findings.Count -gt 0 -or $selfScan.Errors.Count -gt 0) {
            Write-Host ('SELF-TEST FAIL: scripts directory contains {0} finding(s) and {1} error(s).' -f $selfScan.Findings.Count, $selfScan.Errors.Count) -ForegroundColor Red
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

Write-Host ('Scanned {0} file(s); {1} finding(s); {2} known binary file(s) skipped.' -f $result.FilesScanned, $result.Findings.Count, $result.FilesSkippedBinary)
if ($result.Errors.Count -gt 0) {
    foreach ($scanError in $result.Errors) {
        Write-Host $scanError -ForegroundColor Red
    }
    Write-Host 'REDACTION CHECK FAILED: unscannable files were found.' -ForegroundColor Red
    exit 1
}
if ($result.Findings.Count -gt 0) {
    Write-Host 'REDACTION CHECK FAILED: review the findings above.' -ForegroundColor Red
    exit 1
}
if ($result.FilesScanned -eq 0) {
    Write-Host 'REDACTION CHECK FAILED: no scannable text files were found.' -ForegroundColor Red
    exit 1
}

Write-Host 'REDACTION CHECK PASSED.' -ForegroundColor Green
exit 0
