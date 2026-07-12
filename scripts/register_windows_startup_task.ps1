[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$ProjectRoot = "",
    [string]$TaskName = "Sing Yin Roster Host",
    [switch]$AtStartup
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "windows_host_common.ps1")

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = Split-Path -Parent $PSScriptRoot }

$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
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

if ($AtStartup) {
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $trigger.Delay = "PT30S"
    Write-Host "Windows needs the dedicated-host account password once to store this startup task securely." -ForegroundColor Yellow
    $credential = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message "Dedicated Windows host account"
    $plainPassword = $credential.GetNetworkCredential().Password
    try {
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
            -User $credential.UserName -Password $plainPassword -Description $taskDescription -Force | Out-Null
    } finally {
        $plainPassword = $null
        $credential = $null
    }
} else {
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
        -Principal $principal -Description $taskDescription -Force | Out-Null
}

Start-ScheduledTask -TaskName $TaskName
Write-Host "Registered and started '$TaskName'." -ForegroundColor Green
Write-Host "Check: Invoke-RestMethod http://127.0.0.1:8080/healthz | Format-List"
