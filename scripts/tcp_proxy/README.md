# TCP Proxy Tool

This script (`proxy.py`) is a simple TCP proxy designed for inspecting, relaying, and optionally modifying traffic between a local client and a remote host. It's useful for debugging, learning protocol structures, and performing man-in-the-middle style analysis in controlled environments.

------------------------------------------------------------------------

## Usage

``` bash
python3 proxy.py [localhost] [localport] [remotehost] [remoteport] [receive_first]
```

### Example

``` bash
python3 proxy.py 127.0.0.1 9000 example.com 80 True
```

- `localhost`: Local interface to listen on (e.g., `127.0.0.1`)
- `localport`: Local port to bind (e.g., `9000`)
- `remotehost`: Remote host to connect to (e.g., `example.com`)
- `remoteport`: Remote port to connect to (e.g., `80`)
- `receive_first`: `True` if the remote server sends data immediately upon connection (common with some banners or protocol greetings), else `False`.

---

### Reference

These scripts are adapted from exercises in  **Black Hat Python, 2nd Edition** by Justin Seitz & Tim Arnold.  

They have been recreated here for personal study and educational purposes. The original book provides the full context, explanations, and ethical guidance for using these examples responsibly in security research.
