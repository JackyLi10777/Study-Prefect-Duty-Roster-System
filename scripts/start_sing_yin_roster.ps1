# Reliable double-click launcher for the local Sing Yin NiceGUI application.
#
# Exit codes:
#   0 = an existing Sing Yin service was opened successfully
#   1 = the application could not be started or did not become ready
#   2 = the child application stopped after it became ready

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$HostAddress = "127.0.0.1"
$DefaultPort = 8080
$PortScanCount = 19
$ReadinessTimeoutSeconds = 30
$LauncherMutexName = "Local\SingYinStudyPrefectDutyRosterLauncher"
$ExpectedApplicationMode = if ($env:SING_YIN_APP_MODE -eq "practice") { "practice" } else { "official" }

# This launcher is the explicit local-console entry point.  The controlled
# Windows service does not use this script and continues to require a signed
# Cloudflare gateway principal for every application request.
$env:SING_YIN_LOCAL_MAINTENANCE = "1"

function Get-ConfiguredPort {
    if ($env:SING_YIN_PORT -match "^\d+$") {
        return [int]$env:SING_YIN_PORT
    }

    $envFile = Join-Path $ProjectRoot ".env"
    if (Test-Path -LiteralPath $envFile) {
        $match = [regex]::Match((Get-Content -Raw -Encoding utf8 $envFile), "(?m)^\s*SING_YIN_PORT\s*=\s*(\d+)\s*(?:#.*)?$")
        if ($match.Success) {
            return [int]$match.Groups[1].Value
        }
    }

    return $DefaultPort
}

function Get-HttpResponse {
    param([int]$Port, [string]$Path = "/")

    $request = $null
    $response = $null
    $reader = $null
    try {
        $request = [System.Net.HttpWebRequest]::Create("http://$HostAddress`:$Port$Path")
        $request.Method = "GET"
        $request.Timeout = 900
        $request.ReadWriteTimeout = 900
        $request.AllowAutoRedirect = $false
        $response = $request.GetResponse()
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
        return [pscustomobject]@{
            StatusCode = [int]$response.StatusCode
            Body = $reader.ReadToEnd()
        }
    } catch [System.Net.WebException] {
        # A degraded Sing Yin health endpoint may deliberately return 503.
        # Preserve its identity response so the launcher does not start a
        # second process, while readiness below still requires a healthy 2xx.
        $errorResponse = $_.Exception.Response
        if ($null -eq $errorResponse) {
            return $null
        }
        $errorReader = $null
        try {
            $errorReader = New-Object System.IO.StreamReader($errorResponse.GetResponseStream())
            return [pscustomobject]@{
                StatusCode = [int]$errorResponse.StatusCode
                Body = $errorReader.ReadToEnd()
            }
        } finally {
            if ($errorReader) { $errorReader.Dispose() }
            $errorResponse.Close()
        }
    } catch {
        return $null
    } finally {
        if ($reader) { $reader.Dispose() }
        if ($response) { $response.Close() }
    }
}

function Test-SingYinApp {
    param([int]$Port)

    $response = Get-HttpResponse -Port $Port -Path "/healthz"
    if ($null -eq $response -or $response.StatusCode -lt 200 -or $response.StatusCode -ge 600) {
        return $false
    }

    # The health identity prevents the official launcher from opening a practice
    # service, or the practice launcher from opening the official workspace.
    try {
        $health = $response.Body | ConvertFrom-Json
        return $health.application -eq "sing-yin-roster" -and $health.applicationMode -eq $ExpectedApplicationMode
    } catch {
        return $false
    }
}

