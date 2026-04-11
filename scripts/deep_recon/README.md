# Deep Recon

Automated basic recon workflow with optional UDP probing, virtual-host discovery, richer nmap XML parsing, ffuf support, and CSV output for machine processing.

**Includes**: `deep_recon.sh`, `recon_parser.py` (extended), `README.md`

## Highlights of extensions

- `--udp` runs a light UDP probe (nmap -sU --top-ports 100)
- `--vhosts` uses ffuf Host header fuzzing to discover virtual hosts (requires `ffuf`)
- `--ffuf` uses `ffuf` for directory fuzzing instead of `gobuster`
- `--xml` preserves nmap XML and parser will use it to capture service banners and script output
- Parser now emits Markdown, plain text, and a CSV of ports/services for ingestion into tooling
- Better merging between text & XML nmap outputs to keep highest-fidelity service info

## Quick usage examples

```bash
# Full TCP scan, auto-web enum with gobuster
./deep_recon.sh -t target.com

# Quick + UDP probe + keep XML for parser to use
./deep_recon.sh -t 10.10.10.10 --quick --udp --xml

# Use ffuf for dir fuzzing and vhost discovery
./deep_recon.sh -t target.com --ffuf --vhosts -w /path/to/wordlist.txt
```

## Output layout

```sh
recon_<target>/
  scans/
    nmap_<target>.txt
    nmap_<target>.xml            # only if --xml or by default in this script
    nmap_<target>_udp.txt       # if --udp used
  web/
    dirs_<target>_<port>.txt    # gobuster or ffuf output
    ffuf_vhosts_<target>_<port>.txt  # vhost discovery CSV if used
  parsed/
    <target>_recon.txt
    <target>_recon.md
    <target>_recon.csv
```

## Notes

- `ffuf` offers structured CSV output which parser can read; `gobuster` output is supported too.
- XML parsing will be resilient to malformed XML but is limited to common patterns—still review nmap XML when available.
- CSV output can be imported into spreadsheets or tools for pivoting on ports/services
