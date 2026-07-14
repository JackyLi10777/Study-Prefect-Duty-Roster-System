[CmdletBinding()]
param()

Set-StrictMode -Version Latest

$script:SingYinTaskOwnerMarker = "owner=sing-yin-roster-v1"

function Find-SingYinCloudflared {
    $command = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($path in @(
        "$env:ProgramFiles\cloudflared\cloudflared.exe",
        "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Links\cloudflared.exe"
    )) {
        if ($path -and (Test-Path -LiteralPath $path)) {
            return (Resolve-Path -LiteralPath $path).Path
        }
    }
    return $null
}

function Get-SingYinEnvironmentMap {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "The Sing Yin environment file is missing."
    }
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -notmatch '^\s*(?<name>SING_YIN_[A-Z0-9_]+)\s*=\s*(?<value>.*)$') { continue }
        $values[$Matches.name] = $Matches.value.Trim()
    }
    return $values
}

function Get-SingYinConfiguredEndpoint {
    param([Parameter(Mandatory = $true)][string]$EnvironmentPath)

    $values = Get-SingYinEnvironmentMap -Path $EnvironmentPath
    $hostName = if ($values.ContainsKey("SING_YIN_HOST")) { [string]$values["SING_YIN_HOST"] } else { "127.0.0.1" }
    if ($hostName -notin @("127.0.0.1", "localhost", "::1")) {
        throw "The NiceGUI host must remain loopback-only."
    }
    $rawPort = if ($values.ContainsKey("SING_YIN_PORT")) { [string]$values["SING_YIN_PORT"] } else { "8080" }
    $port = 0
    if (-not [int]::TryParse($rawPort, [ref]$port) -or $port -lt 1024 -or $port -gt 65535) {
        throw "The NiceGUI port must be between 1024 and 65535."
    }
    $mode = if ($values.ContainsKey("SING_YIN_DEPLOYMENT_MODE")) {
        ([string]$values["SING_YIN_DEPLOYMENT_MODE"]).ToLowerInvariant()
    } else {
        "local"
    }
    if ($mode -notin @("local", "server")) { throw "The deployment mode must be local or server." }
    return [pscustomobject]@{ Host = $hostName; Port = $port; Mode = $mode; Values = $values }
}

function Test-SingYinAccessRedirect {
    param(
        [Parameter(Mandatory = $true)][string]$Location,
        [Parameter(Mandatory = $true)][string]$TeamDomain
    )

    $expectedHost = $TeamDomain.Trim().ToLowerInvariant().TrimEnd('.')
    if ($expectedHost -notmatch '^[a-z0-9.-]+\.cloudflareaccess\.com$') { return $false }
    try { $uri = [Uri]$Location } catch { return $false }
    if (-not $uri.IsAbsoluteUri -or $uri.Scheme -cne "https") { return $false }
    if ($uri.DnsSafeHost.ToLowerInvariant().TrimEnd('.') -cne $expectedHost) { return $false }
    return $uri.AbsolutePath.StartsWith("/cdn-cgi/access/", [StringComparison]::OrdinalIgnoreCase)
}

