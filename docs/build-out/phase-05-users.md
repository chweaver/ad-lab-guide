# Phase 5: Users

**Status:** Done.

## Goal

Create 12 user accounts, four per department OU, with consistent settings. Lab convenience: passwords never expire and the "must change at next logon" flag is off.

## Why it matters

Real AD work happens against users. With dummy users in place you can practice resets, lockouts, group membership changes, and login script behaviour. Without them, every later phase is theoretical.

A+ Core 2 angle: 2.2 expects you to know that user accounts live in AD and that they can be enabled, disabled, reset, and unlocked. This phase gives you 12 targets to practice on.

## Prerequisites

- Phase 4 complete. `OU=Departments,DC=corp,DC=lab` with child OUs `IT`, `Sales`, `HR`.
- Lab password chosen. Use one strong value for all lab accounts.

## Steps

1. From elevated PowerShell on DC01, define the password and the user table:

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

2. Create each user in its target OU:

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

   (Why `UserPrincipalName`: lets the user sign in as `jsmith@corp.lab` instead of `CORP\jsmith`. Modern Windows prefers UPN form.)

## Verify

```powershell
Get-ADUser -Filter * -SearchBase "OU=Departments,DC=corp,DC=lab" `
    -Properties DisplayName, UserPrincipalName, PasswordNeverExpires |
    Select-Object SamAccountName, DisplayName, UserPrincipalName, Enabled, PasswordNeverExpires |
    Sort-Object SamAccountName |
    Format-Table -AutoSize
```

!!! success "Expected"
    12 rows, 4 per department OU. `Enabled = True`, `PasswordNeverExpires = True` on all of them. UPN form is `<sam>@corp.lab`.

Confirm distribution across OUs:

```powershell
foreach ($ou in "IT","Sales","HR") {
    $count = (Get-ADUser -Filter * -SearchBase "OU=$ou,OU=Departments,DC=corp,DC=lab").Count
    "$ou : $count users"
}
```

!!! success "Expected"
    Each of `IT`, `Sales`, `HR` shows 4 users.

## Snapshot

No new snapshot. Users are scripted; recreating them is one paste away.

## Gotchas

!!! warning "`PasswordNeverExpires` is a LAB shortcut"
    In a real environment, password expiry is required by basically every compliance framework. Set it back to its default (`$false`) and use a Fine-Grained Password Policy if you ever migrate this lab to anything real.

!!! warning "SamAccountName cap is 20 characters"
    Old NetBIOS limit, still enforced. UPN can be longer. Keep `SamAccountName` short.

!!! warning "Account name uniqueness"
    `SamAccountName` and `UserPrincipalName` must be unique across the whole forest. If you re-run the script after a partial failure, `New-ADUser` errors on the existing entries; either delete the duplicates or wrap each call in a try/catch.

!!! tip "Bulk operations are easier in PowerShell than ADUC"
    The same loop pattern handles "reset everyone's password", "disable all HR users", "list everyone whose surname starts with M". Get comfortable with it now.
