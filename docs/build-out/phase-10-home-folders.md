# Phase 10: Home folders and folder redirection

**Status:** Not started.

## Goal

Two distinct things, often confused:

1. **Home folder**: a per-user network drive letter (`H:`) mapped to `\\DC01\Home$\%username%`. Set on the **user object** (Profile tab).
2. **Folder redirection**: replace a user's local **Documents** folder with `\\DC01\Redirect$\<username>\Documents`. Set on a **GPO**.

Both produce server-side storage that follows the user across machines. They are configured in different places and do different things.

## Why it matters

This is the single most-tested distinction on A+ 220-1202 objective 2.2. Outside the exam, it is the standard "user data follows the user" setup for any small Windows environment.

## Prerequisites

- Phase 9 complete. `\\DC01\Home$` and `\\DC01\Redirect$` exist with the create-folder + creator-owner NTFS pattern.
- `WS01` joined to `corp.lab` and a domain user can log in interactively.

## Steps

### Part 1: Home folder

1. Set the home folder on every user in `OU=Departments` in one pass. AD will create `\\DC01\Home$\<sam>` on first logon and ACL it to the user automatically (because of the Creator Owner NTFS pattern from Phase 9).

   ```powershell
   $domain = "DC=corp,DC=lab"
   $users  = Get-ADUser -Filter * -SearchBase "OU=Departments,$domain"

   foreach ($u in $users) {
       Set-ADUser -Identity $u `
           -HomeDrive      "H:" `
           -HomeDirectory  "\\DC01\Home$\$($u.SamAccountName)"
   }
   ```

   Equivalent in ADUC: open a user > Profile tab > **Connect** > drive `H:` > **To** `\\DC01\Home$\%username%`.

2. Log on to `WS01` as `jsmith@corp.lab`. Open File Explorer; an `H:` drive should be present, pointed at `\\DC01\Home$\jsmith`. The folder was created during logon by Netlogon/Userenv and ACLed so only `jsmith` has full control.

### Part 2: Folder redirection

3. From DC01, open **Group Policy Management** (`gpmc.msc`).
4. Create a new GPO named `Dept-FolderRedirect`. Link it to `OU=Departments`.
5. Edit the GPO. Navigate to:

   `User Configuration > Policies > Windows Settings > Folder Redirection > Documents`

6. Right-click **Documents > Properties**.
   - **Setting**: `Basic - Redirect everyone's folder to the same location`.
   - **Target folder location**: `Create a folder for each user under the root path`.
   - **Root Path**: `\\DC01\Redirect$`.
   - **Settings tab**:
     - "Grant the user exclusive rights to Documents" = checked.
     - "Move the contents of Documents to the new location" = checked.
     - "Also apply redirection policy to Windows 2000, XP..." = unchecked (legacy).
     - "Policy Removal" = "Leave the folder in the new location when policy is removed". (Why: safer rollback if you ever unlink the GPO.)
7. Click OK. Confirm the GPO is enabled and linked.

??? info "PowerShell-only version of the redirection settings"
    Folder Redirection uses an XML payload (`fdeploy1.ini`) inside SYSVOL, not registry keys. There is no first-class PowerShell cmdlet for it. Either set it once in GPMC and back up the GPO (`Backup-GPO`), or use the `Microsoft.GroupPolicy.GPRegistryValue` API in `Set-GPRegistryValue` for the registry-CSE half. For a lab, set it in GPMC.

8. On `WS01`, log in as `jsmith@corp.lab` (or run `gpupdate /force` then **log off and back on**; folder redirection takes effect at logon, not at policy refresh).

9. Confirm. From the user's session:

   ```powershell
   [Environment]::GetFolderPath("MyDocuments")
   ```

   should now return `\\DC01\Redirect$\jsmith\Documents`, not `C:\Users\jsmith\Documents`.

## Verify

From DC01:

```powershell
Get-ADUser jsmith -Properties HomeDrive, HomeDirectory |
    Select-Object SamAccountName, HomeDrive, HomeDirectory

Get-ChildItem "C:\Shares\Home"      | Select-Object Name, FullName
Get-ChildItem "C:\Shares\Redirect"  | Select-Object Name, FullName
```

!!! success "Pass criteria"
    - `Get-ADUser` returns `HomeDrive: H:` and `HomeDirectory: \\DC01\Home$\jsmith`.
    - After `jsmith` has logged on once, `C:\Shares\Home\jsmith` exists and `icacls C:\Shares\Home\jsmith` shows `jsmith` with Full Control.
    - After folder redirection applies, `C:\Shares\Redirect\jsmith\Documents` exists.
    - On `WS01`, `H:` is mapped and `Documents` points to `\\DC01\Redirect$\jsmith\Documents`.

## Snapshot

No new VM-level snapshot. The data here is user content; back it up rather than snapshotting (Phase 15 covers AD backup, file backup is a separate concern).

## Gotchas (the big ones)

!!! danger "Home folder ≠ folder redirection"
    Home folder is **a drive letter set on the user object**. Folder redirection is **a per-folder redirect set in a GPO**. CompTIA loves this distinction. They solve overlapping problems and you can use both at once.

!!! warning "Folder redirection needs a logoff/logon, not just `gpupdate`"
    `gpupdate /force` will not move Documents. Log off and back on. The Folder Redirection client-side extension processes only at logon.

!!! danger "Wrong NTFS on the redirect root locks users out of their own Documents"
    If you skip the Creator Owner ACE from Phase 9, the GPO creates the folder, then the user opens Documents and gets "access denied" because they do not own the new folder. Re-run the Phase 9 NTFS block if this happens.

!!! warning '"Grant the user exclusive rights" deletes inherited permissions'
    With that box checked, even Administrators can lose access to the user's redirected folder. The lab's NTFS pattern keeps `Administrators:(OI)(CI)F` at the root, but propagation depends on the folder-redirection setting. For helpdesk-level support, leave it checked; for backup workflows that need to traverse content, set it deliberately.

!!! warning '`%username%` is a logon-time variable, not a generic AD attribute'
    In the user object Profile tab, you can type `\\DC01\Home$\%username%` and AD substitutes the SAM name. In a PowerShell call to `Set-ADUser`, **you have to expand it yourself** (`$u.SamAccountName`); `%username%` will be stored literally and break the path.

??? info "When to use which"
    - **Home folder only**: small environment, users mostly use `H:` for their personal files. Documents stays local.
    - **Folder redirection only**: modern setups; user clicks "Documents", it just works on any machine, no drive-letter shuffle.
    - **Both**: the lab's choice. `H:` is for explicit-network scratch, redirection is for transparent user-data portability. The exam expects you to know both exist.
