# SSH Command & Control Scripts

This dir contains a set of Python scripts built using the **Paramiko** library to demonstrate client-server command execution over SSH. The scripts are designed to work together as a minimal proof-of-concept for remote command execution and server emulation.

---

## Scripts Overview

`ssh-cmd.py`

A simple SSH client that connects to a target server and executes a single command.

- Prompts the user for credentials and server details.  
- Executes a command (default: `id`).  
- Prints standard output and error streams from the remote host.

---

`ssh-rcmd.py`

A client-side script that establishes a reverse SSH session to a server.  
Once connected, it can receive and execute commands issued by the server.

- Connects to a remote SSH server with provided credentials.  
- Waits for server instructions and executes commands locally.  
- Sends command results back to the server.

---

`ssh-server.py`

A custom SSH server that listens for incoming connections and provides an interactive command execution environment.

- Uses Paramiko’s `Transport` and `ServerInterface`.  
- Authenticates with hardcoded credentials (`tim:sekret`).  
- Supports interactive command execution until `exit` is issued.  
- Requires an RSA host key (`test_rsa.key`) in the same directory.

---

## Requirements

- Python 3.8+  
- [Paramiko](https://www.paramiko.org/)  

Install dependencies:

```bash
pip install paramiko
```
---

### Reference

These scripts are adapted from exercises in  **Black Hat Python, 2nd Edition** by Justin Seitz & Tim Arnold.  

They have been recreated here for personal study and educational purposes. The original book provides the full context, explanations, and ethical guidance for using these examples responsibly in security research.

