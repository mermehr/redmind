#!/usr/bin/env python3
# Python ICMP sniffer

import ipaddress
import os
import socket
import struct
import sys

class IP:
    __slots__ = ("ver","ihl","tos","len","id","offset","ttl","protocol_num","sum","src","dst",
                 "src_address","dst_address","protocol")
    def __init__(self, buff):
        # Network byte order (big-endian)
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

def sniff(host):
    if os.name == "nt":
        sock_proto = socket.IPPROTO_IP
    else:
        sock_proto = socket.IPPROTO_ICMP

    # RAW socket
    sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, sock_proto)
    sniffer.bind((host, 0))

    # Include IP headers
    sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

    # Windows: turn on promiscuous mode
    if os.name == "nt":
        sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)

    try:
        while True:
            raw_buffer = sniffer.recvfrom(65535)[0]
            ip_header = IP(raw_buffer[0:20])

            if ip_header.protocol == "ICMP":
                print(f"Protocol: {ip_header.protocol} {ip_header.src_address} -> {ip_header.dst_address}")
                print(f"Version: {ip_header.ver}  Header Length: {ip_header.ihl*4}  TTL: {ip_header.ttl}")

                # ICMP starts after the IP header
                offset = ip_header.ihl * 4
                icmp_buf = raw_buffer[offset:offset + 8]
                icmp_header = ICMP(icmp_buf)

                print(f"ICMP -> Type: {icmp_header.type}  Code: {icmp_header.code}\n")

    except KeyboardInterrupt:
        if os.name == "nt":
            sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
        sys.exit(0)

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) == 2 else ("0.0.0.0" if os.name != "nt" else "127.0.0.1")
    sniff(host)
