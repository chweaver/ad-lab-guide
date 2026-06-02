# Phase 15: AD backup and restore

**Status:** Stretch. Beyond A+ Core 2 scope; portfolio depth toward MSP / SysAdmin work.

## Goal

Take a System State backup of `DC01` with Windows Server Backup, then walk through two restore scenarios:

1. **Non-authoritative restore**: a DC is rebuilt and re-replicates from another DC.
2. **Authoritative restore**: an OU was deleted, and you bring it back as the source of truth.

In a single-DC lab, non-authoritative is mostly theoretical (there is no second DC to replicate from). Phase 16 fixes that. This phase teaches the mechanics.

## Why it matters

Backups are the answer to every "we deleted an OU by accident" ticket. The AD Recycle Bin is the modern fast path. System State + DSRM is the only path for catastrophic loss.

## Prerequisites

- Phase 12 complete (you have content worth backing up).
- DSRM password from Phase 3 saved and known.

## Steps

### Part 1: Install Windows Server Backup

```powershell
Install-WindowsFeature -Name Windows-Server-Backup -IncludeManagementTools
```

### Part 2: Take a System State backup

A "System State" backup includes Active Directory (`NTDS.dit`), SYSVOL, the registry, IIS metabase (if installed), and boot files. Enough to restore a DC.

1. Attach an extra virtual disk to DC01 (let us say drive `E:`, 40 GB, NVMe). Format NTFS. This is the backup target. (Why a separate disk: Windows Server Backup will not back up to the same volume it is backing up.)

2. Run a one-shot System State backup:

   ```powershell
   wbadmin start systemstatebackup -backupTarget:E: -quiet
   ```

   The first run takes a few minutes. The backup lives at `E:\WindowsImageBackup\DC01\`.

3. Confirm:

   ```powershell
   wbadmin get versions -backupTarget:E:
   ```

   Note the version identifier (a timestamp). You will pass it to `wbadmin start systemstaterecovery`.

### Part 3: Enable AD Recycle Bin (separate from backup, but always-on safety net)

The Recycle Bin recovers deleted objects without a restore. It is a one-way switch.

```powershell
Enable-ADOptionalFeature `
    -Identity "Recycle Bin Feature" `
    -Scope ForestOrConfigurationSet `
    -Target "corp.lab" `
    -Confirm:$false
```

After enabling, deleted objects sit in `CN=Deleted Objects,DC=corp,DC=lab` for the **deletedObjectLifetime** (default 180 days). Recover with `Restore-ADObject`.

### Part 4: Practice an undelete (no backup needed)

This is the modern "OU got deleted, undo it" workflow:

1. From DC01 (lab destructive, do this on a test OU not a real one):

   ```powershell
   Set-ADOrganizationalUnit -Identity "OU=HR,OU=Departments,DC=corp,DC=lab" `
       -ProtectedFromAccidentalDeletion:$false
   Remove-ADOrganizationalUnit -Identity "OU=HR,OU=Departments,DC=corp,DC=lab" -Recursive -Confirm:$false
   ```

2. Confirm it is gone:

   ```powershell
   Get-ADOrganizationalUnit -Filter 'Name -eq "HR"'   # empty
   ```

3. Look in the Recycle Bin:

   ```powershell
   Get-ADObject -SearchBase "CN=Deleted Objects,DC=corp,DC=lab" `
       -ldapFilter "(isDeleted=TRUE)" -IncludeDeletedObjects |
       Select-Object Name, ObjectClass, lastKnownParent
   ```

4. Restore the OU first, then its child users (parents must come back before children):

   ```powershell
   Get-ADObject -SearchBase "CN=Deleted Objects,DC=corp,DC=lab" `
       -ldapFilter "(&(isDeleted=TRUE)(name=HR*))" -IncludeDeletedObjects |
       Restore-ADObject

   Get-ADObject -SearchBase "CN=Deleted Objects,DC=corp,DC=lab" `
       -ldapFilter "(&(isDeleted=TRUE)(lastKnownParent=OU=HR,OU=Departments,DC=corp,DC=lab))" `
       -IncludeDeletedObjects |
       Restore-ADObject
   ```

