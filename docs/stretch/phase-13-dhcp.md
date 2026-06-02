# Phase 13: DHCP role

**Status:** Stretch. Beyond A+ Core 2 scope; portfolio depth toward CCNA / MSP work.

## Goal

Install the DHCP Server role on `DC01`, authorize it in AD, and create a scope for `192.168.100.0/24`. New clients on `VMnet1` get an IP automatically; `WS01` keeps its static reservation.

## Why it matters

In a real environment, AD plus DHCP plus DNS is the "name and address" core. A scope reservation, a DNS update from a DHCP lease, an option pack pushing the DC as the DNS server: this is what AD-integrated DHCP looks like end-to-end.

## Prerequisites

- Phase 7 complete (you have a client to test against).
- VMware's own DHCP on `VMnet1` is **disabled** (set up in Phase 1). Two DHCP servers on the same subnet is the standard way to break a lab.

## Steps

1. From elevated PowerShell on DC01, install the role:

   ```powershell
   Install-WindowsFeature -Name DHCP -IncludeManagementTools
   ```

2. Authorize the DHCP server in AD. (Without this, the service starts but refuses to hand out leases. AD authorization is the safety mechanism that prevents random servers from acting as DHCP on a domain network.)

   ```powershell
   Add-DhcpServerInDC -DnsName "dc01.corp.lab" -IPAddress 192.168.100.5
   ```

3. Create a scope covering the bulk of the subnet, leaving room for static assignments at the low and high ends:

   ```powershell
   Add-DhcpServerv4Scope `
       -Name "Lab-VMnet1" `
       -StartRange 192.168.100.100 `
       -EndRange   192.168.100.200 `
       -SubnetMask 255.255.255.0 `
       -LeaseDuration (New-TimeSpan -Days 8) `
       -State Active
   ```

4. Set scope options. Push the gateway, the DC's DNS, and the DNS suffix.

   ```powershell
   Set-DhcpServerv4OptionValue `
       -ScopeId  192.168.100.0 `
       -Router         192.168.100.1 `
       -DnsServer      192.168.100.5 `
       -DnsDomain      corp.lab
   ```

5. Reserve `192.168.100.20` for `WS01` by MAC address. Replace the MAC with `WS01`'s actual MAC (find it on the client with `Get-NetAdapter`).

   ```powershell
   Add-DhcpServerv4Reservation `
       -ScopeId 192.168.100.0 `
       -IPAddress 192.168.100.20 `
       -ClientId  "00-50-56-AA-BB-CC" `
       -Name      "WS01"
   ```

6. Mark the DHCP install as "complete" so the post-install wizard does not nag:

   ```powershell
   Set-ItemProperty `
       -Path "HKLM:\SOFTWARE\Microsoft\ServerManager\Roles\12" `
       -Name ConfigurationState -Value 2
   Restart-Service DHCPServer
   ```

## Verify

```powershell
Get-DhcpServerInDC                                    # the DC appears
Get-DhcpServerv4Scope                                 # Lab-VMnet1, State: Active
Get-DhcpServerv4OptionValue -ScopeId 192.168.100.0    # Router and DNS set correctly
Get-DhcpServerv4Reservation -ScopeId 192.168.100.0    # WS01 reservation
```

On a fresh client (or `WS01` switched to DHCP temporarily):

```powershell
ipconfig /release
ipconfig /renew
ipconfig /all
```

!!! success "Pass criteria"
    Client receives `192.168.100.x`, gateway `192.168.100.1`, DNS `192.168.100.5`, DNS suffix `corp.lab`. DC01's DHCP console shows an active lease.

## Snapshot

Take a snapshot **before** flipping clients to DHCP, named `pre-dhcp`. A misconfigured scope can leave the lab unable to talk to itself.

## Gotchas

!!! danger "Two DHCP servers on one subnet is a race condition"
    VMware Workstation enables DHCP on VMnets by default. The first server to answer wins. Disable VMware DHCP on `VMnet1` in **Edit > Virtual Network Editor** before authorizing your own.

!!! warning "Authorize, do not just install"
    A DHCP server in an AD environment refuses to answer leases until it is listed as authorized in AD. The service appears to be running and the event log silently records why it is not leasing. Run `Add-DhcpServerInDC`.

!!! warning "Static IPs and DHCP scopes can overlap dangerously"
    Reserving `.20` for `WS01` is fine. Letting the scope range include `.5` (the DC) is a disaster waiting to happen. Always exclude your statics, either by setting `StartRange`/`EndRange` outside them or with `Add-DhcpServerv4ExclusionRange`.

!!! warning "DNS suffix matters for short-name resolution"
    Without `DnsDomain corp.lab` in the scope options, clients can ping `dc01.corp.lab` but `ping dc01` will fail.
