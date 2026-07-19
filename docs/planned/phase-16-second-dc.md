# Phase 16: Second DC on Server 2025 and replication

**Status:** Not started. Planned; promoted from stretch with Security+ as the target, and the gateway to hybrid identity (Phase 17).

**Goal:** Build `DC02` on **Windows Server 2025**, promote it into `corp.lab`, confirm two-way replication, and move one FSMO role to it. End state: two DCs on different OS versions, both authoritative, replicating bidirectionally.

**What this proves:** I can take a domain from single point of failure to resilient, and I understand the fact new admins miss most: DC OS version and functional level are independent. Supports SY0-701: 3.4 (high availability, resilience).

The mixed-version pair is the realistic enterprise case (you almost never rebuild every DC at once), and a resilient two-DC domain is the right starting point for Phase 17, where this domain syncs to the cloud.

## Prerequisites

- A healthy `DC01` with the domain populated (Phases 1 through 4). Phases 13 to 15 are not required first.
- About 4 GB of host RAM free for a second VM (8 GB if you can spare it; Server 2025 runs fine on 4).
- A Windows Server 2025 ISO (Standard Evaluation, Desktop Experience).
- Logged in as `CORP\Administrator`, which in a single-domain forest is already a member of Schema Admins and Enterprise Admins. (Why this matters: promoting the first Server 2025 DC extends the schema, and only those two groups can do that.)

!!! note "Schema extension happens automatically on the first newer-OS DC"
    The first time you add a domain controller running a newer Windows Server version, the promotion extends the AD schema to that version's level (the old `adprep /forestprep` and `/domainprep` step). `Install-ADDSDomainController` runs adprep for you when your account has the rights above. The forest schema version moves up; the functional level does not. [VERIFY] the exact Server 2025 schema object-version number against Microsoft docs before quoting it.

## Steps

### Part 1: Build DC02 (Server 2025)

1. Build a fresh Server 2025 VM with the same hardware pattern as DC01: UEFI + TPM, NVMe, `VMnet1`, 4 GB RAM, 2 vCPU. (Why match the pattern: a consistent VM spec keeps snapshots and troubleshooting predictable.)
2. Boot, set the time zone to **Eastern**. (Why: time skew over 5 minutes breaks Kerberos and will block the promotion.)
3. Rename to `DC02`, assign static IP `192.168.100.6/24`, gateway `192.168.100.1`, **DNS = `192.168.100.5` (DC01)**.

   ```powershell
   Rename-Computer -NewName DC02 -Restart
   ```

   After reboot:

   ```powershell
   $nic = (Get-NetAdapter | Where-Object Status -eq Up).Name
   New-NetIPAddress -InterfaceAlias $nic `
       -IPAddress 192.168.100.6 -PrefixLength 24 `
       -DefaultGateway 192.168.100.1
   Set-DnsClientServerAddress -InterfaceAlias $nic -ServerAddresses 192.168.100.5
   ```

   (Why point DNS at DC01: the promotion has to resolve the domain's SRV records, which only the existing DC's AD-integrated DNS knows.)

4. Confirm DC02 can resolve and reach DC01 before promoting:

   ```powershell
   nslookup corp.lab
   Test-NetConnection dc01.corp.lab -Port 389   # LDAP reachability
   ```

   (Why test 389: a successful LDAP connection proves the exact path the promotion uses is open.)

### Part 2: Join and promote DC02

5. Install the role and promote in one step (promotion performs the domain join and the schema extension):

   ```powershell
   Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools

   Install-ADDSDomainController `
       -DomainName "corp.lab" `
       -InstallDns:$true `
       -Credential (Get-Credential corp\Administrator) `
       -DatabasePath "C:\Windows\NTDS" `
       -SysvolPath   "C:\Windows\SYSVOL" `
       -LogPath      "C:\Windows\NTDS" `
       -SiteName     "Default-First-Site-Name" `
       -NoGlobalCatalog:$false `
       -Force
   ```

   You will set a DSRM password for DC02 (separate from DC01's; record it offline). (Why DSRM is per-DC: Directory Services Restore Mode is a local recovery account on each DC, not a domain account.)

6. After the auto-reboot, set DC02's DNS to point at **DC01 first, itself second**:

   ```powershell
   $nic = (Get-NetAdapter | Where-Object Status -eq Up).Name
   Set-DnsClientServerAddress -InterfaceAlias $nic `
       -ServerAddresses ("192.168.100.5","127.0.0.1")
   ```

