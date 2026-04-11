# Python Netcat Replacement

This script is a Python re‑implementation of **netcat (`nc`)**, useful on systems where netcat is not installed. 

## Usage

The script uses command‑line arguments to mimic `nc` functionality.

Examples:

```bash
# Start a command shell on port 5555
python3 netcat.py -t 192.168.1.101 -p 5555 -l -c

# Upload a file to the server
python3 netcat.py -t 192.168.1.101 -p 5555 -l -u=mytest.txt

# Execute a command automatically when a client connects
python3 netcat.py -t 192.168.1.101 -p 5555 -l -e "cat /etc/passwd"

# Connect to a server and send text from stdin
echo 'ABC' | python3 netcat.py -t 192.168.1.101 -p 135

# Connect to a listening server interactively
python3 netcat.py -t 192.168.1.101 -p 5555
```

---

## Arguments

- `-t`, `--target` — Target IP (default: `192.168.1.203`)
- `-p`, `--port` — Target port (default: `5555`)
- `-l`, `--listen` — Listen mode (server mode)
- `-c`, `--command` — Start a command shell
- `-e`, `--execute` — Execute specified command
- `-u`, `--upload` — Upload file path to save received data

---

### Reference

These scripts are adapted from exercises in  **Black Hat Python, 2nd Edition** by Justin Seitz & Tim Arnold.  

They have been recreated here for personal study and educational purposes. The original book provides the full context, explanations, and ethical guidance for using these examples responsibly in security research.
