# Phase 12: Help-desk admin drills

**Status:** Not started.

## Goal

Practice the day-one tasks an A+/help-desk technician actually does on AD: reset a password, unlock a locked-out account, enable/disable an account, configure account lockout policy, and move objects between OUs. PowerShell and ADUC versions of each.

## Why it matters

Phases 1 to 11 build the lab. Phase 12 is the lab paying you back. These five operations cover something like 80% of real-world AD ticket volume.

A+ Core 2 angle: the exam phrasing is "user cannot log in, what do you do?", "the account is locked, how do you fix it?", "what is the difference between disable and delete?". These drills give you literal muscle memory for the answers.

## Prerequisites

- Phase 11 complete. WS01 is fully usable.
- 12 lab users from Phase 5 in `OU=Departments`.

## Steps and drills

### Drill 1: Reset a password

Scenario: `tmarsh` forgot their password.

PowerShell:

```powershell
$new = Read-Host -Prompt "New password" -AsSecureString
Set-ADAccountPassword -Identity tmarsh -NewPassword $new -Reset
Set-ADUser -Identity tmarsh -ChangePasswordAtLogon $true   # force a real change at next logon
```

ADUC: right-click the user > **Reset Password**. Check "User must change password at next logon".

(Why `-Reset` and not `-OldPassword`/`-NewPassword`: a helpdesk reset does not require the old password. A user change does. Different cmdlet path, same outcome.)

### Drill 2: Unlock an account

Scenario: `glowe` typed the wrong password 10 times in a meeting and got locked out.

```powershell
Unlock-ADAccount -Identity glowe
```

ADUC: right-click user > Properties > **Account** tab > "Unlock account" checkbox.

To see who is currently locked:

```powershell
Search-ADAccount -LockedOut | Select-Object SamAccountName, LastLogonDate
```

### Drill 3: Account lockout policy

Scenario: set the domain default. "Lock the account after 5 bad attempts, keep it locked for 15 minutes, reset the bad-attempt counter after 15 minutes."

```powershell
# Default Domain Policy is what enforces this in a single-domain forest.
Set-ADDefaultDomainPasswordPolicy `
    -Identity corp.lab `
    -LockoutThreshold 5 `
    -LockoutDuration (New-TimeSpan -Minutes 15) `
    -LockoutObservationWindow (New-TimeSpan -Minutes 15)
```

Verify:

```powershell
Get-ADDefaultDomainPasswordPolicy
```

(Why these numbers: 5 attempts is the industry common floor. 15 minutes is enough to deter a brute force, short enough that a real user does not call helpdesk in tears.)

### Drill 4: Enable / disable / delete an account

Scenario: `vcarr` is going on long leave. Disable, do not delete.

```powershell
Disable-ADAccount -Identity vcarr
```

Re-enable on return:

```powershell
Enable-ADAccount -Identity vcarr
```

If they leave permanently, then (and only then):

```powershell
Remove-ADUser -Identity vcarr -Confirm:$false
```

ADUC equivalents: right-click > **Disable Account** / **Enable Account** / **Delete**.

Why disable before delete: a disabled account keeps its SID and group memberships. Re-enabling brings the user back exactly as before. A deleted account is gone; recreating with the same name produces a **new SID**, which means all NTFS ACLs and group memberships are lost.

### Drill 5: Move an object between OUs

Scenario: `mdunn` transferred from Sales to IT.

```powershell
# Clear protection if it is set on the source OU (Phase 4 set this on all OUs)
Set-ADUser -Identity mdunn -ProtectedFromAccidentalDeletion:$false

Move-ADObject `
    -Identity (Get-ADUser mdunn).DistinguishedName `
    -TargetPath "OU=IT,OU=Departments,DC=corp,DC=lab"

# Update group memberships to match the new role
Remove-ADGroupMember -Identity Sales-Staff -Members mdunn -Confirm:$false
Add-ADGroupMember    -Identity IT-Staff    -Members mdunn

# Restore protection
Set-ADUser -Identity mdunn -ProtectedFromAccidentalDeletion:$true
```

ADUC: drag the user into the new OU. ADUC handles the protection prompt for you. Group memberships are NOT updated automatically; remember to fix them separately.

(Why moves matter: a user's DN changes, which means OU-linked GPOs change, which means the user's wallpaper, drive maps, and folder redirection all may shift. After a move, log the user out and back in.)

### Drill 6: Reset a computer account ("trust relationship failed")

Scenario: `WS01` boots and shows "the trust relationship between this workstation and the primary domain failed". This means the machine-account password is out of sync with AD.

From an elevated PowerShell on `WS01`, logged in with a local admin (or cached domain admin):

```powershell
Reset-ComputerMachinePassword -Server DC01 -Credential corp\Administrator
# Then reboot.
```

The old way (still works): unjoin from the domain, reboot, rejoin. The `Reset-ComputerMachinePassword` path is faster.

## Verify

After each drill, confirm:

```powershell
# Drill 1
Get-ADUser tmarsh -Properties PasswordLastSet, pwdLastSet |
    Select-Object SamAccountName, PasswordLastSet

# Drill 2
Search-ADAccount -LockedOut    # should be empty after the unlock

# Drill 3
(Get-ADDefaultDomainPasswordPolicy).LockoutThreshold   # 5

# Drill 4
Get-ADUser vcarr -Properties Enabled |
    Select-Object SamAccountName, Enabled

# Drill 5
Get-ADUser mdunn | Select-Object DistinguishedName   # ends in OU=IT,...
Get-ADPrincipalGroupMembership mdunn | Select-Object Name
```

!!! success "Pass criteria"
    Each drill produces the expected state above. If a drill fails, the most common cause is missing rights (run as `corp\Administrator`) or the user being in `CN=Users` instead of `OU=Departments`.

## Snapshot

No snapshot. These are reversible operations; the point is to be able to redo them on demand.

## Gotchas

!!! danger "Disable, do not delete, when in doubt"
    Re-creating a user does not recreate their SID. Every NTFS ACE and group membership keyed to the old SID is lost. Disable first; delete only when policy and time-since-departure say so.

!!! warning "Moving a user changes which GPOs apply"
    A user moved from Sales to IT may inherit different GPOs and different drive maps. Log them off and back on after a move so they get a clean policy refresh.

!!! warning "Lockout threshold of 0 means 'never lock out'"
    Easy to set by accident in `Set-ADDefaultDomainPasswordPolicy`. Confirm with `Get-ADDefaultDomainPasswordPolicy` afterward.

!!! warning '"Trust relationship failed" can also mean the computer object was deleted'
    If `Reset-ComputerMachinePassword` fails, check that the computer object still exists in AD (`Get-ADComputer WS01`). If it is gone, you need to unjoin and rejoin.

!!! tip "Practice the PowerShell and the GUI"
    The exam asks about ADUC menus. Real help-desk work happens in PowerShell because it scripts. Know both.
