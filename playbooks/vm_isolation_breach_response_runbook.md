# VM Isolation Breach (VM Escape/Side‑Channel)

**TL;DR**  
When you suspect a guest‑to‑host escape or cross‑VM data exfiltration (e.g., via speculative‑execution or device‑emulation bugs), **freeze blast radius**, **patch hypervisor + microcode**, **enforce CPU mitigations**, and **rotate secrets** that could have been read from host/hypervisor memory. Detection is weak; favor **containment and hardening**.

> Scope: KVM/QEMU (Linux), VMware ESXi, Xen/Citrix. Lab‑oriented but written as an operational checklist.

---

## Goals

- Contain possible guest‑to‑host (or cross‑VM) impact.  
- Verify and enforce CPU + hypervisor mitigations (Spectre‑class, device emulation).  
- Patch hypervisor stack; rotate sensitive credentials/keys possibly exposed.  
- Document decisions and evidence for after‑action review.

---

## Immediate Actions (All Platforms)

1. **Quarantine the suspect VM(s)**
   - Pause/suspend or snapshot **without powering down** if you need memory artifacts; otherwise **shutdown** to stop further leakage.
   - Block east‑west traffic between guests on the same host. Remove shared PCI devices where feasible.
2. **Host protection posture**
   - Restrict new VM startups on the host; disable live migrations *from* the suspect host until triaged.
   - Enable strict scheduling/isolation (CPU pinning; isolate SMT/HT for high‑risk tenants; consider disabling SMT temporarily).
3. **Evidence preservation**
   - Export hypervisor logs, VM event logs, and host kernel logs. Note timestamps of suspected activity.  
   - Record hypervisor build, CPU microcode, kernel versions, and mitigations state.
4. **Key/secret rotation plan**
   - Assume **memory disclosure**: plan to rotate disk‑encryption keys, hypervisor management creds, and secrets stored in host daemons.

---

## Verify Mitigation Status (Linux/KVM/QEMU)

- Check CPU vuln/mits:

```bash
cat /sys/devices/system/cpu/vulnerabilities/*
dmesg | egrep -i 'spectre|retbleed|ibrs|ibpb|mitigation'
```

- Ensure Spectre v2/BTI mitigations are active (kernel cmdline often includes `spectre_v2=on` or `mitigations=auto`/`auto,nosmt` on older distros).  
- For KVM guests: enforce **IBPB on VMEXIT** and related barriers via current kernels; update to a kernel/QEMU pair that implements recommended defaults.

### Patch & Configuration

```bash
# host
apt/yum update && reboot  # apply latest kernel, microcode, qemu-kvm
qemu-system-x86_64 --version
modinfo kvm
```

- Update **microcode** packages (Intel/AMD), **QEMU**, **libvirt**, and host kernel.  
- Regenerate guest XMLs (libvirt) to remove legacy device models (e.g., FDC, obsolete NICs) and enforce **virtio**‑only where safe.

### Hardening

- Disable unused emulated devices (floppy, IDE, legacy VGA paths).  
- Prefer **paravirtual** drivers (virtio) with current QEMU.  
- Use **vhost‑net offload** cautiously when threat model includes guest‑to‑host attack surface.  
- Consider **CPU model masking** and **EIBRS/IBPB/SSBD** enablement per vendor guidance.  
- Separate high‑risk tenants to dedicated hosts (no co‑tenancy).

---

## VMware ESXi

- **Apply current VMSA patches** on ESXi/Workstation/Fusion.  
- Verify EVC/microcode+IBRS/IBPB mitigations are applied per CPU family.  
- Limit co‑tenancy of untrusted workloads; restrict passthrough devices that expand attack surface.

### Checks

- Baseline: host build number, patch level, microcode revision.  
- Review logs for VMX exceptions and device emulation errors near the incident window.  
- Disable legacy virtual hardware where feasible; prefer modern virtual hardware versions.

---

## Xen / Citrix Hypervisor

- Patch to latest advisory build for guest‑to‑host isolation issues.  
- Review CPU feature flags; enforce branch‑predictor flushing between domains if supported.  
- Reduce shared‑resource exposure: disallow PCI passthrough to untrusted guests; isolate dom0 services.

---

## Forensics & Telemetry (Reality Check)

- **Spectre‑class attacks** typically leave minimal logs. Favor **configuration state + time alignment** over signature hunting.  
- Collect: hypervisor and host kernel logs, perf counters (if configured), QEMU stderr (if daemonized with logging), EDR/AV telemetry on hosts.  
- If you must memory‑dump: prioritize hypervisor userland (e.g., `qemu-system-*`) and management daemons.

---

## Secret & Credential Rotation

- Rotate:
  - Hypervisor/root management creds and API tokens.  
  - Disk/LUKS keys for host‑side encrypted volumes.  
  - Any vault/agent tokens present on host.  
  - Service account passwords cached by host daemons.
- Reissue guest secrets only **after** host rehardening.

---

## Validation & Regression

- Reboot hosts with updated kernel/microcode; confirm mitigations:  

```bash
dmesg | egrep -i 'spectre|ibpb|ibrs|eibrs'
cat /sys/devices/system/cpu/vulnerabilities/*
```

- Launch a **canary VM** and run a benign stress suite; validate performance impact and stability.  
- Run a curated lab harness to ensure VMEXIT/IBPB behavior is enforced (vendor tools or PoCs in a **closed** lab only).

---

## Preventive Architecture

- **Host classing**: separate untrusted/lab VMs from critical infra.  
- **Disable SMT** for high‑risk multi‑tenant hosts or enforce strong core isolation.  
- **Minimal device surface**: no legacy emulation; prefer virtio; avoid passthrough to untrusted tenants.  
- **Patch pipeline**: fast‑track hypervisor and microcode updates; regular drift checks.  
- **Secret hygiene**: minimize long‑lived secrets on hosts; hardware‑backed disk keys where possible.

---

## After‑Action

- Document timeline, versions, and mitigations applied.  
- Build a **playbook** for repeated checks during new disclosures (CPU, hypervisor, device emulation).  
- Schedule purple‑team exercises targeting VM isolation assumptions (lab‑only; never on prod tenants).
