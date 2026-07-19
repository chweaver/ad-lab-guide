# Phase 4: Group Policy basics

**Status:** Done.

**Goal:** Create one GPO (`Dept-Wallpaper`), link it to `OU=Departments`, and prove inheritance applies it to users in child OUs via `gpupdate` and `gpresult`.

**What this proves:** I can link, scope, and verify a GPO, the mechanism every later phase (redirection, scripts, drive maps, security baselines) is built on.

## Prerequisites

- Phase 3 complete. `WS01` is domain-joined. Snapshot `clean-domain-joined` exists.
- GPMC is already on DC01 (it came with the AD DS role tools in Phase 1).

## Steps

### Part 1: Build the GPO

1. On DC01, open **Group Policy Management** (`gpmc.msc`).
2. Right-click **Forest > Domains > corp.lab > Group Policy Objects > New**. Name it `Dept-Wallpaper`. Wallpaper is a clean, visible, harmless test policy.
3. Right-click the new GPO > **Edit**. Navigate to:

    `User Configuration > Policies > Administrative Templates > Desktop > Desktop > Desktop Wallpaper`

    - Set the policy to **Enabled**.
    - **Wallpaper name**: `\\DC01\SYSVOL\corp.lab\scripts\wallpaper.jpg` (any image works; the exact path is illustrative).
    - **Wallpaper style**: `Fill`.
    - Close the editor.
4. Back in GPMC, right-click `OU=Departments` > **Link an Existing GPO...** > select `Dept-Wallpaper`. Scoping to `Departments` keeps built-in service accounts in `CN=Users` unaffected, and `Workstations` does not inherit it either.

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

### Part 2: Force a refresh on WS01

5. Log in to `WS01` as `jsmith@corp.lab` (member of `OU=IT`, a child of `OU=Departments`).
6. From elevated PowerShell on `WS01`:

    ```powershell
    gpupdate /force
    ```

    Expected: "User Policy update has completed successfully. Computer Policy update has completed successfully."

7. Verify which GPOs applied:

    ```powershell
    gpresult /r /scope:user
    ```

    Under **Applied Group Policy Objects**, you should see `Dept-Wallpaper`.

### Part 3: Prove inheritance

8. Log in to `WS01` as `mtate@corp.lab` (member of `OU=Sales`, sibling of IT). The policy applies to this user too, because the link is on the parent OU.
9. Optional: log in as a user outside `OU=Departments` (the built-in `Administrator` lives in `CN=Users`). Confirm the policy does **not** apply, proving the scope is OU-bound.

## Screenshot

- Capture: `gpresult /r /scope:user` on WS01 with `Dept-Wallpaper` under Applied Group Policy Objects. Save as `img/phase-04-gpresult.png`. Slot reserved, not captured yet.

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
    If a test user is still in the default `Users` container, `Dept-Wallpaper` will never apply to them no matter how many times you run `gpupdate`. Move them into `OU=Departments` (or run `redirusr.exe` once, see Phase 2) and retry.

!!! warning "Some settings need a logoff/logon, not just `gpupdate`"
    Wallpaper, drive maps, folder redirection, and printer connections require a fresh user session. `gpupdate /force` updates the policy engine but does not re-trigger the user logon scripts.

!!! warning "`Block Inheritance` and `Enforced` change the rules"
    By default, child OUs inherit GPOs from parent OUs. **Block Inheritance** on a child OU stops that. **Enforced** on a parent GPO bypasses block. If a GPO unexpectedly does not apply, check both flags before blaming AD.

!!! warning "Security filtering trumps OU link"
    By default, `Authenticated Users` is on the GPO's security filter. Removing it (or replacing it with a group the user is not in) silently disables the GPO for that user. CompTIA's "the policy is linked but does not apply" question is usually testing this.

??? info "Refresh timing"
    Clients refresh policy at logon and roughly every 90 minutes thereafter, with a random offset up to 30 minutes (so a fleet of clients does not all hit the DC at once). Domain controllers refresh every 5 minutes. `gpupdate /force` triggers an immediate refresh.
