# AD Recon Scripts

 Lightweight scripts for AD reconnaissance:

- `recon.sh` — Bash script that performs nmap scans, SMB/LDAP checks, optional DNS/Amass enumeration, and gives hints for Impacket usage.
- `quickhost.ps1` — PowerShell script that collects concise host facts, scheduled tasks, shares, and optionally runs PowerView queries when `PowerView.ps1` is present.

## Required / recommended tools

### Linux attacker (recommended installs)

- `nmap` — host/service scans
- `enum4linux` — SMB/AD enumeration (legacy but useful)
- `smbmap` — quick share enumeration
- `ldap-utils` (`ldapsearch`) — LDAP queries
- `gobuster` — web dir brute force (optional)
- `amass` — passive/active DNS enumeration (optional)
- Impacket (python) — `GetUserSPNs.py`, `secretsdump.py` (optional but very useful)
- `crackmapexec` (CME) — quick lateral checks (optional)

### Windows host

- Optionally add `PowerView.ps1` (place next to `quickhost_fixed.ps1`) to enable extended AD queries.
