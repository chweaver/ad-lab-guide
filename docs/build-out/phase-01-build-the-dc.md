# Phase 1: Build the DC

**Status:** Done.

**Goal:** Take a blank VM to a promoted domain controller: install Server 2022 with VMware Tools, set the DC's identity (`DC01`, `192.168.100.5`, DNS at itself), then create the `corp.lab` forest with AD-integrated DNS.

**What this proves:** I can stand up a domain from nothing, in the right order, with DNS pointed where AD needs it.

## Prerequisites

- VMware Workstation Pro on the Windows host. `VMnet1` host-only, subnet `192.168.100.0/24`, VMware DHCP disabled.
- Server 2022 Standard Evaluation ISO available locally.

## Steps

### Part 1: Install Server 2022 and VMware Tools

1. In Workstation, **File > New Virtual Machine** > Custom > latest hardware compatibility.
2. Point at the Server 2022 ISO. **Disable Easy Install** so you get a normal Setup wizard.
3. Guest OS: Windows > Windows Server 2022. VM name: `Windows-Server-2022-base`, stored on an SSD.
4. Firmware: **UEFI** with **Secure Boot**. 2 processors x 2 cores (4 vCPUs minimum). Memory: 4096 MB minimum, 6144 MB recommended.
5. Network: **Custom > VMnet1 (host-only)**. Disk: **NVMe**, 60 GB, single file.
6. After creation, **VM > Settings**:
    - Add a **Trusted Platform Module**.
    - Options > Advanced > Firmware = UEFI, Secure Boot enabled.
    - Options > VMware Tools > **uncheck** "Synchronize guest time with host". The DC will be the domain's time source.
7. Power on, boot the ISO, install **Windows Server 2022 Standard (Desktop Experience)**, custom install, wipe the disk.
8. Set the local **Administrator** password at first logon. One strong lab password, reused everywhere in the lab.
9. **VM > Install VMware Tools**, run the installer in the guest, reboot.
10. Run Windows Update once and reboot.

??? info "Why UEFI + TPM + Secure Boot for a lab"
    None of these are required to run AD. They are required if you ever want to test BitLocker, Credential Guard, virtualization-based security, or attested boot. Modern hardware ships this way, so the lab matches reality.

### Part 2: Pre-promotion configuration

11. From elevated PowerShell, identify the NIC:

    ```powershell
    Get-NetAdapter | Select-Object Name, Status, MacAddress, LinkSpeed
    ```

12. Set the static IP and point DNS at `127.0.0.1` (the DC will host its own DNS after promotion):

    ```powershell
    $nic = "Ethernet0"
    New-NetIPAddress -InterfaceAlias $nic `
        -IPAddress 192.168.100.5 `
        -PrefixLength 24 `
        -DefaultGateway 192.168.100.1
    Set-DnsClientServerAddress -InterfaceAlias $nic `
        -ServerAddresses 127.0.0.1
    ```

13. Rename and reboot:

    ```powershell
    Rename-Computer -NewName DC01 -Force -Restart
    ```

14. After reboot, set the time zone:

    ```powershell
    Set-TimeZone -Id "Eastern Standard Time"
    ```

15. Disable IPv6 on the lab adapter (lab simplification, skip in production; it removes a second DNS lookup path from `nslookup` output):

    ```powershell
    Disable-NetAdapterBinding -Name "Ethernet0" -ComponentID ms_tcpip6
    ```

16. Enable Remote Desktop for later phases:

    ```powershell
    Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" `
        -Name "fDenyTSConnections" -Value 0
    Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
    ```

### Part 3: Promote to domain controller (new forest)

17. Install the AD DS role and management tools:

    ```powershell
    Install-WindowsFeature -Name AD-Domain-Services `
        -IncludeManagementTools
    ```

18. Promote to a new forest root:

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

    - `WinThreshold` is the cmdlet constant for the Server 2016 functional level, the current ceiling (there is no 2022 level).
    - You will be prompted for the **DSRM** password. Save it; Phase 15 needs it.
    - The server reboots automatically. Log back in as `CORP\Administrator`.

19. Add the reverse lookup zone (promotion creates only the forward zone):

    ```powershell
    Add-DnsServerPrimaryZone `
        -NetworkId "192.168.100.0/24" `
        -ReplicationScope "Domain" `
        -DynamicUpdate "Secure"
    ```

20. Force DC01 to register its own records:

    ```powershell
    ipconfig /registerdns
    Restart-Service netlogon
    ```

## Screenshot

- Capture: `Get-ADDomain` and `nslookup dc01.corp.lab` output side by side on DC01. Save as `img/phase-01-dc-promoted.png`. Slot reserved, not captured yet.

## Verify

Part 1, on DC01:

```powershell
Get-ComputerInfo |
    Select-Object CsName, OsName, OsVersion, WindowsInstallationType
