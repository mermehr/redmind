#!/usr/bin/env python3
# General TCP proxy with hex-dumping.

import argparse
import socket
import sys
import threading
from typing import Iterable, List

# Utils
def hexdump(src: bytes | str, length: int = 16, show: bool = True) -> List[str]:
    """Pretty-print a bytes buffer as hex + ASCII."""
    if isinstance(src, str):
        src = src.encode("utf-8", errors="replace")

    results: List[str] = []
    for i in range(0, len(src), length):
        chunk = src[i : i + length]
        hexa = " ".join(f"{b:02X}" for b in chunk)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        results.append(f"{i:04x}  {hexa:<{length*3}}  {text}")
    if show:
        for line in results:
            print(line)
    return results

def receive_from(connection: socket.socket, timeout: float = 5.0) -> bytes:
    # Read as much as is readily available
    buffer = b""
    connection.settimeout(timeout)
    try:
        while True:
            data = connection.recv(4096)
            if not data:
                break
            buffer += data
            if len(data) < 4096:
                # likely no more data
                break
    except Exception:
        pass
    return buffer

def parse_bool(s: str) -> bool:
    return s.strip().lower() in ("1", "true", "t", "y", "yes", "on")

# Handlers
def request_handler(buffer: bytes) -> bytes:
    """Modify outbound client->remote data if desired."""
    return buffer

def response_handler(buffer: bytes) -> bytes:
    """Modify inbound remote->client data if desired."""
    return buffer

# Core proxy logic
def proxy_handler(
    client_socket: socket.socket,
    remote_host: str,
    remote_port: int,
    receive_first: bool,
) -> None:
    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        remote_socket.connect((remote_host, remote_port))
    except Exception as e:
        print(f"[!!] Failed to connect to remote {remote_host}:{remote_port}: {e}")
        client_socket.close()
        return

    try:
        # if the remote speaks first, grab and forward
        if receive_first:
            remote_buffer = receive_from(remote_socket)
            if remote_buffer:
                print(f"[<==] {len(remote_buffer)} bytes from remote (initial):")
                hexdump(remote_buffer)
                remote_buffer = response_handler(remote_buffer)
                if remote_buffer:
                    client_socket.sendall(remote_buffer)

        # Main loop
        while True:
            # From client -> remote
            local_buffer = receive_from(client_socket)
            if local_buffer:
                print(f"[==>] {len(local_buffer)} bytes from localhost:")
                hexdump(local_buffer)
                local_buffer = request_handler(local_buffer)
                try:
                    remote_socket.sendall(local_buffer)
                    print("[==>] Sent to remote.")
                except Exception as e:
                    print(f"[!!] Error sending to remote: {e}")
                    break

            # From remote -> client
            remote_buffer = receive_from(remote_socket)
            if remote_buffer:
                print(f"[<==] {len(remote_buffer)} bytes from remote:")
                hexdump(remote_buffer)
                remote_buffer = response_handler(remote_buffer)
                try:
                    client_socket.sendall(remote_buffer)
                    print("[<==] Sent to localhost.")
                except Exception as e:
                    print(f"[!!] Error sending to client: {e}")
                    break

            # If neither side sent anything, break
            if not local_buffer and not remote_buffer:
                print("[*] No more data. Closing connections.")
                break
    finally:
        try:
            remote_socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        remote_socket.close()
        client_socket.close()

def server_loop(
    local_host: str,
    local_port: int,
    remote_host: str,
    remote_port: int,
    receive_first: bool,
) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((local_host, local_port))
    except Exception as e:
        print(f"[!!] Failed to bind {local_host}:{local_port} — {e}")
        print("[!!] Check privileges or if the port is in use.")
        sys.exit(1)

    server.listen(5)
    print(f"[*] Listening on {local_host}:{local_port} → {remote_host}:{remote_port} (receive_first={receive_first})")

    while True:
        client_socket, addr = server.accept()
        print(f"> Incoming connection from {addr[0]}:{addr[1]}")
        t = threading.Thread(
            target=proxy_handler,
            args=(client_socket, remote_host, remote_port, receive_first),
            daemon=True,
        )
        t.start()

# CLI
def main() -> int:
    p = argparse.ArgumentParser(
        description="General TCP proxy with hex-dumping (client <-> proxy <-> remote)."
    )
    p.add_argument("local_host", help="Local interface/IP to bind (e.g., 127.0.0.1)")
    p.add_argument("local_port", type=int, help="Local port to bind")
    p.add_argument("remote_host", help="Remote host to connect to")
    p.add_argument("remote_port", type=int, help="Remote port to connect to")
    p.add_argument(
        "receive_first",
        help="If 'true', connect to remote and read first (for protocols where server speaks first)",
        choices=["true", "false", "True", "False", "1", "0", "yes", "no", "y", "n"],
    )
    args = p.parse_args()

    server_loop(
        args.local_host,
        args.local_port,
        args.remote_host,
        args.remote_port,
        parse_bool(args.receive_first),
    )
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] Ctrl-C received, exiting.")
        sys.exit(0)