function Get-SingYinTaskInspection {
    param(
        [Parameter(Mandatory = $true)][string]$TaskName,
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [string]$RuntimeUser = ""
    )

    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        return [pscustomobject]@{ Exists = $false; Owned = $false; State = "missing" }
    }
    $expectedRoot = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
    $expectedPython = [IO.Path]::GetFullPath((Join-Path $expectedRoot ".venv\Scripts\python.exe"))
    $matchingAction = @($task.Actions) | Where-Object {
        try {
            [IO.Path]::GetFullPath([string]$_.Execute) -ieq $expectedPython -and
            [IO.Path]::GetFullPath([string]$_.WorkingDirectory).TrimEnd('\') -ieq $expectedRoot -and
            ([string]$_.Arguments).Trim() -ceq "-X utf8 -m nicegui_app.main"
        } catch { $false }
    } | Select-Object -First 1
    $principalOwned = $true
    if (-not [string]::IsNullOrWhiteSpace($RuntimeUser)) {
        try {
            $runtimeAccount = Get-SingYinRuntimeAccount -UserName $RuntimeUser
            $taskSid = Resolve-SingYinIdentitySid -Identity ([string]$task.Principal.UserId)
            $principalOwned = $taskSid.Value -ceq $runtimeAccount.Sid.Value
        } catch {
            $principalOwned = $false
        }
    }
    $description = [string]$task.Description
    $owned = [bool]$matchingAction -and $principalOwned -and $description.Contains($script:SingYinTaskOwnerMarker)
    return [pscustomobject]@{
        Exists = $true
        Owned = $owned
        State = [string]$task.State
        Principal = [string]$task.Principal.UserId
    }
}

function Resolve-SingYinIdentitySid {
    param([Parameter(Mandatory = $true)][string]$Identity)

    if ($Identity -match '^S-1-') {
        return [Security.Principal.SecurityIdentifier]::new($Identity)
    }
    try {
        return [Security.Principal.NTAccount]::new($Identity).Translate(
            [Security.Principal.SecurityIdentifier]
        )
    } catch {
        throw "Windows could not resolve the configured runtime identity."
    }
}

function Get-SingYinRuntimeAccount {
    param([Parameter(Mandatory = $true)][string]$UserName)

    $trimmed = $UserName.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed -match '[\\/@]') {
        throw "RuntimeUser must be the name of one local Windows account."
    }
    $user = Get-LocalUser -Name $trimmed -ErrorAction SilentlyContinue
    if (-not $user) { throw "The configured Sing Yin runtime account does not exist." }
    if (-not $user.Enabled) { throw "The configured Sing Yin runtime account is disabled." }

    $qualifiedName = "$env:COMPUTERNAME\$($user.Name)"
    $sid = Resolve-SingYinIdentitySid -Identity $qualifiedName
    $administrators = Get-LocalGroup -SID "S-1-5-32-544"
    $administratorSids = @(
        Get-LocalGroupMember -Group $administrators.Name -ErrorAction SilentlyContinue |
            ForEach-Object { $_.SID.Value }
    )
    if ($sid.Value -in $administratorSids) {
        throw "The Sing Yin runtime account must remain a standard user, not an administrator."
    }
    return [pscustomobject]@{
        Name = [string]$user.Name
        QualifiedName = $qualifiedName
        Sid = $sid
    }
}

function Grant-SingYinRuntimeReadAccess {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$RuntimeUser
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "The project root is unavailable for runtime access."
    }
    $runtimeAccount = Get-SingYinRuntimeAccount -UserName $RuntimeUser
    $acl = Get-Acl -LiteralPath $Path
    $rule = [Security.AccessControl.FileSystemAccessRule]::new(
        $runtimeAccount.Sid,
        [Security.AccessControl.FileSystemRights]::ReadAndExecute,
        [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
            [Security.AccessControl.InheritanceFlags]::ObjectInherit,
        [Security.AccessControl.PropagationFlags]::None,
        [Security.AccessControl.AccessControlType]::Allow
    )
    $acl.SetAccessRule($rule)
    Set-Acl -LiteralPath $Path -AclObject $acl
}

