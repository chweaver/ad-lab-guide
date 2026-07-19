# Phase 9: Departmental file server

**Status:** Not started. Planned.

**Goal:** Roll the Phase 5 IT-share pattern out to all three departments plus a common share: per-department shares where AGDLP-driven NTFS lets each department write its own share, read nothing else, and everyone reach `Common$`.

**What this proves:** I can design and verify a least-privilege file layout for a whole org, the daily bread of small-business sysadmin work. Supports SY0-701: 4.6 (least privilege, access controls).

## Prerequisites

- Phase 5 complete. `\\DC01\IT$` exists with the AGDLP ACE pattern.
- The six Phase 2 groups exist.

## Steps

1. Create folders and shares for Sales, HR, and Common:

    ```powershell
    foreach ($dept in "Sales","HR","Common") {
        New-Item -Path "C:\Shares\$dept" -ItemType Directory -Force | Out-Null
        New-SmbShare -Name "$dept$" -Path "C:\Shares\$dept" `
            -FullAccess "Administrators" -ChangeAccess "Authenticated Users"
    }
    ```

2. Department shares: Modify for the department's Domain Local group only:

    ```powershell
    foreach ($dept in "Sales","HR") {
        icacls "C:\Shares\$dept" /inheritance:r /grant:r `
            "SYSTEM:(OI)(CI)F" `
            "Administrators:(OI)(CI)F" `
            "$dept-Share-RW:(OI)(CI)M"
    }
    ```

3. Common share: read/write for all three departments through their Domain Local groups (no direct user or Staff-group ACEs):

    ```powershell
    icacls "C:\Shares\Common" /inheritance:r /grant:r `
        "SYSTEM:(OI)(CI)F" `
        "Administrators:(OI)(CI)F" `
        "IT-Share-RW:(OI)(CI)M" `
        "Sales-Share-RW:(OI)(CI)M" `
        "HR-Share-RW:(OI)(CI)M"
    ```

4. Map each department's drive with GPP item-level targeting, extending the Phase 6 `Dept-DriveMaps` GPO: three Mapped Drive items on `S:`, one per department share, each targeted at the matching `<Dept>-Staff` group, plus one `T:` item for `\\DC01\Common$` with no targeting.

## Screenshot

- Capture: one WS01 terminal as `mtate` (Sales) showing `S:` on the Sales share, write success there, and access denied on `\\DC01\HR$`. Save as `img/phase-09-dept-shares.png`. Slot reserved, phase not started.

## Verify

From WS01, once per department (as `jsmith`, `mtate`, `dfrost`):

```powershell
Get-PSDrive S, T | Select-Object Name, DisplayRoot

# Own department: write succeeds
New-Item "\\DC01\Sales$\test-$env:USERNAME.txt" -ItemType File

# Other department: access denied
Get-ChildItem "\\DC01\HR$" -ErrorAction Stop

# Common: write succeeds for everyone
New-Item "\\DC01\Common$\test-$env:USERNAME.txt" -ItemType File
```

!!! success "Pass criteria"
    - Each user's `S:` points at their own department share and `T:` at Common.
    - Own-department write succeeds, cross-department listing is denied, Common write succeeds, for one user from each department.
    - No ACL anywhere names a user or a Staff group directly; every ACE goes through a `*-Share-RW` Domain Local group.

## Snapshot

No snapshot needed. Shares and ACLs are scripted above.

## Gotchas

!!! danger "Permissions go on the Domain Local groups, nothing else"
    The moment one ACE names a user or a Global group directly, offboarding breaks the model. If access looks wrong, audit ACEs first: `icacls C:\Shares\<dept>`.

!!! warning "Same share letter, different targets, needs item-level targeting"
    Three `S:` mappings in one GPO only work because each item targets a different Staff group. Without targeting, last-writer-wins and everyone gets one random share.

!!! warning "Test with one user per department, not just your admin account"
    `corp\Administrator` passes everything through the Administrators ACE and proves nothing about the model.
