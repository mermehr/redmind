# Sudo - Session Hunting

**TL;DR**  
Quick, repeatable steps to detect active or recent `sudo` usage, identify sessions where elevated commands ran, and locate audit traces useful for escalation or cleanup.

## Goal

- Find evidence of `sudo` activity and identify interactive sessions, background commands, or artifacts that indicate privilege escalation opportunities or traces to investigate.

## Prerequisites

- Local or shell access with at least low-privilege user context.  
- Basic UNIX utilities present (`ps`, `last`, `grep`, `journalctl`, `ausearch` when available).  
- (Optional) `sudo` logs may be under `/var/log/auth.log` (Debian/Ubuntu) or `/var/log/secure` (RHEL/CentOS).

> **Note:** paths and log names vary by distro and syslog configuration.

---

## Quick Checklist (high level)

1. Check for running `sudo` processes and interactive shells.
2. Inspect auth logs for recent `sudo` entries.
3. Examine shell history files for `sudo` and `su` commands.
4. Search for SUID binaries, unusual cronjobs, and user service files.
5. Use audit logs (`ausearch`) and `journalctl` for systemd-based auditing traces.

---

## Commands

### 1) Running processes & sessions

- Show processes with PID, user, and command:

```bash
ps -eo pid,uid,user,group,cmd --sort=-pid | head -n 40
```

- Look for shells running as root or with parent process linking to `sudo`:

```bash
ps -ef | egrep "(sudo|root|sshd|bash|zsh|sh)" | less
```

- Find processes whose parent is `sudo` (heuristic):

```bash
ps -o pid,ppid,user,cmd -ax | awk '$4 ~ /sudo/ {print}'
```

### 2) System authentication logs

- Debian/Ubuntu:

```bash
sudo grep --line-number 'sudo' /var/log/auth.log* | tail -n 200
```

- RHEL/CentOS:

```bash
sudo grep --line-number 'sudo' /var/log/secure* | tail -n 200
```

- Filter by a username:

```bash
sudo grep 'username' /var/log/auth.log* /var/log/secure* 2>/dev/null | tail -n 200
```

### 3) Journalctl & audit (systemd)

- Show recent sudo events in system journal:

```bash
sudo journalctl -k | egrep -i 'sudo|authentication' | tail -n 200
```

- If `auditd` present:

```bash
sudo ausearch -m USER_CMD -i -ts recent  # requires audit binary
```

### 4) Shell history investigation

- Inspect common history files:

```bash
ls -la /home/*/.bash_history /root/.bash_history 2>/dev/null
grep -i 'sudo\|su' /home/*/.bash_history /root/.bash_history 2>/dev/null | tail -n 200
```

- For `zsh`:

```bash
grep -i 'sudo\|su' /home/*/.zhistory 2>/dev/null || true
```

> Tip: check timestamps (if preserved) and compare across users.

### 5) SUID/Capable binaries & cron

- Find SUID files (fast scan):

```bash
sudo find / -perm -4000 -type f -print 2>/dev/null
```

- Look for suspicious cronjobs or systemd services:

```bash
sudo ls -la /etc/cron.* /var/spool/cron /etc/systemd/system 2>/dev/null
sudo grep -R --line-number "wget\|curl\|nc\|bash -c" /etc/cron* /etc/systemd/system 2>/dev/null | head
```

### 6) Recent logins & sessions

- Who and last:

```bash
who -a
last -n 50
```

- Check `ss` or `netstat` for active connections:

```bash
ss -tunap | egrep 'ESTAB|LISTEN' | head -n 40
```

---

## Red Flags

- `sudo` entries without a corresponding recorded interactive login.  
- Timestamps in history files that don't match session times (possible cleared history).  
- SUID binaries with uncommon owners or in unexpected paths.  
- Cron entries invoking shells or remote fetch commands.

## Clean artifacts & notes

- Avoid removing logs on live targets. For playground cleanup in lab: rotate logs or snapshot VMs.  
- Keep a short snippet of commands used as a reproducible checklist (see cheatsheet).

## Follow-ups

- Triaging specific suspicious commands from history; pivot to enumerating file permissions for binaries found; check for network-based persistence mechanisms.
