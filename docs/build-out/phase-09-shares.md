# Phase 9: File shares

**Status:** Done.

## Goal

Create two file shares on `DC01` that the rest of the user-experience phases (10, 11) depend on:

- `Home$` at `C:\Shares\Home` for per-user home folders.
- `Redirect$` at `C:\Shares\Redirect` for folder redirection targets.

Both are hidden shares (trailing `$`), wide-open at the share level, locked down with NTFS. Permissions follow the **create-folder + creator-owner** pattern so each user owns only their own subfolder.

## Why it matters

Home folders and folder redirection both need a share to write to. Getting the NTFS pattern right once means Phase 10 and Phase 11 just work; getting it wrong means hours of "the folder appeared but I cannot save anything to it".

A+ Core 2 angle: knowing the difference between share and NTFS permissions, and the "most restrictive wins" rule, is core help-desk knowledge.

## Prerequisites

- Phase 8 complete. Group Policy works end-to-end.
- The Staff and Share-RW groups from Phase 6 exist.

## Steps

### Create the folders

1. From elevated PowerShell on DC01:

   ```powershell
   New-Item -Path "C:\Shares"          -ItemType Directory -Force | Out-Null
   New-Item -Path "C:\Shares\Home"     -ItemType Directory -Force | Out-Null
   New-Item -Path "C:\Shares\Redirect" -ItemType Directory -Force | Out-Null
   ```

### Create the shares (hidden, wide-open share permissions)

2. Share each folder, granting `Authenticated Users: Change`. (Why wide-open at the share level: NTFS will do the real enforcement, and a too-tight share permission silently overrides correct NTFS.)

   ```powershell
   New-SmbShare -Name "Home$"     -Path "C:\Shares\Home"     -FullAccess "Administrators" -ChangeAccess "Authenticated Users" -Description "Per-user home folders"
   New-SmbShare -Name "Redirect$" -Path "C:\Shares\Redirect" -FullAccess "Administrators" -ChangeAccess "Authenticated Users" -Description "Folder redirection targets"
   ```

### Lock down with NTFS (create-folder + creator-owner)

3. Reset NTFS so we start clean, then apply the pattern:

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
   - `SYSTEM:(OI)(CI)F` and `Administrators:(OI)(CI)F`: full control on this folder and everything under it. Lets backups, AV, and admin tools work.
   - `Authenticated Users:(CI)(AD,WD,REA,RA)`: at the root only, any signed-in user can **list contents, read attributes, and create subfolders** (`AD`/`WD` = append data / write data; `REA`/`RA` = read attributes; `CI` = applies to this folder, not files). They cannot read other people's folders because this permission does not propagate down (no `OI`).
   - `CREATOR OWNER:(OI)(CI)(IO)F`: full control, but only on items the user creates. `IO` (inherit-only) means it does not apply to the root, only to the children that get created.

   The net effect: each user can create their own subfolder; once created, they own it and have full control over its contents; no one else can see in.

### (Optional) Per-department share

4. If you want a dedicated read/write share for IT (matching the `IT-Share-RW` group from Phase 6), do this once. Repeat for Sales/HR if desired.

   ```powershell
   New-Item -Path "C:\Shares\IT" -ItemType Directory -Force | Out-Null
   New-SmbShare -Name "IT$" -Path "C:\Shares\IT" -FullAccess "Administrators" -ChangeAccess "Authenticated Users"
   icacls "C:\Shares\IT" /inheritance:r /grant:r `
       "SYSTEM:(OI)(CI)F" `
       "Administrators:(OI)(CI)F" `
       "IT-Share-RW:(OI)(CI)M"
   ```

   `M` = Modify. Note that the ACE is on the **Domain Local** group `IT-Share-RW`, not on `IT-Staff` directly. This is the **P** in AGDLP from Phase 6.

## Verify

From DC01:

```powershell
Get-SmbShare | Where-Object Name -in "Home$","Redirect$","IT$" |
    Select-Object Name, Path, Description |
    Format-Table -AutoSize

Get-SmbShareAccess -Name "Home$"
icacls "C:\Shares\Home"
```

From `WS01`, signed in as `jsmith@corp.lab`:

```powershell
# Listing the share root should work (Authenticated Users gets Read on the root by default)
Test-Path "\\DC01\Home$"

# Creating their own folder should work
New-Item -ItemType Directory -Path "\\DC01\Home$\jsmith" -Force

# Trying to peek inside someone else's folder should fail
Get-ChildItem "\\DC01\Home$\<some-other-user>" -ErrorAction Stop
```

!!! success "Pass criteria"
    - `Test-Path` returns `True`.
    - `New-Item` for the user's own folder succeeds.
    - Listing someone else's folder returns "access denied" (this is the goal: per-user isolation on a shared share).

## Snapshot

No new snapshot required. The shares are scripted and the data underneath is regenerated by users.

## Gotchas

!!! warning "Share permissions AND NTFS permissions both apply, most restrictive wins"
    If you set the share to `Read` and NTFS to `Modify`, the effective permission is `Read`. The wide-open `Authenticated Users: Change` at the share level lets NTFS be the single source of truth.

!!! danger "`$` hides the share, it does not secure it"
    `\\DC01\Home$` is invisible in network browsing. Anyone who knows the path can still try to connect. The protection is the NTFS ACL, not the dollar sign.

!!! warning "If users see 'Access denied' on their own folder"
    The Creator Owner ACE got dropped or misconfigured. Run the `icacls` block in step 3 again. The `(IO)` flag on Creator Owner is required so it applies to children, not the root.

!!! warning "Removing inheritance is destructive if done in the GUI without thinking"
    The PowerShell `icacls /inheritance:r` is explicit. If you redo this from the GUI, choose **Convert inherited permissions into explicit** first, then trim, so you do not strip Administrators by accident.

??? info "Why two shares instead of one"
    Home folders and folder redirection have different lifecycles. A home folder is tied to a user object; deleting the user does not automatically delete the folder. Folder redirection is per-folder per-user; a user can have Documents redirected and Desktop not. Keeping them separate makes backups, retention policies, and (later) DFS targeting cleaner.
