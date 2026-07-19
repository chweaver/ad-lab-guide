# Phase 3: Join a client (WS01)

**Status:** Done.

**Goal:** Build a Windows 10/11 Enterprise VM named `WS01`, point its DNS at the DC, sync time, join `corp.lab`, and log in as a domain user.

**What this proves:** DNS, Kerberos, and the trust chain work end to end, in the order a failed-join ticket gets diagnosed: DNS first, time second, rename third, join fourth.

## Prerequisites

- Phase 2 complete. DC01 is up, AD is healthy, users and groups exist.
- Windows 10 or 11 Enterprise Evaluation ISO available.
- DC01 reachable at `192.168.100.5` on `VMnet1`.

## Steps

### Part 1: Build the VM

1. Create a new VM in VMware Workstation:
    - Guest OS: Windows 10/11 x64.
    - Firmware: UEFI + Secure Boot, TPM enabled (Windows 11 requires both).
    - 2 vCPU, 4096 MB RAM, 60 GB NVMe disk.
    - Network: `VMnet1` (host-only). Same subnet as DC01, so the join does not traverse any router.
2. Install Windows. At OOBE, create a **local** account (any name). Skip Microsoft account prompts.
3. Install **VMware Tools**, reboot.

### Part 2: Pre-join configuration

4. From elevated PowerShell on the client, set static IP and DNS pointing at the DC. AD discovery is a DNS lookup for `_ldap._tcp.dc._msdcs.corp.lab`; if DNS does not point at the DC, discovery fails with an unhelpful error:

    ```powershell
    $nic = (Get-NetAdapter | Where-Object Status -eq Up).Name
    New-NetIPAddress -InterfaceAlias $nic `
        -IPAddress 192.168.100.20 `
        -PrefixLength 24 `
        -DefaultGateway 192.168.100.1
    Set-DnsClientServerAddress -InterfaceAlias $nic `
        -ServerAddresses 192.168.100.5
    ```

5. Confirm DNS works before joining. All three must succeed:

    ```powershell
    nslookup corp.lab
    nslookup dc01.corp.lab
    ping dc01.corp.lab
    ```

    If `nslookup corp.lab` returns the gateway or `8.8.8.8`, step 4 did not stick; re-check with `Get-DnsClientServerAddress`.

6. Check clock drift against the DC. Kerberos rejects tickets with more than 5 minutes of skew. Run `Get-Date` on both machines and compare visually:

    ```powershell
    $dcTime     = (Invoke-Command -ComputerName DC01 -ScriptBlock { Get-Date } -Credential corp\Administrator -ErrorAction SilentlyContinue)
    $localTime  = Get-Date
    # If the remote call is not yet allowed (it is not before the join), just compare manually.
    Get-Date
    ```

    If the client is off by more than a couple of minutes:

    ```powershell
    Set-Date (Get-Date "2026-06-02 14:00:00")   # example, use the DC's current time
    ```

    After the join, `w32time` syncs the client to the PDC emulator automatically.

### Part 3: Rename and join

7. Rename **before** joining. AD captures whatever hostname the client has at join time:

    ```powershell
    Rename-Computer -NewName WS01 -Restart
    ```

8. After reboot, log in to the local account again and join:

    ```powershell
    Add-Computer -DomainName corp.lab -Credential (Get-Credential corp\Administrator) -Restart
    ```

### Part 4: Confirm

9. At the logon screen, click **Other user** and sign in as `jsmith@corp.lab` (or `CORP\jsmith`) with the lab password.

10. From elevated PowerShell as the domain user:

    ```powershell
    whoami                       # CORP\jsmith
    whoami /fqdn                 # CN=J Smith,OU=IT,OU=Departments,DC=corp,DC=lab
    (Get-ComputerInfo).CsDomain  # corp.lab
    nltest /dsgetdc:corp.lab     # locates DC01
    ```

??? info "What happens during a domain join, in order"
    1. Client resolves `corp.lab` via DNS, gets a list of DCs from the `_ldap._tcp.dc._msdcs.corp.lab` SRV record.
    2. Client connects to the DC over LDAP (389) and SMB (445) using the credentials you supplied.
    3. AD creates a computer object in the default Computers OU (or `OU=Workstations` if you ran `redircmp`).
    4. AD generates a machine-account password and stores half on the DC, half locally on the client.
    5. The client requests a reboot. On reboot, the client logs in with its machine account, joins the secure channel, and Kerberos starts working.

## Screenshot

- Capture: `whoami /fqdn` and `nltest /dsgetdc:corp.lab` output in one WS01 terminal as a domain user. Save as `img/phase-03-domain-joined.png`. Slot reserved, not captured yet.

## Verify

!!! success "Domain join is successful when all of these are true"
    - `hostname` on the client returns `WS01`.
    - `(Get-ComputerInfo).CsDomain` returns `corp.lab` (not `WORKGROUP`).
    - A domain user can log in interactively.
    - `nltest /dsgetdc:corp.lab` returns `\\DC01.corp.lab`.
    - On DC01: `Get-ADComputer WS01` returns a computer object (auto-placed in `OU=Workstations` thanks to the `redircmp.exe` step in Phase 2).

## Snapshot

Take a VM snapshot on **WS01** named **`clean-domain-joined`**. This is the baseline before any GPOs apply, before any login script runs, before any drive maps. Rolling back here is the fastest way to debug Phase 4 onward.

Also take a fresh snapshot on **DC01** (optional but recommended), since AD now has a computer object it did not have before.

## Gotchas

!!! danger "DNS pointing at the gateway is the #1 cause of failed joins"
    The error message blames "an Active Directory domain controller could not be contacted" or "the specified domain either does not exist". The cause is almost always the client's DNS still pointing at `192.168.100.1` or `8.8.8.8` instead of `192.168.100.5`. Re-check before doing anything else.

!!! danger "Clock drift over 5 minutes kills the join"
    Error: "the trust relationship between this workstation and the primary domain failed" or "clock skew too great". Set the client's time roughly matching the DC's, then retry.

!!! warning "Rename before join, not after"
    Renaming after join requires the computer object in AD to be renamed in lockstep. Pre-join rename is free.

!!! warning "Do not join while connected to the wrong VMnet"
    If the client adapter is on `VMnet8` (NAT) by accident, the host-only routing to `192.168.100.5` does not exist and the join fails. Confirm `VMnet1` in VM settings before powering on.
