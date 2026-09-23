#!/usr/bin/env python3
# Python Network & Security CLI Toolkit

from __future__ import annotations

import argparse
import os
import re
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Set

# Optional deps
SCAPY_OK = True
try:
    from scapy.all import sniff, ARP, Ether, srp  # type: ignore
except Exception:
    SCAPY_OK = False

COLOR_OK = True
try:
    from colorama import Fore, Style, init as colorama_init  # type: ignore
    colorama_init(autoreset=True)
except Exception:
    COLOR_OK = False

# Fallback if Colorama missing
class _Dummy:
    def __getattr__(self, _): return ""
Fore = Fore if COLOR_OK else _Dummy()
Style = Style if COLOR_OK else _Dummy()

# Requests, needed for httplog
try:
    import requests
except Exception as e:
    print("[!] 'requests' is required for httplog. Install with: pip install requests", file=sys.stderr)
    # We won't exit; only the httplog tool depends on it

ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)

def write_output(output: str, file_path: str | None = None) -> None:
    print(output)
    if file_path:
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(strip_ansi(output) + "\n")
        except Exception as e:
            print(f"{Fore.RED}[!] Failed writing to file: {e}{Style.RESET_ALL}", file=sys.stderr)

# Utilities
def parse_ports(spec: str) -> List[int]:
    """
    Accepts:
      - single range: "1-1024"
      - single port: "22"
      - lists & mixes: "22,80,443,8000-8100"
    """
    ports: Set[int] = set()
    parts = [p.strip() for p in spec.split(",")]
    for p in parts:
        if not p:
            continue
        if "-" in p:
            try:
                start_s, end_s = p.split("-", 1)
                start, end = int(start_s), int(end_s)
                if start > end or start < 1 or end > 65535:
                    raise ValueError(f"Invalid range '{p}'")
                ports.update(range(start, end + 1))
            except ValueError as e:
                raise ValueError(f"Bad port range '{p}': {e}")
        else:
            try:
                val = int(p)
                if val < 1 or val > 65535:
                    raise ValueError
                ports.add(val)
            except ValueError:
                raise ValueError(f"Bad port '{p}'")
    return sorted(ports)

def is_admin_like() -> bool:
    """Best-effort check for elevated privileges (needed for sniff/ARP)."""
    try:
        return os.name == "nt" or os.geteuid() == 0  # Windows can't check; assume admin or let it fail later
    except Exception:
        return False

# Tools
def scan_ports(host: str, ports: Iterable[int], output_file: str | None = None, timeout: float = 0.5) -> None:
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                result = s.connect_ex((host, port))
            status = f"{Fore.GREEN}Open{Style.RESET_ALL}" if result == 0 else f"{Fore.RED}Closed{Style.RESET_ALL}"
            write_output(f"Port {port:>5}: {status}", output_file)
        except Exception as e:
            write_output(f"{Fore.RED}[!] Port {port}: error: {e}{Style.RESET_ALL}", output_file)

def packet_callback_factory(output_file: str | None):
    def _cb(pkt):
        try:
            write_output(pkt.summary(), output_file)
        except Exception:
            # As a fallback if color/str fails
            write_output(repr(pkt), output_file)
    return _cb

def dns_lookup(domain: str, output_file: str | None = None) -> None:
    try:
        # socket.gethostbyname resolves a single A record; getaddrinfo returns more data
        infos = socket.getaddrinfo(domain, None, proto=socket.IPPROTO_TCP)
        ips = sorted({info[4][0] for info in infos})
        for ip in ips:
            write_output(f"{Fore.CYAN}{domain} → {ip}{Style.RESET_ALL}", output_file)
        if not ips:
            write_output(f"{Fore.YELLOW}[?] No results for {domain}{Style.RESET_ALL}", output_file)
    except Exception as e:
        write_output(f"{Fore.RED}[!] DNS error: {e}{Style.RESET_ALL}", output_file)

def log_request(url: str, output_file: str | None = None, method: str = "GET") -> None:
    if 'requests' not in sys.modules:
        write_output(f"{Fore.RED}[!] 'requests' is not available; install with pip install requests{Style.RESET_ALL}", output_file)
        return
    try:
        sess = requests.Session()
        sess.headers.update({
            "User-Agent": "PyNetSec-CLI/1.0 (+https://example.invalid)"
        })
        resp = sess.request(method.upper(), url, timeout=15, allow_redirects=True)

        req_headers = "\n".join(f"{k}: {v}" for k, v in resp.request.headers.items())
        res_headers = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())

        lines = [
            f"{Fore.YELLOW}[Request] {resp.request.method} {resp.request.url}{Style.RESET_ALL}",
            f"{Fore.YELLOW}[Status]  {resp.status_code}{Style.RESET_ALL}",
            f"{Fore.YELLOW}[Request Headers]:{Style.RESET_ALL}\n{req_headers}",
            f"{Fore.YELLOW}[Response Headers]:{Style.RESET_ALL}\n{res_headers}",
            f"{Fore.YELLOW}[Body bytes]: {len(resp.content)}{Style.RESET_ALL}",
        ]
        write_output("\n".join(lines), output_file)
    except requests.RequestException as e:
        write_output(f"{Fore.RED}[!] Request failed: {e}{Style.RESET_ALL}", output_file)

