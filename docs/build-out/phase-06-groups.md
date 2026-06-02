# Phase 6: Security groups and AGDLP

**Status:** Done.

## Goal

Build the security groups every later phase needs. For each department, a **Global** role-based group (`IT-Staff`, `Sales-Staff`, `HR-Staff`) holding that department's users, and a matching **Domain Local** resource-access group (`IT-Share-RW`, etc.) with the Global group nested inside. The IT chain is fully wired as the AGDLP reference example.

## Why it matters

AGDLP is the model AD was designed around. Following it keeps membership (who is in IT) decoupled from access (what IT can do on this share). When someone leaves IT, you remove them from `IT-Staff`; all permissions follow automatically because permissions are on `IT-Share-RW`, not on the users.

A+ Core 2 angle: 2.2 expects you to know what a security group is, the difference between security and distribution, and the rough idea of group scope. AGDLP is one level above what the exam asks but it makes the answers obvious.

## Prerequisites

- Phase 5 complete. 12 users across `IT`, `Sales`, `HR` OUs.

## Steps

1. Create the Global "Staff" groups, one per department:

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

2. Add each department's users to its Staff group. This populates the **A → G** half of AGDLP.

   ```powershell
   foreach ($ou in "IT","Sales","HR") {
       $members = Get-ADUser -Filter * `
           -SearchBase "OU=$ou,OU=Departments,$domain"
       Add-ADGroupMember -Identity "$ou-Staff" -Members $members
   }
   ```

3. Create the Domain Local resource-access groups. These will eventually own NTFS ACLs on the file shares in Phase 9.

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

4. Nest the Global group inside the matching Domain Local group. This is the **G → DL** half.

   ```powershell
   foreach ($ou in "IT","Sales","HR") {
       Add-ADGroupMember -Identity "$ou-Share-RW" -Members "$ou-Staff"
   }
   ```

   At this point, permissions on a share assigned to `IT-Share-RW` (the **P** in AGDLP) will reach every user inside `IT-Staff`. Phase 9 will assign that permission.

## Verify

```powershell
Get-ADGroup -Filter * -SearchBase "OU=Departments,$domain" `
    -Properties GroupScope, GroupCategory |
    Select-Object Name, GroupScope, GroupCategory |
    Sort-Object Name |
    Format-Table -AutoSize
```

!!! success "Expected"
    6 rows: `IT-Staff`, `IT-Share-RW`, `Sales-Staff`, `Sales-Share-RW`, `HR-Staff`, `HR-Share-RW`. Staff groups are `Global`, Share-RW groups are `DomainLocal`. All are `Security`.

Confirm the AGDLP chain for IT:

```powershell
Get-ADGroupMember -Identity IT-Staff    | Select-Object Name, ObjectClass
Get-ADGroupMember -Identity IT-Share-RW | Select-Object Name, ObjectClass
```

!!! success "Expected"
    - `IT-Staff` contains the 4 IT users (ObjectClass: user).
    - `IT-Share-RW` contains the single group `IT-Staff` (ObjectClass: group).

## Snapshot

No new snapshot. The groups are scripted. Next checkpoint is after Phase 7 (`clean-domain-joined`).

## Gotchas

!!! danger "Do not put permissions directly on Global groups"
    Putting an NTFS ACE on `IT-Staff` works but bypasses the model. As soon as you have a second resource (a printer, a different share, an app), you would need to remember every place the Global group sits in an ACL when someone leaves IT. Permissions on the Domain Local only.

!!! warning "Distribution groups grant no access"
    `New-ADGroup -GroupCategory Distribution` produces a mail-list-only group with no SID. CompTIA likes asking you to spot a permission problem caused by someone picking Distribution by mistake.

!!! warning "Group scope is not freely interchangeable"
    You cannot convert Global directly to Domain Local. The legal conversions are Global → Universal and Domain Local → Universal (and the reverse, with member-list restrictions). Pick scope deliberately when you create the group.

!!! tip "Use the same naming convention everywhere"
    The lab uses `<Dept>-Staff` (Global) and `<Dept>-<Resource>-<Access>` (Domain Local). Pick a convention and apply it without exception. Future-you searching ADUC for "who has access to the IT share" will thank present-you.

??? info "Why not Universal groups for everything"
    Universal works across domains and is more flexible. The trade-off is that Universal group membership is replicated to every Global Catalog, which makes large memberships expensive. In a single-domain forest the cost is invisible. AGDLP still wins because it forces you to think about role vs resource separately.
