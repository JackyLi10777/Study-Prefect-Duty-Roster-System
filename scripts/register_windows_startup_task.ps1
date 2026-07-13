[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$ProjectRoot = "",
    [string]$TaskName = "Sing Yin Roster Host",
    [string]$RuntimeUser = "SingYinRosterSvc",
    [switch]$AtStartup
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "windows_host_common.ps1")

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = Split-Path -Parent $PSScriptRoot }

$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$runtimeAccount = Get-SingYinRuntimeAccount -UserName $RuntimeUser
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw ".venv is missing. Run scripts\prepare_windows_host.ps1 first."
}

$action = New-ScheduledTaskAction -Execute $python -Argument "-X utf8 -m nicegui_app.main" -WorkingDirectory $ProjectRoot
$taskDescription = "Starts the local Sing Yin NiceGUI roster host. $script:SingYinTaskOwnerMarker"
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

if (-not $PSCmdlet.ShouldProcess($TaskName, "Register and start Windows scheduled task")) { return }

$inspection = Get-SingYinTaskInspection -TaskName $TaskName -ProjectRoot $ProjectRoot -RuntimeUser $runtimeAccount.Name
if ($inspection.Exists -and -not $inspection.Owned) {
    throw "A same-named Windows task already exists but is not owned by this project and runtime account."
}

if ($AtStartup) {
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $trigger.Delay = "PT30S"
    Write-Host "Windows needs the dedicated-host account password once to store this startup task securely." -ForegroundColor Yellow
    $credential = Get-Credential -UserName $runtimeAccount.QualifiedName -Message "Sing Yin roster runtime account"
    $credentialSid = Resolve-SingYinIdentitySid -Identity $credential.UserName
    if ($credentialSid.Value -cne $runtimeAccount.Sid.Value) {
        throw "The credential must belong to the configured Sing Yin runtime account."
    }
    $plainPassword = $credential.GetNetworkCredential().Password
    try {
        $register = @{
            TaskName = $TaskName
            Action = $action
            Trigger = $trigger
            Settings = $settings
            User = $runtimeAccount.QualifiedName
            Password = $plainPassword
            Description = $taskDescription
        }
        if ($inspection.Exists) { $register.Force = $true }
        Register-ScheduledTask @register | Out-Null
    } finally {
        $plainPassword = $null
        $credential = $null
    }
} else {
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $runtimeAccount.QualifiedName
    $principal = New-ScheduledTaskPrincipal -UserId $runtimeAccount.QualifiedName -LogonType Interactive -RunLevel Limited
    $register = @{
        TaskName = $TaskName
        Action = $action
        Trigger = $trigger
        Settings = $settings
        Principal = $principal
        Description = $taskDescription
    }
    if ($inspection.Exists) { $register.Force = $true }
    Register-ScheduledTask @register | Out-Null
}

Start-ScheduledTask -TaskName $TaskName
Write-Host "Registered and started '$TaskName'." -ForegroundColor Green
Write-Host "Check: Invoke-RestMethod http://127.0.0.1:8080/healthz | Format-List"
