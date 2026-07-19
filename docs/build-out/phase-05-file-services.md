# Phase 5: File services: shares, home folders, redirection

**Status:** Done.

**Goal:** Create the `Home$` and `Redirect$` shares with the create-folder + creator-owner NTFS pattern, then build both server-backed user-data mechanisms on top: a per-user `H:` home folder set on the user object, and Documents folder redirection set in a GPO.

**What this proves:** I know share vs NTFS permissions, and the difference CompTIA tests hardest in objective 2.2: home folder (drive letter, user object) vs folder redirection (named folders, GPO).

## Prerequisites

- Phase 4 complete. Group Policy works end to end.
- The Staff and Share-RW groups from Phase 2 exist.
- `WS01` joined to `corp.lab` and a domain user can log in interactively.

## Steps

### Part 1: Create the folders and shares

1. From elevated PowerShell on DC01:

    ```powershell
    New-Item -Path "C:\Shares"          -ItemType Directory -Force | Out-Null
    New-Item -Path "C:\Shares\Home"     -ItemType Directory -Force | Out-Null
    New-Item -Path "C:\Shares\Redirect" -ItemType Directory -Force | Out-Null
    ```

2. Share each folder, hidden (trailing `$`), wide open at the share level so NTFS is the single source of truth:

    ```powershell
    New-SmbShare -Name "Home$"     -Path "C:\Shares\Home"     -FullAccess "Administrators" -ChangeAccess "Authenticated Users" -Description "Per-user home folders"
    New-SmbShare -Name "Redirect$" -Path "C:\Shares\Redirect" -FullAccess "Administrators" -ChangeAccess "Authenticated Users" -Description "Folder redirection targets"
    ```

### Part 2: Lock down with NTFS (create-folder + creator-owner)

3. Reset NTFS and apply the pattern:

    ```powershell
    # Helper function for readability
    function Set-HomeNTFS {
        param([string]$Path)

        icacls $Path /inheritance:r /grant:r `
            "SYSTEM:(OI)(CI)F" `
            "Administrators:(OI)(CI)F" `
            "Authenticated Users:(CI)(AD,WD,REA,RA)" `
            "CREATOR OWNER:(OI)(CI)(IO)F"
    }

    Set-HomeNTFS -Path "C:\Shares\Home"
    Set-HomeNTFS -Path "C:\Shares\Redirect"
    ```

    What each ACE does:

    - `SYSTEM:(OI)(CI)F` and `Administrators:(OI)(CI)F`: full control on the folder and everything under it. Lets backups, AV, and admin tools work.
    - `Authenticated Users:(CI)(AD,WD,REA,RA)`: at the root only, any signed-in user can list contents, read attributes, and create subfolders. No `OI`, so it does not propagate down; they cannot read other people's folders.
    - `CREATOR OWNER:(OI)(CI)(IO)F`: full control, but only on items the user creates. `IO` (inherit-only) keeps it off the root.

    Net effect: each user can create their own subfolder, owns it fully once created, and no one else can see in.

### Part 3: Per-department share (IT example)

4. A dedicated read/write share for IT, matching the `IT-Share-RW` group from Phase 2. Repeat for Sales/HR later (that rollout is the planned Phase 9):

    ```powershell
    New-Item -Path "C:\Shares\IT" -ItemType Directory -Force | Out-Null
    New-SmbShare -Name "IT$" -Path "C:\Shares\IT" -FullAccess "Administrators" -ChangeAccess "Authenticated Users"
    icacls "C:\Shares\IT" /inheritance:r /grant:r `
        "SYSTEM:(OI)(CI)F" `
        "Administrators:(OI)(CI)F" `
        "IT-Share-RW:(OI)(CI)M"
    ```

    `M` = Modify. The ACE is on the **Domain Local** group `IT-Share-RW`, not on `IT-Staff` directly. This is the **P** in AGDLP.

### Part 4: Home folders

5. Set the home folder on every user in `OU=Departments` in one pass. AD creates `\\DC01\Home$\<sam>` on first logon and ACLs it to the user automatically, thanks to the Creator Owner pattern:

    ```powershell
    $domain = "DC=corp,DC=lab"
    $users  = Get-ADUser -Filter * -SearchBase "OU=Departments,$domain"

    foreach ($u in $users) {
        Set-ADUser -Identity $u `
            -HomeDrive      "H:" `
            -HomeDirectory  "\\DC01\Home$\$($u.SamAccountName)"
    }
    ```

    Equivalent in ADUC: user > Profile tab > **Connect** > drive `H:` > **To** `\\DC01\Home$\%username%`.

6. Log on to `WS01` as `jsmith@corp.lab`. File Explorer shows an `H:` drive pointed at `\\DC01\Home$\jsmith`.

### Part 5: Folder redirection

7. On DC01, open GPMC. Create a GPO named `Dept-FolderRedirect`, link it to `OU=Departments`.
8. Edit it: `User Configuration > Policies > Windows Settings > Folder Redirection > Documents`.
9. Right-click **Documents > Properties**:
    - **Setting**: `Basic - Redirect everyone's folder to the same location`.
    - **Target folder location**: `Create a folder for each user under the root path`.
    - **Root Path**: `\\DC01\Redirect$`.
    - **Settings tab**:
        - "Grant the user exclusive rights to Documents" = checked.
        - "Move the contents of Documents to the new location" = checked.
        - "Also apply redirection policy to Windows 2000, XP..." = unchecked (legacy).
        - "Policy Removal" = "Leave the folder in the new location when policy is removed" (safer rollback if you ever unlink the GPO).
