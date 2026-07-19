# Phase 2: Directory structure: OUs, users, AGDLP

**Status:** Done.

**Goal:** Populate the empty domain: the OU tree (`Departments` with `IT`, `Sales`, `HR`, plus `Workstations`), 12 users (4 per department), and the AGDLP group chain (`<Dept>-Staff` Global groups nested into `<Dept>-Share-RW` Domain Local groups).

**What this proves:** I can structure a directory the way delegation and GPO targeting need it, and wire role-based access with AGDLP instead of putting users on ACLs.

## Prerequisites

- Phase 1 complete. `Get-ADDomain` returns `corp.lab`. Snapshot `clean-dc-promoted` taken.
- Lab password chosen. One strong value for all lab accounts.

## Steps

### Part 1: OU tree

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

    `ProtectedFromAccidentalDeletion` blocks a single mis-clicked delete in ADUC from wiping an OU. Clear the flag before any intentional delete.

2. Retarget where new accounts and computers land by default. GPOs cannot link to `CN=Users` or `CN=Computers`, so new objects should start in a policy-targetable OU:

    ```powershell
    redirusr.exe "OU=Departments,$domain"
    redircmp.exe "OU=Workstations,$domain"
    ```

### Part 2: Users

3. Define the password and the user table:

    ```powershell
    $pw = Read-Host -Prompt "Lab password" -AsSecureString
    $domain = "DC=corp,DC=lab"

    $users = @(
        @{ sam="jsmith";  given="J"; sur="Smith";  ou="IT"    },
        @{ sam="jreed";   given="J"; sur="Reed";   ou="IT"    },
        @{ sam="mhale";   given="M"; sur="Hale";   ou="IT"    },
        @{ sam="squinn";  given="S"; sur="Quinn";  ou="IT"    },
        @{ sam="mtate";   given="M"; sur="Tate";   ou="Sales" },
        @{ sam="vcarr";   given="V"; sur="Carr";   ou="Sales" },
        @{ sam="mdunn";   given="M"; sur="Dunn";   ou="Sales" },
        @{ sam="glowe";   given="G"; sur="Lowe";   ou="Sales" },
        @{ sam="dfrost";  given="D"; sur="Frost";  ou="HR"    },
        @{ sam="jcole";   given="J"; sur="Cole";   ou="HR"    },
        @{ sam="tmarsh";  given="T"; sur="Marsh";  ou="HR"    },
        @{ sam="spark";   given="S"; sur="Park";   ou="HR"    }
    )
    ```

