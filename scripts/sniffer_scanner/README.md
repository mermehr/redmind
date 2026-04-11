# Python Network Sniffer & UDP/ICMP Scanner

## Scripts

 `icmp_sniffer.py`

A minimal ICMP sniffer that parses IP headers and ICMP headers from captured packets.

- Prints out:
  - Source and destination addresses
  - Protocol
  - IP version, header length, TTL
  - ICMP type and code

**Usage:**

``` bash
# Linux/macOS (requires sudo)
sudo python3 icmp_sniffer.py 0.0.0.0

# Windows (run as admin, bind to your local IP)
python icmp_sniffer.py 192.168.56.1
```

------------------------------------------------------------------------

`udp_icmp_scanner.py`

A UDP spray and ICMP response sniffer that discovers live hosts by sending UDP packets containing a magic payload across a subnet, then listening for ICMP Type 3 / Code 3 (Port Unreachable) replies.

- **Default subnet:** `192.168.56.0/24`
- **Magic string:** `DoNoT3tHi$`
- **Destination port:** `65212`

Hosts that respond with an ICMP error containing the magic string are reported as up.

**Usage:**

``` bash
# Linux/macOS (requires sudo)
sudo python3 udp_icmp_scanner.py 0.0.0.0

# Windows (run as admin, bind to your local IP)
python udp_icmp_scanner.py 192.168.56.1
```

------------------------------------------------------------------------

### Reference

These scripts are adapted from exercises in  **Black Hat Python, 2nd Edition** by Justin Seitz & Tim Arnold.  

They have been recreated here for personal study and educational purposes. The original book provides the full context, explanations, and ethical guidance for using these examples responsibly in security research.