Get-Service "VMTools" | Format-List Status, StartType
```

Part 2:

```powershell
hostname                                # DC01
Get-NetIPAddress -InterfaceAlias Ethernet0 -AddressFamily IPv4 |
    Select-Object IPAddress, PrefixLength, AddressState
Get-DnsClientServerAddress -InterfaceAlias Ethernet0 -AddressFamily IPv4 |
    Select-Object ServerAddresses
Get-TimeZone | Select-Object Id, DisplayName
Test-NetConnection 192.168.100.1 -InformationLevel Quiet
```

Part 3:

```powershell
Get-ADDomain | Select-Object Forest, NetBIOSName, DomainMode, DNSRoot
Get-ADForest | Select-Object Name, ForestMode, SchemaMaster, DomainNamingMaster
Get-ADDomainController | Select-Object HostName, IPv4Address, Site, OperationMasterRoles
nslookup dc01.corp.lab
nslookup -type=SRV _ldap._tcp.dc._msdcs.corp.lab
```

!!! success "Expected"
    - `OsName` shows `Microsoft Windows Server 2022 Standard Evaluation`, `WindowsInstallationType` is `Server`. VMTools: Status `Running`, StartType `Automatic`.
    - `hostname` returns `DC01`, IP is `192.168.100.5/24`, DNS list contains `127.0.0.1`, time zone Eastern. `Test-NetConnection` to the gateway returns `True` (or `False` on a quiet host-only subnet; either is fine as long as DC01 reaches VMs on `192.168.100.0/24`).
    - `Get-ADDomain` shows `Forest: corp.lab`, `NetBIOSName: CORP`, `DomainMode: Windows2016Domain`. `Get-ADForest` shows `ForestMode: Windows2016Forest`.
    - `Get-ADDomainController` lists `DC01` with all 5 FSMO roles (PDCEmulator, RIDMaster, InfrastructureMaster, SchemaMaster, DomainNamingMaster).
    - `nslookup dc01.corp.lab` returns `192.168.100.5`. The SRV lookup returns at least one record pointing at `dc01.corp.lab`.

## Snapshot

Two rollback points in this phase:

- **`clean-install-tools-done`** after Part 1. Fresh, patched Server 2022 with Tools.
- **`clean-dc-promoted`** after Part 3. The cleanest possible "working DC" state; later phases roll back here if AD gets corrupted.

If Part 2 breaks, roll back to `clean-install-tools-done` and redo it from PowerShell history.

## Gotchas

!!! warning "Do not skip VMware Tools before promotion"
    Tools installs a paravirtual NIC driver. If you promote to DC before Tools is in, the NIC may get a different identifier afterward, and any static IP you set is now bound to a "ghost" adapter. Tools first, then static IP, then promote.

!!! warning "Disable host-time sync on the DC"
    A DC is the authoritative time source for its domain. Letting VMware push host time onto it fights Windows Time and can produce Kerberos drift later. Uncheck it now in VM Options.

!!! warning "Easy Install is not your friend"
    VMware's Easy Install drops an answer file with a random Administrator password and skips parts of OOBE. For a lab where you want predictable state, do a normal Setup install.

!!! danger "Do not point the DC's DNS at the gateway, your home router, or 8.8.8.8"
    A DC resolves its own domain through itself. The single most common mistake when promoting a DC is leaving the gateway in the DNS field. Set it to `127.0.0.1` and confirm with `Get-DnsClientServerAddress`.

!!! warning "Rename before promotion, never after"
    Renaming a promoted DC is supported but it rewrites SPNs, computer object names, and replication metadata. Worth the avoidance.

!!! warning "Static IP only"
    A DC on DHCP can work, but every other machine in the domain needs to know where the DC lives. Static IP is the default expectation for any AD role.

!!! danger "Promotion fails if DNS is misconfigured"
    The most common error is "an Active Directory domain controller for the domain `corp.lab` could not be contacted". With a brand-new forest there is no domain to contact yet, so the real cause is almost always the DC's own DNS pointing somewhere other than `127.0.0.1`. Re-check step 12.

!!! warning "DSRM password is separate from the domain Administrator password"
    DSRM is used when the DC boots into Directory Services Restore Mode (the AD equivalent of safe mode). You will need it for the AD backup and restore phase. Save it in your password manager.

!!! warning "Do not change the IP or hostname after promotion"
    Both are recorded in AD-integrated DNS and in the computer object. Changing them requires `dcdiag /fix`, manual DNS cleanup, and a `netlogon` restart, sometimes more. If you need to change either, roll back to `clean-install-tools-done` and start over.

!!! warning "No reverse-lookup zone by default"
    Promotion creates the forward zone for `corp.lab`, not the reverse zone for the subnet. Add it manually as in step 19, or `nslookup <ip>` will fail and `dcdiag` complains.
