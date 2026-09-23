## Linux Privilege Escalation: Sudo Session Hunting and Artifact Triage

**Primary Goal:** Find evidence of `sudo` activity and identify interactive sessions, background commands, or artifacts that indicate privilege escalation opportunities or traces to investigate.

**TL;DR:** This playbook provides quick, repeatable steps to detect active or recent `sudo` usage. It outlines how to identify sessions where elevated commands were executed and locate audit traces useful for privilege escalation, lateral movement, or post-engagement cleanup.

### High-Level Enumeration Flow

1. **Active Session Hunting:** Check for running `sudo` processes and interactive shells.
2. **Log Triage:** Inspect system authentication logs for recent `sudo` entries.
3. **Audit Traces:** Use `journalctl` and `ausearch` for systemd-based auditing traces.
4. **History Extraction:** Examine user shell history files for `sudo` and `su` commands.
5. **System Artifacts:** Search for SUID binaries, unusual cronjobs, and user service files.
6. **Network & Login Correlation:** Review recent logins and active network connections.

### Prerequisites

- Local or shell access with at least a low-privilege user context.
- Basic UNIX utilities present (`ps`, `last`, `grep`, `journalctl`, `ausearch` when available).
- *(Optional)* Access to `sudo` logs, which may be located under `/var/log/auth.log` (Debian/Ubuntu) or `/var/log/secure` (RHEL/CentOS). Note that paths and log names vary by distribution and syslog configuration.

### Step 1: Running Processes & Sessions

Identify currently active processes to catch administrators in the act of performing privileged actions.

```
# Show top processes with PID, user, and command
ps -eo pid,uid,user,group,cmd --sort=-pid | head -n 40

# Look for shells running as root or with a parent process linking to sudo
ps -ef | egrep "(sudo|root|sshd|bash|zsh|sh)" | less

# Find processes whose parent is sudo (heuristic check)
ps -o pid,ppid,user,cmd -ax | awk '$4 ~ /sudo/ {print}'
```

### Step 2: System Authentication Logs

Grep through standard authentication logs to find recent, historical use of the `sudo` command.

```
# Debian/Ubuntu systems
sudo grep --line-number 'sudo' /var/log/auth.log* | tail -n 200

# RHEL/CentOS systems
sudo grep --line-number 'sudo' /var/log/secure* | tail -n 200

# Filter by a specific username across both common log locations
sudo grep 'username' /var/log/auth.log* /var/log/secure* 2>/dev/null | tail -n 200
```

### Step 3: Journalctl & Audit (Systemd)

Modern Linux distributions rely heavily on `systemd`. Querying the journal and audit daemon can reveal highly structured logs of privileged execution.

```
# Show recent sudo events in the system journal
sudo journalctl -k | egrep -i 'sudo|authentication' | tail -n 200

# If auditd is present, search for recent user commands
sudo ausearch -m USER_CMD -i -ts recent
```

### Step 4: Shell History Investigation

Users frequently forget to clear their shell history. Searching these files can reveal plaintext passwords passed to scripts, or specific commands run with elevated privileges.

```
# Inspect common bash history files (check timestamps if preserved)
ls -la /home/*/.bash_history /root/.bash_history 2>/dev/null
grep -i 'sudo\|su' /home/*/.bash_history /root/.bash_history 2>/dev/null | tail -n 200

# Inspect zsh history files
grep -i 'sudo\|su' /home/*/.zhistory 2>/dev/null || true
```

### Step 5: SUID/Capable Binaries & Cron

Look for files that may grant elevated privileges automatically, or background tasks that execute as root.

```
# Fast scan for SUID files
sudo find / -perm -4000 -type f -print 2>/dev/null

# Look for suspicious cronjobs or systemd services invoking network tools or shells
sudo ls -la /etc/cron.* /var/spool/cron /etc/systemd/system 2>/dev/null
sudo grep -R --line-number "wget\|curl\|nc\|bash -c" /etc/cron* /etc/systemd/system 2>/dev/null | head
```

### Step 6: Recent Logins & Sessions

Correlate the execution artifacts you found with actual user logins and active network connections.

```
# Check who is currently logged in and recent login history
who -a
last -n 50

# Check ss or netstat for active connections (ESTABLISHED or LISTENING)
ss -tunap | egrep 'ESTAB|LISTEN' | head -n 40
```

## Operational Security (OPSEC) Considerations & Cleanup

### Red Flags to Investigate

- **Orphaned Sudo Entries:** `sudo` log entries without a corresponding recorded interactive login session.
- **History Anomalies:** Timestamps in history files that don't match session times, indicating potentially cleared or tampered history.
- **Unusual SUIDs:** SUID binaries with uncommon owners or located in unexpected, non-standard paths (e.g., `/tmp` or `/dev/shm`).
- **Malicious Cronjobs:** Cron entries invoking shells or remote fetch commands (e.g., `curl`, `wget`) often indicate persistence mechanisms.

### Cleanup Procedures

- **Do not arbitrarily delete logs on live targets.** Modifying `/var/log/auth.log` directly leaves obvious forensic evidence.
- If testing in a lab environment, utilize VM snapshots or rely on standard log rotation.
- Keep a short snippet of the commands used as a reproducible checklist, and document any modifications made during the engagement per your Rules of Engagement (RoE).