10. On `WS01`, log in as `jsmith@corp.lab` (or run `gpupdate /force` then **log off and back on**; redirection applies at logon, not at policy refresh).
11. Confirm from the user's session:

    ```powershell
    [Environment]::GetFolderPath("MyDocuments")
    ```

    Expected: `\\DC01\Redirect$\jsmith\Documents`, not `C:\Users\jsmith\Documents`.

??? info "PowerShell-only version of the redirection settings"
    Folder Redirection uses an XML payload (`fdeploy1.ini`) inside SYSVOL, not registry keys. There is no first-class PowerShell cmdlet for it. Either set it once in GPMC and back up the GPO (`Backup-GPO`), or use the `Microsoft.GroupPolicy.GPRegistryValue` API in `Set-GPRegistryValue` for the registry-CSE half. For a lab, set it in GPMC.

??? info "Why two shares instead of one, and when to use which mechanism"
    Home folders and folder redirection have different lifecycles. A home folder is tied to a user object; deleting the user does not automatically delete the folder. Folder redirection is per-folder per-user. Keeping them separate makes backups, retention, and (later) DFS targeting cleaner.

    - **Home folder only**: small environment, users mostly use `H:` for personal files.
    - **Folder redirection only**: modern setups; Documents just works on any machine.
    - **Both**: the lab's choice. `H:` for explicit-network scratch, redirection for transparent user-data portability. The exam expects you to know both exist.

## Screenshot

- Capture: WS01 File Explorer showing the `H:` drive plus `[Environment]::GetFolderPath("MyDocuments")` returning the UNC path. Save as `img/phase-05-h-drive-redirect.png`. Slot reserved, not captured yet.

## Verify

From DC01:

```powershell
Get-SmbShare | Where-Object Name -in "Home$","Redirect$","IT$" |
    Select-Object Name, Path, Description |
    Format-Table -AutoSize

Get-SmbShareAccess -Name "Home$"
icacls "C:\Shares\Home"

Get-ADUser jsmith -Properties HomeDrive, HomeDirectory |
    Select-Object SamAccountName, HomeDrive, HomeDirectory

Get-ChildItem "C:\Shares\Home"      | Select-Object Name, FullName
Get-ChildItem "C:\Shares\Redirect"  | Select-Object Name, FullName
```

From `WS01`, signed in as `jsmith@corp.lab`:

```powershell
# Listing the share root should work
Test-Path "\\DC01\Home$"

# Creating their own folder should work
New-Item -ItemType Directory -Path "\\DC01\Home$\jsmith" -Force

# Trying to peek inside someone else's folder should fail
Get-ChildItem "\\DC01\Home$\<some-other-user>" -ErrorAction Stop
```

!!! success "Pass criteria"
    - `Test-Path` returns `True`; creating the user's own folder succeeds; listing someone else's folder returns "access denied" (per-user isolation on a shared share).
    - `Get-ADUser` returns `HomeDrive: H:` and `HomeDirectory: \\DC01\Home$\jsmith`.
    - After `jsmith` logs on once, `C:\Shares\Home\jsmith` exists and `icacls C:\Shares\Home\jsmith` shows `jsmith` with Full Control.
    - After redirection applies, `C:\Shares\Redirect\jsmith\Documents` exists, `H:` is mapped, and Documents points at `\\DC01\Redirect$\jsmith\Documents`.

## Snapshot

No new VM-level snapshot. Shares and GPOs are scripted; the data underneath is user content, which gets backed up (Phase 15), not snapshotted.

## Gotchas

!!! danger "Home folder is not folder redirection"
    Home folder is **a drive letter set on the user object**. Folder redirection is **a per-folder redirect set in a GPO**. CompTIA loves this distinction. They solve overlapping problems and you can use both at once.

!!! warning "Share permissions AND NTFS permissions both apply, most restrictive wins"
    If you set the share to `Read` and NTFS to `Modify`, the effective permission is `Read`. The wide-open `Authenticated Users: Change` at the share level lets NTFS be the single source of truth.

!!! danger "`$` hides the share, it does not secure it"
    `\\DC01\Home$` is invisible in network browsing. Anyone who knows the path can still try to connect. The protection is the NTFS ACL, not the dollar sign.

!!! warning "If users see 'Access denied' on their own folder"
    The Creator Owner ACE got dropped or misconfigured. Run the `icacls` block in step 3 again. The `(IO)` flag on Creator Owner is required so it applies to children, not the root.

!!! warning "Removing inheritance is destructive if done in the GUI without thinking"
    The PowerShell `icacls /inheritance:r` is explicit. If you redo this from the GUI, choose **Convert inherited permissions into explicit** first, then trim, so you do not strip Administrators by accident.

!!! warning "Folder redirection needs a logoff/logon, not just `gpupdate`"
    `gpupdate /force` will not move Documents. Log off and back on. The Folder Redirection client-side extension processes only at logon.

!!! danger "Wrong NTFS on the redirect root locks users out of their own Documents"
    If you skip the Creator Owner ACE, the GPO creates the folder, then the user opens Documents and gets "access denied" because they do not own the new folder. Re-run the Part 2 NTFS block if this happens.

!!! warning '"Grant the user exclusive rights" deletes inherited permissions'
    With that box checked, even Administrators can lose access to the user's redirected folder. The lab's NTFS pattern keeps `Administrators:(OI)(CI)F` at the root, but propagation depends on the folder-redirection setting. For helpdesk-level support, leave it checked; for backup workflows that need to traverse content, set it deliberately.

!!! warning '`%username%` is a logon-time variable, not a generic AD attribute'
    In the user object Profile tab, you can type `\\DC01\Home$\%username%` and AD substitutes the SAM name. In a PowerShell call to `Set-ADUser`, **you have to expand it yourself** (`$u.SamAccountName`); `%username%` will be stored literally and break the path.