function Grant-SingYinVenvBasePythonReadAccess {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$RuntimeUser
    )

    $venvConfigPath = Join-Path $ProjectRoot ".venv\pyvenv.cfg"
    if (-not (Test-Path -LiteralPath $venvConfigPath -PathType Leaf)) {
        throw "The virtual environment configuration is missing."
    }
    $homeLine = Get-Content -LiteralPath $venvConfigPath |
        Where-Object { $_ -match '^home\s*=' } |
        Select-Object -First 1
    if (-not $homeLine) { throw "The virtual environment does not declare its base Python location." }
    $pythonHome = ($homeLine -split '=', 2)[1].Trim()
    $resolvedPythonHome = (Resolve-Path -LiteralPath $pythonHome -ErrorAction Stop).Path
    $safePerUserPython = '^C:\\Users\\[^\\]+\\AppData\\Local\\Programs\\Python\\Python\d+$'
    $safeMachinePython = '^C:\\Program Files\\Python\d+$'
    if ($resolvedPythonHome -notmatch $safePerUserPython -and $resolvedPythonHome -notmatch $safeMachinePython) {
        throw "The virtual environment references an unexpected base Python location."
    }
    Grant-SingYinRuntimeReadAccess -Path $resolvedPythonHome -RuntimeUser $RuntimeUser
}