def arp_scan(network: str, output_file: str | None = None) -> None:
    if not SCAPY_OK:
        write_output(f"{Fore.RED}[!] Scapy not available. Install with: pip install scapy{Style.RESET_ALL}", output_file)
        return
    if not is_admin_like():
        write_output(f"{Fore.RED}[!] ARP scan likely requires elevated privileges (run as root/Admin).{Style.RESET_ALL}", output_file)
    try:
        arp = ARP(pdst=network)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        ans = srp(ether / arp, timeout=2, verbose=False)[0]
        write_output(f"{Fore.MAGENTA}\n[Discovered Devices]:{Style.RESET_ALL}", output_file)
        if not ans:
            write_output(f"{Fore.YELLOW}[?] No hosts responded on {network}{Style.RESET_ALL}", output_file)
        for _, rcv in ans:
            write_output(f"{rcv.psrc} → {rcv.hwsrc}", output_file)
    except Exception as e:
        write_output(f"{Fore.RED}[!] ARP scan error: {e}{Style.RESET_ALL}", output_file)

# CLI
def main() -> int:
    parser = argparse.ArgumentParser(description="Python Network & Security CLI Toolkit")
    parser.add_argument("tool", choices=["portscan", "sniffer", "dns", "httplog", "discover"],
                        help="Choose which tool to run")
    parser.add_argument("--target", help="Target IP/domain/subnet (CIDR for 'discover')")
    parser.add_argument("--ports", default="1-1024",
                        help="Port spec for portscan: 'start-end' or comma list; e.g. '22,80,443,8000-8100'")
    parser.add_argument("--count", type=int, default=10, help="Packet count for sniffer")
    parser.add_argument("--iface", help="Interface for sniffer/discover (optional)")
    parser.add_argument("--bpf", help="Sniffer BPF filter, e.g. 'tcp port 80'")
    parser.add_argument("--method", default="GET", help="HTTP method for httplog (default GET)")
    parser.add_argument("--output", help="Optional output file to save results")
    args = parser.parse_args()

    # Prepare output file
    output_file = None
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(f"# Output - {datetime.now().isoformat(timespec='seconds')}\n")
        output_file = args.output

    # Tool dispatch
    if args.tool == "portscan":
        if not args.target:
            print("[!] Port scan requires --target", file=sys.stderr)
            return 2
        try:
            ports = parse_ports(args.ports)
        except ValueError as e:
            print(f"[!] {e}", file=sys.stderr)
            return 2
        scan_ports(args.target, ports, output_file)
        return 0

    if args.tool == "sniffer":
        if not SCAPY_OK:
            print("[!] Scapy not installed. pip install scapy", file=sys.stderr)
            return 2
        cb = packet_callback_factory(output_file)
        try:
            # sniff kwargs are flexible; only pass iface/filter if provided
            sniff_kwargs = dict(count=args.count, prn=cb, store=False)
            if args.iface:
                sniff_kwargs["iface"] = args.iface
            if args.bpf:
                sniff_kwargs["filter"] = args.bpf
            sniff(**sniff_kwargs)
            return 0
        except PermissionError:
            print("[!] Sniffer requires elevated privileges.", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[!] Sniffer error: {e}", file=sys.stderr)
            return 1

    if args.tool == "dns":
        if not args.target:
            print("[!] DNS lookup requires --target (domain)", file=sys.stderr)
            return 2
        dns_lookup(args.target, output_file)
        return 0

    if args.tool == "httplog":
        if not args.target:
            print("[!] HTTP logger requires --target (URL)", file=sys.stderr)
            return 2
        log_request(args.target, output_file, method=args.method)
        return 0

    if args.tool == "discover":
        if not args.target:
            print("[!] Network discovery requires --target (CIDR subnet)", file=sys.stderr)
            return 2
        if not SCAPY_OK:
            print("[!] Scapy not installed. pip install scapy", file=sys.stderr)
            return 2
        arp_scan(args.target, output_file)
        return 0

    # Shouldn't reach here
    return 2

if __name__ == "__main__":
    sys.exit(main())
