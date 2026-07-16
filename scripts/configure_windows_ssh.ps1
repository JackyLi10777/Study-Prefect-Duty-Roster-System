[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$AuthorizedPublicKeyPath,
    [string]$MaintenanceUser = $env:USERNAME,
    [string]$ClientProfilePath = $env:USERPROFILE,
    [string]$ReportPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated Administrator PowerShell."
    }
}

function Write-JsonReport {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Payload
    )
    if ([string]::IsNullOrWhiteSpace($ReportPath)) { return }
    $parent = Split-Path -Parent $ReportPath
    if ($parent) { $null = New-Item -ItemType Directory -Path $parent -Force }
    $json = $Payload | ConvertTo-Json -Depth 6
    [IO.File]::WriteAllText($ReportPath, $json, [Text.UTF8Encoding]::new($false))
}

function Set-RestrictedFileAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][Security.Principal.SecurityIdentifier[]]$AllowedSids,
        [Parameter(Mandatory = $true)][Security.Principal.SecurityIdentifier]$OwnerSid
    )
    $acl = New-Object Security.AccessControl.FileSecurity
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($sid in $AllowedSids) {
        $rule = New-Object Security.AccessControl.FileSystemAccessRule(
            $sid,
            [Security.AccessControl.FileSystemRights]::FullControl,
            [Security.AccessControl.AccessControlType]::Allow
        )
        $acl.AddAccessRule($rule)
    }
    $acl.SetOwner($OwnerSid)
    [IO.File]::SetAccessControl($Path, $acl)
}