5. Verify the OU and its users are back:

   ```powershell
   Get-ADUser -Filter * -SearchBase "OU=HR,OU=Departments,DC=corp,DC=lab"
   ```

### Part 5: Authoritative restore via wbadmin (theoretical in a single-DC lab)

This is the workflow you would run if the Recycle Bin was not enabled or the object lifetime had expired. It requires booting into DSRM.

1. Reboot DC01. At the boot menu, press **F8** to get advanced boot options (in a VM, use the "Advanced startup" path from Settings or set the boot to safe mode beforehand):

   ```powershell
   bcdedit /set safeboot dsrepair
   shutdown /r /t 0
   ```

2. Log in with the DSRM password (username: `.\Administrator` on the local Administrator account, not the domain one).

3. Restore System State:

   ```powershell
   wbadmin get versions -backupTarget:E:
   wbadmin start systemstaterecovery -version:<version-id> -backupTarget:E: -authsysvol -quiet
   ```

4. Mark the deleted OU (or whatever you are bringing back) as authoritative using `ntdsutil`:

   ```
   ntdsutil
     activate instance ntds
     authoritative restore
       restore subtree "OU=HR,OU=Departments,DC=corp,DC=lab"
     quit
     quit
   ```

5. Reboot back into normal mode:

   ```powershell
   bcdedit /deletevalue safeboot
   shutdown /r /t 0
   ```

??? info "Why authoritative vs non-authoritative"
    - **Non-authoritative restore**: bring this DC back to a past state, then let replication overwrite anything that has changed since on other DCs. Useful when the DC itself failed but the rest of AD is fine.
    - **Authoritative restore**: bring a specific object (or subtree) back and **force every other DC to accept this version**. Useful when something was deleted everywhere and you want it back everywhere. `ntdsutil`'s `authoritative restore` bumps the version number high enough that replication propagates it outward instead of overwriting it.

## Verify

After Part 4 (the undelete drill):

```powershell
Get-ADOrganizationalUnit -Identity "OU=HR,OU=Departments,DC=corp,DC=lab"
(Get-ADUser -Filter * -SearchBase "OU=HR,OU=Departments,DC=corp,DC=lab").Count
```

!!! success "Pass criteria"
    OU is restored. Users return with their original SIDs, group memberships, and home folder settings. NTFS ACLs on `\\DC01\Home$\<user>` still recognise them (because the SID did not change).

For Part 5, the verify is "DC boots, AD is healthy, the missing OU is back":

```powershell
dcdiag /v
repadmin /showrepl    # in a multi-DC setup
```

## Snapshot

Take a snapshot **before** doing the DSRM exercise (Part 5). Name it `pre-dsrm-experiment`. If you typo a `ntdsutil` command, rolling back is faster than fixing it.

## Gotchas

!!! danger "Do not snapshot a DC and roll it back if other DCs exist"
    With one DC the lab is forgiving. With two or more (Phase 16), rolling back a DC introduces a **USN rollback** that other DCs detect and quarantine. Use AD-aware backups (Windows Server Backup + DSRM), not VMware snapshots, on multi-DC environments.

!!! warning "AD Recycle Bin is one-way"
    Once enabled, it cannot be disabled. The cost is a slightly larger NTDS.dit and a longer deletedObjectLifetime window. The benefit is undelete without DSRM. Always enable it.

!!! warning "DSRM password is the local Administrator password in DSRM"
    In normal boot, `Administrator` means `CORP\Administrator`. In DSRM, `Administrator` means the local SAM Administrator, and its password is the DSRM password you set at promotion. Mixing these up is a classic stuck-in-DSRM moment.

!!! warning "`-authsysvol` matters for SYSVOL restores"
    Without it, `wbadmin start systemstaterecovery` brings back the AD database but leaves SYSVOL in non-authoritative mode, and GPOs may not replicate correctly. Always pass `-authsysvol` on a DSRM restore unless you have a specific reason not to.

!!! warning "After DSRM restore, watch replication carefully"
    Even in a single-DC lab, run `repadmin /showrepl` and `dcdiag /v`. In a real environment this is where you would coordinate with the team holding the other DCs.
