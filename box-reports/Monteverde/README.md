# Monteverde — Hack The Box Engagement Report

**Author:** mermehr  
**Last Updated:** 2025-10-30  
**Platform:** Hack The Box  
**Category:** Active Directory / Windows Privilege Escalation  

---

## Summary

This repository contains my structured technical report for the **Monteverde** target from Hack The Box.  
The goal of this exercise was to obtain an initial foothold, enumerate domain components, and escalate privileges to achieve full system compromise.  

Each phase of the engagement has been documented in a dedicated Markdown file for transparency and reproducibility.  
The report mirrors a professional red team or penetration testing workflow.

---

## Report Files

| Phase | File | Focus |
|-------|------|-------|
| 01 | [01-Overview.md](./01-Overview.md) | Engagement overview and objectives |
| 02 | [02-Enumeration.md](./02-Enumeration.md) | Service and domain enumeration |
| 03 | [03-Foothold.md](./03-Foothold.md) | Initial access via SMB and credential discovery |
| 04 | [04-MSSQL.md](./04-MSSQL.md) | MSSQL / ADSync enumeration and exploitation |
| 05 | [05-Privesc.md](./05-Privesc.md) | Privilege escalation and recommendations |

For a complete walkthrough, see the [index.md](./index.md) file.

---

## Tools and Techniques

This engagement leveraged a range of enumeration and exploitation tools commonly used in Active Directory assessments, including:

- `nmap`, `enum4linux-ng`, `smbmap`, `netexec`
- `evil-winrm`, `bloodhound-python`, `PowerUpSQL`
- `winPEAS`, `Seatbelt`, and custom PowerShell payloads

---

## Purpose

This report demonstrates practical methodology, documentation style, and technical competence for red team and penetration testing workflows.  
It serves both as a portfolio example and as a reusable internal reference for future AD-based assessments.

---