function Test-SingYinBatchLogonRight {
    param([Parameter(Mandatory = $true)][string]$RuntimeUser)

    $runtimeAccount = Get-SingYinRuntimeAccount -UserName $RuntimeUser
    $tempRoot = Join-Path $env:TEMP ("SingYinRoster-Rights-" + [guid]::NewGuid().ToString("N"))
    try {
        $null = New-Item -ItemType Directory -Path $tempRoot -Force
        $policyPath = Join-Path $tempRoot "rights.inf"
        & "$env:SystemRoot\System32\secedit.exe" /export /cfg $policyPath /areas USER_RIGHTS /quiet | Out-Null
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $policyPath)) {
            throw "Windows could not inspect the batch-logon policy."
        }
        $line = Get-Content -LiteralPath $policyPath |
            Where-Object { $_ -match '^SeBatchLogonRight\s*=' } |
            Select-Object -First 1
        return [bool]($line -and $line.Contains($runtimeAccount.Sid.Value))
    } finally {
        if (Test-Path -LiteralPath $tempRoot) {
            $resolvedTemp = (Resolve-Path -LiteralPath $tempRoot).Path
            $expectedPrefix = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\SingYinRoster-Rights-'
            if ($resolvedTemp.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
                Remove-Item -LiteralPath $resolvedTemp -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Grant-SingYinBatchLogonRight {
    param([Parameter(Mandatory = $true)][string]$RuntimeUser)

    if (Test-SingYinBatchLogonRight -RuntimeUser $RuntimeUser) { return }
    $runtimeAccount = Get-SingYinRuntimeAccount -UserName $RuntimeUser
    if (-not ("SingYinBatchLogonRightsNative" -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Security.Principal;

public static class SingYinBatchLogonRightsNative
{
    [StructLayout(LayoutKind.Sequential)]
    private struct LSA_OBJECT_ATTRIBUTES
    {
        public int Length;
        public IntPtr RootDirectory;
        public IntPtr ObjectName;
        public uint Attributes;
        public IntPtr SecurityDescriptor;
        public IntPtr SecurityQualityOfService;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct LSA_UNICODE_STRING
    {
        public ushort Length;
        public ushort MaximumLength;
        public IntPtr Buffer;
    }

    [DllImport("advapi32.dll", PreserveSig = true)]
    private static extern uint LsaOpenPolicy(IntPtr systemName,
        ref LSA_OBJECT_ATTRIBUTES attributes, uint desiredAccess, out IntPtr policyHandle);

    [DllImport("advapi32.dll", PreserveSig = true)]
    private static extern uint LsaAddAccountRights(IntPtr policyHandle, IntPtr accountSid,
        LSA_UNICODE_STRING[] userRights, uint countOfRights);

    [DllImport("advapi32.dll")]
    private static extern uint LsaClose(IntPtr policyHandle);

    [DllImport("advapi32.dll")]
    private static extern uint LsaNtStatusToWinError(uint status);

    public static void Grant(string accountName, string rightName)
    {
        const uint POLICY_CREATE_ACCOUNT = 0x10;
        const uint POLICY_LOOKUP_NAMES = 0x800;
        var sid = (SecurityIdentifier)new NTAccount(accountName).Translate(typeof(SecurityIdentifier));
        var sidBytes = new byte[sid.BinaryLength];
        sid.GetBinaryForm(sidBytes, 0);
        var sidHandle = GCHandle.Alloc(sidBytes, GCHandleType.Pinned);
        IntPtr policyHandle = IntPtr.Zero;
        IntPtr rightBuffer = IntPtr.Zero;
        try
        {
            var attributes = new LSA_OBJECT_ATTRIBUTES();
            attributes.Length = Marshal.SizeOf(typeof(LSA_OBJECT_ATTRIBUTES));
            uint status = LsaOpenPolicy(IntPtr.Zero, ref attributes,
                POLICY_CREATE_ACCOUNT | POLICY_LOOKUP_NAMES, out policyHandle);
            if (status != 0) throw new Win32Exception((int)LsaNtStatusToWinError(status));
            rightBuffer = Marshal.StringToHGlobalUni(rightName);
            var right = new LSA_UNICODE_STRING {
                Buffer = rightBuffer,
                Length = checked((ushort)(rightName.Length * 2)),
                MaximumLength = checked((ushort)((rightName.Length + 1) * 2))
            };
            status = LsaAddAccountRights(policyHandle, sidHandle.AddrOfPinnedObject(),
                new[] { right }, 1);
            if (status != 0) throw new Win32Exception((int)LsaNtStatusToWinError(status));
        }
        finally
        {
            if (rightBuffer != IntPtr.Zero) Marshal.FreeHGlobal(rightBuffer);
            if (policyHandle != IntPtr.Zero) LsaClose(policyHandle);
            if (sidHandle.IsAllocated) sidHandle.Free();
        }
    }
}
'@
    }
    [SingYinBatchLogonRightsNative]::Grant($runtimeAccount.QualifiedName, "SeBatchLogonRight")
    if (-not (Test-SingYinBatchLogonRight -RuntimeUser $RuntimeUser)) {
        throw "Windows did not retain the required batch-logon right."
    }
}

function Protect-SingYinSensitivePath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$RuntimeUser = ""
    )

    if (-not (Test-Path -LiteralPath $Path)) { return }
    $item = Get-Item -LiteralPath $Path -Force
    $acl = Get-Acl -LiteralPath $item.FullName
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRuleAll($rule) }

    $inheritance = if ($item.PSIsContainer) {
        [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
        [Security.AccessControl.InheritanceFlags]::ObjectInherit
    } else {
        [Security.AccessControl.InheritanceFlags]::None
    }
    $propagation = [Security.AccessControl.PropagationFlags]::None
    $allow = [Security.AccessControl.AccessControlType]::Allow
    [Security.Principal.SecurityIdentifier]$runtimeSid = if ([string]::IsNullOrWhiteSpace($RuntimeUser)) {
        [Security.Principal.WindowsIdentity]::GetCurrent().User
    } else {
        (Get-SingYinRuntimeAccount -UserName $RuntimeUser).Sid
    }
    [Security.Principal.SecurityIdentifier]$systemSid =
        [Security.Principal.SecurityIdentifier]::new("S-1-5-18")
    [Security.Principal.SecurityIdentifier]$administratorsSid =
        [Security.Principal.SecurityIdentifier]::new("S-1-5-32-544")

    # Write each required ACE explicitly.  SetAccessRule is intentionally used
    # instead of an array-driven AddAccessRule loop: it replaces any stale ACE
    # for the same SID and behaves consistently in Windows PowerShell 5.1 on a
    # local host as well as on the GitHub hosted Windows runner.
    $runtimeRule = [Security.AccessControl.FileSystemAccessRule]::new(
        $runtimeSid,
        [Security.AccessControl.FileSystemRights]::Modify,
        $inheritance,
        $propagation,
        $allow
    )
    $systemRule = [Security.AccessControl.FileSystemAccessRule]::new(
        $systemSid,
        [Security.AccessControl.FileSystemRights]::FullControl,
        $inheritance,
        $propagation,
        $allow
    )
    $administratorsRule = [Security.AccessControl.FileSystemAccessRule]::new(
        $administratorsSid,
        [Security.AccessControl.FileSystemRights]::FullControl,
        $inheritance,
        $propagation,
        $allow
    )
    $acl.SetAccessRule($runtimeRule)
    $acl.SetAccessRule($systemRule)
    $acl.SetAccessRule($administratorsRule)
    Set-Acl -LiteralPath $item.FullName -AclObject $acl

    # ACL protection is a release safety boundary.  Re-read what Windows
    # actually retained and fail closed if any maintenance/runtime principal is
    # absent or if a broad write-capable principal survived canonicalisation.
    foreach ($requiredSid in @($runtimeSid.Value, $systemSid.Value, $administratorsSid.Value)) {
        $status = Get-SingYinAclStatus -Paths @($item.FullName) -RequiredIdentitySid $requiredSid
        if (-not $status.Compliant) {
            throw "Windows did not retain the required protected ACL for '$($item.FullName)'."
        }
    }
}

function Get-SingYinAclStatus {
    param(
        [Parameter(Mandatory = $true)][string[]]$Paths,
        [string]$RequiredIdentitySid = "",
        [Security.AccessControl.FileSystemRights]$RequiredRights =
            [Security.AccessControl.FileSystemRights]::Modify
    )

    $broadSids = @("S-1-1-0", "S-1-5-11", "S-1-5-32-545")
    $writeMask =
        [Security.AccessControl.FileSystemRights]::Write -bor
        [Security.AccessControl.FileSystemRights]::Modify -bor
        [Security.AccessControl.FileSystemRights]::FullControl -bor
        [Security.AccessControl.FileSystemRights]::CreateFiles -bor
        [Security.AccessControl.FileSystemRights]::WriteData
    $checked = 0
    $weak = 0
    $unprotected = 0
    $requiredIdentityMissing = 0
    $requiredIdentityInsufficient = 0
    foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $checked += 1
        $acl = Get-Acl -LiteralPath $path
        if (-not $acl.AreAccessRulesProtected) { $unprotected += 1 }
        $identityPresent = [string]::IsNullOrWhiteSpace($RequiredIdentitySid)
        $identitySufficient = $identityPresent
        # Request SID-backed rules directly.  Reading the convenience `.Access`
        # property asks Windows to translate every SID into an account name first;
        # ephemeral CI accounts (and renamed local accounts) can make that reverse
        # lookup fail even though the exact SID ACE is present on disk.
        $accessRules = $acl.GetAccessRules(
            $true,
            $true,
            [Security.Principal.SecurityIdentifier]
        )
        foreach ($rule in @($accessRules)) {
            if ($rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow) { continue }
            $sid = $rule.IdentityReference.Value
            if ($sid -ceq $RequiredIdentitySid) {
                $identityPresent = $true
                if (([int64]$rule.FileSystemRights -band [int64]$RequiredRights) -eq [int64]$RequiredRights) {
                    $identitySufficient = $true
                }
            }
            if ($sid -in $broadSids -and (([int64]$rule.FileSystemRights -band [int64]$writeMask) -ne 0)) {
                $weak += 1
                break
            }
        }
        if (-not $identityPresent) { $requiredIdentityMissing += 1 }
        elseif (-not $identitySufficient) { $requiredIdentityInsufficient += 1 }
    }
    return [pscustomobject]@{
        Checked = $checked
        Weak = $weak
        Unprotected = $unprotected
        RequiredIdentityMissing = $requiredIdentityMissing
        RequiredIdentityInsufficient = $requiredIdentityInsufficient
        Compliant = (
            $checked -gt 0 -and
            $weak -eq 0 -and
            $unprotected -eq 0 -and
            $requiredIdentityMissing -eq 0 -and
            $requiredIdentityInsufficient -eq 0
        )
    }
}
