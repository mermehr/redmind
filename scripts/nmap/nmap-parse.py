#!/usr/bin/env python3

import sys
import os
import subprocess
import argparse
import xml.etree.ElementTree as ET
import shutil
from datetime import datetime

# --- Configuration & Colors ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_info(msg):
    print(f"{Colors.BLUE}[*]{Colors.ENDC} {msg}")

def print_success(msg):
    print(f"{Colors.GREEN}[+]{Colors.ENDC} {msg}")

def print_warn(msg):
    print(f"{Colors.WARNING}[!]{Colors.ENDC} {msg}")

def print_error(msg):
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")

def check_root():
    if os.geteuid() != 0:
        print_error("This script requires root privileges to run effective Nmap scans (SYN/OS detection).")
        sys.exit(1)

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# --- Nmap Wrappers ---

def run_discovery_scan(target, output_dir, protocol="tcp"):
    """
    Runs a fast port discovery scan.
    """
    print_info(f"Starting FAST {protocol.upper()} discovery scan on {target}...")
    
    # Using --min-rate to speed things up since stealth is not required
    output_base = os.path.join(output_dir, f"nmap-discovery-{target}")
    
    cmd = [
        "nmap", "-Pn", "-n", "-T4", "--min-rate", "1000",
        "-oG", f"{output_base}.gnmap"
    ]

    if protocol == "udp":
        cmd.append("-sU")
        # UDP is slow, limit top ports if full range is too slow
        cmd.append("-p-") 
    else:
        cmd.append("-p-") # Full TCP range
        cmd.append("-sS")

    cmd.append(target)

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print_success("Discovery scan complete.")
        return f"{output_base}.gnmap"
    except subprocess.CalledProcessError as e:
        print_error(f"Discovery scan failed: {e}")
        sys.exit(1)

def parse_ports(gnmap_file):
    """
    Extracts open ports from a grepable nmap file.
    """
    open_ports = []
    try:
        with open(gnmap_file, 'r') as f:
            for line in f:
                if "Ports:" in line:
                    parts = line.split("Ports:")[1].strip().split(",")
                    for part in parts:
                        if "open" in part:
                            port = part.split("/")[0].strip()
                            open_ports.append(port)
    except FileNotFoundError:
        print_error("Discovery output file not found.")
        sys.exit(1)
    
    return open_ports

def run_deep_scan(target, ports, output_dir, protocol="tcp"):
    """
    Runs detailed service enumeration on found ports.
    """
    if not ports:
        print_warn("No open ports found. Skipping deep scan.")
        return None

    ports_str = ",".join(ports)
    print_info(f"Starting DEEP scan on {len(ports)} ports: {ports_str}")
    
    timestamp = datetime.now().strftime("%H%M")
    output_base = os.path.join(output_dir, f"nmap-deep-{target}")
    
    # -A: OS detection, version detection, script scanning, traceroute
    # --script "default,vulners": Standard scripts + Vulners
    cmd = [
        "nmap", "-Pn", "-n", "-T4", 
        "-sV", "-O", 
        "--script", "default,vulners",
        "--version-intensity", "5",
        "-p", ports_str,
        "-oA", output_base,
        target
    ]
    
    if protocol == "udp":
        cmd.append("-sU")

    # print stdout here so the user sees progress of the deep scan
    try:
        subprocess.run(cmd, check=True)
        print_success(f"Deep scan complete. Results saved to {output_base}.*")
        return f"{output_base}.xml"
    except subprocess.CalledProcessError:
        print_error("Deep scan encountered an error.")
        return None

# --- Parsing & Heuristics ---

