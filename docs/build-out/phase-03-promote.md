# Phase 3: Promote to domain controller (new forest)

**Status:** Done.

## Goal

Install the AD DS role on `DC01`, then promote it to a domain controller, creating a brand-new forest with domain `corp.lab` (NetBIOS `CORP`). At the end of the phase, `DC01` is hosting Active Directory and an integrated DNS zone.

## Why it matters

This is the moment the lab becomes a domain. After this, every client, share, and GPO has somewhere to attach.

A+ Core 2 angle: 2.2 expects you to know what a domain is and where it lives. After this phase you can point at a process (LSASS, Netlogon, NTDS) and say "AD is running there."

## Prerequisites

- Phase 2 complete: hostname `DC01`, IP `192.168.100.5/24`, DNS `127.0.0.1`, time zone Eastern.
- Snapshot `clean-install-tools-done` taken.
- Local Administrator password set and known.

## Steps

1. From elevated PowerShell on DC01, install the AD DS role and the management tools:

   ```powershell
   Install-WindowsFeature -Name AD-Domain-Services `
       -IncludeManagementTools
   ```

2. Promote the server to a new forest root. (Why a new forest: there is nothing to join.)

   ```powershell
   Install-ADDSForest `
       -DomainName "corp.lab" `
       -DomainNetbiosName "CORP" `
       -ForestMode "WinThreshold" `
       -DomainMode "WinThreshold" `
       -InstallDns `
       -DatabasePath "C:\Windows\NTDS" `
       -SysvolPath "C:\Windows\SYSVOL" `
       -LogPath "C:\Windows\NTDS" `
       -NoRebootOnCompletion:$false `
       -Force
   ```

   - `WinThreshold` is the AD-cmdlet constant for "Server 2016 functional level". (Why 2016 and not 2022: there is no `Windows Server 2022` functional level. Server 2016 is the current ceiling and it includes everything the lab uses.)
   - You will be prompted for a **Directory Services Restore Mode** (DSRM) password. Save it; you need it for authoritative restores in Phase 15.
   - The server reboots automatically.

3. After reboot, log on as `CORP\Administrator` (the local Admin password got migrated; the local account is gone).

4. Confirm the DNS reverse lookup zone exists. (Promotion creates the forward zone for `corp.lab` automatically, but not the reverse zone.)

   ```powershell
   Add-DnsServerPrimaryZone `
       -NetworkId "192.168.100.0/24" `
       -ReplicationScope "Domain" `
       -DynamicUpdate "Secure"
   ```

5. Force DC01 to register its own records in DNS:

   ```powershell
   ipconfig /registerdns
   Restart-Service netlogon
   ```

## Verify

```powershell
Get-ADDomain | Select-Object Forest, NetBIOSName, DomainMode, DNSRoot
Get-ADForest | Select-Object Name, ForestMode, SchemaMaster, DomainNamingMaster
Get-ADDomainController | Select-Object HostName, IPv4Address, Site, OperationMasterRoles
nslookup dc01.corp.lab
nslookup -type=SRV _ldap._tcp.dc._msdcs.corp.lab
```

!!! success "Expected"
    - `Get-ADDomain` shows `Forest: corp.lab`, `NetBIOSName: CORP`, `DomainMode: Windows2016Domain`.
    - `Get-ADForest` shows `ForestMode: Windows2016Forest`.
    - `Get-ADDomainController` lists `DC01` with all 5 FSMO roles (PDCEmulator, RIDMaster, InfrastructureMaster, SchemaMaster, DomainNamingMaster).
    - `nslookup dc01.corp.lab` returns `192.168.100.5`.
    - The SRV lookup returns at least one record pointing at `dc01.corp.lab`.

## Snapshot

Take a VM snapshot named **`clean-dc-promoted`**. This is the cleanest possible "I have a working DC" state. Phases 4 onward populate it with content; if a later phase corrupts AD, this is the rollback target.

## Gotchas

!!! danger "Promotion fails if DNS is misconfigured"
    The most common error is "an Active Directory domain controller for the domain `corp.lab` could not be contacted". With a brand-new forest there is no domain to contact yet, so the real cause is almost always the DC's own DNS pointing somewhere other than `127.0.0.1`. Re-check Phase 2 step 3.

!!! warning "DSRM password is separate from the domain Administrator password"
    DSRM is used when the DC boots into Directory Services Restore Mode (the AD equivalent of safe mode). You will need it for the AD backup and restore phase. Save it in your password manager.

!!! warning "Do not change the IP or hostname after promotion"
    Both are recorded in AD-integrated DNS and in the computer object. Changing them requires `dcdiag /fix`, manual DNS cleanup, and a `netlogon` restart, sometimes more. If you need to change either, roll back to `clean-install-tools-done` and start over.

!!! warning "No reverse-lookup zone by default"
    Promotion creates the forward zone for `corp.lab`, not the reverse zone for the subnet. Add it manually as in step 4, or `nslookup <ip>` will fail and `dcdiag` complains.
