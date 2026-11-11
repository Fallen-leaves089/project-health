# Read-only smoke checks for the Windows Server section in references/windows-pitfalls.md.
# This script does not change services, firewall rules, permissions, registry values,
# scheduled tasks, or cluster state. Role-specific commands are skipped when the role
# or module is not installed on the runner.
$ErrorActionPreference = 'Stop'

$script:Pass = 0
$script:Skip = 0
$script:Fail = 0

function Show-Output {
    param($InputObject)
    $text = $InputObject | Out-String -Width 240
    $text -split "`r?`n" | Select-Object -First 20 | ForEach-Object { Write-Output $_ }
}

function Invoke-Check {
    param(
        [string]$Name,
        [scriptblock]$Action,
        [switch]$Optional
    )
    Write-Output "RUN  $Name"
    try {
        $result = & $Action 2>&1
        Show-Output $result
        $script:Pass++
    } catch {
        if ($Optional) {
            Write-Output "SKIP $Name : $($_.Exception.Message)"
            $script:Skip++
        } else {
            Write-Output "FAIL $Name : $($_.Exception.Message)"
            $script:Fail++
        }
    }
}

function Invoke-ExternalCheck {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [switch]$Optional
    )
    Write-Output "RUN  $Name"
    try {
        $result = & $FilePath @Arguments 2>&1
        $code = $LASTEXITCODE
        Show-Output $result
        if ($code -ne 0) {
            throw "$FilePath exited with code $code"
        }
        $script:Pass++
    } catch {
        if ($Optional) {
            Write-Output "SKIP $Name : $($_.Exception.Message)"
            $script:Skip++
        } else {
            Write-Output "FAIL $Name : $($_.Exception.Message)"
            $script:Fail++
        }
    }
}

function Skip-Check {
    param([string]$Name, [string]$Reason)
    Write-Output "SKIP $Name : $Reason"
    $script:Skip++
}

$os = Get-CimInstance Win32_OperatingSystem
$isServer = $os.ProductType -ne 1
if ($env:REQUIRE_WINDOWS_SERVER -eq '1' -and -not $isServer) {
    Write-Output 'FAIL This validation run requires Windows Server, but ProductType indicates a client OS.'
    exit 1
}

Invoke-Check 'OS information' {
    $os | Select-Object Caption, Version, BuildNumber, ProductType, OSArchitecture
}
Write-Output "Windows Server: $isServer"
Invoke-Check 'PowerShell version' {
    $PSVersionTable | Select-Object PSVersion, PSEdition
}
Invoke-Check 'running services' {
    Get-Service | Where-Object Status -eq 'Running' | Select-Object -First 15 Name, DisplayName
}

if (Get-Module -ListAvailable -Name ServerManager) {
    Import-Module ServerManager
    Invoke-Check 'installed Windows features' {
        Get-WindowsFeature | Where-Object Installed | Select-Object -First 20 Name, DisplayName
    }
} else {
    Skip-Check 'installed Windows features' 'ServerManager module is not installed'
}

if (Get-Module -ListAvailable -Name WebAdministration) {
    Import-Module WebAdministration
    Invoke-Check 'IIS websites' {
        Get-Website | Select-Object -First 10 Name, State, PhysicalPath, Bindings
    }
    Invoke-Check 'IIS application pools' {
        Get-WebConfigurationProperty -PSPath 'IIS:\' -Filter 'system.applicationHost/applicationPools' -Name '.' |
            Select-Object -First 5
    }
} else {
    Skip-Check 'IIS websites and pools' 'WebAdministration module is not installed'
}
Invoke-ExternalCheck 'netsh HTTP SSL bindings' 'netsh.exe' @('http', 'show', 'sslcert')
Invoke-ExternalCheck 'netsh URL ACLs' 'netsh.exe' @('http', 'show', 'urlacl')

Invoke-ExternalCheck 'service configuration' 'sc.exe' @('qc', 'W32Time')
Invoke-ExternalCheck 'service failure actions' 'sc.exe' @('qfailure', 'W32Time')
Invoke-Check 'service CIM details' {
    Get-CimInstance Win32_Service -Filter "Name='W32Time'" |
        Select-Object Name, State, StartMode, StartName, PathName
}
Invoke-Check 'System event log' {
    Get-WinEvent -LogName System -MaxEvents 10 |
        Where-Object { $_.ProviderName -match 'W32Time|Time' } |
        Select-Object -First 5 TimeCreated, ProviderName, Id, LevelDisplayName
}