def parse_nmap_xml(xml_file):
    """
    Parses Nmap XML to extract structured service info and host details.
    """
    if not xml_file or not os.path.exists(xml_file):
        return {}, {}

    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    services = {}
    host_info = {
        'domain': '',
        'fqdn': '',
        'workgroup': '',
        'os': ''
    }

    for host in root.findall('host'):
        # Parse Host Scripts
        hostscripts = host.find('hostscript')
        if hostscripts is not None:
            for script in hostscripts.findall('script'):
                if script.get('id') == 'smb-os-discovery':
                    for elem in script.findall('elem'):
                        key = elem.get('key')
                        val = elem.text
                        if key == 'domain_dns': host_info['domain'] = val
                        if key == 'fqdn': host_info['fqdn'] = val
                        if key == 'workgroup': host_info['workgroup'] = val

        # Parse Ports and script output for Domain Info
        for ports in host.findall('ports'):
            for port in ports.findall('port'):
                port_id = port.get('portid')
                proto = port.get('protocol')
                service_item = port.find('service')
                
                service_name = "unknown"
                product = ""
                version = ""
                tunnel = ""
                script_outputs = []

                if service_item is not None:
                    service_name = service_item.get('name', 'unknown')
                    product = service_item.get('product', '')
                    version = service_item.get('version', '')
                    tunnel = service_item.get('tunnel', '')
                
                # Check scripts on specific ports
                for script in port.findall('script'):
                    sid = script.get('id')
                    output = script.get('output')
                    if output:
                        script_outputs.append((sid, output))
                    
                    # --- Domain Parsing Heuristics ---
                    # Check RDP Info
                    if sid == 'rdp-ntlm-info':
                        for elem in script.findall('elem'):
                            k = elem.get('key')
                            v = elem.text
                            if k == 'DNS_Domain_Name' and not host_info['domain']: 
                                host_info['domain'] = v
                            if k == 'DNS_Computer_Name' and not host_info['fqdn']:
                                host_info['fqdn'] = v
                    
                    # Check SSL Certs for domain hints if we still don't have one
                    if sid == 'ssl-cert' and not host_info['domain']:
                        if "Subject Alternative Name" in output:
                            # Rough parsing for DNS: entries in the output text
                            import re
                            # Look for DNS:something.domain.local
                            matches = re.findall(r'DNS:([^,\s]+)', output)
                            for match in matches:
                                if '.' in match:
                                    # Heuristic: assume the last two/three parts are the domain
                                    host_info['fqdn'] = match
                                    parts = match.split('.')
                                    if len(parts) > 2:
                                        host_info['domain'] = ".".join(parts[1:])
                                    elif len(parts) == 2: # e.g. htb.local
                                        host_info['domain'] = match

                key = f"{port_id}/{proto}"
                services[key] = {
                    'name': service_name,
                    'product': product,
                    'version': version,
                    'tunnel': tunnel,
                    'scripts': script_outputs
                }
    
    return services, host_info

