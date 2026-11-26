<#
.SYNOPSIS
    Run the canonical Project Health package verifier.

.DESCRIPTION
    This is a thin Windows adapter. All package rules live in verify_package.py.
    Exit codes:
      0 = package passed
      1 = verification failed
      2 = usage or Python environment error
#>
[CmdletBinding()]
param(
    [string]$Path = ''
)

$ErrorActionPreference = 'Stop'

$scriptPath = $PSCommandPath
if ([string]::IsNullOrWhiteSpace($scriptPath)) {
    $scriptPath = $MyInvocation.MyCommand.Path
}
if ([string]::IsNullOrWhiteSpace($Path)) {
    $Path = Split-Path -Parent (Split-Path -Parent $scriptPath)
}
if (-not (Test-Path -LiteralPath $Path)) {
    Write-Host ('ERROR: path not found: {0}' -f $Path) -ForegroundColor Red
    exit 2
}

$root = (Get-Item -LiteralPath $Path -Force).FullName
$verifier = Join-Path $root 'scripts/verify_package.py'
if (-not (Test-Path -LiteralPath $verifier)) {
    Write-Host ('ERROR: missing Python verifier: {0}' -f $verifier) -ForegroundColor Red
    exit 2
}

$python = $null
$pythonPrefix = @()
foreach ($candidate in @('python', 'python3', 'py')) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        $python = $command.Source
        if ($candidate -eq 'py') {
            $pythonPrefix = @('-3')
        }
        break
    }
}
if ([string]::IsNullOrWhiteSpace($python)) {
    Write-Host 'ERROR: Python 3.9+ is required by the canonical verifier.' -ForegroundColor Red
    exit 2
}

$oldEncoding = $env:PYTHONIOENCODING
$oldUtf8 = $env:PYTHONUTF8
try {
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONUTF8 = '1'
    & $python @pythonPrefix -B $verifier --path $root
    $exitCode = $LASTEXITCODE
}
finally {
    $env:PYTHONIOENCODING = $oldEncoding
    $env:PYTHONUTF8 = $oldUtf8
}
exit $exitCode
