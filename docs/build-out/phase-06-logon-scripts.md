# Phase 6: Login scripts and drive maps

**Status:** In progress. Remaining: the Verify pass on WS01 (login.log exists, `S:` maps for IT users only).

**Goal:** Run a login script via GPO and map a drive via Group Policy Preferences with item-level targeting, so IT users get `S:` pointed at `\\DC01\IT$` and everyone in `Departments` gets a logged greeting.

**What this proves:** I know both logon-automation techniques and which to prefer: GPP for drives, scripts for everything else.

## Prerequisites

- Phase 5 complete. Folder redirection working end to end, and the `\\DC01\IT$` share exists.

## Steps

### Part 1: Login script via GPO

1. On DC01, create a script in the NETLOGON share (`\\corp.lab\SYSVOL\corp.lab\scripts\` under the hood; SYSVOL replication pushes it to any other DC):

    ```powershell
    $scriptPath = "C:\Windows\SYSVOL\domain\scripts\hello.cmd"
    @"
    @echo off
    echo Welcome to %COMPUTERNAME%, %USERNAME%. >> "%USERPROFILE%\login.log"
    echo Today: %DATE% %TIME% >> "%USERPROFILE%\login.log"
    "@ | Set-Content -Path $scriptPath -Encoding ASCII
    ```

2. Open GPMC. Create a new GPO named `Dept-LoginScript`, link it to `OU=Departments`.
3. Edit it: `User Configuration > Policies > Windows Settings > Scripts (Logon/Logoff) > Logon`.
4. **Add** > **Script Name**: `hello.cmd`. **Script Parameters**: leave blank. Click OK.
    - The "script name" field is relative to the NETLOGON share. Do not enter a full UNC path.

??? info "PowerShell alternative for the script content"
    A `.ps1` works the same way; add it via the **PowerShell Scripts** tab inside the same GPO node. By default, PowerShell scripts run **before** classic scripts; you can change the order on the same dialog. For the lab, `.cmd` is enough.

### Part 2: Drive mapping via Group Policy Preferences

5. Create a GPO called `Dept-DriveMaps`, linked to `OU=Departments`. (One GPO per intent keeps troubleshooting clean.)
6. Navigate to: `User Configuration > Preferences > Windows Settings > Drive Maps`.
7. Right-click **Drive Maps > New > Mapped Drive**:
    - **Action**: `Replace` (creates if missing, replaces if present; safer than `Update` if you ever change the path).
    - **Location**: `\\DC01\IT$`.
    - **Reconnect**: checked.
    - **Label as**: `IT Share`.
    - **Drive Letter**: `Use > S:`.
    - **Common tab**: check **Item-level targeting** > **Targeting...** > **New Item > Security Group** > `CORP\IT-Staff`.
        - The killer feature of GPP: one GPO maps different drives for different groups. Sales gets nothing on `S:` because they are not in `IT-Staff`.
8. OK out. Done.

??? info "Why GPP for drives instead of a `net use` script"
    GPP is declarative ("here is the drive that should exist"), targets by group/OU/IP/anything natively, and removes the drive automatically when the user leaves the group (with the `Replace` action) or when the GPO un-links. `net use` in a script is imperative, leaves stale mappings on user removal, and requires extra logic to scope by group.

### Part 3: Apply and confirm

9. From `WS01` as `jsmith@corp.lab`:

    ```powershell
    gpupdate /force
    # log off and back on for full effect
    ```

10. After logging back in:

    ```powershell
    Get-Content "$env:USERPROFILE\login.log"   # should contain a greeting from hello.cmd
    Get-PSDrive S                              # should show \\DC01\IT$
    ```

## Screenshot

- Capture: WS01 terminal with `Get-Content login.log` output and `Get-PSDrive S` for an IT user. Save as `img/phase-06-script-drivemap.png`. Slot reserved, not captured yet.

## Verify

!!! success "Pass criteria"
    - `gpresult /r /scope:user` on WS01 lists `Dept-LoginScript` and `Dept-DriveMaps` under Applied Group Policy Objects.
    - `%USERPROFILE%\login.log` exists and has at least one line per logon for a Departments user.
    - `S:` is mapped to `\\DC01\IT$` for an IT user. Drive `S:` does not exist for a Sales or HR user (item-level targeting filters by `IT-Staff`).

## Snapshot

No new snapshot. Scripts and GPOs are scripted/exportable and cheap to recreate.

## Gotchas

!!! warning "Logon scripts need a logoff/logon, not just `gpupdate`"
    The Scripts CSE only fires at user logon. `gpupdate /force` updates the policy engine; the next logon runs the script.

!!! danger "Do not store secrets in `Drive Maps > Connect as:` credentials"
    GPP used to allow saving a username/password in the GPO XML. Microsoft published the static AES key in 2014. Result: **anyone with read access to SYSVOL (every authenticated user) can decrypt those credentials.** Microsoft patched the *ability to create* new ones (MS14-025), but old GPOs may still contain them. Never put a password in a GPP item.

!!! warning "Script path is relative to NETLOGON, not an absolute UNC"
    Type `hello.cmd`, not `\\corp.lab\SYSVOL\corp.lab\scripts\hello.cmd`. The Scripts CSE prepends NETLOGON automatically. Putting a full UNC there silently breaks the script.

!!! warning "GPP drive maps need the GPP CSE installed (it is on by default on Win10/11)"
    On older clients (Server 2003 / XP, not relevant in the lab) GPP needs an extra client-side extension. Modern Windows ships with it.

!!! tip "Use one GPO per intent, not one GPO per setting"
    Bundling "logon scripts", "drive maps", and "wallpaper" into one mega-GPO makes troubleshooting painful. Each intent in this lab gets its own GPO so you can disable any one of them in isolation when you debug.

??? info "Which approach for which job"
    - **Drive mapping**: GPP over script. Use Group Policy Preferences with item-level targeting.
    - **Banner / time sync / one-shot registry tweaks**: script (.cmd or .ps1) via GPO Logon Scripts.
    - **Persistent registry settings**: GPP > Registry, or an Administrative Template if one already exists.
    - **Software install**: `Computer Configuration > Software Installation` (MSI only) or Intune in modern environments. Out of scope for this lab.