def generate_recon_plan(target, services, host_info):
    """
    Generates actionable commands based on found services.
    """
    print(f"\n{Colors.HEADER}=== ACTIONABLE RECON PLAN ==={Colors.ENDC}")
    print(f"{Colors.CYAN}Target: {target}{Colors.ENDC}")
    
    domain = host_info.get('domain') or host_info.get('workgroup') or "<DOMAIN>"
    fqdn = host_info.get('fqdn') or target
    
    if host_info.get('domain'):
        print(f"{Colors.GREEN}[+] Domain Detected: {host_info['domain']}{Colors.ENDC}")
    
    print("") # Spacer

    # Basic Categorization
    web_targets = [] # List of (url, type)
    ad_ports = []
    dns_ports = []
    
    for port, info in services.items():
        p_num = port.split('/')[0]
        name = info['name']
        product = info['product'].lower()
        tunnel = info['tunnel']
        full_name = f"{info['product']} {info['version']}".strip()

        # Skip noisy MSRPC lines
        if 'msrpc' in name or 'rpc' in name:
             pass 
        else:
            print(f"{Colors.BOLD}[+] Port {port:<8} {name:<15} {Colors.GREEN}{full_name}{Colors.ENDC}")

        # --- Heuristics ---
        
        # WEB (HTTP/HTTPS)
        is_web = (name in ['http', 'https', 'http-alt', 'soap'] or 'http' in name or tunnel == 'ssl' or p_num in ['80', '443', '8080', '8443', '8000', '5985'])
        is_excluded = (name in ['ldap', 'ldapssl'] or p_num in ['389', '636', '3268', '3269', '593', '445'])
        
        if is_web and not is_excluded:
            proto = "https" if (tunnel == 'ssl' or name == 'https' or p_num == '443') else "http"
            url = f"{proto}://{target}:{p_num}"
            web_targets.append({'url': url, 'port': p_num, 'product': product})
            
            # Print interesting script output immediately
            for sid, out in info['scripts']:
                if sid in ['http-title', 'http-methods']:
                    clean_out = out.strip().replace('\n', ' ')
                    print(f"    {Colors.BLUE}--> {sid}: {clean_out[:80]}...{Colors.ENDC}")

        # SMB / WINDOWS
        if name in ['microsoft-ds', 'netbios-ssn'] or p_num in ['445', '139']:
            print(f"    {Colors.WARNING}-> SMB/Windows Detected:{Colors.ENDC}")
            if not host_info.get('domain'):
                print(f"      enum4linux-ng -A {target}")
                print(f"      nxc smb {target} --shares -u 'guest' -p ''")

        # ACTIVE DIRECTORY (Kerberos/LDAP)
        if name in ['kerberos', 'ldap', 'ldapssl'] or p_num in ['88', '389', '636', '3268']:
            if p_num not in ad_ports: 
                ad_ports.append(p_num)
        
        # DNS
        if name == 'domain' or p_num == '53':
            dns_ports.append(p_num)

        # DATABASE
        if 'sql' in name or p_num in ['3306', '1433', '5432']:
             print(f"    {Colors.WARNING}-> Database Detected:{Colors.ENDC}")
             print(f"      Verify default creds or try mysql -h {target} -u root")

        # SSH
        if name == 'ssh':
            print(f"    {Colors.WARNING}-> SSH:{Colors.ENDC} Check banner. Search exploits.")

        # RDP
        if p_num == '3389' or 'ms-wbt-server' in name:
            print(f"    {Colors.WARNING}-> RDP:{Colors.ENDC} xfreerdp /v:{target} /u:user /p:pass /dynamic-resolution +clipboard")

    # --- Aggregate Logic ---
    
    # DNS Section
    if dns_ports:
        print(f"\n{Colors.HEADER}[i] DNS Enumeration ({domain}){Colors.ENDC}")
        print(f"    dig axfr @{target} {domain}")
        print(f"    dnsrecon -d {domain} -n {target}")

    # AD Section
    if ad_ports or host_info.get('domain'):
        # Construct LDAP DN
        dc_parts = [f"DC={x}" for x in domain.split('.')] if '.' in domain and domain != '<DOMAIN>' else ["DC=domain", "DC=local"]
        base_dn = ",".join(dc_parts)

        print(f"\n{Colors.HEADER}[!] ACTIVE DIRECTORY ENVIRONMENT DETECTED{Colors.ENDC}")
        print(f"    Domain: {Colors.GREEN}{domain}{Colors.ENDC} | DC: {fqdn}")
        print(f"    nxc smb {target} -u 'guest' -p '' --shares")
        print(f"    nxc smb {target} -u 'guest' -p '' --users")
        print(f"    kerbrute userenum -d {domain} --dc {target} /usr/share/seclists/Usernames/xato-net-10-million-usernames.txt")
        print(f"    ldapsearch -x -H ldap://{target} -b '{base_dn}'")
        print(f"    # If you have creds:")
        print(f"    bloodhound-python -u 'USER' -p 'PASS' -d {domain} -c All --zip -ns {target}")

    # Web Summary Section
    if web_targets:
        print(f"\n{Colors.HEADER}[i] Web Recon Summary{Colors.ENDC}")
        print(f"{Colors.BOLD}Detected Web Services:{Colors.ENDC}")
        for t in web_targets:
            print(f"      - {t['url']} ({t['product']})")
        
        print(f"\n{Colors.BOLD}Suggested Tools:{Colors.ENDC}")
        print("nuclei -u <URL> -o nuclei_results.log")
        print("feroxbuster -u <URL> -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt -t 50 -C 404,403")
        
        # Check for specific high-value targets for specific warnings
        for t in web_targets:
            if "tomcat" in t['product']:
                print(f"      {Colors.FAIL}! TOMCAT ({t['url']}) !{Colors.ENDC} Check /manager/html. Default creds: tomcat:s3cret")
            if "jenkins" in t['product']:
                print(f"      {Colors.FAIL}! JENKINS ({t['url']}) !{Colors.ENDC} Check /script, /cli")
    
    print("\n")

# --- Main ---

def main():
    parser = argparse.ArgumentParser(description=f"{Colors.BOLD}RATTLE{Colors.ENDC} - The Loud Enumerator")
    parser.add_argument("target", help="Target IP address")
    parser.add_argument("-o", "--output", default="logs", help="Output directory (default: logs)")
    parser.add_argument("--udp", action="store_true", help="Include UDP scan (Slow!)")
    parser.add_argument("--skip-discovery", action="store_true", help="Skip discovery, assume common ports (not recommended)")
    
    args = parser.parse_args()

    # Pre-flight
    check_root()
    ensure_dir(args.output)
    
    print(f"{Colors.HEADER}Rattling target: {args.target}{Colors.ENDC}")
    
    # Discovery
    gnmap_file = run_discovery_scan(args.target, args.output, "udp" if args.udp else "tcp")
    open_ports = parse_ports(gnmap_file)
    
    if not open_ports:
        print_error("No open ports found during discovery.")
        sys.exit(0)

    print_success(f"Found {len(open_ports)} open ports.")

    # Deep Scan
    xml_file = run_deep_scan(args.target, open_ports, args.output, "udp" if args.udp else "tcp")

    # Analysis
    if xml_file:
        services, host_info = parse_nmap_xml(xml_file)
        generate_recon_plan(args.target, services, host_info)
    
    print_success("Rattle complete.")

if __name__ == "__main__":
    main()