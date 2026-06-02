# Phase 8: Group Policy basics and inheritance

**Status:** Not started.

## Goal

Create one simple Group Policy Object, link it to `OU=Departments`, and confirm it applies to `WS01` via `gpupdate` and `gpresult`. The point is not the policy itself; the point is proving inheritance works from a parent OU down to a user in a child OU.

## Why it matters

Almost every later phase (folder redirection, login scripts, drive maps, security baselines) is implemented as a GPO. If you cannot reliably link, scope, and verify a single GPO, you cannot debug ten of them.

A+ Core 2 angle: 2.2 mentions "Group Policy / updates" by name. The exam expects you to know that GPOs link to sites, domains, and OUs (not to `CN=Users`), and that clients refresh policy on logon and roughly every 90 minutes.

## Prerequisites

- Phase 7 complete. `WS01` is domain-joined. Snapshot `clean-domain-joined` exists.
- The Group Policy Management console (GPMC) is already installed on DC01 (it came with the AD DS role tools in Phase 3).

## Steps

### Build the GPO

1. From DC01, open **Group Policy Management** (`gpmc.msc`).
2. Right-click **Forest > Domains > corp.lab > Group Policy Objects > New**. Name it `Dept-Wallpaper`. (Wallpaper is a clean, visible, harmless test. You can swap it for a security baseline later.)
3. Right-click the new GPO > **Edit**. Navigate to:

   `User Configuration > Policies > Administrative Templates > Desktop > Desktop > Desktop Wallpaper`

   - Set the policy to **Enabled**.
   - **Wallpaper name**: `\\DC01\SYSVOL\corp.lab\scripts\wallpaper.jpg` (any image works; the exact path is illustrative).
   - **Wallpaper style**: `Fill`.
   - Close the editor.
4. Back in GPMC, right-click `OU=Departments` > **Link an Existing GPO...** > select `Dept-Wallpaper`. (Why link here and not at the domain root: scoping to `Departments` means built-in service accounts in `CN=Users` are unaffected, and `Workstations` does not inherit it either.)

??? info "PowerShell-only version of the above"
    ```powershell
    Import-Module GroupPolicy
    $gpo = New-GPO -Name "Dept-Wallpaper" -Comment "Lab GPO to prove inheritance"
    Set-GPRegistryValue -Name "Dept-Wallpaper" `
        -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" `
        -ValueName "Wallpaper" `
        -Type String `
        -Value "\\DC01\SYSVOL\corp.lab\scripts\wallpaper.jpg"
    Set-GPRegistryValue -Name "Dept-Wallpaper" `
        -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" `
        -ValueName "WallpaperStyle" `
        -Type String `
        -Value "10"
    New-GPLink -Name "Dept-Wallpaper" -Target "OU=Departments,DC=corp,DC=lab"
    ```

### Force a refresh on WS01

5. Log in to `WS01` as `jsmith@corp.lab` (a member of `OU=IT`, which is a child of `OU=Departments`).
6. From an elevated PowerShell on `WS01`:

   ```powershell
   gpupdate /force
   ```

   `gpupdate` returns "User Policy update has completed successfully. Computer Policy update has completed successfully."

7. Verify which GPOs applied:

   ```powershell
   gpresult /r /scope:user
   ```

   In the output, under **Applied Group Policy Objects**, you should see `Dept-Wallpaper`.

### Prove inheritance

8. Log in to `WS01` as `mtate@corp.lab` (member of `OU=Sales`, sibling of IT, also a child of `OU=Departments`). The wallpaper policy should apply to this user too, because the link is on the parent OU.

9. Optional: log in as a user outside `OU=Departments` (the built-in `Administrator` lives in `CN=Users` and is unaffected). Confirm the policy does **not** apply, proving the scope is OU-bound.

## Verify

!!! success "Policy is working when..."
    - `gpresult /r /scope:user` on `WS01` lists `Dept-Wallpaper` under **Applied Group Policy Objects** for a user in IT, Sales, or HR.
    - The same user has the wallpaper visibly applied after one logoff/logon (some shell-level settings need a fresh session).
    - The built-in `Administrator` (sitting in `CN=Users`) does NOT show the policy in their `gpresult`.

PowerShell shortcut to inspect the GPO:

```powershell
Get-GPOReport -Name "Dept-Wallpaper" -ReportType Html -Path "C:\Temp\Dept-Wallpaper.html"
```

Open the HTML for a full settings dump.

## Snapshot

No new snapshot here. GPOs are cheap to rebuild and the changes are isolated to AD, not to the OS.

## Gotchas

!!! danger "GPOs do not link to `CN=Users` or `CN=Computers`"
    If a test user is still in the default `Users` container, `Dept-Wallpaper` will never apply to them no matter how many times you run `gpupdate`. Move them into `OU=Departments` (or run `redirusr.exe` once, see Phase 4) and retry.

!!! warning "Some settings need a logoff/logon, not just `gpupdate`"
    Wallpaper, drive maps, folder redirection, and printer connections require a fresh user session. `gpupdate /force` updates the policy engine but does not re-trigger the user logon scripts.

!!! warning "`Block Inheritance` and `Enforced` change the rules"
    By default, child OUs inherit GPOs from parent OUs. **Block Inheritance** on a child OU stops that. **Enforced** on a parent GPO bypasses block. If a GPO unexpectedly does not apply, check both flags before blaming AD.

!!! warning "Security filtering trumps OU link"
    By default, `Authenticated Users` is on the GPO's security filter. Removing it (or replacing it with a group the user is not in) silently disables the GPO for that user. CompTIA's "the policy is linked but does not apply" question is usually testing this.

??? info "Refresh timing"
    Clients refresh policy at logon and roughly every 90 minutes thereafter, with a random offset up to 30 minutes (so a fleet of clients does not all hit the DC at once). Domain controllers refresh every 5 minutes. `gpupdate /force` triggers an immediate refresh.
