#!/usr/bin/env python3
#A sister python parser script for deep_recon.sh
# Usage:
#  python3 recon_parser.py <nmap_oN.txt> [gobuster_or_ffuf_output ...] [--xml nmap_oX.xml] [--outdir DIR]


from __future__ import annotations
import argparse
import csv
import pathlib
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

def parse_nmap_text(path: str) -> Tuple[Optional[str], List[str], List[Dict], List[str]]:
    host = None
    ips: List[str] = []
    ports: List[Dict] = []
    os_info: List[str] = []
    try:
        with open(path, "r", errors="ignore") as fh:
            for raw in fh:
                line = raw.rstrip("\n")
                if "Nmap scan report for" in line:
                    m = re.search(r"Nmap scan report for\s+(\S+)", line)
                    if m and not host:
                        host = m.group(1)
                    ipm = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                    if ipm and ipm.group(1) not in ips:
                        ips.append(ipm.group(1))
                # typical nmap format: "80/tcp  open  http    Apache httpd ..."
                m = re.match(r"^(\d+)/(tcp|udp)\s+(\w+)\s+(\S+)(?:\s+(.*))?$", line.strip())
                if m:
                    port_s, proto, state, service, rest = m.groups()
                    version = (rest or "").strip()
                    try:
                        port = int(port_s)
                    except ValueError:
                        continue
                    ports.append({
                        "proto": proto,
                        "port": port,
                        "state": state,
                        "service": service,
                        "version": version,
                    })
                if line.startswith("OS details:") or line.startswith("Aggressive OS guesses:") or line.startswith("Running:"):
                    os_info.append(line.strip())
    except FileNotFoundError:
        pass
    return host, ips, ports, os_info

def parse_nmap_xml(path: str) -> Tuple[Optional[str], List[str], List[Dict]]:
    host = None
    ips: List[str] = []
    ports: List[Dict] = []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        for host_el in root.findall("host"):
            for addr in host_el.findall("address"):
                ip = addr.get("addr")
                if ip and ip not in ips:
                    ips.append(ip)
            hostnames = host_el.find("hostnames")
            if hostnames is not None:
                hn = hostnames.find("hostname")
                if hn is not None and hn.get("name"):
                    host = hn.get("name")
            ports_el = host_el.find("ports")
            if ports_el is None:
                continue
            for p in ports_el.findall("port"):
                proto = p.get("protocol")
                portid = p.get("portid")
                try:
                    portnum = int(portid)
                except (TypeError, ValueError):
                    continue
                state_el = p.find("state")
                state = state_el.get("state") if state_el is not None else ""
                svc = p.find("service")
                service = ""
                version = ""
                if svc is not None:
                    service = svc.get("name", "") or ""
                    pieces = []
                    for k in ("product", "version", "extrainfo", "hostname"):
                        v = svc.get(k)
                        if v:
                            pieces.append(v)
                    version = " ".join(pieces).strip()
                scripts = p.findall("script")
                script_out = ""
                if scripts:
                    out_parts = []
                    for s in scripts:
                        out_parts.append(s.get("output", ""))
                    script_out = "; ".join([x for x in out_parts if x])
                ports.append({
                    "proto": proto,
                    "port": portnum,
                    "state": state,
                    "service": service,
                    "version": version,
                    "script": script_out,
                })
    except Exception:
        # ignore parse errors, return what we can
        pass
    return host, ips, ports

def parse_gobuster_text(path: str) -> List[str]:
    """
    Accepts gobuster text output, or ffuf CSV-like output.
    Returns normalized endpoint list like ['/admin', '/images']
    """
    endpoints: List[str] = []
    try:
        with open(path, "r", errors="ignore") as fh:
            data = fh.read()
            for line in data.splitlines():
                line = line.strip()
                # ffuf csv-style: first field may be a URL
                if "," in line:
                    first = line.split(",", 1)[0].strip()
                    if first.startswith("http"):
                        m = re.search(r"https?://[^/]+(/.*)$", first)
                        if m:
                            endpoints.append(m.group(1).rstrip("/"))
                        continue
                    if first.startswith("/"):
                        endpoints.append(first.rstrip("/"))
                        continue
                # gobuster line: "/admin (Status: 403) [Size: ...]"
                m = re.search(r"(/\S+)\s+\(Status:\s*\d+", line)
                if m:
                    endpoints.append(m.group(1).rstrip("/"))
    except FileNotFoundError:
        pass
    # normalize and dedupe
    cleaned = sorted({e if e == "/" else e.rstrip("/") for e in endpoints})
    return cleaned

