#!/usr/bin/env python3
#Python UDP scanner, send UDP datagrams across SUBNET; listen for ICMP unreachable
# Notes:
# Needs root/admin (raw sockets).
# On Linux/macOS we sniff IPPROTO_ICMP; on Windows IPPROTO_IP + promiscuous mode.

import ipaddress
import os
import socket
import struct
import sys
import threading
import time

# Adjust these to your lab:
SUBNET  = "192.168.56.0/24"
MESSAGE = "DoNoT3tHi$"
UDP_DST_PORT = 65212

class IP:
    __slots__ = ("ver","ihl","tos","len","id","offset","ttl","protocol_num","sum","src","dst",
                 "src_address","dst_address","protocol")
    def __init__(self, buff):
        ver_ihl, self.tos, self.len, self.id, self.offset, self.ttl, \
        self.protocol_num, self.sum, self.src, self.dst = struct.unpack(
            "!BBHHHBBH4s4s", buff
        )
        self.ver = ver_ihl >> 4
        self.ihl = ver_ihl & 0xF

        self.src_address = ipaddress.ip_address(self.src)
        self.dst_address = ipaddress.ip_address(self.dst)

        proto_map = {1: "ICMP", 6: "TCP", 17: "UDP"}
        self.protocol = proto_map.get(self.protocol_num, str(self.protocol_num))

class ICMP:
    __slots__ = ("type","code","sum","id","seq")
    def __init__(self, buff):
        self.type, self.code, self.sum, self.id, self.seq = struct.unpack("!BBHHH", buff)

def udp_sender():
    """Spray UDP datagrams with our magic payload to the entire SUBNET."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        payload = MESSAGE.encode("utf-8")
        for ip in ipaddress.ip_network(SUBNET).hosts():
            try:
                sender.sendto(payload, (str(ip), UDP_DST_PORT))
            except OSError:
                pass
            time.sleep(0.002)  # small delay to be nice

def sniff(bind_host):
    """Sniff ICMP and extract hosts that send Type 3/Code 3 including our MESSAGE."""
    if os.name == "nt":
        sock_proto = socket.IPPROTO_IP
    else:
        sock_proto = socket.IPPROTO_ICMP

    sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, sock_proto)
    sniffer.bind((bind_host, 0))
    sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

    if os.name == "nt":
        sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)

    seen = set()
    target_net = ipaddress.ip_network(SUBNET)

    try:
        while True:
            raw_buffer = sniffer.recvfrom(65535)[0]
            ip_header = IP(raw_buffer[0:20])

            if ip_header.protocol != "ICMP":
                continue

            # ICMP header sits after IP header
            offset = ip_header.ihl * 4
            icmp_header = ICMP(raw_buffer[offset:offset + 8])

            # We want Destination Unreachable (Type 3) & Port Unreachable (Code 3)
            if icmp_header.type == 3 and icmp_header.code == 3:
                # Validate the source is in our target SUBNET
                if ip_header.src_address in target_net:
                    # Check that our magic MESSAGE is in the original payload echoed back
                    # The original IP header + UDP header + our data follow the ICMP header.
                    if raw_buffer.endswith(MESSAGE.encode("utf-8")):
                        host = str(ip_header.src_address)
                        if host not in seen:
                            seen.add(host)
                            print(f"[+] Host Up: {host}")

    except KeyboardInterrupt:
        if os.name == "nt":
            sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
        sys.exit(0)

if __name__ == "__main__":
    bind_ip = sys.argv[1] if len(sys.argv) >= 2 else ("0.0.0.0" if os.name != "nt" else "127.0.0.1")

    # kick off the sender in the background
    t = threading.Thread(target=udp_sender, daemon=True)
    t.start()

    # give the sender a head start
    time.sleep(1.0)
    sniff(bind_ip)
