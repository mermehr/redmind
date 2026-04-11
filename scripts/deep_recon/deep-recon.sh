#!/usr/bin/env bash
# A robust recon runner.
# Usage:
#   ./deep_recon.sh -t <target> [-o outdir] [-w wordlist] [--no-web] [--quick] [--udp] [--vhosts] [--ffuf] [--xml]
set -Eeuo pipefail
IFS=$'\n\t'

show_help() {
  cat <<'USAGE'
deep_recon.sh - robust recon runner

Required:
  -t, --target <host|ip|cidr>    Target to scan

Optional:
  -o, --outdir <dir>             Output directory (default: ./recon_<target>)
  -w, --wordlist <file>          Wordlist for gobuster/ffuf (default: /usr/share/wordlists/dirb/common.txt)
  --no-web                       Skip web enumeration
  --quick                        Quick nmap (top-1000 ports) instead of full TCP sweep
  --udp                          Run light UDP probe (nmap -sU top-100)
  --vhosts                       Create virtual-host discovery jobs (requires ffuf)
  --ffuf                         Use ffuf for directory fuzzing (instead of gobuster)
  --xml                          Keep nmap XML and pass it to parser
  -h, --help                     Show this help
Examples:
  ./deep_recon.sh -t 10.10.10.10
  ./deep_recon.sh -t example.com --ffuf --vhosts -w ~/wordlists/raft-small-words.txt
USAGE
}

# Defaults
TARGET=""
OUTDIR=""
WORDLIST="/usr/share/wordlists/dirb/common.txt"
DO_WEB=1
QUICK=0
DO_UDP=0
DO_VHOSTS=0
USE_FFUF=0
KEEP_XML=0

# Simple arg parse
while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--target) TARGET="${2:-}"; shift 2;;
    -o|--outdir) OUTDIR="${2:-}"; shift 2;;
    -w|--wordlist) WORDLIST="${2:-}"; shift 2;;
    --no-web) DO_WEB=0; shift;;
    --quick) QUICK=1; shift;;
    --udp) DO_UDP=1; shift;;
    --vhosts) DO_VHOSTS=1; shift;;
    --ffuf) USE_FFUF=1; shift;;
    --xml) KEEP_XML=1; shift;;
    -h|--help) show_help; exit 0;;
    *) echo "[!] Unknown arg: $1" >&2; show_help; exit 1;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "[!] Target is required." >&2
  show_help
  exit 1
fi

# Dependency checker
_need() {
  command -v "$1" >/dev/null 2>&1 || return 1
}
# core requirements
if ! _need nmap; then echo "[!] nmap is required but not found." >&2; exit 127; fi
if ! _need python3; then echo "[!] python3 is required but not found." >&2; exit 127; fi

# optional deps handled later when actually needed

# normalize target
SAFE_TARGET="$(printf "%s" "$TARGET" | tr '/:\\ ' '_')"
OUTDIR="${OUTDIR:-./recon_${SAFE_TARGET}}"
SCANDIR="${OUTDIR}/scans"
WEBDIR="${OUTDIR}/web"
PARSEDIR="${OUTDIR}/parsed"
mkdir -p "$SCANDIR" "$WEBDIR" "$PARSEDIR"

echo "[*] Target: $TARGET"
echo "[*] Output: $OUTDIR"

# Nmap filenames
NMAP_OUT="${SCANDIR}/nmap_${SAFE_TARGET}.txt"
NMAP_XML="${SCANDIR}/nmap_${SAFE_TARGET}.xml"
NMAP_GNMAP="${SCANDIR}/nmap_${SAFE_TARGET}.gnmap"

# Run TCP nmap
if [[ "$QUICK" -eq 1 ]]; then
  echo "[*] Running quick TCP nmap (top-1000 ports, scripts+versions)..."
  nmap -Pn -sC -sV --top-ports 1000 -oN "$NMAP_OUT" -oX "$NMAP_XML" -oG "$NMAP_GNMAP" "$TARGET"
else
  echo "[*] Running full TCP nmap (-p-)..."
  # safe-ish flags:
  nmap -Pn -sC -sV -p- --min-rate 1000 --defeat-rst-ratelimit -oN "$NMAP_OUT" -oX "$NMAP_XML" -oG "$NMAP_GNMAP" "$TARGET"
fi

# Optional UDP
if [[ "$DO_UDP" -eq 1 ]]; then
  echo "[*] Running light UDP probe (top-100 ports) - may take time..."
  UDP_OUT="${SCANDIR}/nmap_${SAFE_TARGET}_udp.txt"
  UDP_XML="${SCANDIR}/nmap_${SAFE_TARGET}_udp.xml"
  nmap -sU --top-ports 100 -Pn -oN "$UDP_OUT" -oX "$UDP_XML" "$TARGET" || true
fi

