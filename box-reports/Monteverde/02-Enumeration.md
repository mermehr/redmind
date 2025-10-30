# Enumeration — Monteverde

This section summarizes active reconnaissance and service enumeration performed against the target. Only salient results are included; raw tool output is referenced where necessary.

## Service Enumeration (Nmap)

The tester executed initial host discovery and service/version detection with standard scripts and service probes. The important open services discovered were:

- 53/tcp — DNS (Simple DNS Plus)
- 88/tcp — Kerberos
- 135/tcp — MS-RPC
- 139/tcp — NetBIOS-SSN
- 389/tcp — LDAP (Active Directory)
- 445/tcp — Microsoft-DS (SMB)
- 464/tcp — kpasswd5
- 593/tcp — MS-RPC over HTTP
- 5985/tcp — WinRM (HTTP/PowerShell Remoting)
- 3268/tcp — Global Catalog (LDAP)

The presence of LDAP, Global Catalog, Kerberos, and WinRM indicates a domain controller or AD-integrated server role and suggests Active Directory–oriented enumeration is likely to be productive.

```sh
sudo nmap -sC -sV -oN logs/nmap.init 10.10.10.172
```

## Identity and SMB Enumeration

User enumeration via `enum4linux-ng` revealed multiple domain principals. A concise user list was created for targeted authentication attempts and password spray testing.

```sh
enum4linux-ng -U 10.10.10.172 | grep "username:" | awk '{ print $2 }' > user.list
```

Example accounts discovered:

- AAD_987d7f2f57d2
- mhope
- SABatchJobs
- svc-ata
- svc-bexec
- svc-netapp
- dgalanos
- roleary
- smorgan
- Guest

## Domain Password Policy

Domain password policy was retrieved and reviewed to inform credential attack cadence. Key attributes:

- Minimum password length: 7
- Password history length: 24
- Minimum password age: 1 day 4 minutes
- Maximum password age: ~41 days
- DOMAIN_PASSWORD_COMPLEX: false (not enforcing complexity)

This policy suggests the potential effectiveness of targeted enumeration and credential reuse attacks. An initial authenticated SMB access was obtained using discovered credentials during testing.

```sh
netexec smb 10.10.10.172 -u user.list -p pass.list
# Result: MEGABANK.LOCAL\SABatchJobs:SABatchJobs
```

**Conclusion:** Enumerated AD services and SMB exposure provided a viable path to initial access and subsequent credential discovery.

