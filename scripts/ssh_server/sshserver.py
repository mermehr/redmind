#!/usr/bin/env python3
# Minimal cross-platform SSH server using Paramiko.
# Notes:
# Requires an RSA host key file (default: ./test_rsa.key).
# This server accepts exactly one username/password combo (tim/sekret).

import os
import sys
import socket
import threading
import paramiko

CWD = os.path.dirname(os.path.realpath(__file__))
HOSTKEY_PATH = os.path.join(CWD, "test_rsa.key")

if not os.path.exists(HOSTKEY_PATH):
    sys.stderr.write(f"[!] Host key not found at {HOSTKEY_PATH}\n")
    sys.stderr.write("    Generate one with:\n")
    sys.stderr.write("    ssh-keygen -t rsa -b 2048 -m PEM -f test_rsa.key -N ''\n")
    sys.exit(1)

HOSTKEY = paramiko.RSAKey(filename=HOSTKEY_PATH)


class Server(paramiko.ServerInterface):
    def __init__(self):
        super().__init__()
        self.event = threading.Event()

    # Allow opening channels only
    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED # type: ignore
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED # type: ignore

    # Password authentication
    def check_auth_password(self, username, password):
        if username == "tim" and password == "sekret":
            return paramiko.AUTH_SUCCESSFUL  # type: ignore
        return paramiko.AUTH_FAILED # type: ignore

    # Tell clients which auth methods are allowed
    def get_allowed_auths(self, username):
        return "password"


def main():
    bind_host = "192.168.56.101"  # adjust to your interface/IP
    bind_port = 2222              # avoid clashing with a real SSH daemon

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((bind_host, bind_port))
        sock.listen(100)
        print(f"[+] Listening on {bind_host}:{bind_port} ...")
        client, addr = sock.accept()
    except Exception as e:
        print("[-] Listen/accept failed:", e)
        sys.exit(1)
    else:
        print(f"[+] Connection from {addr}")

    try:
        transport = paramiko.Transport(client)
        transport.add_server_key(HOSTKEY)

        server_iface = Server()
        transport.start_server(server=server_iface)

        # Wait for a client to open a channel
        chan = transport.accept(20)
        if chan is None:
            print("[!] No channel opened by client (timeout).")
            transport.close()
            sys.exit(1)

        print("[+] Client authenticated and channel established.")

        # Optional: greet client
        chan.send(b"Welcome to the demo SSH server.\n")

        # Simple REPL: send command to client and print the response
        while True:
            try:
                command = input("Enter command (or 'exit'): ").strip()
            except (EOFError, KeyboardInterrupt):
                command = "exit"

            if command.lower() == "exit":
                chan.send(b"exit")
                print("[*] Closing session.")
                break

            # Send command to client
            chan.send(command.encode("utf-8"))

            # Receive response
            try:
                data = chan.recv(65535)
                if not data:
                    print("[!] Client closed the channel.")
                    break
                print(data.decode("utf-8", errors="replace"), end="")
            except Exception as e:
                print("[-] Error receiving data:", e)
                break

    except paramiko.SSHException as e:
        print("[-] SSH negotiation failed:", e)
    finally:
        try:
            transport.close()
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
