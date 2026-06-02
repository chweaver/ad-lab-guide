# Phase 4: OU structure

**Status:** Done.

## Goal

Build the OU tree the rest of the lab depends on. Parent OU `Departments` with children `IT`, `Sales`, `HR`, plus a sibling OU `Workstations`.

## Why it matters

OUs are the unit of delegation and the unit of GPO targeting. Without a clean tree, every GPO ends up linked at the domain root, every helpdesk delegation becomes "do whatever you want to all of AD", and AGDLP turns into a mess.

A+ Core 2 angle: 2.2 lists "organizational units" by name. Knowing OUs are not the same as the built-in `Users` and `Computers` containers is a common exam question.

## Prerequisites

- Phase 3 complete. `Get-ADDomain` returns `corp.lab`.
- Snapshot `clean-dc-promoted` taken.

## Steps

1. From elevated PowerShell on DC01:

   ```powershell
   $domain = "DC=corp,DC=lab"

   New-ADOrganizationalUnit -Name "Departments" -Path $domain `
       -ProtectedFromAccidentalDeletion:$true
   New-ADOrganizationalUnit -Name "Workstations" -Path $domain `
       -ProtectedFromAccidentalDeletion:$true

   $dept = "OU=Departments,$domain"

   New-ADOrganizationalUnit -Name "IT"    -Path $dept -ProtectedFromAccidentalDeletion:$true
   New-ADOrganizationalUnit -Name "Sales" -Path $dept -ProtectedFromAccidentalDeletion:$true
   New-ADOrganizationalUnit -Name "HR"    -Path $dept -ProtectedFromAccidentalDeletion:$true
   ```

   (Why `ProtectedFromAccidentalDeletion`: prevents a single mis-clicked delete in ADUC from wiping the OU and everything inside. To remove an OU later, clear this flag first.)

2. Optional but recommended: retarget where new accounts and computers land by default.

   ```powershell
   redirusr.exe "OU=Departments,$domain"
   redircmp.exe "OU=Workstations,$domain"
   ```

   - `redirusr` changes the default container for new user objects.
   - `redircmp` changes the default container for new computer objects (so freshly domain-joined workstations drop into `OU=Workstations` instead of `CN=Computers`).
   - This matters because GPOs cannot link to `CN=Users` or `CN=Computers`. Retargeting means new objects start in a policy-targetable OU.

## Verify

```powershell
Get-ADOrganizationalUnit -Filter * |
    Select-Object Name, DistinguishedName |
    Sort-Object DistinguishedName
```

!!! success "Expected output (subset)"
    ```
    Name          DistinguishedName
    ----          -----------------
    Departments   OU=Departments,DC=corp,DC=lab
    HR            OU=HR,OU=Departments,DC=corp,DC=lab
    IT            OU=IT,OU=Departments,DC=corp,DC=lab
    Sales         OU=Sales,OU=Departments,DC=corp,DC=lab
    Workstations  OU=Workstations,DC=corp,DC=lab
    ```

Confirm the redirection targets:

```powershell
(Get-ADDomain).UsersContainer       # OU=Departments,DC=corp,DC=lab
(Get-ADDomain).ComputersContainer   # OU=Workstations,DC=corp,DC=lab
```

## Snapshot

No new snapshot. The structure is cheap to rebuild from the commands above. The next snapshot is after Phase 7.

## Gotchas

!!! danger "Do not name a custom OU `Users`"
    The domain root already has a built-in container `CN=Users`. An `OU=Users` next to it works but is confusing in DN paths and in ADUC. `Departments` makes intent obvious.

!!! warning "GPOs link to OUs, not to containers"
    If you skip `redirusr.exe`, new accounts land in `CN=Users` and no OU-linked GPO will touch them. Either move objects after creation or run `redirusr.exe` once now.

!!! warning "Accidental-deletion protection blocks moves and deletes"
    `Move-ADObject` and `Remove-ADOrganizationalUnit` fail with "access denied" until you clear the flag:

    ```powershell
    Set-ADOrganizationalUnit -Identity "OU=Sales,OU=Departments,DC=corp,DC=lab" `
        -ProtectedFromAccidentalDeletion:$false
    ```

    Set it back when you are done.