4. Create each user in its target OU:

    ```powershell
    foreach ($u in $users) {
        $path = "OU=$($u.ou),OU=Departments,$domain"
        New-ADUser `
            -SamAccountName       $u.sam `
            -Name                 "$($u.given) $($u.sur)" `
            -GivenName            $u.given `
            -Surname              $u.sur `
            -DisplayName          "$($u.given) $($u.sur)" `
            -UserPrincipalName    "$($u.sam)@corp.lab" `
            -AccountPassword      $pw `
            -Path                 $path `
            -Enabled              $true `
            -PasswordNeverExpires $true `
            -ChangePasswordAtLogon $false
    }
    ```

    The UPN lets users sign in as `jsmith@corp.lab` instead of `CORP\jsmith`. Modern Windows prefers UPN form.

### Part 3: Security groups and AGDLP

5. Create the Global "Staff" groups, one per department:

    ```powershell
    $domain = "DC=corp,DC=lab"

    foreach ($ou in "IT","Sales","HR") {
        New-ADGroup `
            -Name        "$ou-Staff" `
            -SamAccountName "$ou-Staff" `
            -GroupCategory Security `
            -GroupScope    Global `
            -Path          "OU=$ou,OU=Departments,$domain" `
            -Description   "Members of the $ou department"
    }
    ```

6. Add each department's users to its Staff group (the **A into G** half of AGDLP):

    ```powershell
    foreach ($ou in "IT","Sales","HR") {
        $members = Get-ADUser -Filter * `
            -SearchBase "OU=$ou,OU=Departments,$domain"
        Add-ADGroupMember -Identity "$ou-Staff" -Members $members
    }
    ```

7. Create the Domain Local resource-access groups. These own the NTFS ACLs on the Phase 5 shares:

    ```powershell
    foreach ($ou in "IT","Sales","HR") {
        New-ADGroup `
            -Name        "$ou-Share-RW" `
            -SamAccountName "$ou-Share-RW" `
            -GroupCategory Security `
            -GroupScope    DomainLocal `
            -Path          "OU=$ou,OU=Departments,$domain" `
            -Description   "Read/Write access to the $ou departmental share"
    }
    ```

8. Nest the Global group inside the matching Domain Local group (the **G into DL** half):

    ```powershell
    foreach ($ou in "IT","Sales","HR") {
        Add-ADGroupMember -Identity "$ou-Share-RW" -Members "$ou-Staff"
    }
    ```

    Permissions assigned to `IT-Share-RW` (the **P**) now reach every user in `IT-Staff`. Phase 5 assigns that permission.

??? info "Why not Universal groups for everything"
    Universal works across domains and is more flexible. The trade-off is that Universal group membership is replicated to every Global Catalog, which makes large memberships expensive. In a single-domain forest the cost is invisible. AGDLP still wins because it forces you to think about role vs resource separately.

## Screenshot

- Capture: ADUC showing the `Departments` tree expanded with users and groups in place. Save as `img/phase-02-ou-tree.png`. Slot reserved, not captured yet.

## Verify

```powershell
Get-ADOrganizationalUnit -Filter * |
    Select-Object Name, DistinguishedName |
    Sort-Object DistinguishedName

(Get-ADDomain).UsersContainer       # OU=Departments,DC=corp,DC=lab
(Get-ADDomain).ComputersContainer   # OU=Workstations,DC=corp,DC=lab

Get-ADUser -Filter * -SearchBase "OU=Departments,DC=corp,DC=lab" `
    -Properties DisplayName, UserPrincipalName, PasswordNeverExpires |
    Select-Object SamAccountName, DisplayName, UserPrincipalName, Enabled, PasswordNeverExpires |
    Sort-Object SamAccountName |
    Format-Table -AutoSize

foreach ($ou in "IT","Sales","HR") {
    $count = (Get-ADUser -Filter * -SearchBase "OU=$ou,OU=Departments,DC=corp,DC=lab").Count
    "$ou : $count users"
}

Get-ADGroup -Filter * -SearchBase "OU=Departments,DC=corp,DC=lab" `
    -Properties GroupScope, GroupCategory |
    Select-Object Name, GroupScope, GroupCategory |
    Sort-Object Name |
    Format-Table -AutoSize

Get-ADGroupMember -Identity IT-Staff    | Select-Object Name, ObjectClass
Get-ADGroupMember -Identity IT-Share-RW | Select-Object Name, ObjectClass
```

!!! success "Expected"
    - OUs: `Departments` with children `HR`, `IT`, `Sales`, plus `Workstations` at the root. Redirection targets show `OU=Departments` and `OU=Workstations`.
    - 12 users, 4 per department OU. `Enabled = True`, `PasswordNeverExpires = True`, UPN form `<sam>@corp.lab`.
    - 6 groups: `IT-Staff`, `IT-Share-RW`, `Sales-Staff`, `Sales-Share-RW`, `HR-Staff`, `HR-Share-RW`. Staff groups are `Global`, Share-RW groups are `DomainLocal`, all `Security`.
    - `IT-Staff` contains the 4 IT users. `IT-Share-RW` contains the single group `IT-Staff`.

## Snapshot

No new snapshot. Everything in this phase is scripted; recreating it is one paste away. Next checkpoint is after Phase 3.

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

!!! warning "`PasswordNeverExpires` is a LAB shortcut"
    In a real environment, password expiry is required by basically every compliance framework. Set it back to its default (`$false`) and use a Fine-Grained Password Policy if you ever migrate this lab to anything real.

!!! warning "SamAccountName cap is 20 characters"
    Old NetBIOS limit, still enforced. UPN can be longer. Keep `SamAccountName` short.

!!! warning "Account name uniqueness"
    `SamAccountName` and `UserPrincipalName` must be unique across the whole forest. If you re-run the script after a partial failure, `New-ADUser` errors on the existing entries; either delete the duplicates or wrap each call in a try/catch.

!!! tip "Bulk operations are easier in PowerShell than ADUC"
    The same loop pattern handles "reset everyone's password", "disable all HR users", "list everyone whose surname starts with M". Get comfortable with it now.

!!! danger "Do not put permissions directly on Global groups"
    Putting an NTFS ACE on `IT-Staff` works but bypasses the model. As soon as you have a second resource (a printer, a different share, an app), you would need to remember every place the Global group sits in an ACL when someone leaves IT. Permissions on the Domain Local only.

!!! warning "Distribution groups grant no access"
    `New-ADGroup -GroupCategory Distribution` produces a mail-list-only group with no SID. CompTIA likes asking you to spot a permission problem caused by someone picking Distribution by mistake.

!!! warning "Group scope is not freely interchangeable"
    You cannot convert Global directly to Domain Local. The legal conversions are Global to Universal and Domain Local to Universal (and the reverse, with member-list restrictions). Pick scope deliberately when you create the group.

!!! tip "Use the same naming convention everywhere"
    The lab uses `<Dept>-Staff` (Global) and `<Dept>-<Resource>-<Access>` (Domain Local). Pick a convention and apply it without exception. Future-you searching ADUC for "who has access to the IT share" will thank present-you.
