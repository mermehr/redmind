# Engagement Overview — Monteverde

**Target:** Monteverde (10.10.10.172)  
**Domain:** MEGABANK.LOCAL  
**Test Date:** 2025-10-28  
**Report generated:** 2025-10-30 21:02:44Z

## Objectives

- Obtain an initial foothold on the target host
- Identify and recover credential material suitable for escalation
- Achieve full compromise and capture user and root flags

## Executive Summary

During a black-box assessment of the host `MONTEVERDE` (Windows Server 2019, build 17763) within the MEGABANK.LOCAL domain, a complete compromise was achieved by enumerating services, recovering credentials from accessible file shares and the ADSync database, and leveraging SQL Server functionality to extract credentials and escalate privileges to the domain Administrator account. Both `user.txt` and `root.txt` flags were obtained. The attack chain is documented in the accompanying technical sections.

## Credentials and Flags

**Credentials recovered during engagement:**

- `SABatchJobs:SABatchJobs`
- `mhope:4n0therD4y@n0th3r$`
- `administrator:d0m@in4dminyeah!`

**Flags:**

- user: `b9a355bd318db6299e9d1135b1391cd4`  
- root: `ce0899bf0e75ac4ced4945bd00e6613b`



