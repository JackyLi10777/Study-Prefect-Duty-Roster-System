[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$RuntimeUser = "SingYinRosterSvc",
    [switch]$InstallPrerequisites,
    [switch]$IncludeDevelopmentTools
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "windows_host_common.ps1")

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = Split-Path -Parent $PSScriptRoot }

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Refresh-ProcessPath {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Require-Command([string]$Name, [string]$WingetId) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command }
    if (-not $InstallPrerequisites) {
        throw "$Name is not installed. Re-run this script with -InstallPrerequisites."
    }
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "Windows Package Manager (winget) is unavailable. Install App Installer from Microsoft Store first."
    }
    Write-Step "Installing $Name"
    & winget.exe install --id $WingetId --exact --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "winget could not install $Name (exit $LASTEXITCODE)." }
    Refresh-ProcessPath
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) { throw "$Name was installed but is not visible yet. Restart PowerShell and run the script again." }
    return $command
}

if ($env:OS -ne "Windows_NT") { throw "This installer is for Windows only." }
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
if ($ProjectRoot -match '(?i)\\(OneDrive|Dropbox|Google Drive)(\\|$)') {
    throw "Move the project out of a cloud-sync folder before installation. Recommended: C:\SingYinRoster."
}
$runtimeAccount = Get-SingYinRuntimeAccount -UserName $RuntimeUser

Write-Step "Checking Git and Python 3.12"
$null = Require-Command "git.exe" "Git.Git"
$pythonCommand = Get-Command py.exe -ErrorAction SilentlyContinue
$pythonPrefix = @("-V:3.12")
if ($pythonCommand) {
    & $pythonCommand.Source @pythonPrefix --version 2>$null
    if ($LASTEXITCODE -ne 0) { $pythonCommand = $null }
}
if (-not $pythonCommand) {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    $pythonPrefix = @()
    if ($pythonCommand) {
        $version = & $pythonCommand.Source --version 2>&1
        if ($LASTEXITCODE -ne 0 -or $version -notmatch '^Python 3\.12(?:\.|$)') { $pythonCommand = $null }
    }
}
if (-not $pythonCommand) {
    if (-not $InstallPrerequisites) { throw "Python 3.12 is not installed. Re-run with -InstallPrerequisites." }
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "Windows Package Manager (winget) is unavailable. Install App Installer from Microsoft Store first."
    }
    & winget.exe install --id Python.Python.3.12 --exact --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Python 3.12 installation failed (exit $LASTEXITCODE)." }
    Refresh-ProcessPath
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    $pythonPrefix = @()
    if (-not $pythonCommand) { throw "Python 3.12 was installed. Restart PowerShell and run this script again." }
}
& $pythonCommand.Source @pythonPrefix --version

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Step "Creating the project virtual environment"
    & $pythonCommand.Source @pythonPrefix -m venv (Join-Path $ProjectRoot ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Could not create .venv." }
}

Write-Step "Installing application packages"
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& $venvPython -m pip install --require-hashes -r (Join-Path $ProjectRoot "requirements.lock")
if ($LASTEXITCODE -ne 0) { throw "Application dependency installation failed." }
if ($IncludeDevelopmentTools) {
    & $venvPython -m pip install --require-hashes -r (Join-Path $ProjectRoot "requirements-dev.lock")
    if ($LASTEXITCODE -ne 0) { throw "Development dependency installation failed." }
    Write-Step "Installing the isolated Chromium browser used by release verification"
    & $venvPython -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "Playwright Chromium installation failed." }
}

Write-Step "Preparing local folders and environment file"
foreach ($relative in @("data\runtime", "data\backups", "logs")) {
    $null = New-Item -ItemType Directory -Path (Join-Path $ProjectRoot $relative) -Force
}
$envPath = Join-Path $ProjectRoot ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot ".env.example") -Destination $envPath
    Add-Content -LiteralPath $envPath -Encoding UTF8 -Value @"

# Created by scripts/prepare_windows_host.ps1
SING_YIN_OPEN_BROWSER=false
SING_YIN_LOG_DIR=$ProjectRoot\logs
"@
    Write-Host "Created .env in local-only mode." -ForegroundColor Green
} else {
    Write-Host "Existing .env was preserved." -ForegroundColor Yellow
}

Write-Step "Restricting local application data to the dedicated host account"
Grant-SingYinRuntimeReadAccess -Path $ProjectRoot -RuntimeUser $runtimeAccount.Name
Grant-SingYinVenvBasePythonReadAccess -ProjectRoot $ProjectRoot -RuntimeUser $runtimeAccount.Name
Grant-SingYinBatchLogonRight -RuntimeUser $runtimeAccount.Name
$sensitivePaths = @(
    $envPath,
    (Join-Path $ProjectRoot "data\runtime"),
    (Join-Path $ProjectRoot "data\backups"),
    (Join-Path $ProjectRoot "logs")
)
foreach ($sensitivePath in $sensitivePaths) {
    Protect-SingYinSensitivePath -Path $sensitivePath -RuntimeUser $runtimeAccount.Name
}
$aclState = Get-SingYinAclStatus -Paths $sensitivePaths -RequiredIdentitySid $runtimeAccount.Sid.Value
if (-not $aclState.Compliant) { throw "Local data permissions could not be restricted safely." }

Write-Step "Running safe import and deployment checks"
Push-Location $ProjectRoot
try {
    & $venvPython -X utf8 -c "import nicegui; import nicegui_app.main; print('NiceGUI application imports passed')"
    if ($LASTEXITCODE -ne 0) { throw "Application import check failed." }
    & $venvPython -X utf8 scripts\check_deployment_readiness.py
    if ($LASTEXITCODE -ne 0) { throw "Deployment readiness check failed." }
} finally {
    Pop-Location
}

Write-Host "`nWindows host preparation completed." -ForegroundColor Green
Write-Host "Next: double-click START_SING_YIN_ROSTER.cmd, or register the startup task with scripts\register_windows_startup_task.ps1."
