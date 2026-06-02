# Phase 2: Pre-promotion configuration

**Status:** Done.

## Goal

Rename the server to `DC01`, give it the static lab IP, set DNS to itself, and confirm the network is healthy. The machine is still a workgroup server at the end of this phase; the AD role gets added in Phase 3.

## Why it matters

A DC's identity is baked into AD at promotion time. Changing the hostname, IP, or primary DNS server after promotion is possible but messy (SPN cleanup, DNS scavenging, replication risk). Doing it now is free.

A+ Core 2 angle: objective 2.2 expects you to know that AD depends on DNS. This phase puts DNS where AD wants it.

## Prerequisites

- Phase 1 complete. Snapshot `clean-install-tools-done` exists.
- VMware Tools running. Single virtual NIC bound to `VMnet1`.

## Steps

1. Log on to the server as the local **Administrator**.
2. Open **elevated PowerShell**. Identify the NIC:

   ```powershell
   Get-NetAdapter | Select-Object Name, Status, MacAddress, LinkSpeed
   ```

   Note the adapter name (typically `Ethernet0`).

3. Set the static IP, gateway, and DNS. (DNS points at `127.0.0.1` because the DC will host its own DNS in Phase 3.)

   ```powershell
   $nic = "Ethernet0"
   New-NetIPAddress -InterfaceAlias $nic `
       -IPAddress 192.168.100.5 `
       -PrefixLength 24 `
       -DefaultGateway 192.168.100.1
   Set-DnsClientServerAddress -InterfaceAlias $nic `
       -ServerAddresses 127.0.0.1
   ```

4. Rename the computer to `DC01`:

   ```powershell
   Rename-Computer -NewName DC01 -Force -Restart
   ```

5. After reboot, log back in and set the time zone:

   ```powershell
   Set-TimeZone -Id "Eastern Standard Time"
   ```

6. Disable IPv6 on the lab adapter (lab simplification, not a hard requirement). Skip this in production:

   ```powershell
   Disable-NetAdapterBinding -Name "Ethernet0" -ComponentID ms_tcpip6
   ```

   (Why disable: removes a second DNS lookup path that confuses some students reading `nslookup` output. AD itself is happy with IPv6 enabled.)

7. Enable Remote Desktop for later phases:

   ```powershell
   Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" `
       -Name "fDenyTSConnections" -Value 0
   Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
   ```

## Verify

```powershell
hostname                                # DC01
Get-NetIPAddress -InterfaceAlias Ethernet0 -AddressFamily IPv4 |
    Select-Object IPAddress, PrefixLength, AddressState
Get-DnsClientServerAddress -InterfaceAlias Ethernet0 -AddressFamily IPv4 |
    Select-Object ServerAddresses
Get-TimeZone | Select-Object Id, DisplayName
Test-NetConnection 192.168.100.1 -InformationLevel Quiet
```

!!! success "Expected"
    - `hostname` returns `DC01`.
    - IP is `192.168.100.5/24`.
    - DNS server list contains `127.0.0.1`.
    - Time zone shows Eastern Standard Time.
    - `Test-NetConnection` to the gateway returns `True` (or `False` if the gateway is not active; either is fine for a host-only subnet as long as DC01 can reach VMs on `192.168.100.0/24`).

## Snapshot

No new snapshot here. The next meaningful checkpoint is after promotion. If something breaks, roll back to `clean-install-tools-done` and redo this phase from PowerShell history.

## Gotchas

!!! danger "Do not point the DC's DNS at the gateway, your home router, or 8.8.8.8"
    A DC resolves its own domain through itself. The single most common mistake when promoting a DC is leaving the gateway in the DNS field. Set it to `127.0.0.1` and confirm with `Get-DnsClientServerAddress`.

!!! warning "Rename before promotion, never after"
    Renaming a promoted DC is supported but it rewrites SPNs, computer object names, and replication metadata. Worth the avoidance.

!!! warning "Static IP only"
    A DC on DHCP can work, but every other machine in the domain needs to know where the DC lives. Static IP is the default expectation for any AD role.
