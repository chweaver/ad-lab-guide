# Phase 10: Scripted patching

**Status:** Not started. Planned.

**Goal:** Patch DC01 and WS01 on a schedule with PSWindowsUpdate, logging every run to a central share, so patch state is a query instead of a guess.

**What this proves:** I can run a repeatable, logged patch cycle across a domain, the core of vulnerability management at MSP scale. Supports SY0-701: 4.3 (vulnerability management, patching), 4.1 (hardening).

## Prerequisites

- Phase 5 complete (a share exists for logs).
- Both VMs able to reach Windows Update (temporary NAT adapter or a routed path; the lab subnet itself stays isolated).

## Steps

1. Install the module on both machines:

    ```powershell
    Install-Module PSWindowsUpdate -Force
    Get-Command -Module PSWindowsUpdate | Select-Object -First 5
    ```

2. Create the log share target once on DC01:

    ```powershell
    New-Item -Path "C:\Shares\IT\PatchLogs" -ItemType Directory -Force | Out-Null
    ```

3. Patch script, saved as `C:\Scripts\Invoke-LabPatch.ps1` on each machine:

    ```powershell
    $log = "\\DC01\IT$\PatchLogs\$env:COMPUTERNAME-$(Get-Date -Format yyyy-MM-dd).log"
    Get-WindowsUpdate -AcceptAll -Install -AutoReboot |
        Tee-Object -FilePath $log
    ```

4. Schedule it weekly (Sunday 03:00) as SYSTEM:

    ```powershell
    $action  = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\Scripts\Invoke-LabPatch.ps1"
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am
    Register-ScheduledTask -TaskName "Lab-Patch" -Action $action -Trigger $trigger `
        -User "SYSTEM" -RunLevel Highest
    ```

5. Run it once by hand on each machine and read the log.

??? info "Why scripted instead of WSUS"
    WSUS is the enterprise answer, but it wants the Windows Internal Database and several GB of RAM this lab does not have spare. Scripted patching with central logs proves the same competency (controlled, verifiable patch state) at lab scale. If the host ever grows, WSUS on a member server slots into this same phase: point clients at it with the `Specify intranet Microsoft update service location` GPO and the verify step becomes the WSUS console's compliance report.

## Screenshot

- Capture: the PatchLogs share listing plus the tail of one log showing installed KBs. Save as `img/phase-10-patch-logs.png`. Slot reserved, phase not started.

## Verify

```powershell
# On either machine
Get-WUHistory | Select-Object -First 10 Date, Title, Result
Get-ScheduledTask -TaskName "Lab-Patch" | Select-Object TaskName, State

# On DC01
Get-ChildItem "C:\Shares\IT\PatchLogs"
```

!!! success "Pass criteria"
    - `Get-WUHistory` shows updates with `Result: Succeeded` dated from the manual run.
    - The scheduled task exists and is `Ready` on both machines.
    - One log file per machine sits in the PatchLogs share, listing what was installed.

## Snapshot

Snapshot both VMs **before** the first patch run (`pre-patch-baseline`). A bad update on a DC is exactly the failure mode Phase 15 practices recovering from.

## Gotchas

!!! warning "AutoReboot on a DC means the domain blinks"
    Fine in a single-DC lab at 03:00. In any real environment, DCs get staggered maintenance windows, never a blind auto-reboot.

!!! warning "PSWindowsUpdate needs an execution policy that allows it"
    The scheduled task passes `-ExecutionPolicy Bypass` for exactly this reason. If a manual run fails, check `Get-ExecutionPolicy` first.

!!! warning "The lab subnet has no internet by design"
    Updates need a temporary NAT adapter or a routed path. Remove the NAT adapter after patching, or the isolated-lab assumption every other phase relies on quietly stops being true.
