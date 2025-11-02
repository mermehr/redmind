#!/usr/bin/env bash
# Usage: sudo ./recon.sh <TARGET_IP_or_CIDR> [DOMAIN] [DC_IP]
# Example: sudo ./recon.sh 10.10.0.55 domain.local 10.10.0.53
set -euo pipefail
IFS=$'\n\t'

if [[ $# -lt 1 ]]; then
  echo "Usage: sudo $0 <TARGET_IP_or_CIDR> [DOMAIN] [DC_IP]"
  exit 2
fi

TARGET="$1"
DOMAIN="${2:-}"
DC_IP="${3:-}"

# output dir
OUTDIR="/tmp/recon_$TARGET"

# create output directory
mkdir -p "$OUTDIR"

echo "[+] Output directory: $OUTDIR"

# helper to check command existence
_cmd_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Fast host discovery
echo "[+] Running fast port discovery (this can take a while)..."
if _cmd_exists nmap; then
  # allow nmap failure without exiting
  sudo nmap -n -Pn -T4 --min-rate 500 -p- --open -oA "$OUTDIR/firstpass" "$TARGET" || true
else
  echo "[!] nmap not installed — skipping port discovery"
fi

# Targeted service scan for AD-related ports
echo "[+] Targeted service scan for AD ports (53,88,135,139,389,445,464,636,3268,3389)"
if _cmd_exists nmap; then
  sudo nmap -n -Pn -T4 -p 53,88,135,139,389,445,464,636,3268,3389 -sC -sV -oA "$OUTDIR/services" "$TARGET" || true
fi

# SMB enumeration (if single host)
echo "[+] SMB enumeration (smbmap / enum4linux)"
if _cmd_exists smbmap; then
  # smbmap is host-oriented; if CIDR provided, try to use the TARGET as-is
  smbmap -H "$TARGET" --shares | tee "$OUTDIR/smbmap_shares.txt" || true
else
  echo "[!] smbmap not installed — skipping smbmap"
fi

if _cmd_exists enum4linux; then
  enum4linux -a "$TARGET" | tee "$OUTDIR/enum4linux.txt" || true
else
  echo "[!] enum4linux not installed — skipping enum4linux"
fi

# LDAP anonymous check
if _cmd_exists ldapsearch && [[ -n "$DOMAIN" || -n "$DC_IP" ]]; then
  DC_HOST="${DC_IP:-$TARGET}"
  # attempt to craft base DN from DOMAIN (domain.local -> dc=domain,dc=local)
  if [[ -n "$DOMAIN" && "$DOMAIN" == *.* ]]; then
    IFS='.' read -r -a parts <<< "$DOMAIN"
    base=""
    for p in "${parts[@]}"; do
      if [[ -z "$base" ]]; then base="dc=$p"; else base="${base},dc=$p"; fi
    done
  else
    base="dc=example,dc=local"
  fi
  echo "[+] ldapsearch anonymous query against $DC_HOST (base: $base)"
  ldapsearch -x -H "ldap://$DC_HOST" -b "$base" '(objectClass=*)' > "$OUTDIR/ldap_anon.txt" 2>/dev/null || true
else
  echo "[!] ldapsearch not available or DOMAIN/DC not provided — skip ldapsearch"
fi

# Kerberos / SPN discovery
if [[ -f "/opt/impacket/examples/GetUserSPNs.py" ]]; then
  echo "[+] Impacket GetUserSPNs.py detected at /opt/impacket/examples/GetUserSPNs.py"
  echo "    Example (manual): python3 /opt/impacket/examples/GetUserSPNs.py domain.local/user:'Pass' -dc-ip $DC_IP > $OUTDIR/getuserspns.txt"
else
  echo "[!] GetUserSPNs.py not found at /opt/impacket/examples/GetUserSPNs.py — skip automatic Kerberos collection"
fi

# Web discovery (gobuster) — only if gobuster installed and HTTP found in nmap output
if _cmd_exists gobuster && [[ -f "$OUTDIR/services.nmap" ]]; then
  echo "[+] Running gobuster against HTTP services found in nmap output (heuristic)"
  # extract lines that indicate service on port and open state for http(s)
  mapfile -t hosts < <(grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}:(80|443|8080|8000|8443)' "$OUTDIR/services.nmap" | awk -F: '{print $1}' | sort -u)
  if [[ ${#hosts[@]} -gt 0 ]]; then
    for h in "${hosts[@]}"; do
      # try http and https variations
      if grep -q "443/tcp" "$OUTDIR/services.nmap" 2>/dev/null || grep -q "8443/tcp" "$OUTDIR/services.nmap" 2>/dev/null; then
        url="https://$h"
      else
        url="http://$h"
      fi
      echo "[*] Gobuster on $url"
      gobuster dir -u "$url" -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -o "$OUTDIR/gobuster_${h}.txt" || true
    done
  else
    echo "[!] No HTTP hosts found in nmap output — run gobuster manually against known web hosts"
  fi
else
  echo "[!] gobuster not installed or no nmap services output — skip web bruteforce"
fi

# Passive/OSINT domain enumeration
if _cmd_exists amass && [[ -n "$DOMAIN" ]]; then
  echo "[+] Running amass enum (passive+active) for $DOMAIN"
  amass enum -d "$DOMAIN" -o "$OUTDIR/amass_domains.txt" || true
else
  echo "[!] amass not installed or DOMAIN not provided — skip amass"
fi

echo "[+] Done. Check $OUTDIR for outputs."
echo "Reminder:"
echo " - If you obtain creds, use Impacket (secretsdump/GetUserSPNs) and CrackMapExec for rapid lateral checks."
echo " - Use BloodHound (SharpHound) for graph analysis once you can run an ingestor on a Windows host."
