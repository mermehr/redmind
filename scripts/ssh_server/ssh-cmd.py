#!/usr/bin/env python3
# Run a single command on a remote SSH server using Paramiko and print
# both stdout and stderr, plus the remote exit status.

import sys
import getpass
import paramiko
from typing import Tuple

def _to_text(data) -> str:
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return str(data)

def ssh_command(ip: str, port: int, user: str, passwd: str, cmd: str) -> int:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # lab/demo only

    try:
        client.connect(
            ip,
            port=port,
            username=user,
            password=passwd,
            look_for_keys=False,
            allow_agent=False,
            timeout=15.0,
            banner_timeout=15.0,
            auth_timeout=15.0,
        )
    except Exception as e:
        print(f"[-] SSH connect failed: {e}")
        return 255

    # optional keepalive
    try:
        transport = client.get_transport()
        if transport:
            transport.set_keepalive(30)
    except Exception:
        pass

    try:
        # get_pty=True improves behavior for certain commands
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=30.0)

        # Read all output
        out = stdout.read()
        err = stderr.read()

        # Exit status from the remote side
        status = stdout.channel.recv_exit_status()

        out_s = _to_text(out)
        err_s = _to_text(err)

        if out_s:
            print(out_s, end="" if out_s.endswith("\n") else "\n")
        if err_s:
            print(err_s, end="" if err_s.endswith("\n") else "\n", file=sys.stderr)

        print(f"--- Exit status: {status} ---")
        return status

    except Exception as e:
        print(f"[-] Command execution failed: {e}")
        return 255
    finally:
        client.close()

if __name__ == "__main__":
    try:
        user = input("Username: ").strip() or getpass.getuser()
        password = getpass.getpass("Password: ")
        ip = input("Enter server IP [192.168.56.101]: ").strip() or "192.168.56.101"
        port_str = input("Enter port [2222]: ").strip() or "2222"
        cmd = input("Enter command [whoami]: ").strip() or "whoami"
        port = int(port_str)
    except Exception as e:
        print(f"Input error: {e}")
        sys.exit(1)

    rc = ssh_command(ip, port, user, password, cmd)
    sys.exit(rc)
