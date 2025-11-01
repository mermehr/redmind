
# RedMind Technical Report — Active (HTB medium)
**Box:** Active · **IP:** 10.10.10.100 · **Domain:** active.htb · **OS:** Windows Server (AD)  
**Date (lab):** 2025-10-23

---

## Executive summary
Gained an initial foothold by recovering a Group Policy Preferences (GPP) cpassword from the SYSVOL share; the leaked secret allowed access to the `SVC_TGS` account. Using that account I enumerated users and services, requested service tickets for high-value accounts, captured krb5tgs service ticket hashes, and cracked them offline to recover Administrator credentials. Final result: `user.txt` and `root.txt` captured. Root cause: sensitive secrets stored in SYSVOL and over-exposed service principals.

- Foothold: GPP cpassword recovered from `Policies/.../Groups/Groups.xml` → `SVC_TGS:GPPstillStandingStrong2k18`.  
- Escalation: Kerberoast/TGS capture with offline cracking of `krb5tgs` hashes → Administrator creds recovered.  
- Impact: full domain/host compromise; exposure of privileged accounts and Kerberos service tickets.

---

## Attack chain summary
1. Recon - nmap and enum4linux to map services and shares.  
2. Foothold - enumerate SYSVOL/Shares; find GPP `Groups.xml` with `cpassword`.  
3. Lateral - authenticated SMB access as `SVC_TGS`; downloaded user desktop artifacts and enumerated domain users.  
4. Escalation - requested service tickets for accounts with SPNs; captured `krb5tgs` hashes and performed offline cracking.  
5. Admin takeover - used recovered Administrator credentials to obtain an admin shell and captured `root.txt`.

---

## Technical breakdown

### Recon and FS enumeration
Basic discovery with nmap and enum4linux revealed an Active Directory host with LDAP, SMB and RPC services; SYSVOL was readable from the unauthenticated SMB session.

Key scans:
```bash
sudo nmap -sC -sV -oN logs/nmap.initial 10.10.10.100
# enum4linux-ng -U 10.10.10.100
```

SYSVOL contents (snippets saved under `smb/active.htb/Policies/.../MACHINE/Preferences/Groups/Groups.xml`) contained Group Policy Preference XML entries with `cpassword` blobs.

### Foothold — GPP cpassword recovery
From the downloaded `Groups.xml` I extracted the `cpassword` value and used a GPP decrypt tool to reveal the plaintext:
```
SVC_TGS : GPPstillStandingStrong2k18
```
With those creds I authenticated to SMB:
```bash
smbclient //10.10.10.100/Users -U 'SVC_TGS%GPPstillStandingStrong2k18'
# downloaded desktop artifacts and collected user.txt
# saved file: hashes/10.10.10.100-Users_SVC_TGS_Desktop_user.txt (user flag)
```

User flag:
```
a95a2f3c71ad414ee65d3616fa663242
```

### Enumeration and ticket capture
After logging in as `SVC_TGS`, I enumerated domain users and service principals using Impacket tools. Then I requested service tickets for SPNs of interest and saved the resulting TGS hashes (krb5tgs) for offline cracking. The saved hashes are in `hashes/Administrator.krb5tgs-1` and `hashes/Administrator.krb5tgs-2`.

Sample (truncated) krb5tgs entry:
```
$krb5tgs$23$*Administrator$ACTIVE.HTB$active.htb/Administrator*$...
```

These hashes were cracked offline (tooling and wordlists adapted during the lab), which revealed Administrator password material. The presence of multiple krb5tgs captures suggests multiple ticket requests or encryption type variants.

### Admin takeover and proof
With the recovered Administrator credentials I authenticated to the host and captured the root flag:
```
root.txt : 25a9eb38a763d8a0f04af9a3fc390ee7
```

---

## Key findings and remediation summary
- Storing credentials in Group Policy Preferences is a known risk; remove cpassword entries from SYSVOL and rotate affected credentials immediately.  
- Audit service principals and SPN assignments; ensure Kerberos-exposed services do not use weak service account passwords and rotate them regularly.  
- Monitor for abnormal ticket requests and large numbers of TGS requests from single accounts; consider alerting on mass SPN enumeration behaviour.  
- Limit read access to SYSVOL; enforce tighter ACLs where possible and restrict who can read policy XML files.

---

## Evidence and artifacts (included)
- `hashes/10.10.10.100-Users_SVC_TGS_Desktop_user.txt` → user flag `a95a2f3c71ad414ee65d3616fa663242`  
- `hashes/Administrator.krb5tgs-1` and `hashes/Administrator.krb5tgs-2` → krb5tgs ticket hashes (saved for offline cracking)  
- `smb/active.htb/Policies/.../Groups/Groups.xml` → original GPP file containing `cpassword` (saved)  
- `20251023175355_bloodhound.zip` — BloodHound data collected during enumeration (not used for core exploit but useful for mapping)

---

## Reflection
This box was a neat reminder that small operational mistakes scale; a single leaked GPP password + accessible SYSVOL can cascade into a full domain compromise if combined with ticket-based attacks. I leaned on ticket collection and offline cracking here to turn a low-privilege foothold into a full compromise.