Invoke-ExternalCheck 'NTFS ACL' 'icacls.exe' @($env:SystemRoot)
Invoke-Check 'ACL object' { Get-Acl -LiteralPath $env:SystemRoot | Format-List }
Invoke-Check 'SMB shares' { Get-SmbShare | Select-Object -First 10 Name, Path, Description } -Optional
Invoke-Check 'SMB share access' { Get-SmbShareAccess -Name 'ADMIN$' | Select-Object -First 10 } -Optional
Invoke-Check 'SMB sessions' { Get-SmbSession | Select-Object -First 10 } -Optional

Invoke-Check 'firewall profiles' {
    Get-NetFirewallProfile | Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction
}
Invoke-Check 'enabled inbound firewall rules' {
    Get-NetFirewallRule -Enabled True -Direction Inbound | Select-Object -First 15 DisplayName, Profile, Action
}
Invoke-Check 'listening TCP sockets' {
    Get-NetTCPConnection -State Listen | Select-Object -First 15 LocalAddress, LocalPort, OwningProcess
}
Invoke-Check 'localhost port probe' {
    Test-NetConnection -ComputerName localhost -Port 445 -InformationLevel Quiet
}
Invoke-ExternalCheck 'WinHTTP proxy' 'netsh.exe' @('winhttp', 'show', 'proxy')

Invoke-Check 'machine certificates' {
    Get-ChildItem Cert:\LocalMachine\My | Select-Object -First 10 Subject, NotAfter, Thumbprint
}

Invoke-ExternalCheck 'Kerberos tickets' 'klist.exe' @() -Optional
Invoke-ExternalCheck 'Windows Time status' 'w32tm.exe' @('/query', '/status') -Optional
if ($env:USERDNSDOMAIN) {
    Invoke-ExternalCheck 'domain controller lookup' 'nltest.exe' @("/dsgetdc:$env:USERDNSDOMAIN") -Optional
    Invoke-ExternalCheck 'group policy result' 'gpresult.exe' @('/r') -Optional
} else {
    Skip-Check 'domain controller lookup' 'this host is not joined to a domain'
    Skip-Check 'group policy result' 'this host is not joined to a domain'
}
Skip-Check 'SPN lookup' 'requires a specific domain account; run read-only on the target host'

Invoke-Check 'SQL Server services' {
    Get-Service -Name 'MSSQL*' -ErrorAction SilentlyContinue | Select-Object Name, Status, StartType
}
Invoke-Check 'SQL Server ports' {
    Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 1433, 1434 |
        Select-Object LocalAddress, LocalPort, OwningProcess
}
if (Get-Command sqlcmd.exe -ErrorAction SilentlyContinue) {
    Invoke-ExternalCheck 'sqlcmd help' 'sqlcmd.exe' @('-?') -Optional
} else {
    Skip-Check 'sqlcmd help' 'sqlcmd is not installed'
}

Invoke-Check 'PowerShell execution policy' { Get-ExecutionPolicy -List }
if (Get-Command winrm.exe -ErrorAction SilentlyContinue) {
    Invoke-ExternalCheck 'WinRM listeners' 'winrm.exe' @('enumerate', 'winrm/config/listener') -Optional
} else {
    Skip-Check 'WinRM listeners' 'winrm is not installed'
}
Invoke-Check 'WinRM management test' { Test-WSMan -ComputerName localhost } -Optional

Invoke-Check 'installed hotfixes' {
    Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 HotFixID, InstalledOn
}
Invoke-Check 'Quick Fix Engineering records' {
    Get-CimInstance Win32_QuickFixEngineering | Sort-Object InstalledOn -Descending |
        Select-Object -First 10 HotFixID, InstalledOn
}

Invoke-Check 'scheduled tasks' {
    Get-ScheduledTask | Where-Object TaskName -match 'Time' | Select-Object -First 10 TaskName, State, Principal
}
Invoke-ExternalCheck 'scheduled task query' 'schtasks.exe' @(
    '/query', '/tn', '\Microsoft\Windows\Time Synchronization\SynchronizeTime', '/v', '/fo', 'LIST'
) -Optional

if (Get-Module -ListAvailable -Name FailoverClusters) {
    Import-Module FailoverClusters
    Invoke-Check 'failover cluster nodes' { Get-ClusterNode | Select-Object -First 20 } -Optional
    Invoke-Check 'failover cluster quorum' { Get-ClusterQuorum | Format-List } -Optional
} else {
    Skip-Check 'failover cluster checks' 'FailoverClusters module is not installed'
}

Write-Output "RESULT pass=$script:Pass skip=$script:Skip fail=$script:Fail windows_server=$isServer"
if ($script:Fail -ne 0) {
    exit 1
}
