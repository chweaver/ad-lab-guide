# Reference

Canonical lab facts. Every command and screenshot in this guide uses these exact values. Bookmark this page.

## Forest and domain

| Item | Value |
|------|-------|
| DNS domain name | `corp.lab` |
| NetBIOS name | `CORP` |
| Forest functional level | Windows Server 2016 |
| Domain functional level | Windows Server 2016 |
| AD database path | `C:\Windows\NTDS` (default) |
| SYSVOL path | `C:\Windows\SYSVOL` (default) |
| Time zone | Eastern |

!!! note "Why `.lab` and not `.local`"
    Apple's Bonjour service uses `.local` for mDNS. Mixing it with an AD domain creates name-resolution conflicts on any client running Bonjour (iTunes, AirPrint, Visual Studio installers). Use `.lab`, `.test`, or a real domain you own.

## Hypervisor

| Item | Value |
|------|-------|
| Product | VMware Workstation Pro on a Windows host |
| Lab adapter | `VMnet1` (host-only) |
| Lab subnet | `192.168.100.0/24` |
| Lab gateway | `192.168.100.1` (unused inside the lab so far) |

## Domain controller

| Item | Value |
|------|-------|
| VM name | `Windows-Server-2022-base` |
| Hostname | `DC01` |
| OS | Windows Server 2022 Standard (Evaluation), Desktop Experience |
| Firmware / disk | UEFI + TPM, NVMe |
| IPv4 | `192.168.100.5/24` |
| Gateway | `192.168.100.1` |
| Preferred DNS | `127.0.0.1` (points at itself) |
| Adapter | `VMnet1` |

## Client

| Item | Value |
|------|-------|
| Hostname | `WS01` |
| OS | Windows 10 or 11 Enterprise (Evaluation) |
| IPv4 | `192.168.100.20/24` |
| Gateway | `192.168.100.1` |
| Preferred DNS | `192.168.100.5` (the DC, never pfSense or external) |
| Adapter | `VMnet1` |

## OU tree

```
corp.lab
+-- Departments        (parent OU)
|   +-- IT
|   +-- Sales
|   +-- HR
+-- Workstations       (sibling of Departments)
```

!!! note "Why `Departments` and not `Users`"
    AD already ships a built-in `CN=Users` container at the domain root. Naming a custom OU `Users` causes an RDN collision on creation. `Departments` sidesteps it and reads more clearly.

## Users (12 total)

All users have **password never expires: ON** and **user must change password at next logon: OFF** for lab convenience. Do not copy those settings to a production environment.

| OU | Username | Display name |
|----|----------|--------------|
| IT | `jsmith` | J Smith |
| IT | `jreed` | J Reed |
| IT | `mhale` | M Hale |
| IT | `squinn` | S Quinn |
| Sales | `mtate` | M Tate |
| Sales | `vcarr` | V Carr |
| Sales | `mdunn` | M Dunn |
| Sales | `glowe` | G Lowe |
| HR | `dfrost` | D Frost |
| HR | `jcole` | J Cole |
| HR | `tmarsh` | T Marsh |
| HR | `spark` | S Park |

## Group naming convention

| Scope | Pattern | Purpose |
|-------|---------|---------|
| Global | `<Dept>-Staff` (e.g. `IT-Staff`) | Role / membership. Users go in here. |
| Domain Local | `<Dept>-<Resource>-<Access>` (e.g. `IT-Share-RW`) | Resource access. Permissions get assigned to this group. |

Each group lives inside its department OU.

### AGDLP example already built (IT)

```
[ IT users ]   →   IT-Staff (Global, Security)   →   IT-Share-RW (Domain Local, Security)   →   NTFS permissions on the share
   A                       G                                       DL                                            P
```

- **A**ccount, **G**lobal group, **D**omain **L**ocal group, **P**ermission.
- Users (A) are members of a Global group (G).
- The Global group (G) is nested inside a Domain Local group (DL).
- Permissions (P) are assigned to the Domain Local group only.

## File shares (on DC01)

| Share | Local path | Purpose |
|-------|------------|---------|
| `Home$` | `C:\Shares\Home` | Per-user home folder targets (`H:` drive) |
| `Redirect$` | `C:\Shares\Redirect` | Folder-redirection targets (Documents, Desktop, etc.) |

The trailing `$` hides the share from network browsing. Anyone who knows the path can still connect.

## Snapshots

| Name | When taken | Purpose |
|------|------------|---------|
| `clean-install-tools-done` | After Phase 1 | Roll back to a fresh, patched Server 2022 with VMware Tools. |
| `clean-dc-promoted` | After Phase 3 | Roll back to a working DC before users, GPOs, or shares exist. |
| `clean-domain-joined` | After Phase 7 (planned) | WS01 joined, no GPOs applied yet. |

## Common command quick-pick

```powershell
# Identity / health
whoami
hostname
Get-ComputerInfo | Select-Object CsName, CsDomain, CsDomainRole, OsName, OsVersion

# DNS / connectivity from a client
ipconfig /all
nslookup corp.lab
ping dc01.corp.lab

# AD inventory (from DC01)
Get-ADDomain
Get-ADForest
Get-ADOrganizationalUnit -Filter * | Select-Object Name, DistinguishedName
Get-ADUser -Filter * -SearchBase "OU=Departments,DC=corp,DC=lab" | Select-Object SamAccountName, DistinguishedName
Get-ADGroup -Filter * -SearchBase "OU=Departments,DC=corp,DC=lab" | Select-Object Name, GroupScope, GroupCategory

# GPO
gpupdate /force
gpresult /r
```
