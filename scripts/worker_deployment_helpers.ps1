Set-StrictMode -Version Latest

function ConvertFrom-WorkerSecretInventory {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Json)

    try {
        # Avoid @(... ConvertFrom-Json ...) here: Windows PowerShell 5.1 would
        # retain a top-level JSON array as one nested System.Object[] item.
        $configuredSecrets = ConvertFrom-Json -InputObject $Json
    } catch {
        throw "Wrangler secret inventory was not valid JSON."
    }

    $configuredNames = @()
    foreach ($entry in @($configuredSecrets)) {
        if ($null -eq $entry) { continue }
        $nameProperty = $entry.PSObject.Properties["name"]
        if ($null -eq $nameProperty) {
            throw "Wrangler secret inventory contained an invalid entry."
        }
        $name = [string]$nameProperty.Value
        if ($name -notmatch '^[A-Z][A-Z0-9_]{1,127}$') {
            throw "Wrangler secret inventory contained an invalid secret name."
        }
        $configuredNames += $name
    }
    return @($configuredNames | Select-Object -Unique)
}
