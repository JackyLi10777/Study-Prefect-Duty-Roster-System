# Pure evidence bridge. Dot-sourcing defines a function; it never deploys.
function Assert-ReleaseGateEvidence {
    param(
        [Parameter(Mandatory = $true)][string]$Python,
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string]$ReportPath
    )
    $previousPreference = $ErrorActionPreference
    Push-Location -LiteralPath $Repository
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& $Python -B -X utf8 -m nicegui_app.release_gates --report $ReportPath 2>&1)
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
        Pop-Location
    }
    if ($exitCode -ne 0) {
        throw "The source-owned release gate evidence is invalid."
    }
    return (($output | Out-String) | ConvertFrom-Json)
}
