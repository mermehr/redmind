# Parrot Lab (Docker)

A minimal, no-bullshit Parrot Security workstation running in Docker with GUI apps, host networking, and a persistent home. No VM drama, full CPU, reverse shells.

---

## First run

```bash
# Allow GUI apps from containers to show on your desktop
xhost +local:docker

# Create & enter a Parrot container with host networking + X11 + persistence
docker run -it --name parrot-x11 \
  --network host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $HOME/parrot-home:/root \
  --cap-add=NET_ADMIN --cap-add=NET_RAW \
  --device /dev/net/tun \
  parrotsec/security bash
```

Inside the container, install the starter toolkit:

```bash
apt update && apt install -y \
  metasploit-framework hydra gobuster ffuf nmap \
  wireshark burpsuite seclists curl wget git python3-pip \
  john hashcat enum4linux smbclient ldap-utils netcat-traditional \
  sqlmap dirb nikto aircrack-ng
```

PowerShell (optional):

```bash
apt install -y wget apt-transport-https software-properties-common
wget -q "https://packages.microsoft.com/config/debian/11/packages-microsoft-prod.deb"
dpkg -i packages-microsoft-prod.deb
apt update && apt install -y powershell
# launch:
pwsh
```

---

## Daily usage

```bash
# Re-enter later (tools/configs persist in ~/parrot-home)
docker start -ai parrot-x11
```

Detached + extra shell:

```bash
docker start parrot-x11
docker exec -it parrot-x11 bash
```

Re-allow X after reboot/X-restart:

```bash
xhost +local:docker
```

---

## Why

- Shares the **host kernel** (no OS boot, no hypervisor).
- X11 connects to your host’s display; no desktop stack inside.
- Host networking (`--network host`) = listeners bind directly to your VPN/host interfaces.

---

## Reverse shells & networking

- **Default here = host networking**: reverse shells into Parrot behave like bare metal (bind/listen on your HTB/Tun interface directly).
- If you ever switch to **bridge mode**:
  - Outbound reverse shells from Parrot → OK (NAT).
  - Inbound to Parrot → publish ports: `-p 4444:4444` **or** use `--network host`.

---

## One-liner re-create

```bash
xhost +local:docker && docker run -it --name parrot-x11 \
  --network host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $HOME/parrot-home:/root \
  --cap-add=NET_ADMIN --cap-add=NET_RAW \
  --device /dev/net/tun \
  parrotsec/security bash
```

Reinstall tools:

```bash
apt update && apt install -y \
  metasploit-framework hydra gobuster ffuf nmap \
  wireshark burpsuite seclists curl wget git python3-pip \
  john hashcat enum4linux smbclient ldap-utils netcat-traditional \
  sqlmap dirb nikto aircrack-ng
```

---

## Tiny launcher script (host)

`~/bin/parrot.sh`:

```bash
#!/usr/bin/env bash
set -e
xhost +local:docker >/dev/null 2>&1 || true
docker ps -a --format '{{.Names}}' | grep -qx parrot-x11 && exec docker start -ai parrot-x11
exec docker run -it --name parrot-x11 \
  --network host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "$HOME/parrot-home":/root \
  --cap-add=NET_ADMIN --cap-add=NET_RAW \
  --device /dev/net/tun \
  parrotsec/security bash
```

```bash
chmod +x ~/bin/parrot.sh
parrot.sh
```

---

## Resource limits

```bash
# e.g., 2 CPUs, 4GB RAM
docker run -it --name parrot-x11 \
  --cpus=2 --memory=4g \
  --network host -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix -v $HOME/parrot-home:/root \
  --cap-add=NET_ADMIN --cap-add=NET_RAW --device /dev/net/tun \
  parrotsec/security bash
```

---

## noVNC desktop

If X11 is annoying, run a lightweight XFCE desktop in-browser:

```bash
docker run -it --name parrot-vnc -p 6901:6901 \
  -v $HOME/parrot-home:/root \
  parrotsec/security bash -lc '
    apt update &&
    apt install -y xfce4 xfce4-terminal dbus-x11 tigervnc-standalone-server novnc websockify &&
    tigervncserver :1 -localhost no -geometry 1920x1080 -depth 24 &&
    websockify --web=/usr/share/novnc/ 6901 localhost:5901'
```

Open `http://localhost:6901` → XFCE desktop (no GPU/X11 on host required).

---

## Cleanup

```bash
docker stop parrot-x11
docker rm parrot-x11
# remove persistent home if you really want to
rm -rf $HOME/parrot-home
```

---