7. On DC01, cross-point its DNS at **DC02 first, itself second**:

   ```powershell
   $nic = "Ethernet0"
   Set-DnsClientServerAddress -InterfaceAlias $nic `
       -ServerAddresses ("192.168.100.6","127.0.0.1")
   ```

   (Why cross-point: if one DC dies and each had pointed only at itself, the survivor still registers and resolves records through the peer instead of deadlocking on the dead box.)

### Part 3: Confirm replication

8. From DC01, confirm both DCs and a clean topology:

   ```powershell
   Get-ADDomainController -Filter * |
       Select-Object Name, IPv4Address, OperatingSystem, Site, IsGlobalCatalog, OperationMasterRoles

   repadmin /showrepl
   repadmin /replsummary
   Get-ADReplicationPartnerMetadata -Target "corp.lab" -Scope Domain |
       Select-Object Server, Partner, LastReplicationSuccess
   ```

   `OperatingSystem` should show DC01 as Server 2022 and DC02 as Server 2025, proving the mixed-version pair. No "last failure" entries should appear.

9. Prove an object created on DC01 replicates to DC02:

   ```powershell
   # On DC01
   New-ADUser -SamAccountName replicatest `
       -Name "Repl Test" `
       -Path "OU=IT,OU=Departments,DC=corp,DC=lab" `
       -AccountPassword (Read-Host -AsSecureString) `
       -Enabled $true

   repadmin /syncall /AdeP

   # On DC02
   Get-ADUser replicatest -Server DC02
   ```

   The user appears on DC02. Replication works. (Why force the sync: `/syncall /AdeP` pushes immediately so you are not waiting on the default intra-site delay.)

### Part 4: Move one FSMO role

There are five FSMO roles. Two are forest-wide (Schema Master, Domain Naming Master). Three are domain-wide (PDC Emulator, RID Master, Infrastructure Master). All five start on DC01. Move just the **Infrastructure Master** to DC02 as practice:

```powershell
Move-ADDirectoryServerOperationMasterRole `
    -Identity "DC02" `
    -OperationMasterRole InfrastructureMaster `
    -Confirm:$false

# Verify
netdom query fsmo
```

??? info "Which DC should hold which FSMO role"
    - **PDC Emulator**: time source for the domain. Put it on the most-reliable DC.
    - **RID Master**: hands out blocks of RIDs (the part of a SID unique to a domain). Lightweight; put it anywhere reachable.
    - **Infrastructure Master**: tracks cross-domain object references. In a single-domain forest the rule is "do not put this on a Global Catalog," with one exception: if every DC is a GC (the common case), it does not matter. In the lab both DCs are GCs, so it does not matter.
    - **Schema Master / Domain Naming Master**: only matter during schema extension (Exchange install, a newer-OS DC, etc.). Park them on DC01.

## Screenshot

- Capture: `repadmin /replsummary` clean output plus `Get-ADDomainController` showing the 2022 + 2025 pair. Save as `img/phase-16-replication.png`. Slot reserved, phase not started.

## Verify

```powershell
Get-ADDomainController -Filter * | Select-Object Name, OperatingSystem, OperationMasterRoles
repadmin /replsummary
dcdiag /e /test:replications
netdom query fsmo
```

!!! success "Pass criteria"
    - Two DCs returned by `Get-ADDomainController`, one Server 2022, one Server 2025.
    - `repadmin /replsummary` shows recent success in both directions, no failures.
    - `dcdiag /e /test:replications` passes on both DCs (time/NTP warnings in an isolated lab are fine to note and ignore).
    - `netdom query fsmo` shows DC01 holding four roles and DC02 holding Infrastructure Master.

## Snapshot

After replication is confirmed, snapshot **both DCs together**. Name them `clean-2dc-replicating-01` and `clean-2dc-replicating-02`.

!!! danger "Never roll back one DC alone past the last replication"
    With two DCs, rolling back **one** past the last successful replication triggers USN rollback: the other DC sees the rolled-back DC reissue a USN it has already seen and quarantines it. Snapshot both DCs at the same instant and roll them back together.

## Gotchas

!!! danger "USN rollback is the price of snapshotting a multi-DC AD"
    The mechanism that keeps replication consistent (USNs) cannot tell "this DC was rolled back" from "this DC is corrupt," so it isolates the offender. The safe options:

    - Snapshot all DCs at the same instant and roll all of them back together.
    - Demote and re-promote a single broken DC instead of restoring it.
    - Since Server 2012, restore from a System State backup so AD knows the restore is deliberate.

!!! warning "A newer-OS DC does not raise your functional level"
    Adding DC02 on Server 2025 leaves the domain and forest at the Server 2016 functional level you set in Phase 3. The level only rises when you run `Set-ADDomainMode` / `Set-ADForestMode` after every DC meets the minimum OS. Do not raise it just because you can: a higher level blocks adding any DC on an older OS, which you might still want in a lab.

!!! warning "Cross-point DNS between DCs"
    Each DC should point its DNS at a **peer** first and itself second. Pointing every DC only at itself seems to work until one of them stops registering records properly.

!!! warning "Time hierarchy: the PDC Emulator is the root"
    All DCs sync time from the PDC Emulator (DC01 unless you moved that role). In production it syncs from an external source; in the lab, free-running is fine because every client syncs from it transitively.

## Next

With two healthy DCs, the on-prem domain is resilient enough to extend to the cloud. **[Phase 17](../stretch/phase-17-entra-connect.md)** installs Entra Connect and syncs `corp.lab` identities into Microsoft Entra ID, the first step of the hybrid-identity and AI-security track. See the [Next Lab Series](../next-lab-series.md) page for where this leads.
