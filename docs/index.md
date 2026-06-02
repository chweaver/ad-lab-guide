# AD Lab Foundations

A reproducible Active Directory home lab on VMware Workstation. Two jobs: a personal quick-reference for "what do I do next" and a portfolio piece. It doubles as CompTIA A+ 220-1202 (Core 2) prep for objective 2.2 (Active Directory).

This is a **guide**, not a build log. Every phase is reproducible from a blank VM by following the steps exactly.

## What this lab is

A single-domain forest hosted in VMware Workstation Pro. One Server 2022 domain controller (`DC01`), one Windows 10/11 client (`WS01`), both on a host-only network (`VMnet1`, `192.168.100.0/24`). No internet routing in the lab subnet. Everything internal is resolved by AD-integrated DNS on the DC.

The build moves from a clean Server 2022 install through to a working domain with OUs, users, groups using AGDLP, GPOs, file shares, home folders, folder redirection, and login scripts. Stretch phases add DHCP, RDP, backup/restore, and a second DC for replication.

## Network topology

```
       Host (Windows 11)
              |
          VMnet1 host-only
       192.168.100.0/24
        /              \
   DC01                 WS01
 .100.5/24          .100.20/24
 DNS: 127.0.0.1     DNS: 192.168.100.5
 corp.lab           CORP\<user>
```

Both VMs live on the same subnet, so the domain join does not traverse any external router.

## Prerequisites

- **Host**: Windows 11 with VMware Workstation Pro installed. 16 GB RAM minimum, 32 GB recommended. SSD strongly preferred.
- **ISOs**: Server 2022 Standard Evaluation (Desktop Experience), Windows 10 or 11 Enterprise evaluation.
- **VMnet1**: configured as host-only with subnet `192.168.100.0/24`. Disable VMware's DHCP on VMnet1 (the DC handles DNS, and DHCP is a stretch goal).
- **Comfort level**: basic Windows admin, PowerShell open-a-prompt level, no prior AD experience needed.

## How to use the guide

1. Read [Reference](reference.md) once. It is the canonical table of every name, IP, and path used in the lab. Keep it open in a second tab.
2. Work phases in order. Each one assumes the prior phase finished cleanly.
3. After each verify step passes, take the snapshot the phase recommends. You will rely on these when something breaks.
4. [Gotchas](gotchas.md) collects every pitfall in one place. Skim it before each phase.
5. [Exam notes](exam-notes.md) is the CompTIA A+ 2.2 cheat sheet. Read it once after Phase 6 and again before sitting the exam.

## Phase status

| Phase | Title | Status |
|-------|-------|--------|
| 1 | Install Server 2022 + tools | Done |
| 2 | Pre-promotion config | Done |
| 3 | Promote to DC (new forest) | Done |
| 4 | OU structure | Done |
| 5 | Users | Done |
| 6 | Security groups + AGDLP | Done |
| 7 | Join a client (WS01) | **Next** |
| 8 | Group Policy basics + inheritance | Not started |
| 9 | File shares | Not started |
| 10 | Home folders + folder redirection | Not started |
| 11 | Login scripts + drive mapping | Not started |
| 12 | Help-desk admin drills | Not started |
| 13 | DHCP role | Stretch |
| 14 | RDP / remote access | Stretch |
| 15 | AD backup + restore | Stretch |
| 16 | Second DC + replication | Stretch |

!!! tip "Snapshots are not optional"
    Take a snapshot after every phase that the page recommends. Restoring is the fastest debug tool you have when a GPO or DNS change breaks the lab. Existing snapshots: `clean-install-tools-done`, `clean-dc-promoted`.