function Test-LoopbackPort {
    param([int]$Port)
    $client = New-Object Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(5000, $false)) { return $false }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Get-ManagedClientConfig {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Existing,
        [Parameter(Mandatory = $true)][string]$UserName,
        [Parameter(Mandatory = $true)][string]$IdentityPath,
        [Parameter(Mandatory = $true)][string]$KnownHostsPath
    )
    $startMarker = "# BEGIN SING YIN ROSTER MANAGED SSH"
    $endMarker = "# END SING YIN ROSTER MANAGED SSH"
    $escapedStart = [Regex]::Escape($startMarker)
    $escapedEnd = [Regex]::Escape($endMarker)
    $cleaned = [Regex]::Replace(
        $Existing,
        "(?ms)^\s*$escapedStart.*?^\s*$escapedEnd\s*",
        ""
    ).TrimEnd()
    $identity = $IdentityPath.Replace("\", "/")
    $knownHosts = $KnownHostsPath.Replace("\", "/")
    $managed = @"
$startMarker
Host sing-yin-roster-host
    HostName 127.0.0.1
    Port 22
    User $UserName
    IdentityFile $identity
    IdentitiesOnly yes
    PreferredAuthentications publickey
    PasswordAuthentication no
    StrictHostKeyChecking yes
    UserKnownHostsFile $knownHosts
    ServerAliveInterval 60
    ServerAliveCountMax 3
$endMarker
"@
    if ([string]::IsNullOrWhiteSpace($cleaned)) { return "$managed`r`n" }
    return "$cleaned`r`n`r`n$managed`r`n"
}

Assert-Administrator
if ($env:OS -ne "Windows_NT") { throw "This installer is for Windows only." }
if ($MaintenanceUser -notmatch '^[A-Za-z0-9._-]+$') { throw "MaintenanceUser contains unsupported characters." }

$account = Get-LocalUser -Name $MaintenanceUser -ErrorAction Stop
if (-not $account.Enabled) { throw "The maintenance account is disabled." }
$administrators = Get-LocalGroupMember -Group "Administrators" -ErrorAction Stop
if (-not ($administrators | Where-Object { $_.SID -eq $account.SID })) {
    throw "The maintenance account must already be a local Administrator."
}

$AuthorizedPublicKeyPath = (Resolve-Path -LiteralPath $AuthorizedPublicKeyPath).Path
$ClientProfilePath = (Resolve-Path -LiteralPath $ClientProfilePath).Path
$publicKey = [IO.File]::ReadAllText($AuthorizedPublicKeyPath, [Text.Encoding]::UTF8).Trim()
if ($publicKey -notmatch '^ssh-ed25519 [A-Za-z0-9+/=]+(?:\s+[^\r\n]+)?$') {
    throw "Only one valid Ed25519 public key is accepted."
}

$programDataSsh = Join-Path $env:ProgramData "ssh"
$configPath = Join-Path $programDataSsh "sshd_config"
$backupPath = $null
$serviceWasRunning = $false
$report = @{
    status = "fail"
    maintenanceUser = $MaintenanceUser
    passwordAuthentication = $false
    listenAddresses = @("127.0.0.1", "::1")
    completedAt = $null
}

try {
    $capability = Get-WindowsCapability -Online -Name "OpenSSH.Server*"
    if (-not $capability -or $capability.State -ne "Installed") {
        $null = Add-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0"
        $capability = Get-WindowsCapability -Online -Name "OpenSSH.Server*"
        if (-not $capability -or $capability.State -ne "Installed") {
            throw "Windows did not install OpenSSH Server."
        }
    }

    $sshdExe = Join-Path $env:WINDIR "System32\OpenSSH\sshd.exe"
    $sshKeygen = Join-Path $env:WINDIR "System32\OpenSSH\ssh-keygen.exe"
    if (-not (Test-Path -LiteralPath $sshdExe -PathType Leaf)) { throw "sshd.exe is missing after installation." }
    if (-not (Test-Path -LiteralPath $sshKeygen -PathType Leaf)) { throw "ssh-keygen.exe is missing after installation." }

    $null = New-Item -ItemType Directory -Path $programDataSsh -Force
    & $sshKeygen -A
    if ($LASTEXITCODE -ne 0) { throw "Windows could not create the SSH host keys." }

    $service = Get-Service -Name "sshd" -ErrorAction Stop
    $serviceWasRunning = $service.Status -eq [ServiceProcess.ServiceControllerStatus]::Running
    if ($serviceWasRunning) {
        Stop-Service -Name "sshd" -Force
        $service.WaitForStatus([ServiceProcess.ServiceControllerStatus]::Stopped, [TimeSpan]::FromSeconds(20))
    }

    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        $backupDir = Join-Path $programDataSsh "sing-yin-backups"
        $null = New-Item -ItemType Directory -Path $backupDir -Force
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $backupPath = Join-Path $backupDir "sshd_config.$stamp.bak"
        Copy-Item -LiteralPath $configPath -Destination $backupPath
    }

    $authorizedKeysPath = Join-Path $programDataSsh "administrators_authorized_keys"
    $authorizedTemp = "$authorizedKeysPath.sing-yin.tmp"
    [IO.File]::WriteAllText($authorizedTemp, "$publicKey`r`n", [Text.ASCIIEncoding]::new())
    Move-Item -LiteralPath $authorizedTemp -Destination $authorizedKeysPath -Force

    $systemSid = New-Object Security.Principal.SecurityIdentifier("S-1-5-18")
    $administratorsSid = New-Object Security.Principal.SecurityIdentifier("S-1-5-32-544")
    foreach ($hostPrivateKey in Get-ChildItem -LiteralPath $programDataSsh -File |
        Where-Object { $_.Name -match '^ssh_host_(rsa|ecdsa|ed25519)_key$' }) {
        Set-RestrictedFileAcl -Path $hostPrivateKey.FullName `
            -AllowedSids @($systemSid, $administratorsSid) `
            -OwnerSid $administratorsSid
    }
    Set-RestrictedFileAcl -Path $authorizedKeysPath `
        -AllowedSids @($systemSid, $administratorsSid) `
        -OwnerSid $administratorsSid

    $config = @"
Port 22
AddressFamily any
ListenAddress 127.0.0.1
ListenAddress ::1
HostKey __PROGRAMDATA__/ssh/ssh_host_rsa_key
HostKey __PROGRAMDATA__/ssh/ssh_host_ecdsa_key
HostKey __PROGRAMDATA__/ssh/ssh_host_ed25519_key
SyslogFacility AUTH
LogLevel VERBOSE
LoginGraceTime 30
MaxAuthTries 3
PubkeyAuthentication yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
AllowUsers $MaintenanceUser
AllowAgentForwarding no
AllowTcpForwarding no
GatewayPorts no
PermitTunnel no
X11Forwarding no
ClientAliveInterval 120
ClientAliveCountMax 3
AuthorizedKeysFile .ssh/authorized_keys
Subsystem sftp sftp-server.exe

Match Group administrators
    AuthorizedKeysFile __PROGRAMDATA__/ssh/administrators_authorized_keys
"@
    $configTemp = "$configPath.sing-yin.tmp"
    [IO.File]::WriteAllText($configTemp, "$config`r`n", [Text.ASCIIEncoding]::new())
    & $sshdExe -t -f $configTemp
    if ($LASTEXITCODE -ne 0) { throw "The hardened sshd configuration did not validate." }
    Move-Item -LiteralPath $configTemp -Destination $configPath -Force

    $openSshRegistry = "HKLM:\SOFTWARE\OpenSSH"
    $null = New-Item -Path $openSshRegistry -Force
    Set-ItemProperty -Path $openSshRegistry `
        -Name "DefaultShell" `
        -Type String `
        -Value "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

    Get-NetFirewallRule -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like "*OpenSSH*" -or
            $_.DisplayName -like "*OpenSSH*"
        } |
        Disable-NetFirewallRule | Out-Null

    Set-Service -Name "sshd" -StartupType Automatic
    Start-Service -Name "sshd"
    (Get-Service -Name "sshd").WaitForStatus(
        [ServiceProcess.ServiceControllerStatus]::Running,
        [TimeSpan]::FromSeconds(20)
    )
    if (-not (Test-LoopbackPort -Port 22)) { throw "sshd started but loopback port 22 is unavailable." }

    $hostPublicKeyPath = Join-Path $programDataSsh "ssh_host_ed25519_key.pub"
    $hostPublicKey = [IO.File]::ReadAllText($hostPublicKeyPath, [Text.Encoding]::ASCII).Trim().Split(" ")
    if ($hostPublicKey.Count -lt 2 -or $hostPublicKey[0] -ne "ssh-ed25519") {
        throw "The local Ed25519 host key could not be read."
    }

    $clientSshDir = Join-Path $ClientProfilePath ".ssh"
    $null = New-Item -ItemType Directory -Path $clientSshDir -Force
    $knownHostsPath = Join-Path $clientSshDir "sing_yin_known_hosts"
    [IO.File]::WriteAllText(
        $knownHostsPath,
        "127.0.0.1 $($hostPublicKey[0]) $($hostPublicKey[1])`r`n",
        [Text.ASCIIEncoding]::new()
    )
    $identityPath = Join-Path $clientSshDir "sing_yin_codex_ed25519"
    if (-not (Test-Path -LiteralPath $identityPath -PathType Leaf)) {
        throw "The expected client private key is missing."
    }
    Set-RestrictedFileAcl -Path $identityPath `
        -AllowedSids @($account.SID, $systemSid) `
        -OwnerSid $account.SID
    $clientConfigPath = Join-Path $clientSshDir "config"
    $existingClientConfig = if (Test-Path -LiteralPath $clientConfigPath -PathType Leaf) {
        [IO.File]::ReadAllText($clientConfigPath, [Text.Encoding]::UTF8)
    } else {
        ""
    }
    $managedClientConfig = Get-ManagedClientConfig `
        -Existing $existingClientConfig `
        -UserName $MaintenanceUser `
        -IdentityPath $identityPath `
        -KnownHostsPath $knownHostsPath
    [IO.File]::WriteAllText($clientConfigPath, $managedClientConfig, [Text.UTF8Encoding]::new($false))

    $report.status = "pass"
    $report.serviceStatus = [string](Get-Service -Name "sshd").Status
    $report.serviceStartType = [string](Get-Service -Name "sshd").StartType
    $report.firewallPublicRuleEnabled = $false
    $report.clientAlias = "sing-yin-roster-host"
    $report.configBackupCreated = [bool]$backupPath
    $report.completedAt = (Get-Date).ToString("o")
    Write-JsonReport -Payload $report
} catch {
    $report.error = $_.Exception.Message
    $report.completedAt = (Get-Date).ToString("o")
    Write-JsonReport -Payload $report
    if ($backupPath -and (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
        Copy-Item -LiteralPath $backupPath -Destination $configPath -Force
    }
    if ($serviceWasRunning) {
        Start-Service -Name "sshd" -ErrorAction SilentlyContinue
    }
    throw
}
