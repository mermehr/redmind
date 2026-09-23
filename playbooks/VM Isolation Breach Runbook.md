## Incident Response: VM Isolation Breach (VM Escape / Side-Channel)

**Primary Goal:** Contain suspected guest-to-host escapes or cross-VM data exfiltration incidents, enforce hypervisor and CPU mitigations, rotate potentially compromised host secrets, and harden the environment against subsequent attacks.

**TL;DR:** When a VM escape or side-channel attack (e.g., speculative-execution or device-emulation bugs) is suspected, immediately freeze the blast radius by quarantining the VM. Prioritize patching the hypervisor and microcode, enforcing CPU mitigations (like IBPB/IBRS), and rotating any secrets that may have been read from host memory. Detection is often weak for these vulnerabilities; focus heavily on containment and proactive hardening.

*Scope: KVM/QEMU (Linux), VMware ESXi, Xen/Citrix. Lab-oriented but written as an operational checklist.*

### High-Level Response Flow

1. **Quarantine & Containment:** Isolate the suspect VM, block east-west traffic, and restrict host scheduling.
2. **Evidence Preservation:** Export hypervisor, kernel, and VM event logs before altering the host state.
3. **Verification & Patching:** Check current mitigation status and aggressively patch the hypervisor stack and CPU microcode.
4. **Platform-Specific Hardening:** Apply hardening specific to KVM, ESXi, or Xen (e.g., disabling legacy emulated devices).
5. **Secret Rotation:** Treat host memory as compromised and rotate all hypervisor management credentials and disk keys.
6. **Validation & Architecture Update:** Verify mitigations with canary VMs and adjust host architecture (e.g., tenant classing, disabling SMT).

### Step 1: Immediate Actions (All Platforms)

**1. Quarantine the Suspect VM(s)**

- Pause/suspend or snapshot the VM **without powering down** if you require memory artifacts for forensics.
- If memory forensics are not required, **shutdown** the VM immediately to stop further data leakage.
- Block east-west traffic between guests on the same host and remove shared PCI devices where feasible.

**2. Enforce Host Protection Posture**

- Restrict new VM startups on the affected host.
- Disable live migrations *from* the suspect host until it is fully triaged.
- Enable strict scheduling/isolation (CPU pinning; isolate SMT/HT for high-risk tenants; consider disabling SMT temporarily).

**3. Preserve Evidence**

- Export hypervisor logs, VM event logs, and host kernel logs. Note the precise timestamps of the suspected activity.
- Record the current hypervisor build, CPU microcode version, kernel versions, and hardware mitigation state.

### Step 2: Verify Mitigations and Patch (Linux/KVM/QEMU)

Check the current CPU vulnerabilities and mitigation status via the sysfs interface and kernel ring buffer.

```
# Check hardware vulnerabilities and active mitigations
cat /sys/devices/system/cpu/vulnerabilities/*
dmesg | egrep -i 'spectre|retbleed|ibrs|ibpb|mitigation'
```

*Ensure Spectre v2/BTI mitigations are active (kernel cmdline often includes `spectre_v2=on` or `mitigations=auto`/`auto,nosmt` on older distros). For KVM guests, enforce **IBPB on VMEXIT**.*

**Patch and Configure:**

```
# Update host kernel, microcode, and hypervisor components
apt update && apt upgrade -y && reboot  # Debian/Ubuntu
# OR
yum update -y && reboot                 # RHEL/CentOS

# Verify updated versions
qemu-system-x86_64 --version
modinfo kvm
```

**KVM Hardening:**

- Regenerate guest XMLs (libvirt) to remove legacy device models (e.g., FDC, obsolete NICs) and enforce **virtio**-only where safe.
- Disable unused emulated devices (floppy, IDE, legacy VGA paths).
- Use **vhost-net offload** cautiously when your threat model includes guest-to-host attack surfaces.

### Step 3: Platform-Specific Hardening (VMware ESXi & Xen)

**VMware ESXi**

- **Patching:** Apply current VMSA patches on ESXi/Workstation/Fusion immediately.
- **Mitigations:** Verify EVC/microcode + IBRS/IBPB mitigations are applied per your specific CPU family.
- **Checks:** Review baseline host build numbers and logs for VMX exceptions or device emulation errors near the incident window.
- **Hardening:** Disable legacy virtual hardware where feasible; prefer modern virtual hardware versions and limit co-tenancy of untrusted workloads.

**Xen / Citrix Hypervisor**

- **Patching:** Update to the latest advisory build specifically addressing guest-to-host isolation issues.
- **Mitigations:** Review CPU feature flags; enforce branch-predictor flushing between domains if supported.
- **Hardening:** Disallow PCI passthrough to untrusted guests and strongly isolate `dom0` services.

### Step 4: Forensics & Telemetry (Reality Check)

Spectre-class and side-channel attacks typically leave minimal to no logs. **Favor configuration state analysis and time alignment over traditional signature hunting.**

- **Collect:** Hypervisor and host kernel logs, performance counters (if configured), QEMU stderr (if daemonized with logging), and EDR/AV telemetry on the hosts.
- **Memory Forensics:** If you must memory-dump, prioritize hypervisor userland processes (e.g., `qemu-system-*`) and management daemons rather than the entire host memory.

### Step 5: Secret and Credential Rotation

Assume **memory disclosure** has occurred. Any secrets held in the host's RAM during the attack window must be considered compromised.

**Rotate the following immediately:**

- Hypervisor/root management credentials and API tokens.
- Disk/LUKS keys for host-side encrypted volumes.
- Any vault/agent tokens present on the host.
- Service account passwords cached by host daemons.

*Note: Reissue guest-specific secrets only **after** the host has been successfully re-hardened.*

## Post-Incident Actions & Preventive Architecture

### Validation & Regression

Once the host is patched and rebooted, confirm the mitigations are actively loaded:

```
dmesg | egrep -i 'spectre|ibpb|ibrs|eibrs'
cat /sys/devices/system/cpu/vulnerabilities/*
```

- Launch a **canary VM** and run a benign stress suite to validate performance impact and system stability.
- Run a curated lab harness to ensure VMEXIT/IBPB behavior is enforced (execute vendor tools or PoCs in a **closed** lab only).

### Preventive Architecture (After-Action)

- **Host Classing:** Strictly separate untrusted/lab VMs from critical infrastructure. Do not mix trust levels on the same silicon.
- **SMT Management:** Disable SMT (Hyper-Threading) for high-risk multi-tenant hosts or enforce strong core isolation.
- **Minimal Device Surface:** Completely remove legacy emulation. Prefer paravirtualized drivers (`virtio`) and avoid passthrough to untrusted tenants.
- **Patch Pipeline:** Fast-track hypervisor and microcode updates, implementing regular configuration drift checks.
- **Secret Hygiene:** Minimize the lifespan of secrets on hosts and rely on hardware-backed disk keys (TPM) where possible.
