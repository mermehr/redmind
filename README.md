# RedMind 

My digital landfill. What’s here is what actually matters to me: working binaries that shouldn’t exist but do, write-ups that reflect real decision-making under pressure, curated playbooks for techniques that I actually want at hand during an engagement, and some curated box reports.

This is a growing record of adaptability, break-fix mindset and forward-compatibility obsession. If something broke because it was built for glibc 2.39 and I only had 2.31, I rebuilt it, documented how, and left a breadcrumb for anyone else stuck in dependency hell.

## Inside

- **[Binaries](https://github.com/mermehr/static-binaries)** – Legacy-compatible, rebuilt tools for old systems. If something refused to run on older systems, I'll make it behave.
  - Moved and maintained in linked repo


- **Reports** – HTB and lab machines. Each entry contains enumeration notes, exploit chains, and privilege escalation steps.
- **Playbooks** – Condensed tactical procedures for things I want muscle memory on (Shadow Creds, ADCS relay, pivot chains, etc). These are just field notes.
- **Scripts** – Small tools and helpers I wrote myself. Imperfect, but mine. Everything here actually came from problem-solving, and necessity.
- **Write-Ups** – Long-form pieces where I break something down cleanly, usually after I’ve had enough distance to explain it properly.

## Why

I wanted a place that reflects how I operate: direct, adaptable and not allergic to dirty work. I value backwards compatibility, controlled chaos, and having working artifacts I can drop into a target without praying for matching library versions. I also value transparency, if I pivoted through a DMZ box using Ligolo, I want the sequence written exactly how it happened.

If someone stumbles across this repo and finds something useful, great. But it exists first and foremost as my offensive bench, a kit that evolves as I do.