def write_txt(path: str, target: str, ips: List[str], ports: List[Dict], os_info: List[str], endpoints: List[str]) -> None:
    lines: List[str] = []
    lines.append(f"[+] Target: {target}")
    lines.append("")
    if ips:
        lines.append("[+] IPs:")
        for i in ips:
            lines.append(f"  - {i}")
        lines.append("")
    if ports:
        lines.append("[+] Open ports:")
        for p in sorted(ports, key=lambda x: (x.get("proto", ""), int(x.get("port", 0)))):
            ver = f" | {p.get('version')}" if p.get("version") else ""
            scr = f" | script: {p.get('script')}" if p.get("script") else ""
            lines.append(f"  - {p.get('proto','').upper()} {p.get('port')} | {p.get('service','')}{ver}{scr}")
        lines.append("")
    if os_info:
        lines.append("[+] OS fingerprint:")
        for o in os_info:
            lines.append(f"  - {o}")
        lines.append("")
    lines.append("[+] HTTP endpoints:")
    if endpoints:
        for e in endpoints:
            lines.append(f"  - {e}")
    else:
        lines.append("  - _None detected_")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")

def write_md(path: str, target: str, ips: List[str], ports: List[Dict], os_info: List[str], endpoints: List[str]) -> None:
    md: List[str] = [f"# Recon Summary — {target}", ""]
    if ips:
        md.append("## IPs")
        md += [f"- {i}" for i in ips]
        md.append("")
    if ports:
        md.append("## Open Ports")
        md.append("")
        for p in sorted(ports, key=lambda x: (x.get("proto", ""), int(x.get("port", 0)))):
            ver = f" — {p.get('version')}" if p.get("version") else ""
            script = f"\n\n  - script: `{p.get('script')}`" if p.get("script") else ""
            md.append(f"- **{p.get('proto','').upper()} {p.get('port')}**: {p.get('service','unknown')}{ver}{script}")
        md.append("")
    if os_info:
        md.append("## OS Fingerprint")
        md += [f"- {x}" for x in os_info]
        md.append("")
    md.append("## HTTP Endpoints")
    md.append("")
    if endpoints:
        md += [f"- `{e}`" for e in endpoints]
    else:
        md.append("- _None detected_")
    md.append("")
    with open(path, "w") as fh:
        fh.write("\n".join(md) + "\n")

def write_csv(path: str, ports: List[Dict]) -> None:
    with open(path, "w", newline="") as csvf:
        w = csv.writer(csvf)
        w.writerow(["proto", "port", "state", "service", "version", "script"])
        for p in sorted(ports, key=lambda x: (x.get("proto", ""), int(x.get("port", 0)))):
            w.writerow([p.get("proto"), p.get("port"), p.get("state"), p.get("service"), p.get("version", ""), p.get("script", "")])

def merge_ports(text_ports: List[Dict], xml_ports: List[Dict]) -> List[Dict]:
    # prefer xml_ports over text_ports
    bykey: Dict[Tuple[str,int], Dict] = {}
    for p in text_ports:
        key = (p.get("proto"), int(p.get("port", 0)))
        bykey[key] = p.copy()
    for p in xml_ports:
        key = (p.get("proto"), int(p.get("port", 0)))
        bykey[key] = p.copy()  # xml overrides text
    return list(bykey.values())

def main() -> None:
    ap = argparse.ArgumentParser(description="Parse nmap -oN and optional -oX plus gobuster/ffuf outputs.")
    ap.add_argument("nmap", help="Path to nmap -oN (normal) output")
    ap.add_argument("gobuster", nargs="*", help="Zero or more gobuster/ffuf output files")
    ap.add_argument("--xml", help="Optional nmap -oX XML file")
    ap.add_argument("--outdir", default=".", help="Output directory")
    args = ap.parse_args()

    host, ips, text_ports, os_info = parse_nmap_text(args.nmap)

    xml_ports: List[Dict] = []
    ips2: List[str] = []
    if args.xml:
        h2, ips2, xml_ports = parse_nmap_xml(args.xml)
        # merge IP lists
        combined_ips: List[str] = []
        for ip in (ips + ips2):
            if ip and ip not in combined_ips:
                combined_ips.append(ip)
        ips = combined_ips or ips

    # merge ports preferring xml details
    ports = merge_ports(text_ports, xml_ports) if xml_ports else text_ports

    # endpoints from gobuster/ffuf files
    endpoints: List[str] = []
    for g in args.gobuster:
        endpoints += parse_gobuster_text(g)
    endpoints = sorted(set(endpoints))

    target_id = (ips[0] if ips else (host or "unknown")).replace("/", "_")
    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    txt_path = str(outdir / f"{target_id}_recon.txt")
    md_path = str(outdir / f"{target_id}_recon.md")
    csv_path = str(outdir / f"{target_id}_recon.csv")

    write_txt(txt_path, target_id, ips, ports, os_info, endpoints)
    write_md(md_path, target_id, ips, ports, os_info, endpoints)
    write_csv(csv_path, ports)

    print(f"[+] Wrote: {txt_path}")
    print(f"[+] Wrote: {md_path}")
    print(f"[+] Wrote: {csv_path}")

if __name__ == "__main__":
    main()
