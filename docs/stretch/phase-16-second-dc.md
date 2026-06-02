# Phase 16: Second DC and replication

**Status:** Stretch. Beyond A+ Core 2 scope; portfolio depth toward MSP / SysAdmin work.

## Goal

Build a second domain controller, `DC02`, on the lab subnet. Promote it as an additional DC in `corp.lab`, confirm replication, and (optionally) transfer one FSMO role to it. End state: two DCs, both authoritative for the domain, replicating bidirectionally.

## Why it matters

Single-DC domains are a single point of failure. Every real environment has at least two DCs. Replication, FSMO roles, and site topology are the day-two concepts a sysadmin lives in.

## Prerequisites

- Phase 15 complete (the Recycle Bin is enabled and you have practiced an undelete).
- 4 GB of host RAM available for a second Server 2022 VM.

## Steps

### Part 1: Build DC02

1. Clone the Phase 1 install (`clean-install-tools-done` snapshot) or build a fresh Server 2022 VM with the same hardware settings: UEFI + TPM, NVMe, `VMnet1`, 4 GB RAM, 2 vCPU.
2. Boot. Set the time zone to Eastern.
3. Rename the host to `DC02`. Assign static IP `192.168.100.6/24`, gateway `192.168.100.1`, **DNS = `192.168.100.5` (DC01)**.

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

4. Confirm DNS resolution to DC01 works:

   ```powershell
   nslookup corp.lab
   ping dc01.corp.lab
   ```

### Part 2: Join and promote DC02

5. Install AD DS and join the existing domain in one step (promotion does the join):

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
       -CriticalReplicationOnly:$false `
       -Force
   ```

   You will be prompted for a DSRM password for DC02 (separate from DC01's; record it).

6. After the auto-reboot, on DC02 set its DNS to **point at the other DC first, itself second**. (This is the AD-recommended pattern: every DC prefers a peer for DNS, falls back to itself.)

   ```powershell
   $nic = (Get-NetAdapter | Where-Object Status -eq Up).Name
   Set-DnsClientServerAddress -InterfaceAlias $nic `
       -ServerAddresses ("192.168.100.5","127.0.0.1")
   ```

7. On DC01, change its DNS to the inverse:

   ```powershell
   $nic = "Ethernet0"
   Set-DnsClientServerAddress -InterfaceAlias $nic `
       -ServerAddresses ("192.168.100.6","127.0.0.1")
   ```

   (Why: if DC01 dies and DC02 had been using DC01 as primary DNS, DC02 still resolves through its own copy. Cross-pointing avoids a deadlock where every DC needs the dead one to resolve names.)

### Part 3: Confirm replication

8. From DC01:

   ```powershell
   Get-ADDomainController -Filter * |
       Select-Object Name, IPv4Address, Site, IsGlobalCatalog, OperationMasterRoles

   repadmin /showrepl
   repadmin /replsummary
   ```

   `Get-ADDomainController` should list both DC01 and DC02. `repadmin /showrepl` shows the connection objects in both directions. No "last failure" entries should appear.

9. Force a sync, then confirm an object created on DC01 appears on DC02:

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

   The user appears on DC02. Replication works.

### Part 4 (optional): Move a FSMO role

There are five FSMO roles. Two are forest-wide (Schema Master, Domain Naming Master). Three are domain-wide (PDC Emulator, RID Master, Infrastructure Master). All start on DC01. In production, you would split them; for the lab, move just the **Infrastructure Master** to DC02 as practice.

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
    - **Infrastructure Master**: tracks cross-domain object references. **In a single-domain forest the rule is "do not put this on a Global Catalog"**, with one exception: if every DC is a GC (the common case), then it does not matter. In the lab both DCs are GCs, so it does not matter.
    - **Schema Master / Domain Naming Master**: only matter during schema extension (Exchange install, etc.). Park them on DC01.

## Verify

```powershell
Get-ADDomainController -Filter *
repadmin /showrepl
repadmin /replsummary
dcdiag /v
netdom query fsmo
```

!!! success "Pass criteria"
    - Two DCs returned by `Get-ADDomainController`.
    - Both `repadmin` outputs show successful, recent replication in both directions.
    - `dcdiag /v` reports no failures (warnings about time skew or the firewall are fine to investigate but not blockers).
    - `netdom query fsmo` lists DC01 holding most roles, DC02 holding Infrastructure Master (if you ran the optional step).

## Snapshot

After confirming replication works, snapshot **both DCs together**. Name them `clean-2dc-replicating-01` and `clean-2dc-replicating-02`.

!!! danger "Snapshot warning"
    With two DCs, never roll back **one** of them past the last successful replication. The other DC tracks a USN value, sees the rolled-back DC produce a USN it has already seen, and **quarantines the rolled-back DC**. For lab experiments that need rollback, snapshot both DCs at the same time and roll back together.

## Gotchas

!!! danger "USN rollback is the price of snapshotting a multi-DC AD"
    The mechanism that keeps replication consistent (USNs) cannot tell the difference between "this DC was rolled back" and "this DC is malicious or corrupt", so it isolates the offender. The safe way is either:

    - Snapshot all DCs at the same instant and roll all of them back together.
    - Demote and re-promote a single broken DC instead of restoring it.
    - Or, since Server 2012, restore from a System State backup so AD knows it is being restored deliberately.

!!! warning "Cross-point DNS between DCs"
    Each DC should point its DNS at a **peer** first and itself second. Pointing every DC at itself only seems to work until one of them stops registering records properly.

!!! warning "Time hierarchy: PDC Emulator is the root"
    All DCs sync time from the PDC Emulator (DC01 in this lab unless you moved the role). The PDC Emulator should sync from an authoritative external source in production. In the lab, leaving it free-running is fine because all clients sync from it transitively.

!!! warning "Global Catalog placement"
    By default, the first DC in a forest is a Global Catalog. Subsequent DCs are not, unless you set `NoGlobalCatalog:$false`. The lab makes DC02 a GC. In a multi-site environment you would put a GC in each site to avoid cross-site GC queries.