# Detect web ports using greppable
mapfile -t WEB_PORTS < <(grep -Eo '([0-9]{1,5})/(tcp|udp)[[:space:]]+open' "$NMAP_OUT" 2>/dev/null | awk -F'/' '{print $1}' | sort -n -u || true)

# If not found, fallback to scanning for common ports in nmap
if [[ "${#WEB_PORTS[@]}" -eq 0 ]]; then
  mapfile -t WEB_PORTS < <(grep -Eo '[[:space:]](80|443|8080|8000|8443)[[:space:]]' "$NMAP_OUT" 2>/dev/null | tr -d ' ' | sort -n -u || true)
fi

if [[ "${#WEB_PORTS[@]}" -gt 0 && "$DO_WEB" -eq 1 ]]; then
  echo "[*] Detected web ports: ${WEB_PORTS[*]}"
else
  echo "[*] No web ports detected or web enumeration is disabled."
fi

# If ffuf/gobuster needed, check presence
if [[ "$DO_WEB" -eq 1 && "${#WEB_PORTS[@]}" -gt 0 ]]; then
  if [[ "$USE_FFUF" -eq 1 || "$DO_VHOSTS" -eq 1 ]]; then
    if ! _need ffuf; then echo "[!] ffuf required for --ffuf or --vhosts but not found; disable those flags or install ffuf." >&2; exit 127; fi
  else
    if ! _need gobuster; then echo "[!] gobuster not found; either install it or use --ffuf." >&2; exit 127; fi
  fi
fi

# Run vhost discovery if requested
VHOST_OUTS=()
if [[ "$DO_VHOSTS" -eq 1 && "${#WEB_PORTS[@]}" -gt 0 ]]; then
  echo "[*] Running vhost discovery (Host header fuzzing) with ffuf..."
  for P in "${WEB_PORTS[@]}"; do
    SCHEME="http"
    if [[ "$P" -eq 443 || "$P" -eq 8443 ]]; then SCHEME="https"; fi
    OUT="${WEBDIR}/ffuf_vhosts_${SAFE_TARGET}_${P}.csv"
    # ffuf
    ffuf -w "$WORDLIST" -u "${SCHEME}://${TARGET}:${P}/" -H "Host: FUZZ" -mc 200 -o "$OUT" -of csv || true
    VHOST_OUTS+=("$OUT")
  done
fi

# Directory brute-forcing per web port (gobuster or ffuf)
DIR_OUTS=()
if [[ "$DO_WEB" -eq 1 && "${#WEB_PORTS[@]}" -gt 0 ]]; then
  echo "[*] Running directory discovery on web ports..."
  for P in "${WEB_PORTS[@]}"; do
    SCHEME="http"
    if [[ "$P" -eq 443 || "$P" -eq 8443 ]]; then SCHEME="https"; fi
    URL="${SCHEME}://${TARGET}:${P}/"
    OUT="${WEBDIR}/dirs_${SAFE_TARGET}_${P}.txt"
    if [[ "$USE_FFUF" -eq 1 ]]; then
      echo "    -> ffuf ${URL} (wordlist: ${WORDLIST})"
      ffuf -w "$WORDLIST" -u "${URL}FUZZ" -mc 200 -o "$OUT" -of csv || true
    else
      echo "    -> gobuster ${URL} (wordlist: ${WORDLIST})"
      gobuster dir -u "$URL" -w "$WORDLIST" -q -o "$OUT" || true
    fi
    DIR_OUTS+=("$OUT")
  done
fi

# Find recon_parser.py next to script or in PATH
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARSER="${SCRIPT_DIR}/recon_parser.py"
if [[ ! -f "$PARSER" ]]; then
  if command -v recon_parser.py >/dev/null 2>&1; then
    PARSER="$(command -v recon_parser.py)"
  else
    echo "[!] recon_parser.py not found next to script or in PATH." >&2
    exit 1
  fi
fi

# Build parse args
PARSE_ARGS=()
PARSE_ARGS+=( "$NMAP_OUT" )
if [[ "$KEEP_XML" -eq 1 && -f "$NMAP_XML" ]]; then
  PARSE_ARGS+=( "--xml" "$NMAP_XML" )
fi
# include directory fuzzing outputs and vhost outputs if present
for f in "${DIR_OUTS[@]:-}"; do PARSE_ARGS+=( "$f" ); done
for f in "${VHOST_OUTS[@]:-}"; do PARSE_ARGS+=( "$f" ); done

echo "[*] Parsing results with: $PARSER ${PARSE_ARGS[*]}"
# Use array expansion to preserve spaces and special chars
python3 "$PARSER" "${PARSE_ARGS[@]}" --outdir "$PARSEDIR" || echo "[!] Parser exited with non-zero status (continuing)."

echo "[+] Done. Results: $OUTDIR"