function Test-TcpPortInUse {
    param([int]$Port)

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync($HostAddress, $Port)
        return $task.Wait(150) -and $client.Connected
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Find-ExistingSingYinPort {
    param([int]$StartingPort)

    for ($port = $StartingPort; $port -le ($StartingPort + $PortScanCount); $port++) {
        # A TCP check avoids waiting for an HTTP timeout on unrelated services.
        if ((Test-TcpPortInUse -Port $port) -and (Test-SingYinApp -Port $port)) {
            return $port
        }
    }

    return $null
}

function Find-FreePort {
    param([int]$StartingPort)

    for ($port = $StartingPort; $port -le ($StartingPort + $PortScanCount); $port++) {
        if (-not (Test-TcpPortInUse -Port $port)) {
            return $port
        }
    }

    return $null
}

$launcherMutex = New-Object System.Threading.Mutex($false, $LauncherMutexName)
$ownsLauncherMutex = $false

try {
    $configuredPort = Get-ConfiguredPort
    if ($configuredPort -lt 1024 -or $configuredPort -gt 65500) {
        throw "SING_YIN_PORT must be between 1024 and 65500."
    }

    $virtualPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    $python = if (Test-Path -LiteralPath $virtualPython) {
        Get-Item -LiteralPath $virtualPython
    } else {
        Get-Command python.exe -ErrorAction SilentlyContinue
    }
    if ($null -eq $python) {
        throw "Python is not installed or is not available in PATH. Install Python 3.12, then run the setup in README.md."
    }

    Write-Host "Starting the Sing Yin Study Prefect Duty Roster System..."
    Write-Host "Checking for an existing local Sing Yin service..."

    $existingPort = Find-ExistingSingYinPort -StartingPort $configuredPort
    if ($null -ne $existingPort) {
        $existingUrl = "http://$HostAddress`:$existingPort"
        Write-Host "The system is already running at $existingUrl. Opening it instead of starting a second copy."
        Start-Process $existingUrl
        exit 0
    }

    try {
        $ownsLauncherMutex = $launcherMutex.WaitOne(0)
    } catch [System.Threading.AbandonedMutexException] {
        # The previous launcher crashed; the OS has released the mutex and this
        # process is now the safe owner.
        $ownsLauncherMutex = $true
    }

    if (-not $ownsLauncherMutex) {
        Write-Host "Another launcher is starting the system. Waiting for it to become ready..."
        $waitDeadline = (Get-Date).AddSeconds($ReadinessTimeoutSeconds)
        while ((Get-Date) -lt $waitDeadline) {
            Start-Sleep -Milliseconds 400
            $existingPort = Find-ExistingSingYinPort -StartingPort $configuredPort
            if ($null -ne $existingPort) {
                $existingUrl = "http://$HostAddress`:$existingPort"
                Write-Host "The system is ready at $existingUrl. Opening it instead of starting a second copy."
                Start-Process $existingUrl
                exit 0
            }
        }
        throw "Another launcher is active, but no Sing Yin service became ready within $ReadinessTimeoutSeconds seconds."
    }

    # Re-check after taking the mutex: another launcher may have won the race
    # just before this process acquired the lock.
    $existingPort = Find-ExistingSingYinPort -StartingPort $configuredPort
    if ($null -ne $existingPort) {
        $existingUrl = "http://$HostAddress`:$existingPort"
        Write-Host "The system is already running at $existingUrl. Opening it instead of starting a second copy."
        Start-Process $existingUrl
        exit 0
    }

    $selectedPort = Find-FreePort -StartingPort $configuredPort
    if ($null -eq $selectedPort) {
        throw "No free local port was found between $configuredPort and $($configuredPort + $PortScanCount). Close an unused local service and try again."
    }

    if ($selectedPort -ne $configuredPort) {
        Write-Host "Port $configuredPort is already in use by another program. Using free port $selectedPort instead."
    }

    $env:SING_YIN_PORT = [string]$selectedPort
    # The launcher opens the browser only after a real HTTP readiness check.
    $env:SING_YIN_OPEN_BROWSER = "false"
    $url = "http://$HostAddress`:$selectedPort"
    Write-Host "Starting NiceGUI on $url ..."

    $process = Start-Process `
        -FilePath $python.Source `
        -ArgumentList @("-X", "utf8", "-m", "nicegui_app.main") `
        -WorkingDirectory $ProjectRoot `
        -NoNewWindow `
        -PassThru

    $deadline = (Get-Date).AddSeconds($ReadinessTimeoutSeconds)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 400
        $process.Refresh()
        if ($process.HasExited) {
            throw "NiceGUI stopped before becoming ready (exit code $($process.ExitCode))."
        }
        $readyResponse = Get-HttpResponse -Port $selectedPort -Path "/healthz"
        if ($null -ne $readyResponse -and $readyResponse.StatusCode -ge 200 -and $readyResponse.StatusCode -lt 300 -and (Test-SingYinApp -Port $selectedPort)) {
            $ready = $true
            break
        }
    }

    if (-not $ready) {
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
        throw "NiceGUI did not become ready within $ReadinessTimeoutSeconds seconds. The application was stopped to avoid leaving a broken background process."
    }

    Write-Host "The system is ready. Opening $url"
    Start-Process $url
    Write-Host "Leave this window open while using the system."

    Wait-Process -Id $process.Id
    $process.Refresh()
    Write-Host "The Sing Yin system has stopped (exit code $($process.ExitCode))."
    exit 2
} catch {
    Write-Host ""
    Write-Host "STARTUP ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    if ($ownsLauncherMutex) {
        $launcherMutex.ReleaseMutex()
    }
    $launcherMutex.Dispose()
}
