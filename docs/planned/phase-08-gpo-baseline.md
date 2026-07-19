# Phase 8: GPO security baseline

**Status:** Not started. Planned; first on the list now that A+ is passed and Security+ (SY0-701) is the target.

**Goal:** Replace the lab-convenience defaults with a real security baseline in one GPO set: domain password policy, account lockout, and an audit policy that makes failed logons visible in Event Viewer.

**What this proves:** I can harden a domain with policy instead of per-machine clicks, and produce the audit trail an incident response would need. Supports SY0-701: 4.1 (secure baselines), 4.6 (password and lockout policy), 4.4 (security monitoring and alerting).

## Prerequisites

- Phase 4 complete. Group Policy verified end to end.
- Phase 7 drills done, so the lockout policy from Drill 3 is already in place to build on.

## Steps

### Part 1: Password policy

1. The lab's `PasswordNeverExpires` shortcut from Phase 2 gets retired. In the **Default Domain Policy** (password policy only lives at the domain level for domain accounts), set:

    ```powershell
    Set-ADDefaultDomainPasswordPolicy -Identity corp.lab `
        -MinPasswordLength 12 `
        -PasswordHistoryCount 24 `
        -MaxPasswordAge (New-TimeSpan -Days 365) `
        -MinPasswordAge (New-TimeSpan -Days 1) `
        -ComplexityEnabled $true `
        -ReversibleEncryptionEnabled $false
    ```

2. Clear the per-user shortcut on the lab accounts:

    ```powershell
    Get-ADUser -Filter * -SearchBase "OU=Departments,DC=corp,DC=lab" |
        Set-ADUser -PasswordNeverExpires $false
    ```

### Part 2: Account lockout

3. Keep the Phase 7 Drill 3 values as the baseline, set here for completeness:

    ```powershell
    Set-ADDefaultDomainPasswordPolicy -Identity corp.lab `
        -LockoutThreshold 5 `
        -LockoutDuration (New-TimeSpan -Minutes 15) `
        -LockoutObservationWindow (New-TimeSpan -Minutes 15)
    ```

### Part 3: Audit policy

4. Create a GPO `Baseline-Audit`, link it at the domain root (audit applies to DCs and clients alike). Edit:

    `Computer Configuration > Policies > Windows Settings > Security Settings > Advanced Audit Policy Configuration > Audit Policies`

    - **Logon/Logoff > Audit Logon**: Success and Failure.
    - **Account Logon > Audit Credential Validation**: Success and Failure.
    - **Account Management > Audit User Account Management**: Success and Failure.

5. Force advanced audit policy to win over legacy audit settings:

    `Computer Configuration > Policies > Windows Settings > Security Settings > Local Policies > Security Options > Audit: Force audit policy subcategory settings... ` = **Enabled**.

## Screenshot

- Capture: Event Viewer on DC01 showing a 4740 (lockout) and 4625 (failed logon) pair from the verify test. Save as `img/phase-08-audit-events.png`. Slot reserved, phase not started.

## Verify

```powershell
Get-ADDefaultDomainPasswordPolicy    # all values above reflected

# Deliberately fail 6 logons as mtate on WS01, then:
Search-ADAccount -LockedOut          # mtate listed
Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4740} -MaxEvents 5
Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625} -MaxEvents 5
```

!!! success "Pass criteria"
    - Policy query returns the new minimums.
    - Six bad passwords lock `mtate` out; the account auto-unlocks after 15 minutes.
    - Event 4740 (lockout) appears on DC01 and 4625 (failed logon) records each attempt, proving the audit trail works.

## Snapshot

Take a DC01 snapshot named `pre-baseline` before linking. A wrong lockout threshold at the domain root is the classic way to lock yourself out of your own lab.

## Gotchas

!!! danger "Password policy for domain accounts only works at the domain level"
    A password policy GPO linked to an OU silently does nothing for domain accounts. It only affects local accounts on machines in that OU. Domain-wide policy or a Fine-Grained Password Policy are the two real options.

!!! warning "Lockout threshold of 0 means never lock out"
    Same trap as Phase 7 Drill 3. Confirm with `Get-ADDefaultDomainPasswordPolicy` after any change.

!!! warning "Advanced audit policy and legacy audit policy fight each other"
    Without the "Force audit policy subcategory settings" option enabled, legacy category settings can override the advanced subcategories and your 4625s never appear.
