# Phase 1: Install Server 2022 and VMware Tools

**Status:** Done.

## Goal

Build a clean Windows Server 2022 Standard (Evaluation, Desktop Experience) VM named `DC01`, install VMware Tools, and snapshot. No AD role yet.

## Why it matters

This is the foundation every later phase depends on. Hardware-level mistakes here (wrong firmware, missing TPM, wrong network) are painful to fix after the DC is promoted, because they invalidate snapshots. The cost of starting clean now is five minutes. The cost of fixing it after Phase 6 is several hours.

A+ Core 2 angle: objective 2.2 expects you to recognise that AD lives on a server OS, not a client. Building this VM hands you the mental picture.

## Prerequisites

- VMware Workstation Pro installed on the Windows host.
- `VMnet1` configured as a host-only network with subnet `192.168.100.0/24`. DHCP on VMnet1 is disabled.
- Server 2022 Standard Evaluation ISO available locally.

## Steps

1. In Workstation, **File > New Virtual Machine** > Custom > Workstation hardware compatibility = latest.
2. Installer disc image: point at the Server 2022 ISO. Workstation may detect "Easy Install"; **disable it** so you get a normal Setup wizard. (Easy Install pre-creates a local admin and an answer file you do not want.)
3. Guest OS: Windows > Windows Server 2022.
4. VM name: `Windows-Server-2022-base`. Pick a location on an SSD.
5. Firmware type: **UEFI**. Enable **Secure Boot**.
6. Number of processors: 2. Cores per processor: 2. (Adjust to host capacity, 4 vCPUs total minimum.)
7. Memory: 4096 MB minimum. 6144 MB recommended.
8. Network: **Custom > VMnet1 (host-only)**. (Why: keeps lab traffic isolated from the home LAN and the internet.)
9. SCSI controller: leave default. Virtual disk: **NVMe**. Size: 60 GB. Store as a single file.
10. After creation, **VM > Settings**:
    - Hard Disk: confirm NVMe.
    - Add a **Trusted Platform Module** (Server 2022 likes it; some Defender / Credential Guard features need it).
    - Options > Advanced > Firmware type = UEFI, Secure Boot enabled.
    - Options > VMware Tools > **uncheck** "Synchronize guest time with host" (the DC will be the authoritative time source).
11. Power on. Boot from the ISO.
12. Install: choose **Windows Server 2022 Standard (Desktop Experience)**. Custom install. Wipe the disk; let Setup partition it.
13. At first logon, set the local **Administrator** password. Remember it. (The lab password used everywhere: pick one strong value and reuse it for lab simplicity.)
14. **Install VMware Tools**: `VM > Install VMware Tools` in the Workstation menu, then run the installer from the mounted ISO inside the guest. Reboot when prompted.
15. Run Windows Update once and reboot. (Why: makes the snapshot a known-good patched baseline.)

??? info "Why UEFI + TPM + Secure Boot for a lab"
    None of these are required to run AD. They are required if you ever want to test BitLocker, Credential Guard, virtualization-based security, or attested boot. Modern hardware ships this way, so the lab matches reality.

## Verify

Open an **elevated PowerShell** prompt on DC01.

```powershell
Get-ComputerInfo |
    Select-Object CsName, OsName, OsVersion, WindowsInstallationType
```

!!! success "Expected"
    `CsName` is some default like `WIN-XXXXXX` (we rename in Phase 2). `OsName` shows `Microsoft Windows Server 2022 Standard Evaluation`. `WindowsInstallationType` is `Server`.

Confirm VMware Tools:

```powershell
Get-Service "VMTools" | Format-List Status, StartType
```

!!! success "Expected"
    Status `Running`, StartType `Automatic`.

## Snapshot

Take a VM snapshot named **`clean-install-tools-done`**. This is the baseline you roll back to if anything in Phase 2 or 3 corrupts the OS.

## Gotchas

!!! warning "Do not skip VMware Tools before promotion"
    Tools installs a paravirtual NIC driver. If you promote to DC before Tools is in, the NIC may get a different identifier afterward, and any static IP you set is now bound to a "ghost" adapter. Tools first, then static IP, then promote.

!!! warning "Disable host-time sync on the DC"
    A DC is the authoritative time source for its domain. Letting VMware push host time onto it fights Windows Time and can produce Kerberos drift later. Uncheck it now in VM Options.

!!! warning "Easy Install is not your friend"
    VMware's Easy Install drops an answer file with a random Administrator password and skips parts of OOBE. For a lab where you want predictable state, do a normal Setup install.
